import json
import math
from pathlib import Path
import pytest
from arena.stats import summarize,sprt_llr,elo


def test_likelihood_matches_independent_scipy_optimization():
    fixture=json.loads((Path(__file__).parent/'fixtures/statistics_reference.json').read_text())
    for case in fixture['cases']:
        actual=sprt_llr(case['bins'],case['elo0'],case['elo1'])['llr']
        assert abs(actual-case['expected_llr'])<1e-7


@pytest.mark.parametrize('elo0,elo1',[(float('-inf'),5),(0,float('inf')),(True,5),(0,1e300),(float('nan'),5)])
def test_invalid_or_unrepresentable_sprt_hypotheses_rejected_before_play(elo0,elo1):
    with pytest.raises(ValueError):sprt_llr([0]*5,elo0,elo1)


def test_finite_sample_bounds_remain_available_for_degenerate_samples():
    assert summarize(0,0,0)['ci95_conservative'] is None
    assert summarize(0,2,0,[0,0,1,0,0])['ci95_conservative']==['-infinity','+infinity']
    result=summarize(0,200,0,[0,0,100,0,0]);radius=math.sqrt(math.log(40)/200)
    assert result['ci95'] is None and result['los'] is None
    assert result['ci95_conservative']==[elo(.5-radius),elo(.5+radius)]
    # Exactly enumerate independent bounded extreme outcomes: completed pairs
    # scoring 0 or 2 points. This stresses the largest possible score variance.
    for n in (1,5,20,100):
        radius=math.sqrt(math.log(40)/(2*n))
        for truth in (.01,.1,.5,.9,.99):
            coverage=sum(math.comb(n,w)*truth**w*(1-truth)**(n-w) for w in range(n+1) if abs(w/n-truth)<=radius)
            assert coverage>=.95-1e-12
