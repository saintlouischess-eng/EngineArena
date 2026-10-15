import asyncio
import json
import sqlite3
import chess
import pytest
from aiohttp.test_utils import TestClient,TestServer
from arena.game_moves import read_moves,completion
from arena.profile_import import preview,commit,arguments
from arena.server import create_app
from arena.store import SavingError
from test_core import profile,tournament,run_claim,store


def test_scoresheet_pages_opening_numbering_and_attempt_isolation(store):
    board=chess.Board()
    history=['e2e4','e7e5','g1f3']
    for uci in history:board.push_uci(uci)
    t=store.create_tournament('Black to move',[profile('A'),profile('B')],{'cycles':1},[{'fen':board.fen(),'moves':history}])
    g=run_claim(store,t)
    for ply,uci in enumerate(['b8c6','f1b5','a7a6'],1):
        san=board.san(chess.Move.from_uci(uci));board.push_uci(uci)
        store.move(g['aid'],ply,uci,san,board.fen(),.23,{'white':{'remaining':42}}, {'depth':12,'nodes':100,'time':230,'cp':34})
    first=read_moves(store.path,g['id'],limit=2)
    assert [m['san'] for m in first['opening_moves']]==['e4','e5','Nf3']
    assert [m['label'] for m in first['items']]==['2…','3.']
    assert first['has_more'] and first['latest_ply']==3
    assert first['opening_moves'][-1]['crown_squares']==['h1','f3','g8','h8']
    assert first['items'][0]['crown_squares']==['h1','f3','g8','h8']
    assert first['opening_knight_facings']=={'b1':1,'f3':-1,'b8':1,'g8':-1}
    assert first['items'][0]['knight_facings']=={'b1':1,'f3':-1,'c6':1,'g8':-1}
    tail=read_moves(store.path,g['id'],after=2,limit=2)
    assert not tail['opening_moves'] and tail['items'][0]['san']=='a6' and not tail['has_more']
    assert tail['items'][0]['info']['cp']==34
    assert tail['items'][0]['crown_squares']==first['items'][-1]['crown_squares']
    assert tail['items'][0]['knight_facings']==first['items'][-1]['knight_facings']
    store.finish(g['aid'],'0-1','timeout');store.set_state(t['id'],'paused')
    store.requeue(t['id'],[g['id']],mode='diagnostic');store.set_state(t['id'],'running');second=store.claim(t['id'])
    latest=read_moves(store.path,g['id'])
    assert latest['attempt']['mode']=='diagnostic' and not latest['attempt']['official'] and latest['items']==[]
    assert latest['opening_crown_squares']==['h1','f3','g8','h8']
    assert latest['opening_knight_facings']==first['opening_knight_facings']
    old=read_moves(store.path,g['id'],aid=g['aid'])
    assert old['attempt']['official'] and len(old['items'])==3
    with pytest.raises(ValueError,match='does not belong'):read_moves(store.path,g['id'],aid='other')
    with pytest.raises(ValueError):read_moves(store.path,g['id'],limit=501)
    assert completion(store.path,t['id'])['failures'][0]=={'reason':'timeout','attempts':1,'official':1}


def test_scoresheet_does_not_invent_fen_history(store):
    board=chess.Board();board.push_san('e4')
    t=store.create_tournament('FEN',[profile('A'),profile('B')],{'cycles':1},[{'fen':board.fen()}]);g=run_claim(store,t)
    data=read_moves(store.path,g['id']);assert data['opening_moves']==[] and data['opening']['fen']==board.fen()
    assert data['opening_crown_squares']==[]
    assert data['opening_knight_facings']=={}


def test_import_formats_paths_and_transaction(store,tmp_path):
    engine=tmp_path/'engine folder'/'engine.exe';engine.parent.mkdir();engine.write_bytes(b'fixture')
    source=[{'name':'Cute profile','command':'engine folder/engine.exe','protocol':'uci','arguments':'--net "network with spaces.nnue"','options':[{'name':'Threads','value':2},{'name':'Hash','value':64},{'name':'Clear Hash','type':'button'}]},
            {'app':{'name':'Banksia profile','command':str(engine),'protocol':'uci'},'options':[{'name':'Threads','type':'spin','value':3,'default':1}]},
            {'app':{'name':'WinBoard','command':str(engine),'protocol':'wb'}},
            {'name':'Missing','command':'missing.exe','protocol':'uci'},
            {'name':'Unusual POV','command':str(engine),'protocol':'uci','whitepov':True}]
    body={'source':source,'base_dir':str(tmp_path)};p=preview(store,body)
    assert p['ready']==2 and [i['status'] for i in p['items']]==['ready','ready','skipped','skipped','skipped']
    first=p['items'][0]['profile'];assert first['threads']==2 and first['hash']==64
    assert first['args']==['--net','network with spaces.nnue'] and first['path']==str(engine)
    assert commit(store,body|{'selected':[0,1]})=={'count':2,'duplicates':0}
    assert commit(store,body|{'selected':[0,1]})=={'count':0,'duplicates':2}
    before=store.profiles()['total']
    with pytest.raises(ValueError):commit(store,body|{'selected':[0,3]})
    assert store.profiles()['total']==before
    source[0]['name']='Different settings';source[0]['options'][0]['value']=4
    assert commit(store,body|{'selected':[0]})['count']==1


def test_import_native_snapshots_and_option_injection(store,tmp_path):
    p=profile('Original');p['options']={'Hash':32};store.save_profile(p)
    source=[p,dict(p,name='Imported clone',id='Original'),dict(p,name='Bad',options={'Bad\nquit':3})]
    result=commit(store,{'source':source,'selected':[1]});assert result['count']==1
    assert store.one('SELECT name FROM profiles WHERE id=?',('Original',))['name']=='Original'
    assert preview(store,{'source':source})['items'][2]['status']=='skipped'
    assert preview(store,{'source':{'engines':[p]}})['total']==1


def test_quick_match_common_control_changes_snapshot_only(tmp_path):
    async def run():
        app=await create_app(tmp_path,'test');db=app['db'];app['runner'].scheduler.cancel();await asyncio.gather(app['runner'].scheduler,return_exceptions=True)
        a=await db.call('save_profile',profile('A')|{'time_control':{'kind':'depth','depth':5}})
        b=await db.call('save_profile',profile('B'))
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'test'}) as client:
            response=await client.post('/api/tournaments',json={'name':'Nodes quick match','profiles':[a['id'],b['id']],'common_control':True,'settings':{'cycles':2,'concurrency':1,'time_control':{'kind':'nodes','nodes':10000}}})
            assert response.status==200,await response.text()
            t=await response.json();assert t['total']==4 and t['state']=='paused'
            saved=await db.call('participant',t['id'],0);assert not saved.get('time_control')
            original=await db.call('one','SELECT body FROM profiles WHERE id=?',(a['id'],));assert json.loads(original['body'])['time_control']['depth']==5
            response=await client.get('/api/games/missing/moves');assert response.status==400
    asyncio.run(run())


def test_import_batch_rolls_back_and_option_order_is_irrelevant(store):
    source=[dict(profile('First'),options={'Hash':16,'Threads':1}),dict(profile('Second'),options={'Hash':32,'Threads':2})]
    store.db.execute("CREATE TRIGGER reject_second BEFORE INSERT ON profiles WHEN new.name='Second' BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
    with pytest.raises(SavingError):commit(store,{'source':source,'selected':[0,1]})
    assert store.profiles()['total']==0
    store.db.execute('DROP TRIGGER reject_second')
    assert commit(store,{'source':source,'selected':[0,1]})['count']==2
    source[0]['options']={'Threads':1,'Hash':16}
    assert preview(store,{'source':source})['ready']==0


def test_quick_node_match_runs_and_records_clock_free_moves(tmp_path):
    async def run():
        app=await create_app(tmp_path,'nodes');db=app['db']
        profiles=[(await db.call('save_profile',profile(n)|{'time_control':{'kind':'depth','depth':5}}))['id'] for n in ('A','B')]
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'nodes'}) as client:
            response=await client.post('/api/tournaments',json={'name':'Quick node acceptance','profiles':profiles,'common_control':True,'settings':{'cycles':1,'concurrency':1,'max_plies':6,'time_control':{'kind':'nodes','nodes':1000}}})
            assert response.status==200;tid=(await response.json())['id']
            assert (await client.post(f'/api/tournaments/{tid}/action',json={'action':'start'})).status==200
            for _ in range(200):
                await asyncio.sleep(.1);t=await db.call('snapshot',tid)
                if t['state']=='completed':break
            assert t['state']=='completed' and t['official_games']==2 and t['complete_pairs']==1
            for row in await db.call('rows','SELECT id FROM games WHERE tid=?',(tid,)):
                sheet=read_moves(db.store.path,row['id'])
                assert len(sheet['items'])==6 and sheet['attempt']['official']
                for m in sheet['items']:
                    assert all(c['control']['kind']=='nodes' and c['remaining'] is None for c in m['clocks'].values())
                assert sheet['attempt']['reason']=='max_plies_adjudication'
    asyncio.run(run())
