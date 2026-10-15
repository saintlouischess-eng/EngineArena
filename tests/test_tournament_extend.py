import asyncio
from collections import Counter
from contextlib import closing, suppress
import json
import os
import subprocess
import sys
import time

import chess
import pytest
from aiohttp.test_utils import TestClient,TestServer

from arena.store import Store
from arena.tournament_extend import preview,extend
from arena.schedule_order import canonical
from arena.custom_matchups import pair
from test_core import profile,read_pgn


def finish(s,tid):
    s.set_state(tid,'running')
    while True:
        s.fill_queue(tid,12)
        g=s.claim(tid)
        if not g:break
        s.finish(g['aid'],'1/2-1/2','test_draw')
    s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,))


def completed(s,n=3,**settings):
    items=[{'fen':chess.Board.from_chess960_pos(i).fen(),'name':str(i)} for i in range(100)]
    t=s.create_tournament('Extend test',[profile(str(i)) for i in range(n)],
        {'format':'round_robin','cycles':2,'chess960':True,**settings},items,backup=False)
    finish(s,t['id']);return s.tournament(t['id'])


@pytest.mark.parametrize('policy',['legacy','pair','fixed','cycle','round'])
@pytest.mark.parametrize('order',['legacy','balanced','shuffle','matchup'])
@pytest.mark.parametrize('paired',[True,False])
def test_preserve_games_and_complete_missing_matchups(tmp_path,policy,order,paired):
    with closing(Store(tmp_path)) as s:
        t=completed(s,opening_policy=policy,schedule_order=order,paired=paired);tid=t['id']
        old=s.rows('SELECT * FROM games ORDER BY id');attempts=s.rows('SELECT * FROM attempts ORDER BY id')
        old_profiles=s.rows('SELECT * FROM participants ORDER BY slot');ledger=s.rows('SELECT * FROM rc_games ORDER BY gid')
        add=[profile('new1'),profile('new2')];p=preview(s,tid,add)
        assert p['additional_games']==14*(2 if paired else 1)
        t=extend(s,tid,add,p['expected']);assert t['state']=='paused' and not t['can_edit']
        assert s.rows('SELECT * FROM games ORDER BY id')==old
        assert s.rows('SELECT * FROM attempts ORDER BY id')==attempts
        assert s.rows('SELECT * FROM participants WHERE slot<3 ORDER BY slot')==old_profiles
        assert s.rows('SELECT * FROM rc_games ORDER BY gid')==ledger
        finish(s,tid);g=s.rows('SELECT * FROM games ORDER BY number');legs=2 if paired else 1
        assert len(g)==20*legs
        assert Counter(tuple(sorted((v['white'],v['black']))) for v in g)==Counter({(a,b):2*legs for a in range(5) for b in range(a+1,5)})
        if paired:
            for k in range(20):
                a,b=g[k*2:k*2+2];assert a['opening']==b['opening'] and a['white']==b['black'] and a['black']==b['white']
        new=g[len(old):];assignments=[json.loads(v['opening'])['assignment'] for v in new]
        if not paired:
            assert all(count==1 for count in Counter((v['white'],v['black']) for v in new).values())
        if policy in ('pair','legacy'):assert min(assignments)==len(old)//legs
        if policy=='round':assert min(assignments)>max(json.loads(v['opening'])['assignment'] for v in old)
        if policy=='fixed':assert set(assignments)=={0}
        if policy=='cycle':assert set(assignments)=={0,1}
        snap=s.snapshot(tid);assert snap['official_games']==20*legs
        assert snap['complete_pairs']==(20 if paired else 0)
        assert s.one('SELECT count(*) n FROM rc_games')['n']==20*legs
        # Repeated expansion adds only the next entrant's games.
        p=preview(s,tid,[profile('next')]);assert p['additional_games']==10*legs
        extend(s,tid,[profile('next')],p['expected']);finish(s,tid)
        assert s.snapshot(tid)['official_games']==30*legs
        assert s.one('SELECT count(*) n FROM rc_games')['n']==30*legs


def test_guards_atomicity_and_queue_hold(tmp_path,monkeypatch):
    with closing(Store(tmp_path)) as s:
        t=completed(s);tid=t['id'];add=[profile('new')];p=preview(s,tid,add)
        for bad in ([],[profile('0')],[profile('new'),profile('new')]):
            with pytest.raises(ValueError):preview(s,tid,bad)
        with pytest.raises(ValueError,match='Preview'):extend(s,tid,add,'stale')
        s.execute('INSERT INTO tournament_queue(tid,position,finished) VALUES(?,0,1)',(tid,))
        original=s.audit
        def fail(*a):raise RuntimeError('commit failed')
        monkeypatch.setattr(s,'audit',fail)
        with pytest.raises(RuntimeError):extend(s,tid,add,p['expected'])
        assert s.tournament(tid)['participants']==3 and s.tournament(tid)['state']=='completed'
        monkeypatch.setattr(s,'audit',original);extend(s,tid,add,p['expected'])
        q=s.one('SELECT * FROM tournament_queue WHERE tid=?',(tid,));assert q['held']==1 and q['finished']==0
        with pytest.raises(ValueError):extend(s,tid,add,p['expected'])


@pytest.mark.parametrize('fmt',['match','swiss','knockout','gauntlet'])
def test_other_formats_cannot_be_extended(tmp_path,fmt):
    with closing(Store(tmp_path)) as s:
        t=s.create_tournament('No',[profile('A'),profile('B')],{'format':fmt},backup=False)
        s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(t['id'],))
        with pytest.raises(ValueError,match='round-robin'):preview(s,t['id'],[profile('C')])


def test_large_extension_is_incremental_and_dispatch_looks_past_blocked_engines(tmp_path):
    with closing(Store(tmp_path)) as s:
        t=completed(s,n=2,cycles=1,schedule_order='balanced');tid=t['id']
        add=[profile('new'+str(i)) for i in range(2000)];add[0]['threads']=128
        p=preview(s,tid,add);extend(s,tid,add,p['expected'])
        assert s.one('SELECT count(*) n FROM games')['n']==2
        assert p['total_games']==2002*2001
        s.set_state(tid,'running');s.fill_queue(tid,2)
        used={'threads':0,'memory_mb':0,'gpu':{}}
        admission={'cpu_budget':4,'memory_budget_mb':8192,'gpu_limits':{}}
        result=s.dispatch(tid,used,admission)
        assert result['game'] and 2 not in (result['game']['white'],result['game']['black'])
        assert s.one('SELECT count(*) n FROM games')['n']<=6


def test_extension_survives_forced_exit(tmp_path):
    with closing(Store(tmp_path)) as s:t=completed(s)
    script='''import os,sys
from arena.store import Store
from arena.tournament_extend import preview,extend
s=Store(sys.argv[1]);p={'id':'new','name':'new','path':sys.executable}
v=preview(s,sys.argv[2],[p]);extend(s,sys.argv[2],[p],v['expected']);os._exit(0)
'''
    subprocess.run([sys.executable,'-c',script,str(tmp_path),t['id']],check=True)
    with closing(Store(tmp_path)) as s:
        assert s.tournament(t['id'])['participants']==4
        finish(s,t['id']);assert s.snapshot(t['id'])['official_games']==24
        assert s.one('PRAGMA integrity_check')['integrity_check']=='ok'


def test_api_real_worker_extended_games_pgn_and_ratings(tmp_path):
    from arena.server import create_app
    async def run():
        app=await create_app(tmp_path,'extend');db=app['db'];runner=app['runner']
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'extend'}) as client:
            ids=[]
            for index,name in enumerate(('A','B','C'),1):
                p=await db.call('save_profile',profile(name)|{'hash':index,'options':{'Hash':index}});ids.append(p['id'])
            r=await client.post('/api/tournaments',json={'name':'Worker extension','profiles':ids[:2],
                'settings':{'format':'round_robin','cycles':1,'max_plies':4,'concurrency':2,'time_control':{'kind':'nodes','nodes':100}}})
            t=await r.json();assert r.status==200,t;tid=t['id']
            async def play():
                await client.post(f'/api/tournaments/{tid}/action',json={'action':'start'})
                for _ in range(1200):
                    snap=await db.call('snapshot',tid)
                    assert not runner.error,runner.error
                    if snap['state']=='completed':return snap
                    await asyncio.sleep(.025)
                raise AssertionError('Fixture tournament did not finish')
            assert (await play())['official_games']==2
            url=f'/api/tournaments/{tid}/extend'
            info=await (await client.get(url)).json();assert not info['reason']
            r=await client.post(url,json={'preview':True,'profiles':ids[2:]});p=await r.json();assert r.status==200,p
            assert p['additional_games']==4
            r=await client.post(url,json={'profiles':ids[2:],'expected':p['expected']});assert r.status==200,await r.text()
            assert (await play())['official_games']==6
            await db.call('export_pending')
            games=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'));assert len(games)==6
            assert len({g.headers['AttemptId'] for g in games})==6
            for g in games:
                assert not g.errors
                board=g.board()
                for m in g.mainline_moves():assert m in board.legal_moves;board.push(m)
            assert (await db.call('one','SELECT count(*) n FROM rc_games'))['n']==6
    asyncio.run(run())
