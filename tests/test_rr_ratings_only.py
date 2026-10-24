"""Equal-field RR standings with immutable historical rating evidence."""
from collections import Counter, defaultdict
from contextlib import closing
import json
import pytest

from arena.store import Store
from arena import rr_roster
from arena.tournament_extend import preview, extend
from arena.tournament_report import render
from test_core import profile
from test_rr_withdraw_live import finish_dispatch, play_some
from test_workflow_plus import pgn


def assert_rankings(s,tid):
    games=s.rows('''SELECT g.white,g.black,a.result FROM games g JOIN attempts a ON a.id=g.official
        WHERE g.tid=? AND g.invalid=0''',(tid,))
    points=defaultdict(float);wins=Counter();black_wins=Counter();count=Counter()
    for g in games:
        w,b=g['white'],g['black'];score={'1-0':1,'0-1':0,'1/2-1/2':.5}[g['result']]
        points[w]+=score;points[b]+=1-score;count.update([w,b])
        if score==1:wins[w]+=1
        if score==0:wins[b]+=1;black_wins[b]+=1
    bh=defaultdict(float);sb=defaultdict(float)
    for g in games:
        w,b=g['white'],g['black'];score={'1-0':1,'0-1':0,'1/2-1/2':.5}[g['result']]
        bh[w]+=points[b];bh[b]+=points[w];sb[w]+=score*points[b];sb[b]+=(1-score)*points[w]
    extended=s.one('SELECT extended FROM ranking_meta WHERE tid=?',(tid,))['extended']
    for r in s.rows('SELECT * FROM rankings WHERE tid=?',(tid,)):
        i=r['slot']
        assert (r['score'],r['wins'],r['black_wins'],r['buchholz'],r['sb'])==(points[i],wins[i],black_wins[i],bh[i] if extended else 0,sb[i] if extended else 0)
    return count


@pytest.mark.parametrize('paired',[True,False])
@pytest.mark.parametrize('order',['balanced','shuffle','matchup','legacy'])
@pytest.mark.parametrize('mode',['catch_up','balanced','after_existing'])
def test_replacements_keep_ratings_and_finish_equal(tmp_path,paired,order,mode):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Equal field',[profile(str(i)) for i in range(8)],
            {'format':'round_robin','cycles':2,'paired':paired,'schedule_order':order,'opening_policy':'round',
             'tiebreaks':['buchholz','sonneborn_berger','wins','black_wins']},backup=False);tid=t['id']
        s.set_state(tid,'running')
        for i in range(17):
            s.fill_queue(tid,2);g=s.claim(tid)
            s.finish(g['aid'],['1-0','0-1','1/2-1/2'][i%3],'illegal_move' if i%3==0 else 'fixture')
        s.set_state(tid,'paused')
        old_attempts=s.rows('SELECT * FROM attempts ORDER BY id');old_rc=s.rows('SELECT * FROM rc_games ORDER BY gid')
        old_pgn=list(map(str,pgn(s,tid)));old_games=s.rows('SELECT * FROM games WHERE official IS NOT NULL ORDER BY id')
        removed=[0,3,6];new=[profile('new'+str(i)) for i in removed]
        excluded=sum(bool(set(removed)&{g['white'],g['black']}) for g in old_games)
        v=rr_roster.preview(s,tid,removed,new,mode,'ratings_only')
        assert v['excluded_games']==excluded and v['retained_games']==17-excluded
        assert v['total_games']==t['total'] and v['games_per_active_engine']==14*(2 if paired else 1)
        assert v['canceled_games']==v['additional_games']-excluded
        rr_roster.change(s,tid,removed,new,v['expected'],mode,'ratings_only')
        assert s.tournament(tid)['state']=='paused'
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==old_rc
        assert s.rows('SELECT * FROM attempts ORDER BY id')==old_attempts
        assert list(map(str,pgn(s,tid,1)))==old_pgn
        assert_rankings(s,tid)
        for g in old_games:
            current=s.game_detail(g['id'])
            assert current['official']==g['official']
            if not set(removed)&{g['white'],g['black']}:assert s.one('SELECT * FROM games WHERE id=?',(g['id'],))==g
        s.close();s=Store(tmp_path)
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==old_rc
        finish_dispatch(s,tid,set(removed))
        assert set(assert_rankings(s,tid).values())=={v['games_per_active_engine']}
        assert len(s.snapshot(tid)['standings'])==8
        assert s.one('SELECT count(*) n FROM rc_games')['n']==t['total']+excluded
        assert len(pgn(s,tid))==t['total'] and list(map(str,pgn(s,tid,1)))==old_pgn
        assert 'historical ratings remain recorded' in render(s.path,tid,all_engines=True,technical=False)
        ids=json.dumps([r['gid'] for r in old_rc])
        assert s.rows('SELECT * FROM rc_games WHERE gid IN (SELECT value FROM json_each(?)) ORDER BY gid',(ids,))==old_rc
    finally:s.close()


def test_convert_previous_withdrawals_and_policy_token_guard(tmp_path,monkeypatch):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('Convert',[profile(str(i)) for i in range(5)],{'format':'round_robin','cycles':1},backup=False);tid=t['id']
        play_some(s,tid,3);old=s.rows('SELECT * FROM rc_games ORDER BY gid')
        v=rr_roster.preview(s,tid,[0])
        with pytest.raises(ValueError,match='Preview'):rr_roster.change(s,tid,[0],[],v['expected'],result_policy='ratings_only')
        with pytest.raises(ValueError,match='Unknown'):rr_roster.preview(s,tid,[0],result_policy='typo')
        rr_roster.change(s,tid,[0],[],v['expected'])
        v=rr_roster.preview(s,tid,[],result_policy='ratings_only')
        assert v['excluded_games']==3 and v['total_games']==12 and v['canceled_games']==0
        tables=['games','attempts','rankings','aggregates','rr_revisions','rr_revision_games','tournaments','rc_games','engine_failures','game_counts']
        before={table:s.rows('SELECT * FROM '+table+' ORDER BY 1') for table in tables}
        audit=s.audit;monkeypatch.setattr(s,'audit',lambda *args:(_ for _ in ()).throw(RuntimeError('rollback')))
        with pytest.raises(RuntimeError,match='rollback'):rr_roster.change(s,tid,[],[],v['expected'],result_policy='ratings_only')
        assert {table:s.rows('SELECT * FROM '+table+' ORDER BY 1') for table in tables}==before
        monkeypatch.setattr(s,'audit',audit)
        rr_roster.change(s,tid,[],[],v['expected'],result_policy='ratings_only')
        assert s.tournament(tid)['settings']['rr_withdrawn_retained']==[]
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==old
        play_some(s,tid,3)
        v=rr_roster.preview(s,tid,[1],[profile('later')],result_policy='ratings_only')
        rr_roster.change(s,tid,[1],[profile('later')],v['expected'],result_policy='ratings_only')
        finish_dispatch(s,tid,{0,1})
        assert set(assert_rankings(s,tid).values())=={6}
        rc=s.rows('SELECT * FROM rc_games ORDER BY gid')
        s.delete_tournament(tid,'Convert',True)
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==rc


def test_400_entry_seven_replacements_preview(tmp_path):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('400',[profile(str(i)) for i in range(400)],{'format':'round_robin','cycles':1},backup=False);tid=t['id']
        play_some(s,tid,3)
        new=[profile('new'+str(i)) for i in range(7)]
        v=rr_roster.preview(s,tid,list(range(7)),new,'catch_up','ratings_only')
        assert v['total_games']==159600 and v['games_per_active_engine']==798
        assert v['additional_games']==5544
        rr_roster.change(s,tid,list(range(7)),new,v['expected'],'catch_up','ratings_only')
        revised=s.tournament(tid)
        assert revised['active_participants']==400
        assert s.one('SELECT count(*) n FROM games')['n']<=6
        # Decode the entire 400-entry revised schedule without creating games.
        from arena.tournament_extend import canonical,pair
        active=set(revised['settings']['rr_active_slots']);matchups=Counter();counts=Counter()
        for index in range(revised['schedule_total']//2):
            a,b,_=pair(canonical(index,revised['slot_count'],revised['settings']),revised['slot_count'],revised['settings'])
            if a in active and b in active:matchups[tuple(sorted((a,b)))]+=1;counts[a]+=2;counts[b]+=2
        assert len(matchups)==79800 and set(matchups.values())=={1}
        assert len(counts)==400 and set(counts.values())=={798}


def test_excluded_completed_replay_and_pending_attempts_stay_archived(tmp_path):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('Replay',[profile(str(i)) for i in range(4)],{'format':'round_robin','cycles':1},backup=False);tid=t['id']
        play_some(s,tid,1);g=s.one('SELECT * FROM games WHERE official IS NOT NULL');old=s.rows('SELECT * FROM rc_games')
        s.requeue(tid,[g['id']],mode='replacement')
        v=rr_roster.preview(s,tid,[g['white']],result_policy='ratings_only')
        rr_roster.change(s,tid,[g['white']],[],v['expected'],result_policy='ratings_only')
        assert s.one('SELECT invalid,state,official FROM games WHERE id=?',(g['id'],))==dict(invalid=1,state='completed',official=g['official'])
        assert s.requeue(tid,[g['id']],mode='replacement')['queued']==0
        assert s.rows('SELECT * FROM rc_games')==old
        finish_dispatch(s,tid,{g['white']})
        assert set(assert_rankings(s,tid).values())=={4}
