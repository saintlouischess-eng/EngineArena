"""Bounded monotonic ETA sampling. Pauses/restarts never count as play time."""
from collections import OrderedDict,deque
import time

class Progress:
    def __init__(self):self.samples=OrderedDict()
    def reset(self,tid):self.samples.pop(tid,None)
    def observe(self,t,active=0,now=None):
        now=time.monotonic() if now is None else now
        tid=t['id'];done=t['official_games'];total=t['total'];remaining=max(0,total-done)
        result={'percent':min(100,100*done/total) if total else 0,'remaining_games':remaining,
                'eta_seconds':None,'games_per_hour':None,'status':'collecting',
                'basis':'Recent official game completions during active play; an estimate, not a deadline.'}
        if t['state']=='completed':
            self.reset(tid);return result|{'eta_seconds':0,'status':'finished' if not remaining else 'ended_early'}
        if t['state']!='running' or t.get('dependency') or t.get('saving_error'):
            self.reset(tid);return result|{'status':'paused' if t['state']=='paused' else 'draining' if t['state']=='draining' else 'blocked'}
        if not remaining:return result|{'status':'replays' if active or t.get('counts',{}).get('pending') else 'finishing'}
        saved=self.samples.get(tid)
        if saved and (saved['total']!=total or done<saved['points'][-1][1] or now-saved['points'][-1][0]>15):
            self.reset(tid);saved=None
        if not saved:
            if not active:return result|{'status':'waiting'}
            saved={'total':total,'points':deque(maxlen=301)};self.samples[tid]=saved
            while len(self.samples)>16:self.samples.popitem(last=False)
        points=saved['points']
        if not points or now-points[-1][0]>=2 or done!=points[-1][1]:points.append((now,done))
        while len(points)>2 and now-points[1][0]>600:points.popleft()
        elapsed=now-points[0][0];completed=done-points[0][1]
        if elapsed>=5 and completed>=2:
            rate=completed/elapsed
            return result|{'eta_seconds':remaining/rate,'games_per_hour':rate*3600,'status':'estimated'}
        return result
