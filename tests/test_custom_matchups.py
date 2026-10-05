import contextlib
from collections import Counter
import pytest
from arena.store import Store,DEFAULTS
from arena.custom_matchups import validate,decode
from arena.opening_policy import capacity


@pytest.mark.parametrize('paired',[True,False])
def test_sparse_schedule_colors_pairs_and_replacement(tmp_path,paired):
    with contextlib.closing(Store(tmp_path)) as s:
        items=[{'a':0,'b':2,'count':3},{'a':1,'b':2,'count':2}]
        t=s.create_tournament('Custom',[{'name':str(i)} for i in range(4)],{'format':'custom','custom_matchups':items,'paired':paired,'opening_policy':'cycle'},backup=False)
        tid=t['id'];assert t['total']==5*(2 if paired else 1)
        assert not s.rows('SELECT * FROM games');s.set_state(tid,'running');s.fill_queue(tid,20)
        games=[]
        while g:=s.claim(tid):s.finish(g['aid'],'1/2-1/2','fixture');games.append(g)
        assert Counter(tuple(sorted((g['a'],g['b']))) for g in games)=={(0,2):3*(2 if paired else 1),(1,2):2*(2 if paired else 1)}
        if paired:
            assert all(games[i]['white']==games[i+1]['black'] and games[i]['opening']==games[i+1]['opening'] for i in range(0,len(games),2))
            assert s.snapshot(tid)['complete_pairs']==5
        else:assert [g['white'] for g in games]==[0,2,0,1,2]
        s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1-0','fixture')
        assert s.snapshot(tid)['official_games']==len(games)
        assert len(s.game_detail(g['id'])['attempts'])==2


@pytest.mark.parametrize('items',[[{'a':0,'b':0,'count':1}],[{'a':0,'b':9,'count':1}],[{'a':0,'b':1,'count':0}],[{'a':0,'b':1,'count':1},{'a':1,'b':0,'count':2}],[]])
def test_invalid_matchups(items):
    with pytest.raises(ValueError):validate(3,items)


def test_large_sparse_counts_and_resource_lookahead(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        p=[{'name':'GPU','threads':1,'hash':1,'gpu_group':'gpu0'},{'name':'CPU1','threads':1,'hash':1},{'name':'CPU2','threads':1,'hash':1}]
        t=s.create_tournament('Huge',p,{'format':'custom','custom_matchups':[{'a':0,'b':1,'count':1000000},{'a':1,'b':2,'count':2}]},backup=False)
        assert t['total']==2000004;s.set_state(t['id'],'running');s.fill_queue(t['id'],4)
        s0=t['settings'];assert decode(1000000,s0)[:3]==(1,2,0)
        out=s.dispatch(t['id'],{'threads':0,'memory_mb':0,'gpu':{'gpu0':1}},s0|{'cpu_budget':8,'memory_budget_mb':10000,'gpu_limits':{'gpu0':1}})
        assert {out['game']['white'],out['game']['black']}=={1,2}
        assert len(s.rows('SELECT * FROM games'))<=6


def test_custom_opening_capacity():
    s=DEFAULTS|{'format':'custom','custom_matchups':[{'a':0,'b':1,'count':5},{'a':0,'b':2,'count':2}],'opening_policy':'cycle'}
    r=capacity(3,3,s);assert r['required_positions']=='5' and r['games_before_reuse']=='10'
