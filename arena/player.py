"""Server-authoritative human play. No UI timer decides a result."""
from __future__ import annotations
import asyncio
import copy
import json
import time
import chess
from .models import Clock, TimeControl, go_command
from .uci import UciEngine, EngineFailure
from .store import DEFAULTS
from .resources import fits, thread_count, option
from .crown_marks import CrownMarks
from .search_history import SearchHistory, white_info


def rebuild(game):
    board=chess.Board(game['config']['fen'],chess960=game['config']['chess960']);marks=CrownMarks(board)
    for record in game['moves']:
        move=board.parse_uci(record['uci']);marks.advance(board,move);board.push(move)
    return board,marks


def restore_clock(saved):
    clock=Clock(TimeControl.parse(saved['control']))
    clock.remaining=saved['remaining'] if saved['remaining'] is not None else clock.remaining
    clock.stage=saved['stage'];clock.moves=saved['moves'];return clock


class PlayerArena:
    def __init__(self,db,runner):
        self.db=db;self.runner=runner;self.game=None;self.board=chess.Board();self.marks=CrownMarks(self.board)
        self.lock=asyncio.Lock();self.engine=None;self.task=None;self.turn_started=None;self.closed=False
        self.tick=None;self.exporter=None;self.last_checkpoint=0;self.error='';self.info={};self.hint=None;self.history=SearchHistory();self.search_board=None

    async def start(self):
        self.game=await self.db.call('player_call','recover')
        if self.game:self.board,self.marks=rebuild(self.game)
        self.tick=asyncio.create_task(self._tick())
        self.exporter=asyncio.create_task(self._exports())

    async def _exports(self):
        while not self.closed:
            try:
                if not self.db.store.failure:await self.db.call('player_call','retry_exports')
                await asyncio.sleep(30)
            except asyncio.CancelledError:break
            except Exception as exc:
                self.error='Player PGN saving failed: '+str(exc)
                await asyncio.sleep(30)

    @property
    def human(self):return self.game['config']['color']=='white'

    def elapsed(self,at=None):
        return self.game.get('turn_elapsed',0)+(max(0,(time.monotonic() if at is None else at)-self.turn_started) if self.turn_started is not None else 0)

    def clocks(self):return {s:restore_clock(c) for s,c in self.game['clocks'].items()}

    def view(self):
        if not self.game:return {'game':None,'error_message':self.error}
        g=self.game;clocks=self.clocks();side='white' if self.board.turn else 'black';elapsed=self.elapsed()
        legal=[]
        if g['state']=='playing' and self.board.turn==self.human:
            for move in self.board.legal_moves:
                target=chess.square_name(move.to_square)
                if self.board.is_castling(move):target=chess.square_name(chess.square(6 if self.board.is_kingside_castling(move) else 2,chess.square_rank(move.from_square)))
                legal.append({'uci':move.uci(),'from':chess.square_name(move.from_square),'to':target,'promotion':chess.piece_symbol(move.promotion) if move.promotion else ''})
                if self.board.chess960 and self.board.is_castling(move) and target!=chess.square_name(move.to_square):
                    legal.append({'uci':move.uci(),'from':chess.square_name(move.from_square),'to':chess.square_name(move.to_square),'promotion':''})
        public={k:g[k] for k in ('id','series','number','name','state','revision','created','fen','moves','clocks','rated','result','reason','note','config','category','rating_change','draw_offer')}
        public.update(engine={'name':g['engine']['name'],'identity':g.get('identity',g['engine'].get('identity',{})), 'move_book':g['engine'].get('move_book') if 'book_mode' in g['config'] else None},
            turn=side,turn_elapsed=elapsed,legal=legal,check=self.board.is_check(),claim_draw=self.board.can_claim_draw(),
            crown_squares=self.marks.snapshot(),knight_facings=self.marks.knight_snapshot(),captured=self.marks.capture_snapshot(),
            hint=self.hint,hint_busy=bool(self.board.turn==self.human and self.task and not self.task.done() and g['state']=='playing'),search=self.thinking() if g.get('analysis',False) else {},analysis=g.get('analysis',False),sessions=g['sessions'])
        return {'game':public,'error_message':self.error,'export_error':getattr(self.db.store,'player_export_error','')}

    def thinking(self):
        def pv(info):
            board=self.search_board.copy() if self.search_board else self.board.copy();words=[]
            for uci in info.get('pv','').split():
                try:
                    move=board.parse_uci(uci);words.append((str(board.fullmove_number)+('. ' if board.turn else '… ') if board.turn or not words else '')+board.san(move));board.push(move)
                except ValueError:break
            return ' '.join(words)
        current=self.history.snapshot()
        return {'info':self.info,'pv':pv(self.info),'history':[{'number':r['number'],'move':pv({'pv':r['move']}),'info':r['info']} for r in current['history']],
                'changes':current['changes'],'omitted':current['omitted'],'log':list(self.engine.log) if self.engine else self.game.get('engine_log',[])}

    async def persist(self, *, checkpoint=False):
        self.game['fen']=self.board.fen()
        if self.engine:self.game['engine_log']=list(self.engine.log)
        try:self.game=await self._save(checkpoint)
        except Exception as exc:
            self.hold_clock();self.error='Player saving failed: '+str(exc)
            await self._close_engine()
            # Discard the uncommitted move/clock change, including an apparent mate.
            # A read is safe after a rolled-back write; never continue from memory alone.
            try:
                saved=await self.db.call('player_call','get',self.game['id'])
                self.game=saved;self.board,self.marks=rebuild(saved)
            except Exception:
                self.error+='; the committed position is unavailable. Restart after resolving storage.'
                self.game['storage_blocked']=True
            if self.game['state'] not in ('completed','abandoned'):self.game.update(state='paused',rated=False,note=self.error)
            raise
        self.last_checkpoint=time.monotonic();self.runner.request_backup() if self.game['state'] in ('completed','abandoned') else None

    async def _save(self,checkpoint):
        # player_call keeps all mutations on the existing DB actor.
        body=copy.deepcopy(self.game)
        if checkpoint:body['turn_elapsed']=self.elapsed()
        saved=await self.db.call('player_call','save',body,self.game['revision'],checkpoint)
        if checkpoint:saved['turn_elapsed']=self.game['turn_elapsed']
        return saved

    async def create(self, body, sid=None):
        async with self.lock:
            self.game=await self.db.call('player_call','next',sid) if sid else await self.db.call('player_call','create',body)
            self.board,self.marks=rebuild(self.game);self.turn_started=None;self.info={};self.hint=None;self.error='';self.history=SearchHistory();self.search_board=None
            self.runner.request_backup();return self.view()

    async def reserve(self):
        p=self.game['engine'];cost={'threads':thread_count(p),'memory_mb':int(option(p,'Hash',256))+int(p.get('extra_memory_mb',256)),
                                  'gpu':{p['gpu_group']:1} if p.get('gpu_group') else {}}
        async with self.runner.lifecycle_lock:
            if self.runner.maintenance or self.db.store.failure:raise ValueError('Resolve storage maintenance or saving failures before playing')
            if self.runner.experiment_task and not self.runner.experiment_task.done():raise ValueError('Wait for the active benchmark or suite before playing')
            event=await self.db.call('event_call','scheduling')
            limits=(event['resources'] if event else self.db.store.queue_status.get('resources',{})) or {}
            limits=limits|{'gpu_default_limit':1}
            used=self.runner.resource_usage()
            checks=[limits]
            if not event and self.db.store.queue_status.get('execution_mode')!='parallel':
                for row in await self.db.call('rows',"SELECT settings FROM tournaments WHERE state IN ('running','draining')"):
                    checks.append(json.loads(row['settings']))
            for limit in checks:
                ok,reason=fits(cost,used,limit)
                if not ok:raise ValueError('Player Arena is waiting for resources: '+reason+'. Reduce engine resources or pause and drain testing.')
            self.runner.external_resources['player']={'resource_cost':cost}

    async def resume(self):
        if self.game['state']!='paused':raise ValueError('This game is not paused')
        if self.game.get('storage_blocked'):raise ValueError(self.error)
        await self.reserve()
        self.error=''
        self.game['state']='starting';self.game['note']='Preparing the engine…';self.info={};self.hint=None
        try:await self.persist()
        except BaseException:self.runner.external_resources.pop('player',None);raise
        self.task=asyncio.create_task(self._prepare())

    async def _prepare(self):
        g=self.game;s=DEFAULTS|{'ponder':False,'chess960':g['config']['chess960'],'tolerance':g['config']['tolerance'],'hang_timeout':g['config']['hang_timeout']}
        engine=UciEngine(g['engine'],s);self.engine=engine
        try:
            await engine.start()
            async with self.lock:
                g=self.game;g['identity']=engine.identity;g['sessions'].append({'time':time.time(),'action':'engine_started','ply':len(g['moves']),'identity':engine.identity})
                g['state']='playing';g['note']='Your move.' if self.board.turn==self.human else 'Engine is thinking…'
                await self.persist();self.turn_started=time.monotonic();self.task=None
                if self.board.turn!=self.human:self.task=asyncio.create_task(self._engine_turn())
        except asyncio.CancelledError:raise
        except Exception as exc:await self._fault(exc)

    async def _fault(self, exc):
        async with self.lock:
            self.hold_clock();g=self.game
            g['state']='paused';g['rated']=False;g['draw_offer']=False;g['note']='Engine stopped: '+str(exc)+'. The position is saved; resume or abandon the game.'
            g['sessions'].append({'time':time.time(),'action':'engine_failure','reason':getattr(exc,'reason','error'),'detail':str(exc),'ply':len(g['moves'])})
            self.error=g['note']
            try:await self.persist()
            except Exception as saving:self.error='Player saving failed: '+str(saving)
            await self._close_engine(cancel=False)

    def hold_clock(self):
        if self.game and self.turn_started is not None:self.game['turn_elapsed']=self.elapsed()
        self.turn_started=None

    async def _close_engine(self, *, cancel=True):
        task=self.task;self.task=None
        if cancel and task and task is not asyncio.current_task():
            task.cancel();await asyncio.gather(task,return_exceptions=True)
        engine=self.engine;self.engine=None
        try:
            if engine:await engine.close()
        finally:self.runner.external_resources.pop('player',None)

    async def finish(self, result, reason, note=''):
        self.hold_clock();self.game.update(state='completed',result=result,reason=reason,note=note or reason.replace('_',' '),draw_offer=False)
        await self.persist();await self._close_engine()

    async def timeout(self):
        loser=self.board.turn;winner=not loser
        result='1/2-1/2' if self.board.has_insufficient_material(winner) else '1-0' if winner else '0-1'
        await self.finish(result,'timeout','Time expired.' if result!='1/2-1/2' else 'Time expired; opponent has insufficient mating material.')

    async def push(self, move, elapsed, info):
        side='white' if self.board.turn else 'black';clocks=self.clocks();clocks[side].consume(elapsed)
        san=self.board.san(move);capture=self.board.is_capture(move);castle=self.board.is_castling(move);fullmove=self.board.fullmove_number
        before={'clocks':copy.deepcopy(self.game['clocks']),'elapsed':self.game['turn_elapsed']}
        self.marks.advance(self.board,move);self.board.push(move);self.hint=None
        self.game['clocks']={s:c.snapshot() for s,c in clocks.items()};self.game['turn_elapsed']=0;self.turn_started=None
        self.game['moves'].append({'uci':move.uci(),'san':san,'fen':self.board.fen(),'elapsed':elapsed,'clocks':copy.deepcopy(self.game['clocks']),
            'info':info,'before':before,'capture':capture,'castle':castle,'check':self.board.is_check(),'fullmove':fullmove,'side':side})
        outcome=self.board.outcome(claim_draw=False)
        if outcome:await self.finish(outcome.result(),outcome.termination.name.lower());return
        self.game['note']='Your move.' if self.board.turn==self.human else 'Engine is thinking…'
        await self.persist();self.turn_started=time.monotonic()

    async def _engine_turn(self):
        engine=self.engine
        try:
            clocks=self.clocks();side='white' if self.board.turn else 'black';base=self.game['turn_elapsed'];active=clocks[side]
            budget=None if active.budget is None else active.budget-base
            # Advertise the unused part of an interrupted search without granting a new delay.
            if active.tc.clocked:active.remaining-=base
            self.search_board=self.board.copy();self.history=SearchHistory();self.info={}
            def update(info):
                self.info=white_info(info,self.search_board.turn);self.history.record(self.info)
            engine.info_hook=update
            # The saved mainline is the durable book-exit record. It also makes
            # takebacks and crash recovery return to the correct book state.
            book=self.game['engine'].get('move_book') if 'book_mode' in self.game['config'] else None;move=None
            exited=any(m['side']!=self.game['config']['color'] and m['info'].get('source')!='book' for m in self.game['moves'])
            if book and not exited and not self.game['draw_offer'] and (not book['max_plies'] or self.board.ply()<book['max_plies']):
                from .move_books import key,choose
                rows=await self.db.call('book_candidates',book['id'],key(self.board))
                move=choose(self.board,rows,book,(self.game['id'],book['id'],key(self.board),self.board.ply()))
            if move:
                elapsed=0;info={'source':'book','book_id':book['id'],'book_name':book['name'],'book_policy':book['policy']}
                self.info=info|{'pv':move.uci()}
            else:
                move,elapsed,info=await engine.play(self.board.copy(),go_command(active,clocks['white'],clocks['black']),budget)
            async with self.lock:
                if self.game['state']!='playing':return
                # Arrival timestamps from UCI, not UI polling or durable-store latency, govern the clock.
                spent=base+elapsed
                if self.game['draw_offer']:
                    policy=self.game['config']['draw_policy'];threshold=self.game['config']['draw_cp']
                    accepted=policy=='always' or (policy=='balanced' and info.get('depth',0)>=8 and 'cp' in info and abs(info['cp'])<=threshold and info.get('score_bound') not in ('lowerbound','upperbound'))
                    self.game['draw_offer']=False
                    if accepted:
                        self.game['sessions'].append({'action':'draw_accepted_by_policy','time':time.time(),'cp':info.get('cp'),'depth':info.get('depth')})
                        await self.finish('1/2-1/2','draw_agreement','Draw accepted by the configured Player Arena policy.');return
                    self.game['sessions'].append({'action':'draw_declined','time':time.time(),'ply':len(self.game['moves'])})
                # Engines can exercise a legal claim without making an artificial evaluation adjudication.
                if self.board.can_claim_draw():await self.finish('1/2-1/2','draw_claim','Engine claims a legal draw.');return
                await self.push(move,spent,info)
                if self.game['state']=='playing':self.task=None
        except asyncio.CancelledError:raise
        except EngineFailure as exc:
            if exc.reason=='timeout':
                async with self.lock:await self.timeout()
            else:await self._fault(exc)
        except Exception as exc:await self._fault(exc)

    async def action(self, body):
        received=time.monotonic()
        async with self.lock:
            if not self.game:raise ValueError('Start a Player Arena game first')
            if body.get('id')!=self.game['id'] or body.get('revision')!=self.game['revision']:raise ValueError('The game changed. Refresh before trying again.')
            action=body['action'];g=self.game
            if g['state'] in ('completed','abandoned'):raise ValueError('This game has ended')
            if action=='analysis':
                g['analysis']=bool(body.get('enabled'))
                if g['analysis']:g['rated']=False;g['note']='Engine analysis enabled. This game is now casual.'
                await self.persist();return self.view()
            if action=='resume':await self.resume();return self.view()
            if action=='pause':
                self.hold_clock();g.update(state='paused',rated=False,note='Paused. Resume when ready; this game is now casual.',draw_offer=False)
                g['sessions'].append({'action':'paused','time':time.time(),'ply':len(g['moves'])});await self.persist();await self._close_engine();return self.view()
            if action=='abandon':
                self.hold_clock();g.update(state='abandoned',result='*',reason='abandoned',rated=False,note='Game abandoned.',draw_offer=False)
                await self.persist();await self._close_engine();return self.view()
            if action=='resign':await self.finish('0-1' if self.human else '1-0','resignation',g['name']+' resigned.');return self.view()
            if g['state']!='playing':raise ValueError('Resume the game first')
            side='white' if self.board.turn else 'black';clock=self.clocks()[side]
            if self.board.turn==self.human and clock.budget is not None and self.elapsed(received)>=clock.budget:await self.timeout();return self.view()
            if action=='offer_draw':
                if self.board.turn!=self.human:raise ValueError('Offer a draw on your turn, then play your move')
                if g['config']['draw_policy']=='never':raise ValueError('Draw offers are disabled for this game')
                if self.board.fullmove_number<=g['config']['draw_min_moves']:raise ValueError('Wait until the configured minimum move number before offering a draw')
                g['draw_offer']=not g['draw_offer'];g['note']='Draw offer queued. Play your move.' if g['draw_offer'] else 'Draw offer withdrawn.'
                await self.persist();return self.view()
            if action=='claim_draw':
                if self.board.turn!=self.human or not self.board.can_claim_draw():raise ValueError('No legal draw claim is available on your turn')
                await self.finish('1/2-1/2','draw_claim','Human claims a legal draw.');return self.view()
            if action=='move':
                if self.board.turn!=self.human:raise ValueError('Wait for the engine to move')
                if self.task and not self.task.done():raise ValueError('Wait for the hint search to finish')
                move=self.board.parse_uci(body['move'])
                if not move or move not in self.board.legal_moves:raise ValueError('Illegal move')
                await self.push(move,self.elapsed(received),{})
                if g['state']=='playing' and self.game['state']=='playing':self.task=asyncio.create_task(self._engine_turn())
                return self.view()
            if action=='takeback':
                if g['rated']:raise ValueError('Takebacks are available only in casual games')
                if not g['moves']:raise ValueError('There are no moves to take back')
                await self._close_engine();self.hold_clock()
                end=len(g['moves']);start=end-1
                while start>0 and g['moves'][start]['side']!=g['config']['color']:start-=1
                g['variations'].append({'time':time.time(),'ply':start,'moves':copy.deepcopy(g['moves'][start:])})
                g['clocks']=g['moves'][start]['before']['clocks'];g['moves']=g['moves'][:start];g['turn_elapsed']=0;g['state']='paused';g['draw_offer']=False
                self.board,self.marks=rebuild(g);await self.persist();await self.resume();return self.view()
            if action=='hint':
                if self.board.turn!=self.human:raise ValueError('Hints are available on your turn')
                if self.task and not self.task.done():raise ValueError('A search is already in progress')
                g['rated']=False;g['note']='Hint requested. This game is now casual.';await self.persist()
                self.task=asyncio.create_task(self._hint());return self.view()
            raise ValueError('Unknown player action')

    async def _hint(self):
        try:
            self.engine.info_hook=None
            move,elapsed,info=await self.engine.play(self.board.copy(),'go movetime 500',None)
            async with self.lock:self.hint={'move':move.uci(),'san':self.board.san(move)};self.task=None
        except asyncio.CancelledError:raise
        except Exception as exc:await self._fault(exc)

    async def _tick(self):
        while not self.closed:
            try:
                await asyncio.sleep(.1)
                async with self.lock:
                    if not self.game or self.game['state']!='playing':continue
                    if self.db.store.failure:raise RuntimeError(self.db.store.failure)
                    side='white' if self.board.turn else 'black';budget=self.clocks()[side].budget
                    if self.board.turn==self.human and budget is not None and self.elapsed()>=budget:await self.timeout()
                    elif time.monotonic()-self.last_checkpoint>=5:await self.persist(checkpoint=True)
            except asyncio.CancelledError:break
            except Exception as exc:
                async with self.lock:
                    self.hold_clock();self.error='Player saving failed: '+str(exc)
                    if self.game:self.game['state']='paused';self.game['rated']=False;self.game['note']=self.error
                    await self._close_engine()

    async def close(self):
        self.closed=True
        if self.tick:self.tick.cancel();await asyncio.gather(self.tick,return_exceptions=True)
        if self.exporter:self.exporter.cancel();await asyncio.gather(self.exporter,return_exceptions=True)
        async with self.lock:
            if self.game and self.game['state'] in ('playing','starting'):
                self.hold_clock();self.game.update(state='paused',rated=False,note='Saved on close. Resume when ready; this game is now casual.')
                try:await self.persist()
                except Exception as exc:self.error=str(exc)
            await self._close_engine()
