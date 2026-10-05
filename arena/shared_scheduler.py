"""Work-conserving weighted resource-time accounting; no game clocks here.

Reservations let a larger waiting game acquire resources as existing games
finish. Dispatch remains on the runner's single admission/lifecycle lock.
"""
import time
from .resources import usage


EMPTY={'threads':0,'memory_mb':0,'gpu':{}}


def dominant(cost,limits):
    values=[cost['threads']/limits['cpu_budget'],cost['memory_mb']/limits['memory_budget_mb']]
    values.extend(n/max(1,limits['gpu_limits'].get(g,1)) for g,n in cost['gpu'].items())
    return max(values,default=0.)


class FairShare:
    def __init__(self):
        self.service={};self.tried={};self.waiting={};self.last=time.monotonic();self.reservation=None;self.reservation_cost=None

    def update(self,views,candidates,limits,now=None):
        now=time.monotonic() if now is None else now;elapsed=max(0,now-self.last);self.last=now
        ids={c['id'] for c in candidates};baseline=min((v for k,v in self.service.items() if k in ids),default=0.)
        self.service={k:self.service.get(k,baseline) for k in ids}
        self.tried={k:v for k,v in self.tried.items() if k in ids};self.waiting={k:v for k,v in self.waiting.items() if k in ids}
        weights={c['id']:c['priority'] for c in candidates}
        for view in views:
            tid=view['tid']
            if tid in ids:self.service[tid]+=elapsed*dominant(usage([view]),limits)/weights[tid]
        if self.reservation not in ids:self.reservation=None

    def order(self,candidates):
        return sorted(candidates,key=lambda c:(c['id']!=self.reservation,self.service.get(c['id'],0),self.tried.get(c['id'],0),c['position'],c['id']))

    def attempted(self,tid):self.tried[tid]=time.monotonic()

    def started(self,tid,cost,limits,weight):
        # A small admission debit spreads the initial burst before elapsed-time
        # samples arrive. Subsequent service reflects actual reserved duration.
        self.service[tid]=self.service.get(tid,0)+.1*dominant(cost,limits)/weight
        self.waiting.pop(tid,None)
        if self.reservation==tid:self.reservation=None

    def blocked(self,tid,cost=None):
        self.waiting.setdefault(tid,time.monotonic())
        if self.reservation is None and time.monotonic()-self.waiting[tid]>=2:self.reservation=tid
        if self.reservation==tid:self.reservation_cost=cost
