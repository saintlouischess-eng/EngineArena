import asyncio
import contextlib
import csv
import io
import chess
from aiohttp.test_utils import TestClient,TestServer
from arena.reports import opening_report,crosstable
from arena.server import create_app
from arena.store import Store


def setup(s):
    board=chess.Board();board.push_uci('e2e4')
    t=s.create_tournament('Opening evidence',[{'name':'Alpha'},{'name':'Beta'}],{'cycles':2},[
      {'name':'Same name','fen':chess.STARTING_FEN},{'name':'Same name','fen':board.fen()}])
    tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,4);games=[]
    for result in ('1-0','0-1','1/2-1/2','1-0'):
        g=s.claim(tid);s.finish(g['aid'],result,'fixture');games.append(g)
    return tid,games


def test_opening_color_official_replacement_and_restart(tmp_path):
    s=Store(tmp_path);tid,games=setup(s)
    r=opening_report(s.path,tid,0)
    assert r['summary']=={'games':4,'wins':2,'draws':1,'losses':1,'score_pct':62.5,'draw_pct':25}
    assert [(c['color'],c['score_pct']) for c in r['colors']]==[('White',75),('Black',50)]
    assert len(r['openings'])==2 and [o['complete_pairs'] for o in r['openings']]==[1,1]
    cross=crosstable(s.path,tid);cell=next(c for c in cross['cells'] if c['a']==0 and c['b']==1)
    assert cell['wins']==2 and cell['draws']==1 and cell['losses']==1 and cell['pairs']==2
    assert r['openings'][0]['fen']!=r['openings'][1]['fen'] # same labels remain distinct openings
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='diagnostic');s.set_state(tid,'running')
    g=s.claim(tid);s.finish(g['aid'],'0-1','diagnostic_fixture')
    assert opening_report(s.path,tid,0)==r
    s.set_state(tid,'paused');s.requeue(tid,[g['id']],mode='replacement');s.set_state(tid,'running')
    g=s.claim(tid);s.finish(g['aid'],'0-1','replacement_fixture')
    revised=opening_report(s.path,tid,0)
    assert revised['summary']['games']==4 and revised['summary']['score_pct']==37.5 and revised['revision']>r['revision']
    assert next(c for c in crosstable(s.path,tid)['cells'] if c['a']==0 and c['b']==1)['score_pct']==37.5
    assert sum(o['complete_pairs'] for o in revised['openings'])==2
    white=opening_report(s.path,tid)
    assert white['summary']['score_pct']==37.5 and white['summary']['games']==4
    records=list(csv.DictReader(io.StringIO(opening_report(s.path,tid,0,export=True))))
    assert len(records)==2 and sum(int(r['games']) for r in records)==4
    assert len(s.game_detail(g['id'])['attempts'])==3
    s.close();s=Store(tmp_path)
    assert opening_report(s.path,tid,0)==revised;s.close()


def test_report_pages_and_selfplay_count_each_game_once(tmp_path):
    s=Store(tmp_path)
    t=s.create_tournament('65 openings',[{'name':'Solo'}],{'format':'self_play','cycles':65},[
      {'name':f'Opening {i}','fen':chess.STARTING_FEN} for i in range(65)])
    tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,130)
    while g:=s.claim(tid):s.finish(g['aid'],'1-0','fixture')
    first=opening_report(s.path,tid,0);last=opening_report(s.path,tid,0,50)
    assert first['total_openings']==65 and len(first['openings'])==50 and len(last['openings'])==15
    assert first['summary']['games']==130 and first['summary']['wins']==130
    assert first['colors'][0]['color']=='White' and len(first['colors'])==1
    assert len(list(csv.DictReader(io.StringIO(opening_report(s.path,tid,0,export=True)))))==65
    s.close()


def test_report_excludes_invalidated_swiss_rounds(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Swiss',[{'name':str(i)} for i in range(4)],{'format':'swiss','cycles':1,'rounds':3});tid=t['id']
    s.set_state(tid,'running');games=[]
    for _ in range(2):
        s.fill_queue(tid,4)
        while g:=s.claim(tid):s.finish(g['aid'],'1-0','fixture');games.append(g)
    assert opening_report(s.path,tid)['summary']['games']==8
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement',invalidate=True)
    assert opening_report(s.path,tid)['summary']['games']==4
    assert sum(o['complete_pairs'] for o in opening_report(s.path,tid)['openings'])==2
    s.close()


def test_report_api_refreshes_only_official_revision(tmp_path):
    async def run():
        app=await create_app(tmp_path,'reports');runner=app['runner'];db=app['db'];runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'reports'}) as client:
            t=await db.call('create_tournament','API',[{'name':'Alpha'},{'name':'Beta'}],{'cycles':1});tid=t['id']
            r=await client.get(f'/api/tournaments/{tid}/participants?q=Beta');v=await r.json();assert v=={'total':1,'items':[{'slot':1,'name':'Beta'}]}
            r=await client.get(f'/api/tournaments/{tid}/openings');v=await r.json();assert v['summary']['games']==0
            await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2);g=await db.call('claim',tid);await db.call('finish',g['aid'],'1-0','fixture')
            r=await client.get(f'/api/tournaments/{tid}/openings');v2=await r.json();assert v2['summary']['games']==1 and v2['revision']>v['revision']
            r=await client.get(f'/api/tournaments/{tid}/openings?export=csv');assert r.content_type=='text/csv' and len(list(csv.DictReader(io.StringIO(await r.text()))))==1
    asyncio.run(run())


def test_large_crosstable_and_head_to_head_pages(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Paged comparisons',[{'name':f'Engine {i:03}'} for i in range(102)],{'format':'round_robin','cycles':1});tid=t['id']
    # Synthetic aggregate rows isolate presentation scaling from game scheduling.
    with s.tx():
        s.db.executemany('INSERT INTO aggregates(tid,a,b,w,d,l,p2) VALUES(?,0,?,2,1,3,3)',((tid,i) for i in range(1,102)))
    page=s.h2h_page(tid,0);last=s.h2h_page(tid,0,100);search=s.h2h_page(tid,0,0,'099')
    assert page['total']==101 and len(page['items'])==50 and len(last['items'])==1
    assert last['items'][0]['opponent']==101 and search['total']==1 and search['items'][0]['name']=='Engine 099'
    cross=crosstable(s.path,tid,0,100)
    assert len(cross['rows'])==20 and len(cross['columns'])==2 and len(cross['cells'])==2
    assert all(c['a']==0 and c['b'] in (100,101) for c in cross['cells'])
    assert crosstable(s.path,tid,100,0)['rows'][0]['slot']==100
    assert crosstable(s.path,tid,search='099')['total']==1;s.close()
