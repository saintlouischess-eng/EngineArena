import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from arena.resources import game_cost,usage
from arena.runner import Database,Runner
from arena.store import Store
from test_core import profile,read_pgn


def field(n=4):
    return [profile(str(i))|{'gpu_group':'gpu0' if i==0 else '', 'extra_memory_mb':0} for i in range(n)]


def settings(**kw):
    return {'format':'round_robin','cycles':20,'concurrency':28,'cpu_budget':28,
            'memory_budget_mb':10000,'gpu_limits':{'gpu0':1},**kw}


def select(s,t,active=(),scan=None,limit=256):
    return s.dispatch(t['id'],usage(active,t['settings']['ponder']),t['settings'],scan,limit)


@pytest.mark.parametrize('policy',['pair','round'])
@pytest.mark.parametrize('order',['legacy','balanced','matchup','shuffle'])
def test_240_games_cpu_runs_ahead_gpu_catches_up_and_pairs_pgn_stay_exact(tmp_path,policy,order):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Mixed RR',field(),settings(opening_policy=policy,schedule_order=order),backup=False)
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,56)
        active=[]
        for _ in range(28):
            picked=select(s,t,active);assert picked['game'];active.append(picked)
        assert usage(active)['gpu']=={'gpu0':1}
        assert usage(active)['threads']==28
        assert not select(s,t,active)['game']
        gpu=next(p for p in active if p['white']['gpu_group'] or p['black']['gpu_group'])
        cpu_done=0
        while True:
            for p in active:
                if p is gpu:continue
                s.finish(p['game']['aid'],'1/2-1/2','fixture');cpu_done+=1
            active=[gpu];s.fill_queue(tid,56)
            while len(active)<28:
                p=select(s,t,active)
                if not p['game']:break
                assert not game_cost(p['white'],p['black'])['gpu'];active.append(p)
            if len(active)==1:break
        # Every CPU-only pairing can finish while the very first GPU game waits.
        assert cpu_done==120
        assert s.snapshot(tid)['official_games']==120
        assert s.snapshot(tid)['complete_pairs']==60
        s.finish(gpu['game']['aid'],'1/2-1/2','fixture')
        while True:
            s.fill_queue(tid,56);p=select(s,t)
            if not p['game']:break
            s.finish(p['game']['aid'],'1/2-1/2','fixture')
        snap=s.snapshot(tid);assert snap['official_games']==240 and snap['complete_pairs']==120
        assert s.tournament(tid)['cursor']==120
        games=s.rows('SELECT * FROM games WHERE tid=? ORDER BY number',(tid,))
        assert [g['number'] for g in games]==list(range(240))
        for a,b in zip(games[::2],games[1::2]):
            assert a['opening']==b['opening'] and (a['white'],a['black'])==(b['black'],b['white'])
            assert a['pair_no']==b['pair_no']
        while (s.one("SELECT last_id FROM exports WHERE stream='games'") or {'last_id':0})['last_id']<s.one("SELECT max(id) n FROM outbox WHERE stream='games'")['n']:
            s.export_pending()
        pgn=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'))
        assert len(pgn)==240 and len({g.headers['GameId'] for g in pgn})==240
        assert s.one('SELECT count(*) n FROM attempts')['n']==240
    finally:s.close()


def test_huge_implicit_schedule_looks_past_gpu_runs_without_materializing_them(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Large',field(10000),settings(cycles=1000000),backup=False)
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,56)
        first=select(s,t);assert first['game']['number']==0
        scan=None;calls=0
        while True:
            p=select(s,t,[first],scan,limit=256);calls+=1;scan=p['scan']
            if p['game']:break
            assert not p['exhausted'] and calls<45
        assert calls>1 and not game_cost(p['white'],p['black'])['gpu']
        assert p['game']['pair_no']==9999*1000000
        assert s.one('SELECT count(*) n FROM games')['n']==58
        assert s.tournament(tid)['cursor']==28
    finally:s.close()


def test_lookahead_keeps_progress_when_gpu_games_finish_each_scan_page(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Busy GPU',field(1000),settings(cycles=1000),backup=False)
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,56)
        gpu=select(s,t);scan=None
        for _ in range(8):
            p=select(s,t,[gpu],scan);scan=p['scan']
            if p['game']:break
            assert not p['exhausted']
            s.finish(gpu['game']['aid'],'1-0','fixture');s.fill_queue(tid,56)
            gpu=select(s,t,scan=scan);scan=gpu['scan']
            assert gpu['game'] and game_cost(gpu['white'],gpu['black'])['gpu']=={'gpu0':1}
        assert p['game'] and not game_cost(p['white'],p['black'])['gpu']
        assert p['game']['pair_no']==999*1000
        assert s.one('SELECT count(*) n FROM games')['n']<70
    finally:s.close()


@pytest.mark.parametrize('restriction',['threads','memory','ponder','gpu'])
def test_skips_ineligible_pair_but_enforces_every_resource(tmp_path,restriction):
    s=Store(tmp_path)
    try:
        profiles=field()
        profiles[0]['gpu_group']=''
        cfg=settings(cycles=1,cpu_budget=4,memory_budget_mb=20)
        if restriction=='threads':profiles[0]['threads']=8
        elif restriction=='memory':profiles[0]['hash']=30
        elif restriction=='ponder':profiles[0]['threads']=4;cfg['ponder']=True
        else:profiles[0]['gpu_group']=profiles[1]['gpu_group']='gpu0'
        t=s.create_tournament('Skip blocked',profiles,cfg,backup=False)
        s.set_state(t['id'],'running');s.fill_queue(t['id'],2)
        p=select(s,t);assert p['game']
        assert p['game']['a']>0 if restriction!='gpu' else p['game']['b']>1
        assert game_cost(p['white'],p['black'],cfg.get('ponder',False))['threads']<=4
        assert game_cost(p['white'],p['black'])['memory_mb']<=20
    finally:s.close()


def test_exact_claim_rejects_other_tournament_stale_invalid_and_dependencies(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('A',field(),settings(cycles=1),backup=False);tid=t['id']
        s.set_state(tid,'running');s.fill_queue(tid,4)
        gs=s.rows('SELECT id FROM games ORDER BY number')
        assert s.claim('other',gs[1]['id']) is None
        g=s.claim(tid,gs[1]['id']);assert g['number']==1 and s.claim(tid,g['id']) is None
        s.finish(g['aid'],'1-0','fixture');assert s.claim(tid,g['id']) is None
        s.execute('UPDATE games SET invalid=1 WHERE id=?',(gs[2]['id'],));assert s.claim(tid,gs[2]['id']) is None
        s.execute("UPDATE tournaments SET dependency='Resolve rounds first' WHERE id=?",(tid,))
        assert s.claim(tid) is None and select(s,t)['game'] is None
        assert s.one('SELECT count(*) n FROM attempts')['n']==1
    finally:s.close()


def test_dependent_rounds_do_not_use_static_lookahead(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Swiss',field(),settings(format='swiss',cycles=2),backup=False)
        tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,8)
        used={'threads':0,'memory_mb':0,'gpu':{'gpu0':1}};selected=[]
        while True:
            p=s.dispatch(tid,used,t['settings'])
            if not p['game']:break
            selected.append(p['game']);s.finish(p['game']['aid'],'1-0','fixture')
        assert selected
        s.fill_queue(tid,4)
        assert {g['round'] for g in s.rows('SELECT round FROM games')}=={0}
    finally:s.close()


def test_forced_crash_preserves_sparse_ahead_pairs_and_recovers_once(tmp_path):
    root=Path(__file__).resolve().parents[1];ready=tmp_path/'ready.json';data=tmp_path/'data'
    script=tmp_path/'crash.py'
    script.write_text('''import json,sys,time
from pathlib import Path
from arena.store import Store
s=Store(sys.argv[1]);p=[{'name':str(i),'threads':1,'hash':1,'gpu_group':'gpu0' if i==0 else ''} for i in range(4)]
t=s.create_tournament('Sparse recovery',p,{'format':'round_robin','cycles':20,'cpu_budget':28,'memory_budget_mb':10000,'gpu_limits':{'gpu0':1}})
s.set_state(t['id'],'running');s.fill_queue(t['id'],4)
used={'threads':1,'memory_mb':514,'gpu':{'gpu0':1}}
g=s.dispatch(t['id'],used,t['settings'])['game'];s.finish(g['aid'],'1-0','fixture')
r=s.dispatch(t['id'],used,t['settings'])['game']
Path(sys.argv[2]).write_text(json.dumps({'tid':t['id'],'done':g,'running':r}))
time.sleep(120)
''',encoding='utf-8')
    p=subprocess.Popen([sys.executable,str(script),str(data),str(ready)],env=os.environ|{'PYTHONPATH':str(root)},creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    try:
        deadline=time.monotonic()+15
        while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
        assert ready.exists();p.kill();p.wait(timeout=5)
    finally:
        if p.poll() is None:p.kill();p.wait()
    ids=json.loads(ready.read_text());s=Store(data)
    try:
        tid=ids['tid'];assert s.snapshot(tid)['official_games']==1
        done=s.game_detail(ids['done']['id']);run=s.game_detail(ids['running']['id'])
        assert done['number']==120 and run['number']==121
        assert run['state']=='pending' and run['attempts'][0]['reason']=='interrupted'
        s.set_state(tid,'running');g=s.claim(tid,run['id'])
        assert g['seq']==2 and g['opening']==ids['running']['opening']
        s.finish(g['aid'],'0-1','fixture');s.fill_queue(tid,240)
        assert s.one('SELECT count(*) n FROM games')['n']==240
        assert s.snapshot(tid)['official_games']==2 and s.snapshot(tid)['complete_pairs']==1
        s.export_pending();assert len(read_pgn((data/'games.pgn').read_text(encoding='utf-8')))==2
    finally:s.close()


@pytest.mark.parametrize('finish_during_dispatch',[False,True])
def test_real_runner_mixed_gpu_cpu_node_only_finishes_and_obeys_limits(tmp_path,finish_during_dispatch):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            t=await db.call('create_tournament','Live mixed',field(),settings(cycles=1,concurrency=4,cpu_budget=4,max_plies=2,time_control={'kind':'nodes','nodes':100}))
            original_call=db.call;interleavings=[]
            async def interleaved_call(method,*args,**kwargs):
                result=await original_call(method,*args,**kwargs)
                if finish_during_dispatch and method=='dispatch' and not result['game'] and result['reason'] and r.tasks:
                    await asyncio.gather(*list(r.tasks.values()));await asyncio.sleep(0)
                    interleavings.append(result['reason'])
                return result
            db.call=interleaved_call
            await db.call('set_state',t['id'],'running');await r.start()
            deadline=time.monotonic()+30;peak=0
            while time.monotonic()<deadline:
                assert not r.error
                cost=usage(r.live.values());assert cost['gpu'].get('gpu0',0)<=1 and cost['threads']<=4
                peak=max(peak,len(r.live));snap=await db.call('snapshot',t['id'])
                if snap['state']=='completed':break
                await asyncio.sleep(.01)
            assert snap['state']=='completed' and snap['official_games']==12 and snap['complete_pairs']==6
            assert peak==4
            assert {a['reason'] for a in await db.call('rows','SELECT reason FROM attempts')}=={'max_plies_adjudication'}
            assert len(read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8')))==12
            if finish_during_dispatch:assert interleavings
        finally:await r.close()
    asyncio.run(run())
