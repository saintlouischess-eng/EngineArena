import asyncio,json
from unittest.mock import patch
from aiohttp.test_utils import TestClient,TestServer
from arena import i18n
from arena.server import create_app

def test_report_messages_preserve_values_and_escape_translated_markup():
    with patch('arena.i18n.catalog',return_value={'Game {0}':'Partida {0}','White':'<Blancas>','Move {0}':'Jugada {0}'}):
        with i18n.using('es'):
            assert i18n.t('Game {0}','White')=='Partida White'
            assert i18n.h('<b>White</b><i>{0}</i>','White')=='<b>&lt;Blancas&gt;</b><i>White</i>'
            assert i18n.h('<span title="Move {0}">{1}</span>',4,'Draw')=='<span title="Jugada 4">Draw</span>'
            assert i18n.number(1234.5)=='1.234,5'
    assert i18n.current.get()=='en' and i18n.language([])=='en'

def test_locale_is_request_scoped_and_persisted_without_changing_tournament(tmp_path):
    async def run():
        app=await create_app(tmp_path,'test');db=app['db']
        app['runner'].scheduler.cancel();await asyncio.gather(app['runner'].scheduler,return_exceptions=True)
        tid=(await db.call('create_tournament','Draw <White>',[{'name':'Draw'},{'name':'White'}],{}))['id']
        before=await db.call('snapshot',tid)
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'test'}) as client:
            response=await client.post('/api/preferences',json={'language':'es','fontSize':18})
            assert response.status==200
            source=await (await client.get('/')).text()
            assert 'window.ARENA_LANGUAGE="es"' in source
            assert 'ArenaI18n.staticRoot(document.body)' in source
            for code in i18n.LANGUAGES:
                html=await (await client.get('/?lang='+code)).text()
                assert 'window.ARENA_LANGUAGE="'+code+'"' in html
            # Switching the presentation does not mutate settings or official data.
            after=await db.call('snapshot',tid)
            for key in ('settings','standings','official_games','complete_pairs','state'):assert before[key]==after[key]
            report=await (await client.get('/api/tournaments/'+tid+'/report',headers={'X-Arena-Language':'es'})).json()
            assert '<html lang="es">' in report['html'] and 'Draw &lt;White&gt;' in report['html']
            raw=await (await client.get('/api/tournaments/'+tid)).json()
            assert raw['name']=='Draw <White>'
    asyncio.run(run())


def test_all_languages_render_completed_results_and_leave_readout_math_unchanged(tmp_path):
    from arena.store import Store
    from arena.i18n import render_report
    s=Store(tmp_path)
    try:
        tid=s.create_tournament('Draw <White>',[{'name':'White'},{'name':'Draw'}],{})['id']
        s.set_state(tid,'running');s.fill_queue(tid,4)
        g=s.claim(tid);s.finish(g['aid'],'1-0','illegal_move')
        s.set_state(tid,'paused')
        original=s.snapshot(tid)
        for code in i18n.LANGUAGES:
            report=render_report(str(s.path),tid,locale=code)
            assert '<html lang="'+code+'">' in report
            assert 'Draw &lt;White&gt;' in report and '<td>White</td>' in report
            assert report.count('<table>')>=10
            assert '\ue100' not in report
        after=s.snapshot(tid)
        for key in ('settings','standings','official_games','complete_pairs','state'):assert original[key]==after[key]
    finally:s.close()


def test_switching_languages_during_node_only_play_keeps_original_attempts(tmp_path):
    import sys,time
    from pathlib import Path
    async def run():
        fixture=Path(__file__).with_name('fault_engine.py')
        transcript=tmp_path/'uci.txt'
        profiles=[{'name':name,'path':sys.executable,'args':[str(fixture),'--mode','strict_nodes','--wait','.06','--transcript',str(transcript)],'threads':1,'hash':1} for name in ('White','Draw')]
        app=await create_app(tmp_path,'live-test');db=app['db']
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'live-test'}) as client:
            t=await db.call('create_tournament','Language switch',profiles,{'cycles':1,'concurrency':1,'time_control':{'kind':'nodes','nodes':100},'max_plies':30})
            tid=t['id'];await db.call('set_state',tid,'running')
            deadline=time.monotonic()+20
            while not (await db.call('one','SELECT id FROM attempts WHERE ended IS NULL')):
                assert time.monotonic()<deadline;await asyncio.sleep(.05)
            for code in i18n.LANGUAGES:
                assert (await client.post('/api/preferences',json={'language':code})).status==200
                assert 'window.ARENA_LANGUAGE="'+code+'"' in await (await client.get('/')).text()
            while (await db.call('snapshot',tid))['official_games']<2:
                assert time.monotonic()<deadline;await asyncio.sleep(.05)
            attempts=await db.call('rows','SELECT seq,reason FROM attempts')
            assert len(attempts)==2 and all(a['seq']==1 and a['reason']!='illegal_move' for a in attempts)
            commands=[line for line in transcript.read_text().splitlines() if line.startswith('go ')]
            assert commands and all(line=='go nodes 100' for line in commands)
    asyncio.run(run())
