"""Independent dense SciPy reference for the sparse production pool estimator."""
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc
import numpy as np
from scipy.optimize import minimize,root
from scipy.special import expit

ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from arena.ratings import fit_pool,estimate,SCALE


def independent(count,observations,anchor):
    members=[i for i in range(count) if i!=anchor];design=[];success=[];frequency=[];samples=[]
    for a,b,bins in observations:
        row=np.array([float(i==a)-float(i==b) for i in members]);design.append(row)
        scores=np.linspace(0,1,len(bins));frequency.append(sum(bins));success.append(scores@bins);samples.append((scores,np.asarray(bins)))
    x=np.array(design);n=np.array(frequency);y=np.array(success)
    objective=lambda v:float(np.sum(n*np.logaddexp(0,x@v)-y*(x@v)))
    gradient=lambda v:x.T@(n*expit(x@v)-y)
    hessian=lambda v:x.T@((n*expit(x@v)*(1-expit(x@v)))[:,None]*x)
    opt=minimize(objective,np.zeros(count-1),jac=gradient,hess=hessian,method='trust-exact',options={'gtol':1e-9})
    polished=root(gradient,opt.x,jac=hessian,method='hybr',options={'xtol':1e-11})
    if np.max(np.abs(gradient(polished.x)))<np.max(np.abs(gradient(opt.x))):opt.x=polished.x
    if np.max(np.abs(gradient(opt.x)))>1e-6:raise RuntimeError(opt.message)
    probabilities=expit(x@opt.x);bread=np.linalg.inv(hessian(opt.x));meat=np.zeros((count-1,count-1))
    for row,p,(scores,bins) in zip(x,probabilities,samples):meat+=float(bins@((scores-p)**2))*np.outer(row,row)
    covariance=bread@meat@bread*n.sum()/(n.sum()-(count-1))
    return {slot:(opt.x[k]*SCALE,math.sqrt(covariance[k,k])*SCALE) for k,slot in enumerate(members)}


def main():
    rng=np.random.default_rng(7970);cases=[]
    for count in (2,3,5,12):
        for paired in (False,True):
            for repeat in range(5):
                observations=[]
                for a in range(count):
                    for b in range(a+1,count):
                        bins=(rng.multinomial(200,rng.dirichlet(np.ones(5 if paired else 3)*4))+1).tolist();observations.append((a,b,bins))
                anchor=repeat%count;fit=fit_pool(count,observations,anchor);reference=independent(count,observations,anchor)
                assert fit['status']=='ok'
                for slot,(delta,se) in reference.items():
                    value=estimate(fit,slot,anchor,2400);actual_se=(value['ci95'][1]-value['ci95'][0])/(2*1.959963984540054)
                    cases.append({'participants':count,'paired':paired,'anchor':anchor,'slot':slot,'rating_error':abs(value['delta']-delta),'se_error':abs(actual_se-se)})
    coverage=[]
    for draw,rho in ((.5,0),(.9,.6)):
        strengths=np.array([0,.08,-.06]);covered=np.zeros(2);available=np.zeros(2)
        for _ in range(1000):
            observations=[]
            for a,b in ((0,1),(0,2),(1,2)):
                p=expit(strengths[a]-strengths[b]);single=np.array([1-p-draw/2,draw,p-draw/2])
                probs=(1-rho)*np.convolve(single,single)+rho*np.array([single[0],0,single[1],0,single[2]])
                observations.append((a,b,rng.multinomial(500,probs).tolist()))
            fit=fit_pool(3,observations,0)
            for k in (1,2):
                value=estimate(fit,k,0,0)
                if value['ci95']:
                    available[k-1]+=1;covered[k-1]+=value['ci95'][0]<=strengths[k]*SCALE<=value['ci95'][1]
        coverage.append({'draw_probability':draw,'pair_correlation_mixture':rho,'replications':1000,'pairs_per_matchup':500,'available':available.tolist(),'coverage':(covered/available).tolist()})
    tracemalloc.start();start=time.monotonic();fit=fit_pool(10000,[(0,i,[2,0,6,0,2]) for i in range(1,10000)],0)
    rows=[estimate(fit,i,0,2500) for i in range(9950,10000)];seconds=time.monotonic()-start;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    report={'seed':7970,'reference':'SciPy trust-exact fit and dense sandwich covariance','reference_estimates':len(cases),
      'max_rating_error':max(r['rating_error'] for r in cases),'max_standard_error_error':max(r['se_error'] for r in cases),
      'coverage':coverage,'large_pool':{'participants':10000,'comparison_edges':len(fit['hessian']),'visible_estimates':len(rows),'elapsed_seconds_with_tracemalloc':seconds,'peak_traced_bytes':peak}}
    assert report['max_rating_error']<1e-4 and report['max_standard_error_error']<1e-4
    (ROOT/'test-output/ratings-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
