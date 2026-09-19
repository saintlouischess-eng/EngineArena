from collections import Counter,defaultdict
import json
import random
import pytest
from arena.store import Store
from arena.models import scheduled_pairs
from arena.rounds import build_plan,context,swiss_matches,manual_round,manual_winner,match_key,ladder_positions
from arena.rankings import rebuild_extended

def profiles(n):return [{'name':str(i)} for i in range(n)]

def finish_window(s,tid,result='1/2-1/2',window=64):
    s.fill_queue(tid,window);games=[]
    while g:=s.claim(tid):
        value=result(g) if callable(result) else result;s.finish(g['aid'],value,'fixture');games.append(g)
    return games

def state(s,tid,round_no):return json.loads(s.one('SELECT body FROM round_state WHERE tid=? AND round=?',(tid,round_no))['body'])

def test_swiss_complete_field_and_no_rematch(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Swiss',profiles(8),{'format':'swiss','cycles':1,'rounds':7,'paired':False,'tiebreaks':['buchholz','sonneborn_berger','seed']});tid=t['id'];s.set_state(tid,'running')
    pairs=set();colors=Counter()
    for round_no in range(7):
        games=finish_window(s,tid)
        assert len(games)==4
        for g in games:
            pair=frozenset((g['a'],g['b']));assert pair not in pairs;pairs.add(pair);colors[g['white']]+=1;colors[g['black']]-=1
        assert s.tournament(tid)['round']==round_no
    s.fill_queue(tid,64);assert s.tournament(tid)['state']=='completed';assert len(pairs)==28
    assert max(abs(v) for v in colors.values())<=3
    s.close()

def test_matching_repairs_nonlocal_greedy_trap():
    # A perfect matching exists, but choosing edge 0-1 first prevents it.
    pool=list(range(6));allowed={(0,1),(0,2),(1,3),(2,3),(2,4),(3,5)};opponents=defaultdict(set)
    for a in pool:
        for b in pool:
            if a!=b and tuple(sorted((a,b))) not in allowed:opponents[a].add(b)
    matches,byes=swiss_matches(pool,dict.fromkeys(pool,0),dict(enumerate(pool)),Counter(),defaultdict(list),opponents,Counter())
    assert len(matches)==3 and not byes and len(set(sum((list(p) for p in matches),[])))==6

def test_byes_points_separate_from_rated_games_and_reversible(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Swiss',profiles(5),{'format':'swiss','cycles':2,'rounds':3,'paired':True,'tiebreaks':['buchholz','sonneborn_berger','seed']});tid=t['id'];s.set_state(tid,'running')
    first=finish_window(s,tid);second=finish_window(s,tid);assert len(first)==len(second)==8
    assert state(s,tid,0)['byes']!=state(s,tid,1)['byes']
    r=s.snapshot(tid)['standings'];assert sum(x['bye_points'] for x in r)==8;assert sum(x['games'] for x in r)==32
    before=s.rows('SELECT slot,buchholz,sb FROM rankings WHERE tid=? ORDER BY slot',(tid,));rebuild_extended(s,tid)
    assert before==s.rows('SELECT slot,buchholz,sb FROM rankings WHERE tid=? ORDER BY slot',(tid,))
    s.set_state(tid,'paused');s.requeue(tid,[first[0]['id']],mode='replacement',invalidate=True)
    assert sum(x['bye_points'] for x in s.snapshot(tid)['standings'])==4
    before=s.rows('SELECT slot,buchholz,sb FROM rankings WHERE tid=? ORDER BY slot',(tid,));rebuild_extended(s,tid)
    assert before==s.rows('SELECT slot,buchholz,sb FROM rankings WHERE tid=? ORDER BY slot',(tid,));s.close()

def test_manual_swiss_recovers_impossible_rematch_free_round(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Swiss',profiles(2),{'format':'swiss','cycles':1,'rounds':2});tid=t['id'];s.set_state(tid,'running');finish_window(s,tid);s.fill_queue(tid,8)
    assert s.tournament(tid)['state']=='paused' and s.tournament(tid)['dependency']
    with pytest.raises(ValueError,match='rematches'):manual_round(s,tid,[[1,0]],[],False)
    manual_round(s,tid,[[1,0]],[],True);assert not s.tournament(tid)['dependency'];s.set_state(tid,'running');games=finish_window(s,tid);assert len(games)==2 and games[0]['white']==1;s.close()

@pytest.mark.parametrize('n',[2,3,5,8,9])
def test_seeded_single_elimination_and_totals(tmp_path,n):
    s=Store(tmp_path);t=s.create_tournament('KO',profiles(n),{'format':'knockout','cycles':1,'paired':False});tid=t['id'];s.set_state(tid,'running');games=[]
    for _ in range(12):
        games+=finish_window(s,tid)
        if s.tournament(tid)['state']=='completed':break
    assert len(games)==n-1 and s.tournament(tid)['total']==n-1 and s.tournament(tid)['note']=='Winner: 0'
    if n==5:assert set(state(s,tid,0)['byes'])=={0,1,2}
    s.close()

@pytest.mark.parametrize('reset',[False,True])
def test_double_elimination_final_reset_requires_two_losses(tmp_path,reset):
    s=Store(tmp_path);t=s.create_tournament('Double',profiles(2),{'format':'double_elimination','cycles':1,'paired':False});tid=t['id'];s.set_state(tid,'running');games=[]
    for r in range(5):
        winner=1 if reset and r==1 else 0
        games+=finish_window(s,tid,lambda g:'1-0' if g['white']==winner else '0-1')
        if s.tournament(tid)['state']=='completed':break
    assert len(games)==(3 if reset else 2) and s.tournament(tid)['note']=='Winner: 0';s.close()

def test_knockout_playoff_pairs_and_manual_fallback(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Playoffs',profiles(2),{'format':'knockout','cycles':1,'paired':True,'knockout_tiebreak':'playoff','playoff_limit':1,'playoff_cycles':2,'playoff_fallback':'manual'});tid=t['id'];s.set_state(tid,'running')
    regular=finish_window(s,tid);playoff=finish_window(s,tid);assert len(regular)==2 and len(playoff)==4 and s.tournament(tid)['total']==6
    assert len({g['pair_no'] for g in regular+playoff})==3
    s.fill_queue(tid,64);assert s.tournament(tid)['state']=='paused'
    manual_winner(s,tid,0,1,1);s.set_state(tid,'running');s.fill_queue(tid,64);assert s.tournament(tid)['note']=='Winner: 1';s.close()

def test_round_materialization_is_bounded_for_many_cycles(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Large round',profiles(1000),{'format':'swiss','cycles':100,'rounds':5});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,64)
    assert s.one('SELECT count(*) n FROM games WHERE tid=?',(tid,))['n']==64
    assert sum(c['count'] for c in state(s,tid,0)['chunks'])==50000
    assert s.tournament(tid)['total']==500000;s.close()

def test_ladder_challenges_move_winner_and_total_is_exact(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Ladder',profiles(6),{'format':'ladder','cycles':1,'rounds':4,'paired':False,'ladder_distance':2,'ladder_swap':'leap'});tid=t['id'];s.set_state(tid,'running');games=[]
    for r in range(5):
        games+=finish_window(s,tid,lambda g:'1-0' if g['white']>g['black'] else '0-1')
        if s.tournament(tid)['state']=='completed':break
    expected=sum(len(ladder_positions(6,r,2)[0]) for r in range(4));assert len(games)==expected==t['total'];assert state(s,tid,1)['ladder_order']!=list(range(6));s.close()

def test_self_play_counts_real_games_once(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Self',profiles(2),{'format':'self_play','cycles':2});tid=t['id'];s.set_state(tid,'running');games=finish_window(s,tid,'1-0')
    snap=s.snapshot(tid);assert len(games)==8 and snap['official_games']==8 and snap['complete_pairs']==4
    assert sum(r['games'] for r in snap['standings'])==8 and all(r['elo'] is None for r in snap['standings'])
    assert all(r['elo'] is None and r['ci95'] is None and r['los'] is None for r in s.h2h(tid,0));s.close()


def test_last_ladder_result_updates_final_order_and_replacement(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Final ladder',profiles(2),{'format':'ladder','cycles':1,'rounds':1,'paired':False});tid=t['id'];s.set_state(tid,'running')
    games=finish_window(s,tid,lambda g:'1-0' if g['white']==1 else '0-1');s.fill_queue(tid,8)
    assert s.tournament(tid)['state']=='completed' and [r['slot'] for r in s.snapshot(tid)['standings']]==[1,0]
    s.close();s=Store(tmp_path);assert [r['slot'] for r in s.snapshot(tid)['standings']]==[1,0]
    s.requeue(tid,[games[0]['id']],mode='replacement');assert 'final_ladder_order' not in state(s,tid,0)
    s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1-0' if g['white']==0 else '0-1','replacement');s.fill_queue(tid,8)
    assert [r['slot'] for r in s.snapshot(tid)['standings']]==[0,1];assert s.snapshot(tid)['official_games']==1;s.close()

def test_replacement_invalidates_same_round_playoffs_and_decision(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Playoffs',profiles(2),{'format':'knockout','cycles':1,'knockout_tiebreak':'playoff','playoff_limit':1,'playoff_fallback':'manual'});tid=t['id'];s.set_state(tid,'running')
    original=finish_window(s,tid);playoffs=finish_window(s,tid);s.fill_queue(tid,64);manual_winner(s,tid,0,1,1)
    effect=s.requeue(tid,[original[0]['id']],mode='replacement');assert effect['dependency'] and effect['effects']['playoffs']
    s.requeue(tid,[original[0]['id']],mode='replacement',invalidate=True)
    assert s.snapshot(tid)['official_games']==2 and s.snapshot(tid)['complete_pairs']==1
    assert not state(s,tid,0)['manual_winners'];assert state(s,tid,0)['playoffs']['0:1']==[]
    assert all(s.game_detail(g['id'])['invalid'] and s.game_detail(g['id'])['attempts'] for g in playoffs)
    s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1-0' if g['white']==0 else '0-1','replacement')
    s.fill_queue(tid,64);assert s.tournament(tid)['note']=='Winner: 0' and s.tournament(tid)['total']==2;s.close()

def test_round_plan_is_rejected_when_inputs_change(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Swiss',profiles(4),{'format':'swiss','cycles':1});tid=t['id'];s.set_state(tid,'running');first=finish_window(s,tid)
    plan=build_plan(context(s,s.tournament(tid)));s.set_state(tid,'paused');s.requeue(tid,[first[0]['id']],mode='replacement');s.set_state(tid,'running')
    assert not s.apply_round_plan(plan);assert s.tournament(tid)['round']==0;s.close()


@pytest.mark.parametrize('n',[3,5,9,16,31])
@pytest.mark.parametrize('paired',[False,True])
def test_larger_double_elimination_keeps_every_loser_until_second_loss(tmp_path,n,paired):
    s=Store(tmp_path);t=s.create_tournament('Two losses',profiles(n),{'format':'double_elimination','cycles':1,'paired':paired,'seeding':'random','seed':n});tid=t['id'];s.set_state(tid,'running')
    losses=Counter();rng=random.Random(n);match_count=0;completed=[]
    for _ in range(n*3):
        s.fill_queue(tid,8)
        if s.tournament(tid)['state']=='completed':break
        saved=state(s,tid,s.tournament(tid)['round']);matches=saved['matches'];flat=[a for pair in matches for a in pair]+saved['byes']
        assert len(flat)==len(set(flat)) and set(flat)=={a for a in range(n) if losses[a]<2}
        chosen={match_key(a,b):rng.choice((a,b)) for a,b in matches};round_games=[]
        while True:
            while g:=s.claim(tid):
                assert losses[g['white']]<2 and losses[g['black']]<2
                winner=chosen[match_key(g['a'],g['b'])];s.finish(g['aid'],'1-0' if g['white']==winner else '0-1','fixture');round_games.append(g)
            current=state(s,tid,s.tournament(tid)['round'])
            if all(c['materialized']==c['count'] for c in current['chunks']):break
            s.fill_queue(tid,8)
        assert len(round_games)==len(matches)*(2 if paired else 1)
        if paired:
            for no in {g['pair_no'] for g in round_games}:
                a,b=sorted([g for g in round_games if g['pair_no']==no],key=lambda g:g['leg'])
                assert (a['white'],a['black'])==(b['black'],b['white']) and a['opening']==b['opening']
        for a,b in matches:losses[b if chosen[match_key(a,b)]==a else a]+=1
        match_count+=len(matches);completed.extend(round_games)
    assert s.tournament(tid)['state']=='completed'
    champion=[a for a in range(n) if losses[a]<2];assert len(champion)==1
    assert all(losses[a]==2 for a in range(n) if a!=champion[0]) and match_count in (2*n-2,2*n-1)
    assert s.tournament(tid)['note']==f'Winner: {champion[0]}' and s.snapshot(tid)['official_games']==len(completed)
    s.close()


@pytest.mark.parametrize('n',[7,16,31])
def test_swiss_mixed_scores_unique_fields_byes_and_colors(tmp_path,n):
    s=Store(tmp_path);t=s.create_tournament('Mixed Swiss',profiles(n),{'format':'swiss','cycles':1,'rounds':6,'paired':False});tid=t['id'];s.set_state(tid,'running')
    seen=set();colors=Counter();byes=Counter();rng=random.Random(n)
    for round_no in range(6):
        games=finish_window(s,tid,lambda g:rng.choice(('1-0','0-1','1/2-1/2')))
        assert s.tournament(tid)['round']==round_no and len(games)==n//2
        saved=state(s,tid,round_no);flat=[a for g in games for a in (g['white'],g['black'])]+saved['byes'];assert len(flat)==n and set(flat)==set(range(n))
        byes.update(saved['byes'])
        for g in games:
            key=match_key(g['a'],g['b']);assert key not in seen;seen.add(key);colors[g['white']]+=1;colors[g['black']]-=1
    assert max(byes.values(),default=0)<=1 and max(map(abs,colors.values()))<=2
    s.fill_queue(tid,64);assert s.tournament(tid)['state']=='completed';s.close()
