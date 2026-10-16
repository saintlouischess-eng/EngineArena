from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import time
import chess
import chess.syzygy
import psutil
from .models import Clock,TimeControl,go_command
from .store import Store,SavingError
from .uci import UciEngine,EngineFailure
from .resources import usage,game_cost
from .search_history import SearchHistory,white_info

class Database:
    """One database actor; fsync/PGN/backup never block the chess event loop."""
    def __init__(self):
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='DurableStore');self.store=None;self.pending_moves=[];self.flusher=None
        self.backup_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='RecoveryBackup')
    async def open(self,folder,*,defer_maintenance=False,startup_progress=None):
        self.store=await asyncio.get_running_loop().run_in_executor(self.executor,functools.partial(Store,folder,defer_maintenance=defer_maintenance,startup_progress=startup_progress));return self
    async def call(self,method,*args,**kwargs):
        loop=asyncio.get_running_loop()
        if method=='backup':return await loop.run_in_executor(self.backup_executor,functools.partial(self.store.backup,*args,**kwargs))
        if method=='retry_saving':
            # Verify the backup before clearing a previous saving failure.
            await self.call('backup');kwargs['backup']=False
        needs_backup=method in ('create_tournament','edit_tournament') and kwargs.get('backup',True)
        if method in ('create_tournament','edit_tournament'):kwargs['backup']=False
        result=await loop.run_in_executor(self.executor,functools.partial(getattr(self.store,method),*args,**kwargs))
        if needs_backup:await self.call('backup')
        return result
    async def close(self):
        # Drain cancelled/background backup requests before releasing writer.lock.
        await asyncio.get_running_loop().run_in_executor(self.backup_executor,lambda:None)
        await self.call('close');self.executor.shutdown();self.backup_executor.shutdown()

    async def save_move(self,*args):
        future=asyncio.get_running_loop().create_future();self.pending_moves.append((args,future))
        if self.flusher is None or self.flusher.done():self.flusher=asyncio.create_task(self._flush_moves())
        try:await asyncio.shield(future)
        except asyncio.CancelledError:
            await future
            raise

    async def _flush_moves(self):
        while self.pending_moves:
            await asyncio.sleep(.002)
            batch=self.pending_moves;self.pending_moves=[]
            try:
                await self.call('move_batch',[args for args,_ in batch])
                for _,f in batch:
                    if not f.done():f.set_result(None)
            except Exception as e:
                for _,f in batch:
                    if not f.done():f.set_exception(e)

class Runner:
    def __init__(self,db):
        self.db=db;self.tasks={};self.live={};self.closed=False;self.error='';self.last_backup=time.monotonic();self.scheduler=None
        self.max_active=0;self.completed=0;self.started=time.monotonic();self.memory_budgets={};self.experiment_task=None;self.experiment_id=None;self.backup_task=None
        self.lifecycle_lock=asyncio.Lock();self.maintenance=False
        self.storage_task=None;self.backup_requested=False
        self.admission_scans={};self.resource_probes={}
        self.search_histories={};self.external_resources={}
        from .shared_scheduler import FairShare
        self.fair_share=FairShare();self.scheduling_status={}
        from .runtime_evidence import RunRecorder
        self.runtime=RunRecorder(db)
        from .pgn_output import Outputs
        self.pgn_outputs=Outputs(db)

    async def start(self):
        self.pgn_outputs.task=asyncio.create_task(self.pgn_outputs.loop())
        if self.db.store.startup_pending:
            self.maintenance=True
            self.storage_task=asyncio.create_task(self._finish_startup())
        self.scheduler=asyncio.create_task(self._schedule())

    def resource_usage(self):
        return usage([*self.live.values(),*self.external_resources.values()])

    async def _finish_startup(self):
        from .storage import progress
        async with self.lifecycle_lock:
            try:await self.db.call('finish_startup')
            except Exception as exc:
                self.error=str(exc)
                progress(self.db.store,busy=False,phase='Failed',error=str(exc))
            finally:self.maintenance=False

    def request_backup(self):
        # A committed setup is already durable in SQLite's WAL. A recovery copy
        # must not delay its acknowledgement or turn a successful save into an
        # apparent failure. Coalesce requests, including edits during a copy.
        self.backup_requested=True

    async def _schedule(self):
        while not self.closed:
            try:
                async with self.lifecycle_lock:
                    await self.db.call('export_pending')
                    if self.backup_task and self.backup_task.done():
                        completed_backup=self.backup_task;self.backup_task=None;self.last_backup=time.monotonic()
                        completed_backup.result()
                    from .storage import backup_interval
                    if not self.backup_task and (self.backup_requested or time.monotonic()-self.last_backup>backup_interval(self.db.store.storage_settings,self.db.store.backup_state)):
                        self.backup_requested=False
                        self.backup_task=asyncio.create_task(self.db.call('backup',force=False))
                    if self.error or self.db.store.failure:
                        try:
                            await self.db.call('queue_call','hold','Worker or saving failure. Resolve the error before resuming the queue.')
                            await self.db.call('event_call','hold','Worker or saving failure. Resolve the error before resuming the event.')
                        except SavingError:pass
                        await asyncio.sleep(.25);continue
                    await self.db.call('event_call','tick',{v['tid'] for v in self.live.values()},bool(self.experiment_task and not self.experiment_task.done()))
                    await self.db.call('queue_call','tick',{v['tid'] for v in self.live.values()},bool(self.experiment_task and not self.experiment_task.done()))
                    if self.experiment_task and not self.experiment_task.done():
                        await asyncio.sleep(.1);continue
                    if self.experiment_task and self.experiment_task.done():
                        if not self.experiment_task.cancelled() and self.experiment_task.exception():raise self.experiment_task.exception()
                        self.experiment_task=None;self.experiment_id=None
                    tournaments=await self.db.call('rows',"SELECT id,state FROM tournaments WHERE state IN ('running','draining') ORDER BY created")
                    await self.runtime.update({v['id'] for v in tournaments},{v['tid'] for v in self.live.values()})
                    event_schedule=await self.db.call('event_call','scheduling')
                    shared=(event_schedule['execution_mode']=='parallel') if event_schedule else self.db.store.queue_status.get('execution_mode')=='parallel'
                    if shared:await self._schedule_shared(event_schedule)
                    for item in ([] if shared else tournaments):
                        tid=item['id'];t=await self.db.call('tournament',tid)
                        active=sum(v['tid']==tid for v in self.live.values())
                        if item['state']=='draining':
                            if not active:await self.db.call('set_state',tid,'paused')
                            continue
                        # Queued comparisons share one global budget; first running
                        # tournament completes before the next tournament dispatches.
                        if self.live and any(v['tid']!=tid for v in self.live.values()):break
                        budget=t['settings']['concurrency']
                        if tid not in self.memory_budgets:self.memory_budgets[tid]=int(psutil.virtual_memory().available/2**20*.85)
                        admission=t['settings']|{'memory_budget_mb':t['settings'].get('memory_budget_mb') or self.memory_budgets[tid]}
                        await self.runtime.begin(tid,t['settings'],admission)
                        pairing=await self.db.call('fill_queue',tid,max(4,budget*2),True)
                        if pairing:
                            from .rounds import build_plan
                            plan=await asyncio.to_thread(build_plan,pairing)
                            await self.db.call('apply_round_plan',plan)
                            await self.db.call('fill_queue',tid,max(4,budget*2),True)
                        while len(self.tasks)<budget:
                            used=self.resource_usage()
                            selected=await self.db.call('dispatch',tid,used,admission,self.admission_scans.get(tid))
                            self.admission_scans[tid]=selected['scan']
                            g=selected['game']
                            if not g:
                                # Games can finish while dispatch runs on the DB actor.
                                # A rejection using occupied resources is not evidence
                                # that the remaining games cannot fit an empty machine.
                                if not self.tasks and not used['threads'] and not used['memory_mb'] and not used['gpu'] and selected['exhausted'] and selected['reason']:
                                    await self.db.call('execute',"UPDATE tournaments SET state='paused',note=? WHERE id=?",('No remaining game fits the resource budgets: '+selected['reason']+'. Adjust profile resources or tournament budgets.',tid))
                                break
                            wp=selected['white'];bp=selected['black']
                            self._launch(g,t,wp,bp)
                        snap=await self.db.call('snapshot',tid,0,1)
                        if t['settings']['format']=='sprt' and snap.get('sprt',{}).get('decision') in ('H0','H1') and not snap['sprt_status']['can_diagnostic_start']:
                            await self.db.call('set_state',tid,'draining')
                        if not any(v['tid']==tid for v in self.live.values()):
                            t=await self.db.call('tournament',tid)
                            unfinished=await self.db.call('one',"SELECT count(*) n FROM games WHERE tid=? AND invalid=0 AND state IN ('running','pending')",(tid,))
                            if not unfinished['n'] and t['cursor']*(2 if t['settings']['paired'] else 1)>=t['total'] and t['settings']['format'] not in ('swiss','knockout','double_elimination','ladder'):
                                await self.db.call('execute',"UPDATE tournaments SET state='completed' WHERE id=?",(tid,))
                        if self.tasks:break
                    if not self.tasks and not tournaments and not self.external_resources:
                        experiment=await self.db.call('one',"SELECT id FROM experiments WHERE state='running' ORDER BY created LIMIT 1")
                        if experiment:
                            case=await self.db.call('experiment_claim',experiment['id'])
                            if case:
                                from .experiments import execute
                                self.experiment_id=experiment['id'];self.experiment_task=asyncio.create_task(execute(self.db,case))
            except asyncio.CancelledError:break
            except Exception as e:self.error=str(e)
            await asyncio.sleep(.1)

    def _launch(self,g,t,wp,bp):
        self.live[g['aid']]={'tid':t['id'],'tournament_name':t['name'],'game':g['id'],'number':g['number'],
            'claim_draws':t['settings']['claim_draws'],'fen':g['opening']['fen'],'white':wp,'black':bp,'status':'Starting','ply':0,
            'ponder':t['settings']['ponder'],'resource_cost':game_cost(wp,bp,t['settings']['ponder'])}
        task=asyncio.create_task(self._game(g,t));self.tasks[g['aid']]=task
        task.add_done_callback(lambda task,aid=g['aid']:self._done(aid,task))
        self.max_active=max(self.max_active,len(self.tasks))

    async def _schedule_shared(self,event_schedule=None):
        from .shared_scheduler import EMPTY
        limits=(event_schedule['resources'] if event_schedule else self.db.store.queue_status['resources'])|{'gpu_default_limit':1}
        if not limits.get('cpu_budget'):return
        candidates=await self.db.call('queue_call','candidates')
        self.resource_probes={k:v for k,v in self.resource_probes.items() if k in {c['id'] for c in candidates}}
        active={}
        for view in self.live.values():active[view['tid']]=active.get(view['tid'],0)+1
        self.scheduling_status={k:v for k,v in self.scheduling_status.items() if k in {c['id'] for c in candidates}}
        eligible=[]
        for c in candidates:
            tid=c['id']
            if c['state']=='draining':
                if not active.get(tid):await self.db.call('set_state',tid,'paused')
                self.scheduling_status[tid]='Finishing active games';continue
            if c['dependency']:
                await self.db.call('queue_call','block',tid,c['dependency']);continue
            if active.get(tid,0)>=c['game_limit']:
                self.scheduling_status[tid]='Tournament game limit reached';continue
            eligible.append(c)
        self.fair_share.update(self.live.values(),candidates,limits)
        if self.fair_share.reservation not in {c['id'] for c in eligible}:self.fair_share.reservation=None
        started=time.monotonic();checked=set();cache={};launches=0
        # Bounded scheduler work per pass, independent of the saved queue size.
        while eligible and len(self.tasks)<limits['concurrency'] and launches<32 and time.monotonic()-started<.10:
            available=[c for c in eligible if c['id'] not in checked]
            if not available:break
            c=self.fair_share.order(available)[0];tid=c['id'];self.fair_share.attempted(tid);checked.add(tid)
            reserve=self.fair_share.reservation and self.fair_share.reservation!=tid
            if reserve and len(self.tasks)>=limits['concurrency']-1:
                self.scheduling_status[tid]='Reserving resources for the next game';continue
            if c['state']=='paused':
                await self.db.call('set_state',tid,'running');c['state']='running'
            t=cache.get(tid) or await self.db.call('tournament',tid);cache[tid]=t;s=t['settings']
            budget=s['concurrency']
            if tid not in self.memory_budgets:self.memory_budgets[tid]=int(psutil.virtual_memory().available/2**20*.85)
            local=s|{'memory_budget_mb':s.get('memory_budget_mb') or self.memory_budgets[tid]}
            pairing=await self.db.call('fill_queue',tid,max(4,min(budget,limits['concurrency'])*2),True)
            if pairing:
                from .rounds import build_plan
                plan=await asyncio.to_thread(build_plan,pairing);await self.db.call('apply_round_plan',plan)
                await self.db.call('fill_queue',tid,max(4,min(budget,limits['concurrency'])*2),True)
            used=self.resource_usage();local_used=usage(v for v in self.live.values() if v['tid']==tid)
            admission=limits|{'_local_used':local_used,'_local_limits':local}
            if reserve and self.fair_share.reservation_cost:admission['_reservation_cost']=self.fair_share.reservation_cost
            selected=await self.db.call('dispatch',tid,used,admission,self.admission_scans.get(tid))
            self.admission_scans[tid]=selected['scan'];g=selected['game']
            if g:
                self.resource_probes.pop(tid,None)
                await self.runtime.begin(tid,s,local,shared=limits,priority=c['priority'])
                self._launch(g,t,selected['white'],selected['black']);launches+=1
                self.fair_share.started(tid,self.live[g['aid']]['resource_cost'],limits,c['priority'])
                self.scheduling_status[tid]='Running';active[tid]=active.get(tid,0)+1
                if active[tid]<budget:checked.discard(tid)
            else:
                self.scheduling_status[tid]=selected['reason'] or 'Waiting for pairing or active games'
                if selected['reason'] and selected['exhausted']:
                    probe_limits=limits|{'_local_used':EMPTY,'_local_limits':local}
                    probe=await self.db.call('dispatch',tid,EMPTY,probe_limits,self.resource_probes.get(tid),256,True)
                    self.resource_probes[tid]=probe['scan']
                    if probe['game']:
                        self.fair_share.blocked(tid,game_cost(probe['white'],probe['black'],s['ponder']))
                        if self.fair_share.reservation==tid:
                            self.scheduling_status[tid]='Reserving resources for the next game'
                    elif probe['exhausted'] and probe['reason']:
                        await self.db.call('queue_call','block',tid,'No remaining game fits the resource budgets: '+probe['reason'])
                        if self.fair_share.reservation==tid:self.fair_share.reservation=None
                await self._settle_shared(tid,s)
        if len(self.tasks)>=limits['concurrency']:
            for c in eligible:
                if not active.get(c['id']):self.scheduling_status[c['id']]='Shared game limit reached'

    async def _settle_shared(self,tid,settings):
        if settings['format']=='sprt':
            decision=await self.db.call('one',"SELECT json_extract(body,'$.frozen') frozen FROM sequential_state WHERE tid=?",(tid,))
            if decision and decision['frozen']:
                pending=await self.db.call('one',"SELECT 1 FROM games WHERE tid=? AND invalid=0 AND mode='diagnostic' AND state='pending' LIMIT 1",(tid,))
                if not pending:await self.db.call('set_state',tid,'draining')
        if not any(v['tid']==tid for v in self.live.values()):
            t=await self.db.call('tournament',tid)
            unfinished=await self.db.call('one',"SELECT 1 FROM games WHERE tid=? AND invalid=0 AND state IN ('running','pending') LIMIT 1",(tid,))
            if not unfinished and t['cursor']*(2 if settings['paired'] else 1)>=t['total'] and settings['format'] not in ('swiss','knockout','double_elimination','ladder'):
                await self.db.call('execute',"UPDATE tournaments SET state='completed' WHERE id=?",(tid,))

    def _done(self,aid,task):
        self.tasks.pop(aid,None);self.live.pop(aid,None)
        self.search_histories.pop(aid,None)
        if not task.cancelled() and task.exception():self.error=str(task.exception())

    async def _game(self,g,t):
        aid=g['aid'];s=t['settings'];white=await self.db.call('participant',g['tid'],g['white']);black=await self.db.call('participant',g['tid'],g['black'])
        from .knockout import game_control,game_label
        profiles={chess.WHITE:white,chess.BLACK:black};engines={};clocks={c:Clock(TimeControl.parse(game_control(s,p,g['opening']))) for c,p in profiles.items()}
        board=chess.Board(g['opening']['fen'],chess960=s['chess960']);result='*';reason='interrupted';detail='';identity={};tablebase=None;turn=board.turn;save_failed=False;referee_notes=set()
        elapsed_by_side={}
        from .crown_marks import opening_marks
        crown_marks=opening_marks(g['opening'],s['chess960'])
        recorders=[]
        def clock_snapshot():return {side:clocks[color].snapshot()|{'elapsed':elapsed_by_side.get(side,0)} for side,color in [('white',chess.WHITE),('black',chess.BLACK)]}
        view=self.live.get(aid,{})
        view.update(clocks=clock_snapshot(),clock_active=None,last_move_seconds=elapsed_by_side,searches={},competition_label=game_label(s,g['round'],g['opening']),crown_squares=crown_marks.snapshot(),knight_facings=crown_marks.knight_snapshot(),captured=crown_marks.capture_snapshot())
        self.search_histories[aid]={}
        try:
            await self.db.call('execute','UPDATE attempts SET clocks=? WHERE id=?',(__import__('json').dumps(clock_snapshot()),aid))
            for color in (chess.WHITE,chess.BLACK):
                from .runtime_evidence import EngineRecorder
                turn=color;e=UciEngine(profiles[color],s);engines[color]=e
                recorder=EngineRecorder(self.db,aid,'white' if color else 'black',e,self.runtime.sessions.get(g['tid'],{}).get('id'));recorders.append(recorder);e.runtime_hook=recorder.changed
                await e.start();identity['white' if color else 'black']=e.identity
                def telemetry(info,color=color,engine=e):
                    view=self.live.get(aid)
                    if view and view.get('status')==('White thinking' if color else 'Black thinking') and engine.info_position==view.get('fen'):
                        data=white_info(info,color)
                        side='white' if color else 'black'
                        history=self.search_histories[aid][side];history.record(white_info(engine.last_update,color))
                        view['info']=data;view['info_side']=side
                        view['searches']={**view['searches'],side:{**view['searches'][side],'info':data,'history_revision':history.revision}}
                e.info_hook=telemetry
            if s.get('syzygy_path'):tablebase=chess.syzygy.open_tablebase(s['syzygy_path'])
            streak=[];book_exited=set()
            while True:
                turn=board.turn
                outcome=board.outcome(claim_draw=False)
                if outcome:result=outcome.result();reason=outcome.termination.name.lower();break
                if s['claim_draws'] and (board.is_fifty_moves() or board.is_repetition(3)):
                    result='1/2-1/2';reason='fifty_moves' if board.is_fifty_moves() else 'threefold_repetition';break
                if s['max_plies'] and len(board.move_stack)>=s['max_plies']:result='1/2-1/2';reason='max_plies_adjudication';break
                if tablebase and len(board.piece_map())<=7 and not board.castling_rights:
                    from .referee import syzygy_decision
                    decision=await asyncio.to_thread(syzygy_decision,tablebase,board)
                    if decision['result']:result=decision['result'];reason=decision['reason'];detail=decision['note'];break
                    self.live.get(aid,{})['tablebase_note']=decision['note']
                    if decision['note'] and decision['note'] not in referee_notes:
                        referee_notes.add(decision['note']);await self.db.call('log',aid,['# Referee: '+decision['note']])
                cmd=go_command(clocks[turn],clocks[chess.WHITE],clocks[chess.BLACK])
                view=self.live.get(aid,{})
                side='white' if turn else 'black'
                book=profiles[turn].get('move_book') if s.get('use_engine_books',True) else None
                book_move=None
                # Stop using this profile's book on its first miss. Re-entry is
                # deliberately disabled, making the handoff to search explicit.
                if book and side not in book_exited:
                    absolute_ply=board.ply()
                    if book['max_plies'] and absolute_ply>=book['max_plies']:book_exited.add(side)
                    else:
                        from .move_books import key,choose
                        rows=await self.db.call('book_candidates',book['id'],key(board))
                        book_move=choose(board,rows,book,(s['seed'],g['number'],g['white'] if turn else g['black'],book['id'],key(board),absolute_ply))
                        if book_move is None:book_exited.add(side)
                search={'ply':len(board.move_stack)+1,'move_number':board.fullmove_number,'info':{},'complete':False,'history_revision':0}
                history=SearchHistory();self.search_histories[aid][side]=history
                view.update(status='White thinking' if turn else 'Black thinking',clock_active=side,fen=board.fen(),clocks=clock_snapshot(),search_started=time.monotonic(),command=cmd,info={},info_side=side,searches={**view['searches'],side:search})
                # Preserve clock debt: tolerance is a bound on the overrun, not
                # a fresh allowance for every move after the clock reaches zero.
                if book_move:
                    view.update(status='Playing book move',clock_active=None)
                    view.pop('search_started',None)
                    if engines[turn].pondering:await engines[turn].stop_ponder()
                    engines[turn].ponder_candidate=None
                    move,elapsed,info=book_move,0,{'source':'book','book_id':book['id'],'book_name':book['name'],'book_policy':book['policy']}
                else:move,elapsed,info=await engines[turn].play(board,cmd,None if clocks[turn].budget is None else clocks[turn].budget-s['overhead'])
                history.finish(board.uci(move),info)
                view['searches']={**view['searches'],side:{**search,'info':info,'complete':True,'elapsed':elapsed,'history_revision':history.revision}}
                san=board.san(move);clocks[turn].consume(elapsed,0 if book_move else s['overhead']);crown_marks.advance(board,move);board.push(move)
                view['last_move_seconds']['white' if turn else 'black']=elapsed
                view.pop('search_started',None)
                view.update(clock_active=None,status='Saving move',clocks=clock_snapshot())
                lines=list(engines[turn].log);engines[turn].log.clear()
                await self.db.save_move(aid,len(board.move_stack),move.uci(),san,board.fen(),elapsed,clock_snapshot(),info,lines)
                view.update(fen=board.fen(),ply=len(board.move_stack),last_move=move.uci(),san=san,info=info,clocks=clock_snapshot(),crown_squares=crown_marks.snapshot(),knight_facings=crown_marks.knight_snapshot(),captured=crown_marks.capture_snapshot())
                if s['ponder'] and not book_move:await engines[turn].begin_ponder(board,go_command(clocks[turn],clocks[chess.WHITE],clocks[chess.BLACK]))
                streak.append(info.get('cp'));streak=streak[-max(s['resign_plies'],s['draw_plies']):]
                if s['resign_cp'] and len(streak)>=s['resign_plies']:
                    tail=streak[-s['resign_plies']:]
                    if all(v is not None and v>=s['resign_cp'] for v in tail):result='1-0';reason='resign_adjudication';break
                    if all(v is not None and v<=-s['resign_cp'] for v in tail):result='0-1';reason='resign_adjudication';break
                if s['draw_cp'] and len(board.move_stack)>=s['draw_after'] and len(streak)>=s['draw_plies'] and all(v is not None and abs(v)<=s['draw_cp'] for v in streak[-s['draw_plies']:]):
                    result='1/2-1/2';reason='draw_adjudication';break
        except EngineFailure as e:
            if e.reason=='configuration_changed':
                result='*';reason='interrupted';detail=str(e)
                await self.db.call('execute',"UPDATE tournaments SET state='draining',note=? WHERE id=?",(detail+' Restore the recorded file before resuming.',g['tid']))
            else:result='0-1' if turn else '1-0';reason=e.reason;detail=str(e)
        except asyncio.CancelledError:result='*';reason='interrupted';detail='User cancelled active game; requeued from opening'
        except SavingError as e:save_failed=True;self.error=str(e)
        except Exception as e:result='*';reason='interrupted';detail='Worker error: '+str(e);self.error=detail
        finally:
            # Stop display timing before process shutdown or disk I/O. A failed
            # search spends time but earns no increment or stage bonus.
            started=view.pop('search_started',None)
            if started is not None:
                engine=engines.get(turn)
                elapsed=max(0,time.perf_counter()-engine.search_started) if engine and engine.search_started is not None else max(0,time.monotonic()-started)
                clock=clocks[turn]
                view['last_move_seconds']['white' if turn else 'black']=elapsed
                if clock.tc.clocked:
                    delay=clock.tc.delay if clock.tc.kind in ('delay','bronstein') else 0
                    clock.remaining=max(0,clock.remaining-max(0,elapsed+s['overhead']-delay))
            view.update(clock_active=None,status='Finishing',clocks=clock_snapshot())
            await asyncio.gather(*(e.close() for e in engines.values()),return_exceptions=True)
            if tablebase:tablebase.close()
            captured=await asyncio.gather(*(recorder.close() for recorder in recorders),return_exceptions=True)
            for error in captured:
                if isinstance(error,BaseException):save_failed=True;self.error='Saving engine runtime evidence failed: '+str(error)
            if not save_failed:
                await self.db.call('execute','UPDATE attempts SET clocks=? WHERE id=?',(__import__('json').dumps(clock_snapshot()),aid))
                for e in engines.values():await self.db.call('log',aid,list(e.log))
                await self.db.call('finish',aid,result,reason,detail,identity);await self.db.call('export_pending');self.completed+=1

    async def pause(self,tid,cancel=False):
        await self.db.call('set_state',tid,'draining')
        if cancel:
            tasks=[self.tasks[aid] for aid,v in self.live.items() if v['tid']==tid]
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            await self.db.call('set_state',tid,'paused')

    async def adjudicate(self,tid,gid,aid,result,note):
        # Complete the durable command and process cleanup even if the caller
        # closes its window or disconnects while waiting for the HTTP response.
        return await asyncio.shield(self._adjudicate(tid,gid,aid,result,note))

    async def _adjudicate(self,tid,gid,aid,result,note):
        async with self.lifecycle_lock:
            if not isinstance(aid,str):raise ValueError('Select a running game attempt')
            view=self.live.get(aid);task=self.tasks.get(aid)
            if not view or view['tid']!=tid or view['game']!=gid or not task or task.done() or not view.get('clocks') or view.get('status')=='Finishing':
                raise ValueError('This attempt is starting or already finishing. Refresh the game before adjudicating.')
            await self.db.call('request_adjudication',tid,gid,aid,result,note)
            # finish() reads the committed decision, including after a crash.
            # Never cancel a task already in cleanup: let it commit normally.
            if not task.done() and view.get('status')!='Finishing':task.cancel()
            await asyncio.gather(task,return_exceptions=True)
            attempt=await self.db.call('one','SELECT result,reason,ended FROM attempts WHERE id=?',(aid,))
            if not attempt['ended'] or attempt['reason']!='manual_adjudication':
                raise SavingError(self.error or self.db.store.failure or 'Adjudication is saved but result finalization needs recovery. Stop and retry saving.')
            return {'ok':True,'attempt':aid,'result':attempt['result'],'reason':attempt['reason']}

    async def set_concurrency(self,tid,value):
        # Serialize against dispatch: acknowledgement means no further games
        # can start using the previous limit. Existing tasks finish normally.
        async with self.lifecycle_lock:
            if self.maintenance:raise ValueError('Storage maintenance is in progress')
            if self.db.store.failure:raise SavingError(self.db.store.failure)
            result=await self.db.call('set_concurrency',tid,value)
            return result|{'active':sum(v['tid']==tid for v in self.live.values())}

    def search_detail(self,aid,side):
        if side not in ('white','black'):raise ValueError('Select White or Black')
        view=self.live.get(aid);history=self.search_histories.get(aid,{}).get(side)
        if not view or not history:return {'available':False}
        search=view['searches'][side]
        return history.snapshot()|{'available':True,'attempt':aid,'game':view['game'],'side':side,
          'ply':search['ply'],'move_number':search['move_number'],'complete':search['complete']}

    def status(self):
        memory=psutil.virtual_memory()
        # Even cpu_percent(interval=None) can spend tens of milliseconds inside
        # Windows performance counters. Status polling shares the UCI event loop;
        # use the existing off-thread hardware sample instead of blocking replies.
        hardware=self.runtime.monitor.snapshot() if self.runtime.monitor else {}
        cpu=None if hardware.get('stale',True) else hardware.get('metrics',{}).get('cpu_percent')
        views=[]
        for aid,v in self.live.items():
            item=dict(v);item['attempt']=aid;item['search_elapsed']=max(0,time.monotonic()-v['search_started']) if 'search_started' in v else 0;views.append(item)
        return {'live':views,'scheduling':{'used':self.resource_usage(),'waiting':dict(self.scheduling_status)},'player_active':bool(self.external_resources),'maintenance':self.maintenance,'error':self.error or self.db.store.failure,'cpu_percent':cpu,
          'memory_used_gb':round(memory.used/2**30,2),'memory_available_gb':round(memory.available/2**30,2),'logical_cpus':psutil.cpu_count(),
          'active_games':len(self.tasks),'max_active_games':self.max_active,'engine_process_bound':2*len(self.tasks),
          'games_finished':self.completed,'uptime':time.monotonic()-self.started,'pgn_outputs':list(self.pgn_outputs.status.values()),
          'backup':dict(self.db.store.backup_state)|{'retention':self.db.store.storage_settings['backup_copies'],'minimum_minutes':self.db.store.storage_settings['backup_minutes']}}

    async def delete_tournament(self,tid,name,keep_ratings=True):
        async with self.lifecycle_lock:
            if self.tasks or (self.experiment_task and not self.experiment_task.done()):
                raise ValueError('Stop or pause and drain all tournaments and experiments before deleting a tournament')
            self.maintenance=True
            try:
                await self.pgn_outputs.flush()
                if self.backup_task:
                    await self.backup_task;self.backup_task=None
                result=await self.db.call('delete_tournament',tid,name,keep_ratings)
                self.memory_budgets.pop(tid,None)
                self.admission_scans.pop(tid,None)
                return result
            finally:self.maintenance=False

    async def delete_events(self,ids,expected,keep_ratings=True):
        async with self.lifecycle_lock:
            if self.tasks or (self.experiment_task and not self.experiment_task.done()):
                raise ValueError('Stop or pause and drain all tournaments and experiments before deleting records.')
            self.maintenance=True
            try:
                await self.pgn_outputs.flush()
                if self.backup_task:
                    await self.backup_task;self.backup_task=None
                result=await self.db.call('event_call','delete_events',ids,expected,keep_ratings)
                for row in result['stages']:
                    self.memory_budgets.pop(row['tid'],None);self.admission_scans.pop(row['tid'],None)
                return result
            finally:self.maintenance=False

    async def optimize_storage(self):
        async with self.lifecycle_lock:
            if self.tasks or (self.experiment_task and not self.experiment_task.done()):
                raise ValueError('Stop or pause and drain all tournaments and experiments before storage maintenance')
            from .storage import ensure_idle
            await asyncio.get_running_loop().run_in_executor(self.db.executor,ensure_idle,self.db.store)
            self.maintenance=True
            try:
                if self.backup_task:
                    await self.backup_task;self.backup_task=None
                result=await self.db.call('optimize_storage')
                if self.error.startswith(('Storage cleanup did not finish:','Tournament deletion cleanup failed:','Backup saving failed:')):self.error=''
                self.last_backup=time.monotonic()
                return result
            finally:self.maintenance=False

    async def close(self):
        self.closed=True
        if self.storage_task:await asyncio.gather(self.storage_task,return_exceptions=True)
        if self.scheduler:self.scheduler.cancel();await asyncio.gather(self.scheduler,return_exceptions=True)
        if self.experiment_task:
            self.experiment_task.cancel();await asyncio.gather(self.experiment_task,return_exceptions=True)
        for task in list(self.tasks.values()):task.cancel()
        await asyncio.gather(*list(self.tasks.values()),return_exceptions=True)
        try:
            await self.runtime.close()
            if self.backup_task:await asyncio.gather(self.backup_task,return_exceptions=True)
            await self.db.call('backup',force=False)
        finally:
            await self.pgn_outputs.close()
            await self.db.close()
