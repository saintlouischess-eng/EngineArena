import asyncio
import contextlib
from html.parser import HTMLParser
from aiohttp.test_utils import TestClient,TestServer
from arena.server import create_app
from arena.store import Store
from arena.tournament_report import render


class Tables(HTMLParser):
    def __init__(self):super().__init__();self.tables=[];self.table=None;self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.table=[];self.tables.append(self.table)
        elif tag=='tr':self.row=[];self.table.append(self.row)
        elif tag in ('th','td'):self.cell=''
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self,tag):
        if tag in ('th','td'):self.row.append(self.cell);self.cell=None


def test_report_uses_current_official_attempts_and_escapes_text(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('<script>bad</script>',[{'name':'<Alpha>'},{'name':'Beta'}],{'cycles':1,'time_control':{'kind':'nodes','nodes':12345}});tid=t['id']
    s.set_state(tid,'running');s.fill_queue(tid,2);games=[]
    for result in ('1-0','0-1'):
        g=s.claim(tid);s.finish(g['aid'],result,'crash');games.append(g)
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='diagnostic');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','diagnostic_only')
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'0-1','replacement_reason')
    text=render(s.path,tid);p=Tables();p.feed(text)
    assert '<script>bad</script>' not in text and '&lt;script&gt;bad&lt;/script&gt;' in text
    assert '12,345 nodes per move; no chess clock' in text and '<b>2<small>official games / 2 scheduled' in text
    assert p.tables[0][1][1:3]==['<Alpha>','1–0–1']
    assert ['crash','1'] in p.tables[2] and ['replacement_reason','1'] in p.tables[2]
    assert 'diagnostic_only' not in text and ['diagnostic','1'] in p.tables[3] and ['replacement','1'] in p.tables[3]
    assert '<b>1<small>completed opening pairs' in text and 'Full settings SHA-256' in text;s.close()


def test_concise_report_handles_large_empty_tournament(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Large report',[{'name':f'Engine {i:04}'} for i in range(1001)],{'format':'round_robin'})
    text=render(s.path,t['id']);p=Tables();p.feed(text)
    assert 'First 50 of 1001 participants' in text and len(p.tables[0])==51
    assert '10,010,000 scheduled' in text and 'Engine 0050' not in text;s.close()


def test_html_report_api_and_download(tmp_path):
    async def run():
        app=await create_app(tmp_path,'reports');runner=app['runner'];db=app['db'];runner.scheduler.cancel()
        with contextlib.suppress(asyncio.CancelledError):await runner.scheduler
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'reports'}) as client:
            t=await db.call('create_tournament','API report',[{'name':'Alpha'},{'name':'Beta'}],{'cycles':1});tid=t['id']
            r=await client.get(f'/api/tournaments/{tid}/report');assert r.status==200 and '<h1>API report</h1>' in (await r.json())['html']
            r=await client.get(f'/api/export/{tid}/html');assert r.status==200 and r.content_type=='text/html' and '.html' in r.headers['Content-Disposition']
            assert '<!doctype html>' in await r.text()
    asyncio.run(run())
