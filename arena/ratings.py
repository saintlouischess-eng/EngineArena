"""Sparse logistic score pool fit, conditional on a fixed reference rating.

One independent observation is a completed opening pair (or an unpaired game).
The sandwich covariance uses the full observed score histogram, not a binomial
variance assumption. No dense participant-by-participant matrix is allocated.
"""
from collections import OrderedDict
import csv
import io
import json
import math
from pathlib import Path
import sqlite3
import time

SCALE=400/math.log(10)
_cache=OrderedDict()
STATUS_LABELS={'fixed_anchor':'Fixed reference','estimated':'Estimated','disconnected':'No comparison path to reference','no_comparisons':'No completed comparisons','no_finite_fit':'No finite fit: separated results','not_converged':'Fit did not converge','uncertainty_unavailable':'Uncertainty unavailable','uncertainty_not_converged':'Uncertainty did not converge'}


def background_priority():
    """Yield CPU priority to engines while fitting a requested report."""
    import os
    import psutil
    process=psutil.Process()
    if os.name=='nt':process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    else:process.nice(10)


def logistic(x):
    if x>=0:return 1/(1+math.exp(-x))
    z=math.exp(x);return z/(1+z)


def reach(start,neighbors):
    seen={start};pending=[start]
    while pending:
        for b in neighbors[pending.pop()]:
            if b not in seen:seen.add(b);pending.append(b)
    return seen


def solve(n,edges,rhs,anchor,tolerance=1e-10):
    """Jacobi-preconditioned conjugate gradients on an anchored Laplacian."""
    diagonal=[0.]*n
    for a,b,w in edges:diagonal[a]+=w;diagonal[b]+=w
    diagonal[anchor]=1.
    if any(d<=0 for d in diagonal):raise ArithmeticError('Unidentifiable rating system')
    def product(v):
        out=[0.]*n
        for a,b,w in edges:
            z=w*(v[a]-v[b]);out[a]+=z;out[b]-=z
        out[anchor]=v[anchor];return out
    x=[0.]*n;r=list(rhs);r[anchor]=0.;z=[v/d for v,d in zip(r,diagonal)];p=z.copy()
    rz=sum(a*b for a,b in zip(r,z));threshold=tolerance**2*max(sum(v*v for v in r),1e-30)
    if sum(v*v for v in r)<=threshold:return x
    for _ in range(4*n+20):
        ap=product(p);denom=sum(a*b for a,b in zip(p,ap))
        if denom<=0:raise ArithmeticError('Rating solver lost positive definiteness')
        alpha=rz/denom;x=[a+alpha*b for a,b in zip(x,p)];r=[a-alpha*b for a,b in zip(r,ap)]
        if sum(v*v for v in r)<=threshold:return x
        z=[v/d for v,d in zip(r,diagonal)];updated=sum(a*b for a,b in zip(r,z));beta=updated/rz
        p=[a+beta*b for a,b in zip(z,p)];rz=updated
    raise ArithmeticError('Rating solver did not converge')


def fit_pool(participant_count,observations,anchor=0):
    """observations: (slot a, slot b, histogram of normalized a scores)."""
    if not 0<=anchor<participant_count:raise ValueError('Invalid reference participant')
    adjacent=[[] for _ in range(participant_count)];forward=[[] for _ in adjacent];backward=[[] for _ in adjacent]
    inputs=[]
    for a,b,bins in observations:
        if a==b:continue
        if not (0<=a<participant_count and 0<=b<participant_count) or len(bins) not in (3,5) or any(v<0 for v in bins):raise ValueError('Invalid pool observations')
        n=sum(bins)
        if not n:continue
        scores=[i/(len(bins)-1) for i in range(len(bins))];score=sum(x*c for x,c in zip(scores,bins))
        inputs.append((a,b,n,score,bins));adjacent[a].append(b);adjacent[b].append(a)
        if score>0:forward[a].append(b);backward[b].append(a)
        if score<n:forward[b].append(a);backward[a].append(b)
    component=reach(anchor,adjacent)
    # Separation only prevents finite offsets BETWEEN strong components. The
    # reference's strong component still has identifiable relative ratings.
    # Cross-component outcomes have limiting fitted scores 0/1 and contribute
    # no curvature or score variance to that finite fit. Do not add pseudo-games
    # or let a new all-loss opponent erase the established pool's estimates.
    finite=reach(anchor,forward)&reach(anchor,backward)
    members=sorted(finite);mapping={s:i for i,s in enumerate(members)};reference=mapping[anchor]
    records=[(mapping[a],mapping[b],n,score,bins) for a,b,n,score,bins in inputs if a in finite and b in finite]
    totals=[0]*participant_count
    for a,b,n,_,_ in inputs:totals[a]+=n;totals[b]+=n
    result={'members':members,'connected_members':sorted(component),'connected_index':dict.fromkeys(component),
            'separated_members':sorted(component-finite),
            'index':mapping,'anchor':reference,'samples':sum(n for a,b,n,_,_ in inputs if a in component),
            'fit_samples':sum(r[2] for r in records),'participant_samples':totals,'status':'ok','theta':None,'hessian':[],'meat':[]}
    if not records:
        result['status']='no_finite_fit' if component-finite else 'no_comparisons';return result
    n=len(members);theta=[0.]*n;degree=[0.]*n
    for a,b,count,_,_ in records:degree[a]+=count;degree[b]+=count
    def objective_change(candidate):
        # Compare the change per observation, not two large total losses. Near
        # the optimum their difference is below floating-point summation noise,
        # which used to reject the last Newton step and blank the entire pool.
        changes=[]
        for a,b,count,score,_ in records:
            x=theta[a]-theta[b];y=candidate[a]-candidate[b];delta=y-x
            if abs(delta)<=1:
                change=count*math.log1p(logistic(x)*math.expm1(delta))-score*delta
            else:
                def loss(z):
                    return (count-score)*max(z,0)+score*max(-z,0)+count*math.log1p(math.exp(-abs(z)))
                change=loss(y)-loss(x)
            changes.append(change)
        return math.fsum(changes)
    converged=False
    for iteration in range(100):
        gradient=[0.]*n;hessian=[]
        for a,b,count,score,_ in records:
            p=logistic(theta[a]-theta[b]);g=score-count*p;gradient[a]+=g;gradient[b]-=g;hessian.append((a,b,count*p*(1-p)))
        gradient[reference]=0.
        if max(abs(g)/max(1,d) for g,d in zip(gradient,degree))<1e-10:converged=True;break
        try:step=solve(n,hessian,gradient,reference)
        except ArithmeticError:break
        gain=math.fsum(a*b for a,b in zip(gradient,step));rate=1.
        while rate>1e-8:
            candidate=[a+rate*b for a,b in zip(theta,step)]
            if objective_change(candidate)<=-1e-4*rate*gain:theta=candidate;break
            rate/=2
        else:break
    if not converged:result['status']='not_converged';return result
    meat=[];hessian=[]
    for a,b,count,score,bins in records:
        p=logistic(theta[a]-theta[b]);hessian.append((a,b,count*p*(1-p)))
        meat.append((a,b,sum(c*(i/(len(bins)-1)-p)**2 for i,c in enumerate(bins))))
    result.update(theta=theta,hessian=hessian,meat=meat,iterations=iteration)
    return result


def estimate(fit,slot,anchor_slot,anchor_rating,confidence=95):
    from .stats import confidence_level,critical_value
    confidence=confidence_level(confidence)
    value={'slot':slot,'rating':None,'delta':None,'ci95':None,'ci':None,'confidence':confidence,'los':None,'samples':fit['participant_samples'][slot],'status':'disconnected'}
    if slot==anchor_slot:return value|{'rating':anchor_rating,'delta':0.,'status':'fixed_anchor'}
    if slot not in fit['index']:
        return value|{'status':'no_finite_fit'} if slot in fit['connected_index'] else value
    if fit['status']!='ok':return value|{'status':fit['status']}
    index=fit['index'][slot];theta=fit['theta'][index];delta=theta*SCALE;rating=anchor_rating+delta
    value.update(rating=rating,delta=delta,status='uncertainty_unavailable')
    dimension=len(fit['members'])-1;samples=fit['fit_samples']
    if samples<=dimension:return value
    rhs=[0.]*len(fit['members']);rhs[index]=1.
    try:column=solve(len(rhs),fit['hessian'],rhs,fit['anchor'])
    except ArithmeticError:return value|{'status':'uncertainty_not_converged'}
    variance=sum(w*(column[a]-column[b])**2 for a,b,w in fit['meat'])*samples/(samples-dimension)
    if variance<=1e-20:return value
    se=math.sqrt(variance)*SCALE
    return value|{'ci95':[rating-1.959963984540054*se,rating+1.959963984540054*se],
                  'ci':[rating-critical_value(confidence)*se,rating+critical_value(confidence)*se],
                  'los':50*math.erfc(-delta/(se*math.sqrt(2))),'status':'estimated'}


def pool_report(path,tid,offset=0,limit=50,search='',export='',confidence=95,sort='slot',direction='asc'):
    from .stats import confidence_level
    confidence=confidence_level(confidence)
    if offset<0 or limit<1:raise ValueError('Invalid rating page')
    if sort not in ('slot','name','rating','delta','ci','los','samples','status') or direction not in ('asc','desc'):raise ValueError('Invalid rating sort')
    started=time.monotonic();db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row
    try:
        db.execute('BEGIN')
        tournament=db.execute('SELECT name,settings FROM tournaments WHERE id=?',(tid,)).fetchone()
        if not tournament:raise ValueError('Tournament not found')
        settings=json.loads(tournament['settings']);paired=settings['paired']
        anchor=db.execute('SELECT slot,rating FROM rating_anchors WHERE tid=?',(tid,)).fetchone()
        anchor=dict(anchor) if anchor else {'slot':0,'rating':0.}
        revision=db.execute('SELECT revision FROM report_revisions WHERE tid=?',(tid,)).fetchone();revision=revision[0] if revision else 0
        profiles=[{'slot':r['slot'],'name':r['name']} for r in db.execute("SELECT slot,json_extract(profile,'$.name') name FROM participants WHERE tid=? AND slot IN (SELECT slot FROM rankings WHERE tid=participants.tid) ORDER BY slot",(tid,))]
        by_slot={p['slot']:p for p in profiles}
        if anchor['slot'] not in by_slot:anchor={'slot':profiles[0]['slot'],'rating':0.,'note':'Former reference withdrawn; revised standings use the first active entrant at zero.'}
        key=(str(path),tid,revision,anchor['slot'])
        cached=_cache.get(key)
        if cached is None:
            observations=[]
            for r in db.execute('SELECT * FROM aggregates WHERE tid=? AND a<b AND b>=0',(tid,)):
                bins=[r[f'p{i}'] for i in range(5)] if paired else [r['l'],r['d'],r['w']]
                if sum(bins):observations.append((r['a'],r['b'],bins))
        else:observations=None
    finally:db.close()
    # Close the read transaction before CPU work so WAL checkpointing can proceed.
    if cached is None:
        cached=fit_pool(max(by_slot)+1,observations,anchor['slot']);_cache[key]=cached
        while len(_cache)>2:_cache.popitem(last=False)
    else:_cache.move_to_end(key)
    anchor['name']=by_slot[anchor['slot']]['name'];query=search.casefold()
    matching=[p for p in profiles if query in p['name'].casefold()]
    # Cache uncertainty solves by report revision/reference/confidence. Simple
    # sorts need only the fitted strengths, not an expensive solve for every row.
    signature=(anchor['rating'],confidence)
    if cached.get('row_signature')!=signature:
        cached.update(row_signature=signature,rows={})
    def row(p):
        slot=p['slot']
        if slot not in cached['rows']:cached['rows'][slot]=p|estimate(cached,slot,anchor['slot'],anchor['rating'],confidence)
        return cached['rows'][slot]
    def value(p):
        slot=p['slot']
        if sort=='slot':return slot
        if sort=='name':return p['name'].casefold()
        if sort=='samples':return cached['participant_samples'][slot]
        if sort in ('rating','delta'):
            if slot==anchor['slot']:return anchor['rating'] if sort=='rating' else 0.
            if cached['status']!='ok' or slot not in cached['index']:return None
            delta=cached['theta'][cached['index'][slot]]*SCALE
            return delta+(anchor['rating'] if sort=='rating' else 0)
        item=row(p)
        if sort=='ci':return item['ci'][1]-item['ci'][0] if item['ci'] else None
        if sort=='status':return STATUS_LABELS.get(item['status'],item['status']).casefold()
        return item[sort]
    values={p['slot']:value(p) for p in matching}
    available=[p for p in matching if values[p['slot']] is not None]
    missing=[p for p in matching if values[p['slot']] is None]
    # Python's stable sort retains participant order for ties in both directions.
    available.sort(key=lambda p:values[p['slot']],reverse=direction=='desc')
    ordered=available+missing
    selected=ordered if export else ordered[offset:offset+limit]
    rows=[row(p) for p in selected]
    result={'tournament':tid,'name':tournament['name'],'revision':revision,'anchor':anchor,'paired':paired,'sample_unit':'completed opening pairs' if paired else 'games',
      'samples':cached['samples'],'fit_samples':cached['fit_samples'],'connected_participants':len(cached['connected_members']),
      'finite_participants':len(cached['members']),'separated_participants':len(cached['separated_members']),
      'participant_count':len(profiles),'total':len(matching),'offset':offset,'items':rows,'status':cached['status'],
      'confidence':confidence,'sort':sort,'direction':direction,'model':f'Logistic expected-score pool fit; fixed reference rating; {"paired" if paired else "game"}-score sandwich normal {confidence:g}% intervals',
      'assumptions':'Independent fixed samples, stable transitive strengths; intervals and LOS are approximate and conditional on the supplied anchor. No anchor-rating uncertainty or color parameter is estimated. Separated results do not suppress finite ratings within the reference comparison group; their games remain recorded but do not add precision to that fit.',
      'elapsed_ms':1000*(time.monotonic()-started)}
    from .knockout import sample_note
    if sample_note(settings):result['model']+='; '+sample_note(settings)
    if export=='csv':
        output=io.StringIO();writer=csv.DictWriter(output,fieldnames=['slot','participant_id','name','rating','delta','ci_lower','ci_upper','confidence','los','los_display','samples','status','anchor','anchor_rating','model'],extrasaction='ignore');writer.writeheader()
        for row in rows:
            interval=row['ci']
            from .display import los_percent
            writer.writerow(row|{'participant_id':row['slot']+1,'los_display':los_percent(row['los']),'ci_lower':interval[0] if interval else None,'ci_upper':interval[1] if interval else None,
                                 'anchor':anchor['name'],'anchor_rating':anchor['rating'],'model':result['model']})
        return output.getvalue()
    return result
