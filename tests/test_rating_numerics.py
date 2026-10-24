"""Regression for intermittent blank ratings in large, uneven live fields."""
import math
import random
import pytest
from arena.ratings import fit_pool, estimate, SCALE


def large_field():
    # A reproducible, partial 400-entry RR spanning a broad range of strengths.
    # The former total-loss subtraction stalled on seed 0 close to the optimum.
    rng=random.Random(0)
    strengths=[rng.uniform(-10,3) for _ in range(400)]
    rows=[]
    for a in range(400):
        for b in range(a+1,400):
            if rng.random()>.18:continue
            p=1/(1+math.exp(strengths[b]-strengths[a]));bins=[0]*5
            bins[sum(rng.random()<p for _ in range(4))]=1
            rows.append((a,b,bins))
    return rows


def assert_stationary(fit,rows,anchor):
    assert fit['status']=='ok'
    assert len(fit['members'])==400
    # Independently check the likelihood score equations, not a success flag.
    residual=[0.]*400;degree=[0]*400
    for a,b,bins in rows:
        difference=fit['theta'][fit['index'][a]]-fit['theta'][fit['index'][b]]
        expected=1/(1+math.exp(-difference))
        actual=sum(i*count/(len(bins)-1) for i,count in enumerate(bins))
        error=actual-sum(bins)*expected
        residual[a]+=error;residual[b]-=error
        degree[a]+=sum(bins);degree[b]+=sum(bins)
    assert max(abs(g)/d for i,(g,d) in enumerate(zip(residual,degree)) if i!=anchor)<1e-10
    assert fit['theta'][fit['index'][anchor]]==0
    # This field needs fewer than 15 Newton iterations, not repeated backtracking.
    assert fit['iterations']<15


def test_large_field_remains_rated_as_results_arrive():
    rows=large_field()
    for added in range(9):
        current=rows[:len(rows)-8+added]
        fit=fit_pool(400,current,0)
        assert_stationary(fit,current,0)
        for slot in (1,199,399):
            value=estimate(fit,slot,0,3586)
            assert value['status']=='estimated'
            assert value['ci'][0]<value['rating']<value['ci'][1]


def test_large_field_is_invariant_to_order_color_and_anchor():
    rows=large_field();first=fit_pool(400,rows,0)
    assert_stationary(first,rows,0)
    reordered=[(b,a,list(reversed(bins))) for a,b,bins in reversed(rows)]
    second=fit_pool(400,reordered,199)
    assert_stationary(second,reordered,199)
    offset=first['theta'][first['index'][199]]
    for slot in range(400):
        delta=(first['theta'][first['index'][slot]]-offset)*SCALE
        assert second['theta'][second['index'][slot]]*SCALE==pytest.approx(delta,abs=1e-5)
