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
from .resources import game_cost,fits,usage

class Database:
    """One database actor; fsync/PGN/backup never block the chess event loop."""
    def __init__(self):
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='DurableStore');self.store=None;self.pending_moves=[];self.flusher=None
        self.backup_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='RecoveryBackup')
    async def open(self,folder):
        self.store=await asyncio.get_running_loop().run_in_executor(self.executor,Store,folder);return self
    async def call(self,method,*args,**kwargs):
        loop=asyncio.get_running_loop()
        if method=='backup':return await loop.run_in_executor(self.backup_executor,functools.partial(self.store.backup,*args,**kwargs))
        if method=='retry_saving':
            # Verify the backup before clearing a previous saving failure.
            await self.call('backup');kwargs['backup']=False
        if method=='create_tournament':kwargs['backup']=False
        result=await loop.run_in_executor(self.executor,functools.partial(getattr(self.store,method),*args,**kwargs))
        if method=='create_tournament':await self.call('backup')
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

    async def start(self):self.scheduler=asyncio.create_task(self._schedule())

    async def _schedule(self):
        while not self.closed:
            try:
                async with self.lifecycle_lock:
                    await self.db.call('export_pending')
                    if self.backup_task and self.backup_task.done():
                        completed_backup=self.backup_task;self.backup_task=None;self.last_backup=time.monotonic()
                        completed_backup.result()
                    backup_interval=max(60,min(900,10*(self.db.store.backup_state.get('duration_seconds') or 0)))
                    if not self.backup_task and time.monotonic()-self.last_backup>backup_interval:
                        self.backup_task=asyncio.create_task(self.db.call('backup',force=False))
                    if self.error or self.db.store.failure:
                        await asyncio.sleep(.25);continue
                    if self.experiment_task and not self.experiment_task.done():
                        await asyncio.sleep(.1);continue
                    if self.experiment_task and self.experiment_task.done():
                        if not self.experiment_task.cancelled() and self.experiment_task.exception():raise self.experiment_task.exception()
                        self.experiment_task=None;self.experiment_id=None
                    tournaments=await self.db.call('rows',"SELECT id,state FROM tournaments WHERE state IN ('running','draining') ORDER BY created")
                    for item in tournaments:
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
                        pairing=await self.db.call('fill_queue',tid,max(4,budget*2),True)
                        if pairing:
                            from .rounds import build_plan
                            plan=await asyncio.to_thread(build_plan,pairing)
                            await self.db.call('apply_round_plan',plan)
                            await self.db.call('fill_queue',tid,max(4,budget*2),True)
                        while len(self.tasks)<budget:
                            next_game=await self.db.call('one',"SELECT * FROM games WHERE tid=? AND state='pending' AND invalid=0 ORDER BY number LIMIT 1",(tid,))
                            if not next_game:break
                            wp=await self.db.call('participant',tid,next_game['white']);bp=await self.db.call('participant',tid,next_game['black'])
                            allowed,why=fits(game_cost(wp,bp,t['settings']['ponder']),usage(self.live.values(),t['settings']['ponder']),admission)
                            if not allowed:
                                if not self.tasks:
                                    await self.db.call('execute',"UPDATE tournaments SET state='paused',note=? WHERE id=?",('Cannot start one game: '+why+'. Adjust profile resources or tournament budgets.',tid))
                                break
                            g=await self.db.call('claim',tid)
                            if not g:break
                            self.live[g['aid']]={'tid':tid,'game':g['id'],'number':g['number'],'fen':g['opening']['fen'],'white':wp,'black':bp,'status':'Starting','ply':0}
                            task=asyncio.create_task(self._game(g,t));self.tasks[g['aid']]=task
                            task.add_done_callback(lambda task,aid=g['aid']:self._done(aid,task))
                            self.max_active=max(self.max_active,len(self.tasks))
                        snap=await self.db.call('snapshot',tid,0,1)
                        if t['settings']['format']=='sprt' and snap.get('sprt',{}).get('decision') in ('H0','H1'):
                            await self.db.call('set_state',tid,'draining')
                        if not any(v['tid']==tid for v in self.live.values()):
                            t=await self.db.call('tournament',tid)
                            unfinished=await self.db.call('one',"SELECT count(*) n FROM games WHERE tid=? AND invalid=0 AND state IN ('running','pending')",(tid,))
                            if not unfinished['n'] and t['cursor']*(2 if t['settings']['paired'] else 1)>=t['total'] and t['settings']['format'] not in ('swiss','knockout','double_elimination','ladder'):
                                await self.db.call('execute',"UPDATE tournaments SET state='completed' WHERE id=?",(tid,))
                        if self.tasks:break
                    if not self.tasks and not tournaments:
                        experiment=await self.db.call('one',"SELECT id FROM experiments WHERE state='running' ORDER BY created LIMIT 1")
                        if experiment:
                            case=await self.db.call('experiment_claim',experiment['id'])
                            if case:
                                from .experiments import execute
                                self.experiment_id=experiment['id'];self.experiment_task=asyncio.create_task(execute(self.db,case))
            except asyncio.CancelledError:break
            except Exception as e:self.error=str(e)
            await asyncio.sleep(.1)

    def _done(self,aid,task):
        self.tasks.pop(aid,None);self.live.pop(aid,None)
        if not task.cancelled() and task.exception():self.error=str(task.exception())

    async def _game(self,g,t):
        aid=g['aid'];s=t['settings'];white=await self.db.call('participant',g['tid'],g['white']);black=await self.db.call('participant',g['tid'],g['black'])
        profiles={chess.WHITE:white,chess.BLACK:black};engines={};clocks={c:Clock(TimeControl.parse(p.get('time_control') or s['time_control'])) for c,p in profiles.items()}
        board=chess.Board(g['opening']['fen'],chess960=s['chess960']);result='*';reason='interrupted';detail='';identity={};tablebase=None;turn=board.turn;save_failed=False;referee_notes=set()
        elapsed_by_side={}
        def clock_snapshot():return {side:clocks[color].snapshot()|{'elapsed':elapsed_by_side.get(side,0)} for side,color in [('white',chess.WHITE),('black',chess.BLACK)]}
        view=self.live.get(aid,{})
        view.update(clocks=clock_snapshot(),clock_active=None,last_move_seconds=elapsed_by_side,searches={})
        try:
            await self.db.call('execute','UPDATE attempts SET clocks=? WHERE id=?',(__import__('json').dumps(clock_snapshot()),aid))
            for color in (chess.WHITE,chess.BLACK):
                turn=color;e=UciEngine(profiles[color],s);engines[color]=e;await e.start();identity['white' if color else 'black']=e.identity
                def telemetry(info,color=color):
                    view=self.live.get(aid)
                    if view and view.get('status')==('White thinking' if color else 'Black thinking'):
                        data=dict(info)
                        for key in ('cp','mate'):
                            if key in data:data[key]*=1 if color else -1
                        if 'wdl' in data and not color:data['wdl']=list(reversed(data['wdl']))
                        side='white' if color else 'black'
                        view['info']=data;view['info_side']=side
                        view['searches']={**view['searches'],side:{**view['searches'][side],'info':data}}
                e.info_hook=telemetry
            if s.get('syzygy_path'):tablebase=chess.syzygy.open_tablebase(s['syzygy_path'])
            streak=[]
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
                search={'ply':len(board.move_stack)+1,'move_number':board.fullmove_number,'info':{},'complete':False}
                view.update(status='White thinking' if turn else 'Black thinking',clock_active=side,fen=board.fen(),clocks=clock_snapshot(),search_started=time.monotonic(),command=cmd,info={},info_side=side,searches={**view['searches'],side:search})
                move,elapsed,info=await engines[turn].play(board,cmd,None if clocks[turn].budget is None else max(0,clocks[turn].budget-s['overhead']))
                view['searches']={**view['searches'],side:{**search,'info':info,'complete':True,'elapsed':elapsed}}
                san=board.san(move);clocks[turn].consume(elapsed,s['overhead']);board.push(move)
                view['last_move_seconds']['white' if turn else 'black']=elapsed
                view.pop('search_started',None)
                view.update(clock_active=None,status='Saving move',clocks=clock_snapshot())
                lines=list(engines[turn].log);engines[turn].log.clear()
                await self.db.save_move(aid,len(board.move_stack),move.uci(),san,board.fen(),elapsed,clock_snapshot(),info,lines)
                view.update(fen=board.fen(),ply=len(board.move_stack),last_move=move.uci(),san=san,info=info,clocks=clock_snapshot())
                if s['ponder']:await engines[turn].begin_ponder(board,go_command(clocks[turn],clocks[chess.WHITE],clocks[chess.BLACK]))
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
                elapsed=max(0,time.monotonic()-started);clock=clocks[turn]
                view['last_move_seconds']['white' if turn else 'black']=elapsed
                if clock.tc.clocked:
                    delay=clock.tc.delay if clock.tc.kind in ('delay','bronstein') else 0
                    clock.remaining=max(0,clock.remaining-max(0,elapsed+s['overhead']-delay))
            view.update(clock_active=None,status='Finishing',clocks=clock_snapshot())
            await asyncio.gather(*(e.close() for e in engines.values()),return_exceptions=True)
            if tablebase:tablebase.close()
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

    def status(self):
        memory=psutil.virtual_memory()
        views=[]
        for v in self.live.values():
            item=dict(v);item['search_elapsed']=max(0,time.monotonic()-v['search_started']) if 'search_started' in v else 0;views.append(item)
        return {'live':views,'maintenance':self.maintenance,'error':self.error or self.db.store.failure,'cpu_percent':psutil.cpu_percent(),
          'memory_used_gb':round(memory.used/2**30,2),'memory_available_gb':round(memory.available/2**30,2),'logical_cpus':psutil.cpu_count(),
          'active_games':len(self.tasks),'max_active_games':self.max_active,'engine_process_bound':2*len(self.tasks),
          'games_finished':self.completed,'uptime':time.monotonic()-self.started,
          'backup':dict(self.db.store.backup_state)}

    async def delete_tournament(self,tid,name):
        async with self.lifecycle_lock:
            if self.tasks or (self.experiment_task and not self.experiment_task.done()):
                raise ValueError('Stop or pause and drain all tournaments and experiments before deleting a tournament')
            self.maintenance=True
            try:
                if self.backup_task:
                    await self.backup_task;self.backup_task=None
                result=await self.db.call('delete_tournament',tid,name)
                self.memory_budgets.pop(tid,None)
                return result
            finally:self.maintenance=False

    async def close(self):
        self.closed=True
        if self.scheduler:self.scheduler.cancel();await asyncio.gather(self.scheduler,return_exceptions=True)
        if self.experiment_task:
            self.experiment_task.cancel();await asyncio.gather(self.experiment_task,return_exceptions=True)
        for task in list(self.tasks.values()):task.cancel()
        await asyncio.gather(*list(self.tasks.values()),return_exceptions=True)
        try:
            if self.backup_task:await asyncio.gather(self.backup_task,return_exceptions=True)
            await self.db.call('backup',force=False)
        finally:await self.db.close()
