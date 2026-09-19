"""Independent constrained-optimization checks and fixed-sample CI simulation.

Run with .validation-venv after installing requirements-statistics.txt. SciPy
optimizes category probabilities directly, independently of the production
one-dimensional multiplier/bisection implementation.
"""
import json
import math
from pathlib import Path
import sys
import warnings
import numpy as np
import scipy
from scipy.optimize import minimize
from scipy.special import logsumexp
from scipy.stats import norm,binomtest

ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from arena.stats import sprt_llr,summarize


def optimized_log_likelihood(bins,target):
    w=np.maximum(.001,np.asarray(bins,dtype=float));total=w.sum();w/=total
    x=np.linspace(0,1,len(w));interior=min(target,1-target)/4
    q=np.full(len(w),interior/(len(w)-2));q[0]=1-target-interior/2;q[-1]=target-interior/2
    def log_prob(z):
        logits=np.r_[z,0.];return logits-logsumexp(logits)
    def objective(z):return -float(w@log_prob(z))
    def gradient(z):return np.exp(log_prob(z))[:-1]-w[:-1]
    def constraint(z):return float(np.exp(log_prob(z))@x-target)
    def constraint_jac(z):
        p=np.exp(log_prob(z));return p[:-1]*(x[:-1]-p@x)
    fit=minimize(objective,np.log(q[:-1]/q[-1]),jac=gradient,method='SLSQP',
      constraints=[{'type':'eq','fun':constraint,'jac':constraint_jac}],options={'ftol':1e-13,'maxiter':3000})
    if not fit.success or abs(constraint(fit.x))>1e-8:
        raise RuntimeError(f'Independent optimizer failed for {bins}: {fit.message}')
    return -float(total*fit.fun)


def numerical(rng):
    rows=[]
    cases=[[400,200,400],[50,800,150],[150,200,300,200,150],[30000,40000,140000,42000,32000],
      [0,0,99,1,0],[0,30,0],[1,0,0,0,99],[400,0,600]]
    for k in (3,5):
        for _ in range(32):cases.append(rng.multinomial(int(rng.integers(50,5000)),rng.dirichlet(np.ones(k)*2)).tolist())
    for bins in cases:
        for e0,e1 in [(0,5),(-20,20)]:
            ref=optimized_log_likelihood(bins,1/(1+10**(-e1/400)))-optimized_log_likelihood(bins,1/(1+10**(-e0/400)))
            actual=sprt_llr(bins,e0,e1)['llr'];error=abs(actual-ref)
            rows.append({'bins':bins,'elo0':e0,'elo1':e1,'expected_llr':ref,'actual_llr':actual,'absolute_error':error})
    return {'cases':len(rows),'max_absolute_error':max(r['absolute_error'] for r in rows),'rows':rows}


def confidence(rng,repetitions=50000):
    rows=[]
    for draw,rho,true_elo in [(0,0,0),(.5,0,5),(.5,.6,5),(.9,0,0),(.9,.6,0),(.99,.6,0)]:
        mean=1/(1+10**(-true_elo/400));single=np.array([(1-draw)/2-(mean-.5),draw,(1-draw)/2+(mean-.5)])
        probs=(1-rho)*np.convolve(single,single)+rho*np.array([single[0],0,single[1],0,single[2]])
        for n in (20,100,1000,10000):
            bins=rng.multinomial(n,probs,size=repetitions);scores=np.arange(5)/4
            means=bins@scores/n;variance=(bins@(scores*scores)-n*means*means)/(n-1);se=np.sqrt(np.maximum(0,variance)/n)
            available=se>0;covered=available&(np.abs(means-mean)<=norm.ppf(.975)*se)
            conservative_covered=np.abs(means-mean)<=math.sqrt(math.log(2/.05)/(2*n))
            ci=binomtest(int(covered.sum()),int(available.sum())).proportion_ci(confidence_level=.95,method='exact')
            rows.append({'draw_probability':draw,'within_pair_correlation_mixture':rho,'true_elo':true_elo,'pairs':n,
              'replications':repetitions,'interval_available_fraction':float(available.mean()),
              'coverage_when_available':float(covered.sum()/available.sum()),'coverage_mc_ci95':[ci.low,ci.high],
              'hoeffding_coverage':float(conservative_covered.mean())})
            # Compare production output against scipy's independent normal CDF,
            # generic repeated observations and sample standard deviation.
            for b in bins[:8]:
                sample=np.repeat(scores,b);avg=float(sample.mean());stderr=float(sample.std(ddof=1)/math.sqrt(n))
                result=summarize(0,2*n,0,[int(x) for x in b])
                if not stderr:assert result['ci95'] is None and result['los'] is None
                else:
                    expected=100*norm.cdf((avg-.5)/stderr);assert abs(result['los']-expected)<1e-9
                    for actual,bound in zip(result['ci95'],[avg-norm.ppf(.975)*stderr,avg+norm.ppf(.975)*stderr]):
                        target=400*math.log10(bound/(1-bound)) if 0<bound<1 else '+infinity' if bound>=1 else '-infinity'
                        assert actual==target if isinstance(target,str) else abs(actual-target)<1e-7
    return rows


def sequential():
    source=ROOT/'test-output/statistics-sprt-simulation.json'
    simulations=json.loads(source.read_text());rows=[];errors=[]
    for r in simulations:
        ci=binomtest(r['Errors'],r['Trials']).proportion_ci(confidence_level=.95,method='wilson')
        rows.append({'scenario':r['Scenario'],'trials':r['Trials'],'errors':r['Errors'],'unresolved':r['Unresolved'],
          'error_rate':r['Errors']/r['Trials'],'error_rate_mc_ci95':[ci.low,ci.high],'mean_samples':r['MeanSamples'],'max_samples':r['MaxSamples']})
        for checkpoint in r['Checkpoints']:
            actual=sprt_llr(checkpoint['Bins'],checkpoint['Elo0'],checkpoint['Elo1'])['llr']
            errors.append(abs(actual-checkpoint['Llr']))
    assert max(errors)<1e-6
    assert all(r['unresolved']==0 for r in rows)
    return {'trials':sum(r['trials'] for r in rows),'checkpoint_count':len(errors),'max_checkpoint_error':max(errors),'scenarios':rows,
      'all_nominal_rates_within_mc_ci95':all(r['error_rate_mc_ci95'][0]<=.05<=r['error_rate_mc_ci95'][1] for r in rows)}


def main():
    rng=np.random.default_rng(7970)
    report={'seed':7970,'numpy':np.__version__,'scipy':scipy.__version__,'optimizer':'SLSQP over logit probabilities with exact expected-score constraint'}
    report['numerical']=numerical(rng)
    print('Numerical likelihood checks:',report['numerical']['cases'],'max error:',report['numerical']['max_absolute_error'],flush=True)
    report['confidence']=confidence(rng)
    report['sequential']=sequential()
    if '--write-fixtures' in sys.argv:
        fixture={'seed':7970,'scipy':scipy.__version__,'optimizer':'SLSQP over logit probabilities with exact expected-score constraint',
          'cases':[{k:r[k] for k in ('bins','elo0','elo1','expected_llr')} for r in report['numerical']['rows']]}
        target=ROOT/'tests/fixtures/statistics_reference.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(fixture,indent=2),encoding='utf-8')
    output=ROOT/'test-output/statistics-validation.json';output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['numerical']['max_absolute_error']<1e-4
    print('Saved',output,flush=True)
    for r in report['confidence']:print(json.dumps(r),flush=True)
    print(json.dumps(report['sequential']),flush=True)

if __name__=='__main__':main()
