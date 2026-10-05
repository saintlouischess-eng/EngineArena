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
    s=Store(tmp_path);t=s.create_tournament('<script>bad</script>',[{'name':'<Alpha>'},{'name':'Beta'}],{'cycles':1,'time_control':{'kind':'nodes','nodes':12345},'opening_source':{'name':'Book & variations.bin','depth':16}});tid=t['id']
    s.set_state(tid,'running');s.fill_queue(tid,2);games=[]
    for result in ('1-0','0-1'):
        g=s.claim(tid);s.finish(g['aid'],result,'crash');games.append(g)
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='diagnostic');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','diagnostic_only')
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running');g=s.claim(tid);s.finish(g['aid'],'0-1','replacement_reason')
    text=render(s.path,tid);p=Tables();p.feed(text)
    assert '<script>bad</script>' not in text and '&lt;script&gt;bad&lt;/script&gt;' in text
    assert '12,345 nodes per move; no chess clock' in text and '<b>2<small>official games / 2 scheduled' in text
    standings=next(t for t in p.tables if 'Engine profile' in t[0]);assert standings[1][1:4]==['<Alpha>','2','1–0–1']
    assert ['Opening book file','Book & variations.bin'] in next(t for t in p.tables if t[0]==['Setting','Value'])
    assert 'Book &amp; variations.bin' in text
    reasons=next(t for t in p.tables if t[0]==['Termination reason','Official games']);assert ['Crash','1'] in reasons and ['Replacement reason','1'] in reasons
    attempts=next(t for t in p.tables if t[0]==['Preserved attempt mode','Attempts'])
    assert 'diagnostic_only' not in text and ['diagnostic','1'] in attempts and ['replacement','1'] in attempts
    assert '<b>1<small>completed opening pairs' in text and 'Full settings SHA-256' in text;s.close()


def test_concise_report_handles_large_empty_tournament(tmp_path):
    s=Store(tmp_path);t=s.create_tournament('Large report',[{'name':f'Engine {i:04}'} for i in range(1001)],{'format':'round_robin'})
    text=render(s.path,t['id']);p=Tables();p.feed(text)
    assert 'First 50 of 1001 participants' in text and len(next(t for t in p.tables if 'Engine profile' in t[0]))==51
    assert ['Opening book file','Not recorded'] in next(t for t in p.tables if t[0]==['Setting','Value'])
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


def test_sequential_report_retains_runtime_sections_after_result_replacement(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Sequential report',[{'name':'A'},{'name':'B'}],{'format':'sprt','cycles':20})
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,4);games=[]
        for _ in range(2):
            g=s.claim(tid);s.finish(g['aid'],'1-0','fixture');games.append(g)
        text=render(s.path,tid)
        assert 'Log likelihood ratio' in text and 'Test system and resources' in text and 'Displayed engine configurations' in text
        s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running')
        g=s.claim(tid);s.finish(g['aid'],'0-1','fixture')
        text=render(s.path,tid)
        assert 'Sequential decision invalidated by result replacement' in text and 'Historical hardware snapshot not recorded' in text
    finally:s.close()


def test_swiss_report_accounts_for_bye_points_separately(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Swiss byes',[{'name':n} for n in ('A','B','C')],{'format':'swiss','rounds':1,'cycles':1})
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,20)
        while g:=s.claim(tid):s.finish(g['aid'],'1/2-1/2','fixture')
        s.fill_queue(tid,20);html=render(s.path,tid);tables=Tables();tables.feed(html)
        rows=next(t for t in tables.tables if 'Engine profile' in t[0]);headers=rows[0]
        assert 'Bye points' in headers and 'Bye points do not count as played games' in html
        for r in rows[1:]:
            w,d,l=map(int,r[headers.index('W–D–L')].split('–'));bye=float(r[headers.index('Bye points')])
            assert float(r[headers.index('Points')])==w+d/2+bye
            assert int(r[headers.index('Games')])==w+d+l
        assert sum(float(r[headers.index('Bye points')]) for r in rows[1:])==2
    finally:s.close()


def test_tied_ko_report_and_live_data_identify_seed_decision(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Legacy tied KO',[{'name':n} for n in ('A','B')],{'format':'knockout','cycles':1,'knockout_tiebreak':'seed'})
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,20)
        while g:=s.claim(tid):s.finish(g['aid'],'1/2-1/2','fixture')
        s.fill_queue(tid,20);match=s.snapshot(tid)['knockout']['rounds'][0]['matches'][0]
        assert match['a_score']==match['b_score']==1 and match['decision_basis']=='Initial seed'
        html=render(s.path,tid);tables=Tables();tables.feed(html);stages=next(t for t in tables.tables if 'A – B score' in t[0])
        assert stages[1][-1]=='Initial seed' and 'Winner: A' in html
    finally:s.close()
