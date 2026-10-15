"""All-tournament monitoring preserves separate queue/event ownership."""
import asyncio
import contextlib
import json

import pytest
from aiohttp.test_utils import TestClient, TestServer
from arena.server import create_app
from arena.store import Store
from test_league_update import create, definition
from test_events import command
from test_shared_tournaments import draft, setup


def view(s,**kw):return s.queue_call('page',scope='all',**kw)


@pytest.mark.parametrize('parallel',[False,True])
def test_all_stages_visible_without_enrolling_in_queue(tmp_path,parallel):
    with contextlib.closing(Store(tmp_path)) as s:
        queued=draft(s,'Independent');s.queue_call('add',[queued])
        if parallel:setup(s)
        e=create(s);command(s,e['id'],'run');s.event_call('tick');s.event_call('tick')
        before=s.rows('SELECT * FROM tournament_queue')
        p=view(s);assert p['total']==1 and p['filtered_total']==5 and p['overview']
        assert p['active_event']['id']==e['id'] and p['active_event']['resources']==definition()['resources']
        stages=[r for r in p['items'] if r['event_id']]
        assert len(stages)==3 and all(not r['queued'] and r['state']=='running' for r in stages)
        assert s.rows('SELECT * FROM tournament_queue')==before
        tid=stages[0]['tid'];s.fill_queue(tid,2);g=s.claim(tid)
        row=next(r for r in view(s)['items'] if r['tid']==tid)
        assert (row['active_games'],row['official_games'])==(1,0)
        s.finish(g['aid'],'1/2-1/2','fixture')
        row=next(r for r in view(s)['items'] if r['tid']==tid)
        assert (row['active_games'],row['official_games'],row['total'])==(0,1,2)
        assert view(s,status='active')['filtered_total']==3
        assert s.queue_call('page',scope='queue')['filtered_total']==1
        assert s.queue_call('page',scope='events')['filtered_total']==3
        assert len(s.queue_call('page')['items'])==1  # legacy queue contract
        for action in ('pause','finish_current'):
            with pytest.raises(ValueError,match='event controls'):
                s.queue_call('command',action,s.queue_call('summary')['revision'])
        assert s.event_call('detail',e['id'])['state']=='running'
        assert s.tournament(tid)['state']=='running'
        s.set_concurrency(tid,3)
        assert next(r for r in view(s)['items'] if r['tid']==tid)['game_limit']==3


def test_filters_sorting_archives_and_committed_counters(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);command(s,e['id'],'run');s.event_call('tick');s.event_call('tick')
        stages=view(s,status='active')['items'];tid=stages[0]['tid']
        s.fill_queue(tid,2);g=s.claim(tid);s.finish(g['aid'],'1-0','fixture')
        assert view(s,sort='progress',direction='desc')['items'][0]['tid']==tid
        s.execute('UPDATE event_children SET valid=0 WHERE tid=?',(tid,))
        assert tid not in {r['tid'] for r in view(s)['items']}
        assert view(s,status='archived')['items'][0]['tid']==tid
        s.execute("UPDATE tournaments SET state='paused',started_once=1 WHERE id=?",(stages[1]['tid'],))
        assert view(s,status='paused')['items'][0]['tid']==stages[1]['tid']
        assert view(s,search='Template')['filtered_total']==1
        assert not view(s,search='%')['items']
        assert not view(s,search='_')['items']
        for kwargs in ({'scope':'bad'},{'status':'bad'},{'sort':'DROP TABLE'},{'direction':'bad'}):
            with pytest.raises(ValueError):s.queue_call('page',**({'scope':'all'}|kwargs))


def test_bounded_paging_large_list_without_game_materialization(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        for i in range(121):draft(s,f'Draft {i:03}')
        page=view(s,offset=50,sort='name',direction='desc')
        assert page['filtered_total']==121 and len(page['items'])==50
        assert page['items'][0]['name']=='Draft 070'
        assert view(s,offset=100)['filtered_total']==121 and len(view(s,offset=100)['items'])==21
        assert not s.rows('SELECT * FROM games') and not s.rows('SELECT * FROM tournament_queue')
        assert len(s._manager_game_limits)<=256


def test_overview_api_does_not_change_event_or_saved_tournament(tmp_path):
    async def run():
        app=await create_app(tmp_path,'overview-test')
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'overview-test'}) as client:
            t=await app['db'].call('create_tournament','Unstarted',[{'name':'A'},{'name':'B'}],{'cycles':1},backup=False)
            response=await client.get('/api/tournament-queue?scope=all')
            assert response.status==200
            body=await response.json();assert body['items'][0]['tid']==t['id'] and not body['items'][0]['queued']
            assert body['total']==0 and body['filtered_total']==1
            assert (await app['db'].call('tournament',t['id']))['can_edit']
            assert (await client.get('/api/tournament-queue?scope=invalid')).status==400
    asyncio.run(run())
