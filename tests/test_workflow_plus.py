"""1.10 lifecycle tests use only disposable workspaces."""
from contextlib import closing
from collections import Counter
import json

import chess
import pytest

from arena.store import Store
from arena.tournament_extend import preview, extend
from arena import rr_roster, activity
from arena.pgn_export import OfficialPgnReader
from arena.rating_center_report import report
from arena.ratings import pool_report
from arena.reports import crosstable
from arena.tournament_report import render
from test_core import profile, read_pgn
from test_tournament_extend import completed, finish


def pgn(s,tid,revision=None):
    with closing(OfficialPgnReader(s.path,tid,roster_revision=revision)) as reader:
        chunks=[]
        while chunk:=reader.chunk():chunks.append(chunk)
    return read_pgn(b''.join(chunks).decode())


@pytest.mark.parametrize('replacement',[False,True])
@pytest.mark.parametrize('paired',[False,True])
def test_roster_revision_preserves_evidence_and_sparse_slots(tmp_path,replacement,paired):
    with closing(Store(tmp_path)) as s:
        t=completed(s,5,cycles=1,paired=paired,tiebreaks=['buchholz','sonneborn_berger','wins']);tid=t['id']
        attempts=s.rows('SELECT * FROM attempts ORDER BY id');ratings=s.rows('SELECT * FROM rc_games ORDER BY gid')
        new=[profile('replacement')] if replacement else []
        v=rr_roster.preview(s,tid,[0,2],new)
        with pytest.raises(ValueError,match='Preview'):rr_roster.change(s,tid,[0,2],new,'stale')
        rr_roster.change(s,tid,[0,2],new,v['expected'])
        assert s.rows('SELECT * FROM attempts ORDER BY id')==attempts
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==ratings
        assert len(pgn(s,tid,1))==len(attempts)
        assert len(pgn(s,tid))==3*(2 if paired else 1)
        if replacement:finish(s,tid)
        active=[1,3,4]+([5] if replacement else [])
        snap=s.snapshot(tid);n=len(active)
        assert snap['official_games']==n*(n-1)//2*(2 if paired else 1)
        assert {r['slot'] for r in snap['standings']}==set(active)
        assert all(r['games']==(n-1)*(2 if paired else 1) for r in snap['standings'])
        assert all(r['buchholz']==pytest.approx((n-1)**2*(2 if paired else 1)**2/2) for r in snap['standings'])
        assert crosstable(s.path,tid)['total']==n
        pool=pool_report(s.path,tid);assert pool['participant_count']==n and pool['anchor']['slot']==1
        assert all(r['rating'] is not None for r in pool['items'])
        assert 'Tiebreak values and ranking explanation' in render(s.path,tid,technical=False)
        old_count=len(ratings)
        assert s.one('SELECT count(*) n FROM rc_games')['n']==old_count+v['additional_games']
        # A second extension after sparse withdrawal cannot recycle old game IDs.
        add=[profile('next')];v=preview(s,tid,add);extend(s,tid,add,v['expected']);finish(s,tid)
        games=s.rows('SELECT white,black FROM games WHERE invalid=0')
        active.append(6 if replacement else 5)
        assert Counter(tuple(sorted((g['white'],g['black']))) for g in games)==Counter({(a,b):(2 if paired else 1) for a in active for b in active if a<b})


@pytest.mark.parametrize('mode',['catch_up','balanced','after_existing'])
@pytest.mark.parametrize('order',['legacy','balanced','shuffle','matchup'])
def test_ongoing_addition_dispatch_complete_restart(tmp_path,mode,order):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Ongoing',[profile(str(i)) for i in range(4)],{'format':'round_robin','cycles':1,'schedule_order':order},backup=False);tid=t['id']
        s.set_state(tid,'running');s.fill_queue(tid,6)
        for _ in range(4):g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','fixture')
        s.set_state(tid,'paused');old=s.rows('SELECT * FROM attempts ORDER BY id');v=preview(s,tid,[profile('new')],mode)
        extend(s,tid,[profile('new')],v['expected'],mode)
        assert s.rows('SELECT * FROM attempts ORDER BY id')==old
        s.close();s=Store(tmp_path);s.set_state(tid,'running')
        used={'threads':0,'memory_mb':0,'gpu':{}};limits={'cpu_budget':4,'memory_budget_mb':8192,'gpu_limits':{}}
        seen=[]
        for _ in range(60):
            s.fill_queue(tid,2);r=s.dispatch(tid,used,limits)
            if not r['game']:break
            g=r['game'];seen.append((g['white'],g['black']));s.finish(g['aid'],'1/2-1/2','fixture')
        assert len(seen)==16
        if mode=='catch_up':assert 4 in seen[0]
        if mode=='after_existing':assert all(4 not in pair for pair in seen[:8])
        assert s.snapshot(tid)['official_games']==20
        assert Counter(tuple(sorted(p)) for p in seen+[(g['white'],g['black']) for g in s.rows('SELECT white,black FROM games WHERE official IN (SELECT value FROM json_each(?))',(json.dumps([a['id'] for a in old]),))])==Counter({(a,b):2 for a in range(5) for b in range(a+1,5)})
    finally:s.close()


def test_activity_does_not_count_shutdown_or_sleep_as_uptime(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Activity',[profile('a'),profile('b')],{},backup=False);tid=t['id']
    def observe(stamp,active=()):s.activity_due=0;activity.observe(s,active,stamp)
    observe(100);observe(110);s.set_state(tid,'running');observe(120,[tid]);observe(130,[tid]);s.set_state(tid,'paused');observe(140);observe(150)
    assert {r['state']:r['seconds'] for r in activity.report(s,tid)['totals']}['active']==20
    s.close();s=Store(tmp_path);observe(300);observe(310);observe(500);observe(510)
    r=activity.report(s);assert r['sessions']==3 and r['totals'][0]['seconds']==70 and r['unobserved_seconds']==340
    s.close()


def test_exact_profile_aliases_survive_rename_and_source_deletion(tmp_path):
    with closing(Store(tmp_path)) as s:
        profiles=[s.save_profile(profile('Named '+str(i))|{'identity':{'name':'Protocol '+str(i)}}) for i in range(2)]
        t=s.create_tournament('Aliases',profiles,{'format':'round_robin','cycles':1},backup=False);tid=t['id'];finish(s,tid)
        original=s.rows('SELECT * FROM rc_games ORDER BY gid');r=report(s.path,{'category':'blitz'})
        assert r['items'] and all(x['profile_names'] and len(x['short_id'])>=12 for x in r['items'])
        s.save_profile(profiles[0]|{'name':'New display alias'})
        r=report(s.path,{'category':'blitz','q':'New display alias'})
        assert any('New display alias' in x['profile_names'] for x in r['items'])
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==original
        s.delete_tournament(tid,'Aliases',True)
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==original
        assert any('New display alias' in x['profile_names'] for x in report(s.path,{'category':'blitz'})['items'])
    with closing(Store(tmp_path)) as s:
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==original
        assert any('New display alias' in x['profile_names'] for x in report(s.path,{'category':'blitz'})['items'])


def test_ongoing_requires_fully_drained_and_dry_run_has_no_game_writes(tmp_path):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('Drain',[profile('a'),profile('b')],{'format':'round_robin'},backup=False);tid=t['id']
        s.set_state(tid,'running');s.fill_queue(tid,2);g=s.claim(tid);s.set_state(tid,'paused')
        with pytest.raises(ValueError,match='draining'):preview(s,tid,[profile('new')])
        s.finish(g['aid'],'1/2-1/2','fixture');v=preview(s,tid,[profile('new')]);extend(s,tid,[profile('new')],v['expected']);s.set_state(tid,'running')
        before=s.rows('SELECT * FROM games ORDER BY id')
        r=s.dispatch(tid,{'threads':0,'memory_mb':0,'gpu':{}},{'cpu_budget':4,'memory_budget_mb':8192,'gpu_limits':{}},dry_run=True)
        assert r['game'] and s.rows('SELECT * FROM games ORDER BY id')==before


def test_withdrawal_replacement_is_atomic_and_retained_after_restart(tmp_path,monkeypatch):
    with closing(Store(tmp_path)) as s:
        t=completed(s,4,cycles=1);tid=t['id'];ratings=s.rows('SELECT * FROM rc_games ORDER BY gid')
        v=rr_roster.preview(s,tid,[1],[profile('replacement')]);original=s.audit
        def fail(*args):raise RuntimeError('injected transaction failure')
        monkeypatch.setattr(s,'audit',fail)
        with pytest.raises(RuntimeError):rr_roster.change(s,tid,[1],[profile('replacement')],v['expected'])
        assert s.snapshot(tid)['official_games']==12 and not rr_roster.history(s,tid)
        monkeypatch.setattr(s,'audit',original);rr_roster.change(s,tid,[1],[profile('replacement')],v['expected'])
    with closing(Store(tmp_path)) as s:
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==ratings
        finish(s,tid);assert s.snapshot(tid)['official_games']==12
        assert len(pgn(s,tid,1))==12


def test_primary_move_hint_is_legal_and_position_bound():
    from arena.search_history import intention
    b=chess.Board();hint=intention(b,'e2e4 e7e5');assert hint['from']=='e2' and hint['to']=='e4' and hint['fen']==b.fen()
    assert intention(b,'e2e5') is None and intention(b,'0000') is None
    b=chess.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',chess960=True)
    assert intention(b,'e1h1')['to']=='g1'


@pytest.mark.parametrize('paired',[True,False])
def test_early_additions_reserve_unmaterialized_shared_opening_rounds(tmp_path,paired):
    with closing(Store(tmp_path)) as s:
        openings=[{'fen':chess.Board.from_chess960_pos(i).fen(),'name':str(i)} for i in range(200)]
        t=s.create_tournament('Shared rounds',[profile(str(i)) for i in range(6)],{'format':'round_robin','cycles':2,'chess960':True,'paired':paired,'opening_policy':'round','schedule_order':'balanced'},openings,backup=False);tid=t['id']
        s.set_state(tid,'running');s.fill_queue(tid,1);g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','fixture');s.set_state(tid,'paused')
        for name in ['first','second']:
            v=preview(s,tid,[profile(name)]);extend(s,tid,[profile(name)],v['expected'])
        finish(s,tid)
        rows=s.rows('SELECT white,black,opening FROM games')
        groups=[set() for _ in range(3)]
        for row in rows:
            latest=max(row['white'],row['black']);group=0 if latest<6 else latest-5
            groups[group].add(json.loads(row['opening'])['assignment'])
        assert all(groups) and not groups[0]&groups[1] and not groups[1]&groups[2] and not groups[0]&groups[2]
