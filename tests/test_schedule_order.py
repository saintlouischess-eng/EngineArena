"""Launch order is a permutation, not a change to tournament conditions/results."""
from collections import Counter
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys

import chess
import pytest
from arena.store import Store,DEFAULTS
from arena.models import scheduled_pairs
from arena.custom_matchups import pair
from arena.schedule_order import canonical,interleaved,rr_index,shuffled
from arena.opening_policy import round_pair
from test_core import profile


def create(s,order='balanced',fmt='round_robin',n=8,**kw):
    openings=[]
    for move in chess.Board().legal_moves:
        b=chess.Board();b.push(move)
        openings.append({'fen':b.fen(),'name':move.uci(),'moves':[move.uci()],'start_fen':chess.STARTING_FEN})
    cfg={'format':fmt,'schedule_order':order,'schedule_seed':2718,'cycles':3,
         'opening_policy':'pair','opening_order':'shuffle','seed':42,'rounds':3,'cpu_budget':8,'memory_budget_mb':1024,**kw}
    return s.create_tournament(order,[profile(str(i)) for i in range(n)],cfg,openings,backup=False)


@pytest.mark.parametrize('fmt',['round_robin','gauntlet','self_play'])
@pytest.mark.parametrize('policy',['pair','round','cycle','fixed'])
def test_static_orders_are_complete_permutations_with_balanced_cycles(fmt,policy):
    for n in range(2,16):
        for candidates in ({1,n//2,n-1} if fmt=='gauntlet' else {1}):
            s=DEFAULTS|dict(format=fmt,cycles=3,candidates=candidates,opening_policy=policy)
            total=scheduled_pairs(n,fmt,3,candidates)
            for order in ('balanced','matchup','shuffle'):
                cfg=s|{'schedule_order':order}
                sequence=[canonical(i,n,cfg) for i in range(total)]
                assert sorted(sequence)==list(range(total))
                if fmt=='round_robin' and order=='balanced':
                    per=n//2
                    for start in range(0,total,per):
                        engines=[v for k in sequence[start:start+per] for v in pair(k,n,cfg)[:2]]
                        assert len(engines)==len(set(engines))
            if fmt=='round_robin':
                for i in range(n*(n-1)//2):
                    a,b,_=round_pair(i,n,fmt,1)
                    assert rr_index(a,b,n)==i


def test_seeded_shuffle_and_ragged_interleave_are_bounded_and_repeatable():
    for count in (1,2,3,15,16,17,501,4097):
        values=[shuffled(i,count,1234) for i in range(count)]
        assert sorted(values)==list(range(count))
        assert values==[shuffled(i,count,1234) for i in range(count)]
        if count>3:assert values!=[shuffled(i,count,4567) for i in range(count)]
    for counts in ((1,5,2),(1000000,2,100),tuple(range(1,10))):
        prefix=[interleaved(i,counts) for i in range(min(sum(counts),200))]
        assert len(set(prefix))==len(prefix)
    assert [interleaved(i,(1,3,2)) for i in range(6)]==[0,1,4,2,5,3]
    assert 0<=shuffled(9238475,49995000000000,7)<49995000000000


@pytest.mark.parametrize('order',['balanced','matchup','shuffle'])
@pytest.mark.parametrize('paired',[False,True])
def test_reordered_games_preserve_canonical_openings_colors_counts_and_replays(tmp_path,order,paired):
    with contextlib.closing(Store(tmp_path)) as s:
        old=create(s,'legacy',paired=paired,cycles=2);new=create(s,order,paired=paired,cycles=2)
        sequences=[]
        for t in (old,new):
            s.set_state(t['id'],'running');s.fill_queue(t['id'],t['total'])
            seq=[]
            while g:=s.claim(t['id']):
                seq.append(g['number']);s.finish(g['aid'],'1/2-1/2','fixture')
            sequences.append(seq)
        fields='number,pair_no,leg,a,b,white,black,round,opening'
        assert s.rows('SELECT '+fields+' FROM games WHERE tid=? ORDER BY number',(old['id'],))==s.rows('SELECT '+fields+' FROM games WHERE tid=? ORDER BY number',(new['id'],))
        assert len(set(sequences[1]))==new['total']
        if order!='matchup':assert sequences[0]!=sequences[1]
        if order=='balanced':
            first=s.rows('SELECT white,black FROM games WHERE tid=? ORDER BY schedule_index LIMIT ?',(new['id'],4*(2 if paired else 1)))
            assert Counter(v for g in first for v in g.values())==Counter({i:2 if paired else 1 for i in range(8)})
        snap=s.snapshot(new['id']);assert snap['official_games']==new['total']
        if paired:assert snap['complete_pairs']==new['total']//2
        s.set_state(new['id'],'paused');gid=s.one('SELECT id FROM games WHERE tid=? ORDER BY schedule_index LIMIT 1',(new['id'],))['id']
        before=s.one('SELECT opening,schedule_index,official FROM games WHERE id=?',(gid,))
        s.requeue(new['id'],[gid],mode='replacement');s.set_state(new['id'],'running')
        g=s.claim(new['id']);assert g['id']==gid
        s.finish(g['aid'],'1-0','fixture')
        after=s.one('SELECT opening,schedule_index,official FROM games WHERE id=?',(gid,))
        assert (before['opening'],before['schedule_index'])==(after['opening'],after['schedule_index'])
        assert before['official']!=after['official'] and s.snapshot(new['id'])['official_games']==new['total']
        assert s.one('SELECT count(*) n FROM attempts WHERE gid=?',(gid,))['n']==2


@pytest.mark.parametrize('order',['balanced','shuffle'])
@pytest.mark.parametrize('fmt',['swiss','knockout','double_elimination','ladder'])
def test_dynamic_formats_order_within_committed_rounds_and_survive_restart(tmp_path,order,fmt):
    s=Store(tmp_path)
    try:
        t=create(s,order,fmt=fmt,knockout_tiebreak='seed',cycles=2);tid=t['id']
        s.set_state(tid,'running');s.fill_queue(tid,4)
        first=s.claim(tid);s.finish(first['aid'],'1-0','fixture')
        s.close();s=Store(tmp_path);assert s.snapshot(tid)['official_games']==1
        s.set_state(tid,'running');seen={first['id']}
        for step in range(500):
            s.fill_queue(tid,6);current=s.tournament(tid)
            if current['state']=='completed':break
            game=s.claim(tid);assert game
            assert game['id'] not in seen;seen.add(game['id'])
            assert not s.one("SELECT 1 FROM games WHERE tid=? AND round<? AND state IN ('running','pending')",(tid,game['round']))
            s.finish(game['aid'],'1-0' if game['white']<game['black'] else '0-1','fixture')
        else:raise AssertionError('format did not finish')
        assert s.snapshot(tid)['official_games']==len(seen)
        assert not s.rows("SELECT * FROM games WHERE tid=? AND state IN ('running','pending')",(tid,))
    finally:s.close()


def test_balanced_does_not_wait_for_previous_round_and_resource_limits_still_apply(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        t=create(s,cycles=1);s.set_state(t['id'],'running');s.fill_queue(t['id'],4)
        first=s.claim(t['id']);later=[]
        for i in range(16):
            s.fill_queue(t['id'],4)
            picked=s.dispatch(t['id'],{'threads':1,'memory_mb':2,'gpu':{}},t['settings'])
            g=picked['game'];assert g and g['id']!=first['id'];later.append(g['number']);s.finish(g['aid'],'1-0','fixture')
        assert s.one('SELECT state FROM games WHERE id=?',(first['id'],))['state']=='running'
        assert len(later)==16
        assert not s.dispatch(t['id'],{'threads':8,'memory_mb':0,'gpu':{}},t['settings'])['game']


def test_large_balanced_and_shuffle_materialize_only_small_window(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        for order in ('balanced','shuffle'):
            t=create(s,order,n=10000,cycles=1000000);s.set_state(t['id'],'running');s.fill_queue(t['id'],32)
            assert t['total']==99990000000000
            assert s.one('SELECT count(*) n FROM games WHERE tid=?',(t['id'],))['n']==32
            assert s.tournament(t['id'])['cursor']==16


def test_forced_exit_recovers_exact_shuffle_and_committed_results(tmp_path):
    root=Path(__file__).resolve().parents[1];script=tmp_path/'crash.py';data=tmp_path/'data'
    script.write_text("""import os,sys,json
from arena.store import Store
s=Store(sys.argv[1]);t=s.create_tournament('Recovery',[{'name':str(i)} for i in range(8)],{'format':'round_robin','schedule_order':'shuffle','schedule_seed':199,'cycles':3},backup=False)
s.set_state(t['id'],'running');s.fill_queue(t['id'],12)
for _ in range(3):
 g=s.claim(t['id']);s.finish(g['aid'],'1-0','fixture')
g=s.claim(t['id'])
open(sys.argv[2],'w').write(json.dumps({'tid':t['id'],'gid':g['id'],'aid':g['aid']}))
os._exit(73)
""",encoding='utf-8')
    env=os.environ|{'PYTHONPATH':str(root)};record=tmp_path/'record.json'
    result=subprocess.run([sys.executable,str(script),str(data),str(record)],env=env,timeout=30)
    assert result.returncode==73
    ids=json.loads(record.read_text())
    with contextlib.closing(Store(data)) as s:
        assert s.snapshot(ids['tid'])['official_games']==3
        assert s.one('SELECT reason FROM attempts WHERE id=?',(ids['aid'],))['reason']=='interrupted'
        s.set_state(ids['tid'],'running');assert s.claim(ids['tid'])['id']==ids['gid']
        games=s.rows('SELECT number,schedule_index FROM games WHERE tid=? ORDER BY schedule_index',(ids['tid'],))
        cfg=s.tournament(ids['tid'])['settings']
        assert all(g['number']//2==canonical(g['schedule_index']//2,8,cfg) for g in games)


def test_invalid_schedule_settings_rejected(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        for changes in ({'schedule_order':'invalid'},{'schedule_seed':True},{'schedule_seed':-1},{'schedule_seed':2147483648}):
            with pytest.raises(ValueError):create(s,**changes)


@pytest.mark.parametrize('order',['balanced','matchup','shuffle'])
def test_custom_matchups_preserve_unequal_counts(tmp_path,order):
    with contextlib.closing(Store(tmp_path)) as s:
        matchups=[{'a':0,'b':1,'count':1},{'a':2,'b':3,'count':5},{'a':0,'b':3,'count':2}]
        t=create(s,order,fmt='custom',n=4,custom_matchups=matchups)
        s.set_state(t['id'],'running');s.fill_queue(t['id'],32)
        assert s.one('SELECT count(*) n FROM games')['n']==16
        counts=Counter()
        while g:=s.claim(t['id']):counts[(g['a'],g['b'])]+=1;s.finish(g['aid'],'1-0','fixture')
        assert counts=={(0,1):2,(2,3):10,(0,3):4}


def test_event_override_and_source_inheritance(tmp_path):
    from test_events import command
    from test_league_update import definition,drive
    with contextlib.closing(Store(tmp_path)) as s:
        t=create(s,n=6)
        for order in ('source','shuffle'):
            e=s.event_call('create',order,t['id'],definition(schedule_order=order,schedule_seed=23))
            body=s.event_call('get',e['id'])['body']
            assert body['settings']['schedule_order']==('balanced' if order=='source' else order)
            result=drive(s,e['id'])
            assert result['state']=='completed'
            children=s.rows('SELECT t.settings FROM tournaments t JOIN event_children c ON c.tid=t.id WHERE c.eid=?',(e['id'],))
            assert all(json.loads(c['settings'])['schedule_order']==body['settings']['schedule_order'] for c in children)
        assert s.tournament(t['id'])['settings']['schedule_order']=='balanced'


@pytest.mark.parametrize('order',['balanced','shuffle'])
def test_replacement_archives_partial_tiebreak_batches_without_losing_other_matches(tmp_path,order):
    with contextlib.closing(Store(tmp_path)) as s:
        t=create(s,order,fmt='knockout',n=4,cycles=1,playoff_cycles=10,knockout_tiebreak='continuous')
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,8)
        originals=[]
        while g:=s.claim(tid):originals.append(g);s.finish(g['aid'],'1/2-1/2','fixture')
        s.fill_queue(tid,2)  # only part of both tied matches' next batch exists
        s.set_state(tid,'paused')
        r=s.requeue(tid,[originals[0]['id']],mode='replacement');assert r['dependency']
        s.requeue(tid,[originals[0]['id']],mode='replacement',invalidate=True)
        s.set_state(tid,'running')
        for _ in range(150):
            s.fill_queue(tid,4)
            if s.tournament(tid)['state']=='completed':break
            g=s.claim(tid);assert g
            s.finish(g['aid'],'1-0' if g['white']<g['black'] else '0-1','fixture')
        else:raise AssertionError('corrected knockout did not finish')
        assert s.one('SELECT count(*) n FROM attempts WHERE gid=?',(originals[0]['id'],))['n']==2
        assert all(s.one('SELECT id FROM attempts WHERE id=?',(g['aid'],)) for g in originals)
