from __future__ import annotations
import asyncio
from collections import deque
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import chess
import chess.engine
from .windows_job import Job

class EngineFailure(Exception):
    def __init__(self,reason,detail):super().__init__(detail);self.reason=reason


async def search_result(future, started, allowance):
    """Event-loop timers may wake early on Windows. Only QPC decides expiry.

    wait() leaves the bestmove future intact while we re-arm an early timer.
    A reply carries its own read timestamp, checked by play() below.
    """
    deadline=started+allowance
    while not future.done():
        remaining=deadline-time.perf_counter()
        if remaining<=0:raise asyncio.TimeoutError
        await asyncio.wait((future,),timeout=max(.001,remaining))
    return future.result()

def normalize_promotion(move):
    # Some engines (including Naum 4.6) use uppercase promotion pieces.
    # Accept that spelling only; the board must still validate the move.
    if len(move)==5 and move[4] in 'QRBN' and re.fullmatch(r'[a-h][1-8][a-h][1-8][QRBN]',move):return move[:4]+move[4].lower()
    return move


def parse_option(line):
    match=re.fullmatch(r'option name (.*?) type (check|spin|combo|button|string)(.*)',line)
    if not match:raise ValueError('Malformed UCI option: '+line)
    name,kind,tail=match.groups();values={};variants=[]
    for m in re.finditer(r' (default|min|max|var) (.*?)(?= (?:default|min|max|var) |$)',tail):
        key,value=m.groups()
        if key=='var':variants.append(value)
        else:values[key]=value
    default=values.get('default')
    if default=='<empty>':default=''
    option=chess.engine.Option(name,kind,default,int(values['min']) if 'min' in values else None,int(values['max']) if 'max' in values else None,variants)
    if default is not None:default=option.parse(default)
    return {'name':name,'type':kind,'default':default,'min':option.min,'max':option.max,'var':variants}

def validated_options(options,advertised):
    values={};lookup={k.lower():v for k,v in advertised.items()}
    for key,value in options.items():
        if key.lower() not in lookup:raise ValueError('Engine does not advertise option '+key)
        o=lookup[key.lower()];opt=chess.engine.Option(o['name'],o['type'],o['default'],o['min'],o['max'],o['var'])
        parsed=opt.parse(value)
        if o['name'] in values and values[o['name']]!=parsed:raise ValueError('Conflicting values for option '+o['name'])
        values[o['name']]=parsed
    return values

class UciEngine:
    def __init__(self,profile,settings):
        self.profile=profile;self.settings=settings;self.process=None;self.tasks=[];self.identity={};self.options={}
        self.log=deque(maxlen=256);self.last_info={};self.search=None;self.uciok=None;self.ready=None;self.job=Job();self.error=None
        self.pondering=False;self.ponder_position=None;self.ponder_candidate=None;self.info_hook=None;self.last_update={};self.info_position=None
        self.runtime={};self.runtime_hook=None;self.process_started=None;self.process_ended=None;self.search_started=None

    def runtime_changed(self,line=None):
        from .runtime_evidence import observe_line
        if line is not None and not observe_line(self.runtime,line):return
        if self.runtime_hook:self.runtime_hook()

    async def start(self):
        try:
            from .fingerprints import verify
            try:await asyncio.to_thread(verify,self.profile)
            except (ValueError,OSError) as e:raise EngineFailure('configuration_changed',str(e)) from e
            args=self.profile.get('args',[])
            if isinstance(args,str):args=shlex.split(args,posix=os.name!='nt');args=[a.strip('"') for a in args]
            self.process=await asyncio.create_subprocess_exec(self.profile['path'],*args,cwd=self.profile.get('cwd') or str(Path(self.profile['path']).parent),
                stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,limit=65536)
            self.job.assign(self.process.pid)
            self.process_started=time.time();self.runtime_changed()
            if self.profile.get('affinity'):
                import psutil
                psutil.Process(self.process.pid).cpu_affinity(self.profile['affinity'])
            loop=asyncio.get_running_loop();self.uciok=loop.create_future()
            self.tasks=[asyncio.create_task(self._read()),asyncio.create_task(self._stderr())]
            await self.send('uci')
            try:await asyncio.wait_for(self.uciok,self.settings['startup_timeout'])
            except asyncio.TimeoutError:raise EngineFailure('startup_timeout','No uciok before startup watchdog')
            chosen=dict(self.profile.get('options',{}))
            for name,value in (('Threads',self.profile.get('threads',1)),('Hash',self.profile.get('hash',1024)),('Ponder',self.settings.get('ponder',False)),('UCI_Chess960',self.settings.get('chess960',False))):
                from .engine_options import find_name
                actual=find_name(self.options,name)
                supplied=find_name(chosen,name)
                if actual and (supplied is None or name in ('Ponder','UCI_Chess960')):
                    if supplied is not None:chosen.pop(supplied)
                    chosen[actual]=value
            if self.settings.get('chess960') and 'uci_chess960' not in {k.lower() for k in self.options}:raise EngineFailure('protocol_error','Engine does not advertise UCI_Chess960')
            try:options=validated_options(chosen,self.options)
            except ValueError as e:raise EngineFailure('protocol_error',str(e))
            self.runtime.update(options=options,advertised=list(self.options),affinity=self.profile.get('affinity',[]))
            self.runtime_changed()
            for k,v in options.items():
                await self.send('setoption name '+k+(' value '+str(v).lower() if isinstance(v,bool) else ' value '+str(v) if v is not None else ''))
            await self.send('ucinewgame');await self.ping()
        except (OSError,ValueError) as e:raise EngineFailure('crash','Engine launch/configuration failed: '+str(e)) from e

    async def ping(self):
        self.ready=asyncio.get_running_loop().create_future();await self.send('isready')
        try:await asyncio.wait_for(self.ready,self.settings['readiness_timeout'])
        except asyncio.TimeoutError:raise EngineFailure('readiness_timeout','No readyok before readiness watchdog')

    async def send(self,line):
        if '\n' in line or '\r' in line:raise EngineFailure('protocol_error','Newline in UCI command')
        self.log.append('> '+line)
        if not self.process or self.process.returncode is not None:raise EngineFailure('crash','Engine process exited')
        try:self.process.stdin.write((line+'\n').encode());await self.process.stdin.drain()
        except (OSError,ConnectionError) as e:raise EngineFailure('crash',str(e)) from e

    async def _read(self):
        try:
            count=0
            while raw:=await self.process.stdout.readline():
                received=time.perf_counter()
                count+=1
                line=raw.decode('utf-8','replace').strip();self.log.append('< '+line)
                if line.startswith('info string '):self.runtime_changed(line)
                if line.startswith('id '):
                    key,_,value=line[3:].partition(' ');self.identity[key]=value
                elif line.startswith('option '):
                    o=parse_option(line);self.options[o['name']]=o
                elif line=='uciok' and self.uciok and not self.uciok.done():self.uciok.set_result(True)
                elif line=='readyok' and self.ready and not self.ready.done():self.ready.set_result(True)
                elif line.startswith('bestmove ') and self.search and not self.search.done():
                    tokens=line.split();ponder=tokens[3] if len(tokens)>=4 and tokens[2]=='ponder' else None
                    self.search.set_result((tokens[1],received,ponder))
                elif line.startswith('info '):self._info(line)
                # Complete/timestamp a received reply before yielding for UI and
                # other engines. That fairness work must not extend its clock.
                if count%64==0:await asyncio.sleep(0)
            raise EngineFailure('crash',f'Engine stdout closed (exit {self.process.returncode})')
        except asyncio.CancelledError:pass
        except Exception as e:
            self.error=e if isinstance(e,EngineFailure) else EngineFailure('protocol_error',str(e))
            for f in (self.search,self.uciok,self.ready):
                if f and not f.done():f.set_exception(self.error)

    async def _stderr(self):
        try:
            count=0
            while raw:=await self.process.stderr.readline():
                line='stderr '+raw.decode('utf-8','replace').strip();self.log.append(line);self.runtime_changed(line);count+=1
                if count%64==0:await asyncio.sleep(0)
        except (ValueError,asyncio.CancelledError):pass

    def _info(self,line):
        fields=line.split()
        if len(fields)>1 and fields[1]=='string':return
        if 'multipv' in fields:
            try:
                if int(fields[fields.index('multipv')+1])!=1:return
            except (ValueError,IndexError):return
        update={}
        for key in ('depth','seldepth','nodes','nps','hashfull','tbhits','time'):
            if key in fields:
                try:update[key]=int(fields[fields.index(key)+1])
                except (ValueError,IndexError):pass
        if 'score' in fields:
            try:
                k=fields.index('score');kind=fields[k+1];value=int(fields[k+2])
                if kind in ('cp','mate'):
                    self.last_info.pop('cp',None);self.last_info.pop('mate',None);update[kind]=value
                    update['score_bound']=fields[k+3] if len(fields)>k+3 and fields[k+3] in ('lowerbound','upperbound') else 'exact'
            except (ValueError,IndexError):pass
        if 'wdl' in fields:
            try:k=fields.index('wdl');update['wdl']=[int(v) for v in fields[k+1:k+4]]
            except ValueError:pass
        if 'pv' in fields:update['pv']=' '.join(normalize_promotion(m) for m in fields[fields.index('pv')+1:fields.index('pv')+65])
        from .telemetry import clean
        elapsed=time.perf_counter()-self.search_started if self.search_started is not None else None
        self.last_update=clean(update,elapsed);self.last_info=clean(self.last_info|update,elapsed)
        if self.info_hook:self.info_hook(self.last_info)

    async def play(self,board,command,clock_budget):
        self.search_started=None
        if self.error:raise self.error
        hang=self.settings['hang_timeout'];chess_deadline=(clock_budget+self.settings['tolerance']) if clock_budget is not None else None
        if chess_deadline is not None and chess_deadline<=0:
            raise EngineFailure('timeout',f'Chess clock and tolerance exhausted before search; budget {clock_budget:.6f}s, tolerance {self.settings["tolerance"]:.6f}s')
        hit=self.pondering and self.ponder_position==board.fen()
        if hit:
            if self.search.done():raise EngineFailure('protocol_error','Engine ended pondering before ponderhit/stop')
            self.pondering=False;started=self.search_started=time.perf_counter();await self.send('ponderhit')
        else:
            if self.pondering:await self.stop_ponder()
            self.last_info={};self.last_update={};self.info_position=board.fen();self.search=asyncio.get_running_loop().create_future()
            await self.position(board)
            started=self.search_started=time.perf_counter();await self.send(command)
        limit=min(hang,chess_deadline) if chess_deadline is not None else hang
        reason='timeout' if chess_deadline is not None and chess_deadline<=hang else 'hang'
        try:move,finished,ponder=await search_result(self.search,started,limit)
        except asyncio.TimeoutError:
            elapsed=max(0,time.perf_counter()-started)
            raise EngineFailure(reason,f'{reason}: elapsed {elapsed:.6f}s, allowance {limit:.6f}s; command: {command}')
        elapsed=finished-started
        if elapsed>limit:raise EngineFailure(reason,f'Move took {elapsed:.6f}s, allowance {limit:.6f}s')
        from .telemetry import clean
        info=clean(self.last_info,elapsed)
        for key in ('cp','mate'):
            if key in info:info[key]*=1 if board.turn else -1
        if 'wdl' in info:info['wdl']=list(info['wdl']) if board.turn else list(reversed(info['wdl']))
        if not board.turn and info.get('score_bound') in ('lowerbound','upperbound'):
            info['score_bound']='upperbound' if info['score_bound']=='lowerbound' else 'lowerbound'
        normalized=normalize_promotion(move)
        try:parsed=board.parse_uci(normalized)
        except ValueError:raise EngineFailure('illegal_move','Illegal bestmove '+move+' in '+board.fen())
        if not parsed or parsed not in board.legal_moves:raise EngineFailure('illegal_move','Illegal bestmove '+move)
        if normalized!=move:self.log.append('# Compatibility: promotion '+move+' accepted as '+normalized)
        self.ponder_candidate=normalize_promotion(ponder) if ponder else None
        return parsed,elapsed,info

    async def position(self,board):
        root=board.root();history=' '.join(m.uci() for m in board.move_stack)
        await self.send('position fen '+root.fen(shredder=board.chess960)+(' moves '+history if history else ''))

    async def begin_ponder(self,board,command):
        if not self.settings.get('ponder') or not self.ponder_candidate or board.is_game_over():return
        actual=next((k for k in self.options if k.lower()=='ponder'),None)
        if not actual:return
        predicted=board.copy()
        try:predicted.push_uci(self.ponder_candidate)
        except ValueError:return
        self.last_info={};self.last_update={};self.search=asyncio.get_running_loop().create_future();self.ponder_position=predicted.fen();self.info_position=self.ponder_position;self.pondering=True
        await self.position(predicted);await self.send(command.replace('go ','go ponder ',1))

    async def stop_ponder(self):
        self.pondering=False;await self.send('stop')
        try:await asyncio.wait_for(self.search,self.settings['stop_timeout'])
        except asyncio.TimeoutError:raise EngineFailure('hang','Engine did not stop pondering before stop watchdog')

    async def close(self):
        if self.process and self.process.returncode is None:
            try:
                await self.send('quit');await asyncio.wait_for(self.process.wait(),self.settings.get('stop_timeout',3))
            except Exception:
                try:self.process.kill()
                except ProcessLookupError:pass
        self.job.close()
        if self.process:
            try:await asyncio.wait_for(self.process.wait(),3)
            except Exception:pass
        for t in self.tasks:t.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)
        for f in (self.search,self.uciok,self.ready):
            if f and f.done() and not f.cancelled():f.exception()
        if self.process_started is not None:self.process_ended=time.time();self.runtime_changed()

async def discover(profile,settings):
    # Re-discovery is the explicit way to accept a changed executable/network.
    profile={k:v for k,v in profile.items() if k not in ('sha256','fingerprints')}
    e=UciEngine(profile,settings)
    try:
        await e.start()
        from .fingerprints import capture
        result=profile|{'name':profile.get('name') or e.identity.get('name',Path(profile['path']).stem),
                       'options':validated_options(profile.get('options',{}),e.options),'identity':e.identity,'advertised':e.options}
        identity=await asyncio.to_thread(capture,result)
        return result|{'sha256':identity['executable']['sha256'],'fingerprints':identity}
    finally:await e.close()
