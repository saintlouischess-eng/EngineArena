from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Any

FAILURES = ('timeout', 'crash', 'hang', 'illegal_move', 'interrupted', 'startup_timeout', 'readiness_timeout', 'protocol_error')
FORMATS = ('match', 'round_robin', 'gauntlet', 'self_play', 'swiss', 'knockout', 'double_elimination', 'ladder', 'sprt')

@dataclass
class TimeControl:
    kind: str = 'fischer'
    seconds: float = 180
    increment: float = 2
    delay: float = 0
    nodes: int = 10000
    depth: int = 12
    stages: list[dict] = field(default_factory=list)
    repeat: bool = False

    @classmethod
    def parse(cls, value: dict | None):
        if value is not None and not isinstance(value,dict):raise ValueError('Time control must be an object')
        tc = cls(**(value or {}))
        if tc.kind not in ('sudden_death','fischer','delay','bronstein','staged','movetime','depth','nodes'):
            raise ValueError('Unknown time control')
        for v in (tc.seconds,tc.increment,tc.delay):
            if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v < 0: raise ValueError('Times must be finite and non-negative')
        if not isinstance(tc.repeat,bool):raise ValueError('Repeat must be true or false')
        if tc.kind in ('nodes','depth'):
            n = getattr(tc,tc.kind)
            if not isinstance(n,int) or isinstance(n,bool) or n <= 0: raise ValueError('Node/depth limit must be a positive integer')
        elif tc.kind == 'staged':
            if not isinstance(tc.stages,list) or not tc.stages: raise ValueError('At least one stage required')
            for i,s in enumerate(tc.stages):
                if not isinstance(s,dict):raise ValueError('Stage must be an object')
                for key in ('seconds','increment'):
                    v=s.get(key,0)
                    if not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0:raise ValueError('Invalid stage time')
                if s.get('seconds',0)<=0:raise ValueError('Invalid stage time')
                if not isinstance(s.get('moves',0),int) or isinstance(s.get('moves',0),bool) or s.get('moves',0)<0: raise ValueError('Invalid stage move count')
                if not s.get('moves') and (i<len(tc.stages)-1 or tc.repeat): raise ValueError('Only a non-repeating final stage can be sudden death')
        elif tc.seconds <= 0: raise ValueError('Time must be positive')
        return tc

    @property
    def clocked(self): return self.kind not in ('nodes','depth','movetime')

@dataclass
class Clock:
    tc: TimeControl
    remaining: float = 0
    stage: int = 0
    moves: int = 0

    def __post_init__(self):
        self.remaining = self.tc.stages[0]['seconds'] if self.tc.kind=='staged' else self.tc.seconds

    @property
    def increment(self):
        if self.tc.kind=='staged': return self.tc.stages[self.stage].get('increment',0)
        return self.tc.increment if self.tc.kind=='fischer' else 0

    @property
    def moves_to_go(self):
        if self.tc.kind!='staged': return None
        moves=self.tc.stages[self.stage].get('moves',0)
        return moves-self.moves if moves and self.moves<moves else None

    @property
    def budget(self):
        if self.tc.kind=='movetime': return self.tc.seconds
        if not self.tc.clocked: return None
        return self.remaining + (self.tc.delay if self.tc.kind in ('delay','bronstein') else 0)

    def consume(self,elapsed:float,overhead:float=0):
        if not self.tc.clocked: return
        cost=elapsed+overhead
        if self.tc.kind in ('delay','bronstein'): cost=max(0,cost-self.tc.delay)
        self.remaining-=cost
        self.remaining+=self.increment
        self.moves+=1
        if self.tc.kind=='staged':
            s=self.tc.stages[self.stage]
            if s.get('moves') and self.moves>=s['moves']:
                if self.stage+1<len(self.tc.stages): self.stage+=1
                elif not self.tc.repeat: return
                self.moves=0
                self.remaining+=self.tc.stages[self.stage]['seconds']

    def snapshot(self):
        return {'remaining':self.remaining if self.tc.clocked else None,'stage':self.stage,'moves':self.moves,'control':asdict(self.tc)}

def go_command(active:Clock,white:Clock,black:Clock)->str:
    tc=active.tc
    if tc.kind=='nodes': return f'go nodes {tc.nodes}'
    if tc.kind=='depth': return f'go depth {tc.depth}'
    if tc.kind=='movetime': return f'go movetime {max(1,round(tc.seconds*1000))}'
    # UCI has no delay token. Grant the current delay in the advertised time;
    # the referee independently charges elapsed time under the selected rule.
    def ms(c): return max(1,round((c.budget if c.budget is not None else 0)*1000))
    cmd=f'go wtime {ms(white)} btime {ms(black)} winc {round(white.increment*1000)} binc {round(black.increment*1000)}'
    if active.moves_to_go: cmd+=f' movestogo {active.moves_to_go}'
    return cmd

def scheduled_pairs(n:int,fmt:str,cycles:int,candidates:int=1,rounds:int=5,ladder_distance:int=1)->int:
    if n<1 or cycles<1 or rounds<1: raise ValueError('Positive participant/cycle/round count required')
    if fmt in ('match','sprt'):
        if n!=2: raise ValueError('This format requires exactly two profiles')
        return cycles
    if fmt=='self_play': return n*cycles
    if n<2: raise ValueError('At least two participants required')
    if fmt=='round_robin': return n*(n-1)//2*cycles
    if fmt=='gauntlet':
        if not 0<candidates<n: raise ValueError('Candidate count must be between one and participants minus one')
        return candidates*(n-candidates)*cycles
    if fmt=='swiss': return (n//2)*rounds*cycles
    if fmt=='ladder':
        if not 1<=ladder_distance<n:raise ValueError('Ladder distance must be positive and smaller than the field')
        from .rounds import ladder_positions
        period=ladder_distance+1;whole,rest=divmod(rounds,period)
        counts=[len(ladder_positions(n,i,ladder_distance)[0]) for i in range(min(rounds,period))]
        return (whole*sum(counts)+sum(counts[:rest]))*cycles
    if fmt=='knockout': return (n-1)*cycles
    if fmt=='double_elimination': return (2*n-2)*cycles # final reset may add one matchup
    raise ValueError('Unknown tournament format')

def static_pair(index:int,n:int,fmt:str,cycles:int,candidates:int=1):
    # Pair number decodes in O(log n) without constructing an O(n²) schedule.
    repetition=index%cycles; k=index//cycles
    if fmt in ('match','sprt'): return 0,1,repetition
    if fmt=='self_play': return k,k,repetition
    if fmt=='gauntlet': return k//(n-candidates),candidates+k%(n-candidates),repetition
    lo,hi=0,n-1
    while lo<hi:
        mid=(lo+hi+1)//2
        if mid*(2*n-mid-1)//2<=k: lo=mid
        else: hi=mid-1
    a=lo; return a,a+1+k-a*(2*n-a-1)//2,repetition
