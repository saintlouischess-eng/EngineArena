"""Descriptive logistic Elo and opening-pair multinomial statistics.

Confidence intervals are fixed-sample normal estimates or conservative
Hoeffding bounds, not confidence sequences or sequential stopping rules.
"""
import math
from functools import lru_cache
from statistics import NormalDist

def confidence_level(value=95):
    if isinstance(value,bool):raise ValueError('Confidence must be between 50 and 99.99 percent')
    value=float(value)
    if not math.isfinite(value) or not 50<=value<=99.99:raise ValueError('Confidence must be between 50 and 99.99 percent')
    return value

@lru_cache(maxsize=128)
def critical_value(confidence=95):
    return NormalDist().inv_cdf(.5+confidence_level(confidence)/200)

def elo(p):
    if p<=0: return '-infinity'
    if p>=1: return '+infinity'
    return 400*math.log10(p/(1-p))

def summarize(w,d,l,penta=None,confidence=95):
    confidence=confidence_level(confidence)
    n=w+d+l
    result={'games':n,'wins':w,'draws':d,'losses':l,'score':w+d/2,'score_pct':100*(w+d/2)/n if n else None,'draw_pct':100*d/n if n else None}
    bins=penta if penta is not None else [l,d,w]
    count=sum(bins); denom=len(bins)-1
    result.update(pairs=count if penta is not None else None,pentanomial=penta,model='Pentanomial opening-pair, logistic Elo' if penta is not None else 'Trinomial game, logistic Elo',elo=None,ci95=None,ci95_conservative=None,los=None,
      ci95_method='Fixed-sample normal approximation; sample variance with Bessel correction',
      ci95_conservative_method='Fixed-sample two-sided Hoeffding bound for independent bounded observations',los_method='Normal approximation')
    result.update(ci=None,ci_conservative=None,confidence=confidence)
    if not count: return result
    p=sum(i/denom*v for i,v in enumerate(bins))/count
    result['elo']=elo(p)
    radius=math.sqrt(math.log(40)/(2*count))
    result['ci95_conservative']=[elo(max(0,p-radius)),elo(min(1,p+radius))]
    radius=math.sqrt(math.log(2/(1-confidence/100))/(2*count))
    result['ci_conservative']=[elo(max(0,p-radius)),elo(min(1,p+radius))]
    if count<2: return result
    variance=sum(v*(i/denom-p)**2 for i,v in enumerate(bins))/(count-1)
    se=math.sqrt(variance/count)
    # Degenerate samples have no defensible plug-in uncertainty estimate.
    if se==0: return result
    result['ci95']=[elo(max(0,p-1.959963984540054*se)),elo(min(1,p+1.959963984540054*se))]
    radius=critical_value(confidence)*se
    result['ci']=[elo(max(0,p-radius)),elo(min(1,p+radius))]
    # erfc retains the small lower tail instead of cancelling 1 + erf(z).
    result['los']=50*math.erfc((.5-p)/(se*math.sqrt(2)))
    return result

def sprt_llr(bins,elo0,elo1,alpha=.05,beta=.05):
    if len(bins) not in (3,5) or any(not isinstance(x,int) or isinstance(x,bool) or x<0 for x in bins):raise ValueError('SPRT requires three or five non-negative integer frequencies')
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in (elo0,elo1,alpha,beta)):raise ValueError('SPRT hypotheses and error rates must be finite numbers')
    if not elo0<elo1 or not 0<alpha<1 or not 0<beta<1 or alpha+beta>=1: raise ValueError('Invalid SPRT hypotheses/error rates')
    def score(e):
        z=e/400*math.log(10)
        if z>=0:return 1/(1+math.exp(-z))
        exp=math.exp(z);return exp/(1+exp)
    score0,score1=score(elo0),score(elo1)
    if not 0<score0<score1<1:raise ValueError('SPRT hypotheses cannot be distinguished at floating-point precision')
    if not sum(bins): return {'llr':0,'lower':math.log(beta/(1-alpha)),'upper':math.log((1-beta)/alpha),'decision':'continue'}
    # Constrained multinomial MLE; tiny pseudocounts regularize empty categories.
    weights=[max(.001,x) for x in bins]; n=sum(weights); probs=[x/n for x in weights]
    def mle(target):
        scores=[i/(len(bins)-1) for i in range(len(bins))]
        low=-1/(1-target)+1e-12; high=1/target-1e-12
        for _ in range(100):
            theta=(low+high)/2
            f=sum(p*(x-target)/(1+theta*(x-target)) for x,p in zip(scores,probs))
            if f>0: low=theta
            else: high=theta
        return [p/(1+(low+high)/2*(x-target)) for x,p in zip(scores,probs)]
    p0=mle(score0);p1=mle(score1)
    llr=sum(w*math.log(b/a) for w,a,b in zip(weights,p0,p1))
    lower=math.log(beta/(1-alpha));upper=math.log((1-beta)/alpha)
    return {'llr':llr,'lower':lower,'upper':upper,'decision':'H1' if llr>=upper else 'H0' if llr<=lower else 'continue'}
