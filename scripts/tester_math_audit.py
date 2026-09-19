"""Independent SciPy checks of every selectable confidence level and score model."""
from pathlib import Path
import json
import math
import sys
import numpy as np
from scipy.stats import norm

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from arena.stats import summarize
from scripts.statistics_validation import numerical

def logistic_elo(p):
    if p<=0:return '-infinity'
    if p>=1:return '+infinity'
    return float(400/np.log(10)*(np.log(p)-np.log1p(-p)))

def main():
    rng=np.random.default_rng(20260918);checks=0;largest=0.;los_relative=0.
    levels=[50,68,80,85,90,95,97.5,98,99,99.9,99.99]
    for categories in (3,5):
        for n in (2,10,100,1000):
            for _ in range(16):
                bins=rng.multinomial(n,rng.dirichlet(np.ones(categories))).tolist()
                samples=np.repeat(np.linspace(0,1,categories),bins)
                mean=float(np.mean(samples));se=float(np.std(samples,ddof=1)/np.sqrt(n))
                w,d,l=(bins[2],bins[1],bins[0]) if categories==3 else (bins[3]+2*bins[4],bins[1]+2*bins[2]+bins[3],2*bins[0]+bins[1])
                for confidence in levels:
                    result=summarize(w,d,l,bins if categories==5 else None,confidence)
                    refs={'elo':logistic_elo(mean),'ci_conservative':[logistic_elo(float(np.clip(mean+direction*np.sqrt(np.log(2/(1-confidence/100))/(2*n)),0,1))) for direction in (-1,1)]}
                    refs['ci']=[logistic_elo(float(np.clip(mean+direction*norm.ppf((1+confidence/100)/2)*se,0,1))) for direction in (-1,1)] if se>0 else None
                    for key,expected in refs.items():
                        actual=result[key]
                        for a,b in zip(actual if isinstance(actual,list) else [actual],expected if isinstance(expected,list) else [expected]):
                            if a is None or isinstance(a,str):assert a==b,(key,a,b)
                            else:
                                difference=abs(a-b);largest=max(largest,difference);assert difference<1e-7,(bins,confidence,key,a,b)
                    if se>0:
                        expected=float(100*norm.cdf((mean-.5)/se));actual=result['los']
                        assert math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-300),(actual,expected)
                        if expected:los_relative=max(los_relative,abs(actual-expected)/expected)
                    else:assert result['los'] is None
                    checks+=1
    tail=summarize(40,0,160)['los'];assert 0<tail<1e-10
    likelihood=numerical(np.random.default_rng(7970))
    assert likelihood['max_absolute_error']<1e-7
    report={'confidence_levels':levels,'independent_score_interval_cases':checks,'maximum_elo_or_bound_error':largest,
            'maximum_los_relative_error':los_relative,'small_los_percent_retained':tail,'independent_sprt_cases':likelihood['cases'],
            'maximum_sprt_llr_error':likelihood['max_absolute_error'],'reference':'Expanded observations, NumPy sample variance, SciPy normal quantiles/CDF; separate constrained likelihood optimizer'}
    (ROOT/'test-output/tester-math-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
