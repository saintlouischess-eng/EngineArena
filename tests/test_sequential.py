import json
import pytest
from arena.store import Store
from arena.stats import sprt_llr

def make(store,extra=None):
    return store.create_tournament('SPRT',[{'name':'A'},{'name':'B'}],{'format':'sprt','cycles':100,'sprt':{'elo0':-100,'elo1':100,'alpha':.1,'beta':.1},**(extra or {})})

def complete_pair(s,tid,win=True):
    s.fill_queue(tid,4)
    for _ in range(2):
        g=s.claim(tid)
        if g is None:return
        s.finish(g['aid'],'1-0' if (g['white']==0)==win else '0-1','checkmate')

def test_stopping_evidence_survives_drain_restart_and_replacement(tmp_path):
    s=Store(tmp_path);t=make(s);tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,40)
    # Pre-claim a later pair to simulate processes in flight at the boundary.
    in_flight=[s.claim(tid) for _ in range(4)]
    for g in in_flight[:2]:s.finish(g['aid'],'1-0' if g['white']==0 else '0-1','checkmate')
    while not s.snapshot(tid)['sprt'].get('frozen'):complete_pair(s,tid)
    stopped=s.snapshot(tid)['sprt'];assert stopped['decision']=='H1';assert s.claim(tid) is None
    for g in in_flight[2:]:s.finish(g['aid'],'0-1' if g['white']==0 else '1-0','checkmate')
    assert s.snapshot(tid)['sprt']==stopped
    with pytest.raises(ValueError,match='stopping boundary'):s.set_state(tid,'running')
    s.close();s=Store(tmp_path)
    assert s.snapshot(tid)['sprt']==stopped
    s.set_state(tid,'paused');s.requeue(tid,[in_flight[0]['id']],mode='replacement')
    assert s.snapshot(tid)['sprt']['decision']=='invalidated'
    s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','stalemate')
    assert s.snapshot(tid)['sprt']['previous']==stopped
    assert s.one("SELECT count(*) n FROM audit WHERE action='sprt_stopped'")['n']==1
    s.close()

def test_retry_pair_enters_sequential_sample_once(tmp_path):
    s=Store(tmp_path);t=make(s,{'retry_limit':1});s.set_state(t['id'],'running');s.fill_queue(t['id'],4)
    a,b=s.claim(t['id']),s.claim(t['id']);s.finish(a['aid'],'0-1','crash');s.finish(b['aid'],'1/2-1/2','stalemate')
    assert s.snapshot(t['id'])['sprt'].get('samples',0)==0
    retry=s.claim(t['id']);assert retry['id']==a['id'];s.finish(retry['aid'],'1-0','checkmate')
    state=s.snapshot(t['id'])['sprt'];assert state['samples']==1 and state['bins']==[0,0,0,1,0]
    s.close()

def test_likelihood_symmetry_and_wald_bounds():
    a=sprt_llr([11,17,40,32,25],-10,10);b=sprt_llr([25,32,40,17,11],-10,10)
    assert a['llr']==pytest.approx(-b['llr'],abs=1e-10)
    assert a['lower']==pytest.approx(-a['upper'])
