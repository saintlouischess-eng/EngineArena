"""Withdrawal cancels future RR games, never played results or rating evidence."""
import asyncio
from collections import Counter
from contextlib import closing
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer

from arena.store import Store
from arena import rr_roster
from arena.tournament_extend import preview, extend
from arena.stat_exports import standings_csv
from arena.tournament_report import render
from arena.reports import crosstable
from test_core import profile, read_pgn
from test_workflow_plus import pgn

EMPTY={'threads':0,'memory_mb':0,'gpu':{}}
LIMITS={'cpu_budget':4,'memory_budget_mb':8192,'gpu_limits':{}}


def play_some(s,tid,count):
    s.set_state(tid,'running')
    for _ in range(count):
        s.fill_queue(tid,2);g=s.claim(tid)
        assert g
        s.finish(g['aid'],'1/2-1/2','fixture')
    s.set_state(tid,'paused')


def finish_dispatch(s,tid,forbidden):
    s.set_state(tid,'running');seen=[];scan=None
    for _ in range(3000):
        s.fill_queue(tid,2);r=s.dispatch(tid,EMPTY,LIMITS,scan,limit=3);scan=r['scan']
        if g:=r['game']:
            assert not forbidden.intersection((g['white'],g['black']))
            seen.append(g);s.finish(g['aid'],'1/2-1/2','fixture')
        t=s.tournament(tid)
        if t['cursor']*(2 if t['settings']['paired'] else 1)>=t['schedule_total'] and not s.one("SELECT 1 FROM games WHERE tid=? AND invalid=0 AND state IN ('pending','running')",(tid,)):break
    else:raise AssertionError('Remaining schedule did not finish')
    s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))
    assert s.snapshot(tid)['official_games']==s.tournament(tid)['total']
    return seen


@pytest.mark.parametrize('paired',[True,False])
@pytest.mark.parametrize('order',['legacy','balanced','shuffle','matchup'])
@pytest.mark.parametrize('mode',['catch_up','balanced','after_existing'])
def test_withdraw_after_early_addition_preserves_results_and_finishes(tmp_path,paired,order,mode):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Partial',[profile(str(i)) for i in range(5)],{'format':'round_robin','paired':paired,'cycles':2,'schedule_order':order,'opening_policy':'round','tiebreaks':['buchholz','sonneborn_berger']},backup=False);tid=t['id']
        play_some(s,tid,3)
        v=preview(s,tid,[profile('sixth')],mode);extend(s,tid,[profile('sixth')],v['expected'],mode)
        play_some(s,tid,2)
        old_games=s.rows('SELECT * FROM games WHERE official IS NOT NULL ORDER BY id')
        attempts=s.rows('SELECT * FROM attempts ORDER BY id');ratings=s.rows('SELECT * FROM rc_games ORDER BY gid')
        aggregates=s.rows('SELECT * FROM aggregates ORDER BY a,b');rankings=s.rows('SELECT * FROM rankings ORDER BY slot')
        old_pgn=pgn(s,tid);removed=[0,2,5]
        v=rr_roster.preview(s,tid,removed)
        assert v['keep_played'] and v['retained_games']==5 and v['excluded_games']==0
        assert v['canceled_games']==t['total']+10*(2 if paired else 1)-v['total_games']  # five incumbents × two cycles
        rr_roster.change(s,tid,removed,[],v['expected'])
        assert s.tournament(tid)['state']=='paused'
        assert s.rows('SELECT * FROM games WHERE official IS NOT NULL ORDER BY id')==old_games
        assert s.rows('SELECT * FROM attempts ORDER BY id')==attempts
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==ratings
        assert s.rows('SELECT * FROM aggregates ORDER BY a,b')==aggregates
        assert s.rows('SELECT * FROM rankings ORDER BY slot')==rankings
        assert len(pgn(s,tid))==len(old_pgn)==len(pgn(s,tid,2))==5
        snap=s.snapshot(tid)
        assert snap['participants']==6 and snap['active_participants']==3
        assert {r['slot'] for r in snap['standings'] if r['withdrawn']}==set(removed)
        assert 'withdrawn' in standings_csv(snap['standings']).splitlines()[0]
        assert 'Unplayed games were canceled' in render(s.path,tid,all_engines=True,technical=False)
        assert crosstable(s.path,tid)['total']==6
        # Retired entrants cannot be queued for a diagnostic/replacement replay.
        retired=[g['id'] for g in old_games if set(removed).intersection((g['white'],g['black']))]
        if retired:assert s.requeue(tid,retired,mode='replacement')['queued']==0
        s.close();s=Store(tmp_path)
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==ratings
        new=[profile('seventh')];v=preview(s,tid,new,mode)
        assert v['additional_games']==3*2*(2 if paired else 1)
        extend(s,tid,new,v['expected'],mode)
        finish_dispatch(s,tid,set(removed))
        active=[1,3,4,6]
        active_games=s.rows('SELECT white,black FROM games WHERE invalid=0 AND white IN (1,3,4,6) AND black IN (1,3,4,6)')
        assert Counter(tuple(sorted((g['white'],g['black']))) for g in active_games)==Counter({(a,b):2*(2 if paired else 1) for a in active for b in active if a<b})
        assert s.rows('SELECT * FROM games WHERE id IN (SELECT value FROM json_each(?)) ORDER BY id',(json.dumps([g['id'] for g in old_games]),))==old_games
        assert len(pgn(s,tid))==s.snapshot(tid)['official_games']
        assert s.one('SELECT count(*) n FROM rc_games')['n']==s.snapshot(tid)['official_games']
    finally:s.close()


def test_guards_rollback_replay_and_repeated_withdrawals(tmp_path,monkeypatch):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('Guards',[profile(str(i)) for i in range(5)],{'format':'round_robin','cycles':1},backup=False);tid=t['id']
        s.set_state(tid,'running');s.fill_queue(tid,5);g=s.claim(tid)
        with pytest.raises(ValueError,match='Pause and drain'):rr_roster.preview(s,tid,[0])
        s.set_state(tid,'paused')
        with pytest.raises(ValueError,match='draining'):rr_roster.preview(s,tid,[0])
        s.finish(g['aid'],'1-0','fixture');ratings=s.rows('SELECT * FROM rc_games')
        withdrawn=g['white'];s.requeue(tid,[g['id']],mode='replacement')
        v=rr_roster.preview(s,tid,[withdrawn]);tables=['games','attempts','aggregates','rankings','rr_revisions','rr_revision_games','tournaments','rc_games']
        before={name:s.rows('SELECT * FROM '+name+' ORDER BY 1') for name in tables}
        audit=s.audit
        monkeypatch.setattr(s,'audit',lambda *args:(_ for _ in ()).throw(RuntimeError('injected')))
        with pytest.raises(RuntimeError,match='injected'):rr_roster.change(s,tid,[withdrawn],[],v['expected'])
        assert {name:s.rows('SELECT * FROM '+name+' ORDER BY 1') for name in tables}==before
        monkeypatch.setattr(s,'audit',audit)
        s.set_concurrency(tid,3)
        with pytest.raises(ValueError,match='Preview'):rr_roster.change(s,tid,[withdrawn],[],v['expected'])
        v=rr_roster.preview(s,tid,[withdrawn]);rr_roster.change(s,tid,[withdrawn],[],v['expected'])
        assert s.game_detail(g['id'])['state']=='completed' and s.game_detail(g['id'])['official']==g['aid']
        assert s.rows('SELECT * FROM rc_games')==ratings
        with pytest.raises(ValueError,match='active entrants'):rr_roster.preview(s,tid,[withdrawn])
        more=[i for i in range(5) if i!=withdrawn][:2]
        v=rr_roster.preview(s,tid,more);rr_roster.change(s,tid,more,[],v['expected'])
        assert s.tournament(tid)['total']==3  # retained first game plus the remaining pair
        with pytest.raises(ValueError,match='two active'):rr_roster.preview(s,tid,[i for i in range(5) if i not in [withdrawn,*more]])
        finish_dispatch(s,tid,{withdrawn,*more})
        assert s.snapshot(tid)['official_games']==3


def test_large_implicit_schedule_cancellation_does_not_materialize_it(tmp_path):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('Scale',[profile(str(i)) for i in range(2000)],{'format':'round_robin','cycles':1},backup=False);tid=t['id']
        v=rr_roster.preview(s,tid,list(range(2,2000)))
        assert v['total_games']==2 and v['canceled_games']==3997998
        rr_roster.change(s,tid,list(range(2,2000)),[],v['expected'])
        assert s.one('SELECT count(*) n FROM games')['n']==0
        assert s.tournament(tid)['schedule_total']==3998000 and not s.tournament(tid)['can_edit']
        s.set_state(tid,'running');s.fill_queue(tid,2)
        assert s.one('SELECT count(*) n FROM games')['n']<=2


@pytest.mark.parametrize('mode',['catch_up','balanced','after_existing'])
def test_simultaneous_addition_and_later_completed_revision(tmp_path,mode):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('Mixed',[profile(str(i)) for i in range(4)],{'format':'round_robin','cycles':1},backup=False);tid=t['id']
        play_some(s,tid,1);old=s.rows('SELECT * FROM rc_games')
        additions=[profile('new')];v=rr_roster.preview(s,tid,[0],additions,mode)
        rr_roster.change(s,tid,[0],additions,v['expected'],mode)
        assert s.tournament(tid)['settings']['rr_admission']['mode']==mode
        assert s.rows('SELECT * FROM rc_games')==old
        finish_dispatch(s,tid,{0})
        assert s.tournament(tid)['total']==13
        # A completed-table revision now consistently excludes all withdrawn
        # entrants, including a previous keep-results withdrawal.
        v=rr_roster.preview(s,tid,[3]);rr_roster.change(s,tid,[3],[],v['expected'])
        assert s.snapshot(tid)['official_games']==s.tournament(tid)['total']==6
        assert s.snapshot(tid)['participants']==3 and s.tournament(tid)['active_participants']==3
        assert s.one('SELECT count(*) n FROM rc_games')['n']==13
        v=preview(s,tid,[profile('last')]);assert v['additional_games']==6


@pytest.mark.parametrize('result_policy',['keep','ratings_only'])
def test_api_pause_drain_withdraw_resume_and_finish(tmp_path,result_policy):
    from arena.server import create_app
    async def run():
        app=await create_app(tmp_path,'withdraw');db=app['db'];runner=app['runner']
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'withdraw'}) as client:
            ids=[]
            for i in range(4):
                p=await db.call('save_profile',profile(str(i),wait=.04)|{'hash':i+1,'options':{'Hash':i+1}});ids.append(p['id'])
            r=await client.post('/api/tournaments',json={'name':'Withdrawal workflow','profiles':ids,'settings':{'format':'round_robin','cycles':1,'max_plies':4,'concurrency':1}})
            assert r.status==200,await r.text()
            tid=(await r.json())['id'];url=f'/api/tournaments/{tid}'
            async def until(predicate):
                for _ in range(1500):
                    snap=await db.call('snapshot',tid)
                    assert not runner.error,runner.error
                    if predicate(snap):return snap
                    await asyncio.sleep(.02)
                raise AssertionError('Worker did not reach expected state')
            await client.post(url+'/action',json={'action':'start'})
            await until(lambda t:t['official_games']>=1)
            await client.post(url+'/action',json={'action':'pause'})
            snap=await until(lambda t:t['state']=='paused')
            assert snap['official_games']<12
            old=await db.call('rows','SELECT * FROM rc_games ORDER BY gid')
            body={'action':'revise','removed':[0],'profiles':[],'scheduling':'catch_up','result_policy':result_policy}
            r=await client.post(url+'/extend',json=body|{'preview':True});v=await r.json();assert r.status==200,v
            r=await client.post(url+'/extend',json=body|{'expected':v['expected']});assert r.status==200,await r.text()
            assert (await r.json())['state']=='paused'
            assert await db.call('rows','SELECT * FROM rc_games ORDER BY gid')==old
            await client.post(url+'/action',json={'action':'start'})
            final=await until(lambda t:t['state']=='completed')
            assert final['official_games']==v['total_games'] and final['active_participants']==3
            assert not db.store.warning and not db.store.failure
            await db.call('export_pending')
            games=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'))
            # The append-only automatic archive preserves excluded games too;
            # the on-demand current-tournament export follows revised standings.
            assert len(games)==final['official_games']+v['excluded_games']
            assert len(pgn(db.store,tid))==final['official_games']
            assert (await db.call('one','SELECT count(*) n FROM rc_games'))['n']==len(games)
    asyncio.run(run())
