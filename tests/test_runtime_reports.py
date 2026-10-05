import asyncio
import hashlib
import io
import json
from pathlib import Path
import sys
import subprocess

import chess.pgn
import pytest
from arena.store import Store
from arena.runner import Database,Runner
from arena.runtime_evidence import observe_line,observed_fingerprint,add_sample,RunRecorder
from arena.report_evidence import configured_option,option_rows
from arena.tournament_report import render
from arena.pgn_format import render_attempt


def test_lc0_hash_and_legacy_network_report(tmp_path):
    s=Store(tmp_path)
    try:
        cpu={'name':'CPU','advertised':{'Threads':{'default':1},'Hash':{'default':16}},'options':{'Threads':1,'Hash':32}}
        gpu={'name':'Lc0','gpu_group':'gpu0','advertised':{'WeightsFile':{'default':'<autodiscover>'},'NNCacheSize':{'default':2000000}},'hash':1024,
             'options':{'WeightsFile':'<autodiscover>','NNCacheSize':20000000,'Backend':'cuda-auto'}}
        t=s.create_tournament('Legacy KO',[cpu,gpu],{'format':'knockout','cycles':1});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,2)
        for result in ('1-0','0-1'):
            g=s.claim(tid);s.log(g['aid'],['stderr Loading weights file from: C:\\engines\\net & test.pb.gz','stderr Switching to [cuda-fp16]...',
                'stderr GPU: Test GPU','stderr Unhandled exception: CUBLAS_STATUS_INTERNAL_ERROR']);s.finish(g['aid'],result,'crash','stdout closed')
        s.fill_queue(tid,2);html=render(s.path,tid)
        assert '2 failure forfeits' in html and 'CUBLAS_STATUS_INTERNAL_ERROR' in html and 'Recorded loser' in html
        assert 'Legacy log sample' in html and 'net &amp; test.pb.gz' in html and 'cuda-fp16' in html
        assert 'Historical hardware snapshot not recorded' in html and 'implicit legacy default' in html
        assert 'N/A (unsupported)' in html and '20,000,000' in html and 'Runner-up' in html and '>Seed</th>' in html
        assert '2 regular games + 0 tiebreak games' in html and 'Unique starting positions used' in html
        assert 'nominal confidence level is not a calibrated guarantee' in html
        assert configured_option(gpu,'Hash')=='N/A (unsupported)'
        assert dict(option_rows({'name':'Limited option','options':{'UCI_LimitStrength':False,'UCI_Elo':1320}}))['UCI_Elo']=='1320 (inactive; UCI_LimitStrength is off)'
        pgn=chess.pgn.read_game(io.StringIO(render_attempt(s.db,g['aid'])))
        assert pgn.headers['WhiteHashMB']=='N/A (unsupported)' and pgn.headers['WhiteNNCachePositions']=='20000000'
    finally:s.close()


def test_fingerprint_scope_and_sensor_samples(tmp_path):
    network=tmp_path/'weights.pb.gz';network.write_bytes(b'network one')
    p={'path':str(tmp_path/'engine.exe')}
    f=observed_fingerprint(p,str(network));assert f['sha256']==hashlib.sha256(b'network one').hexdigest()
    data={};assert observe_line(data,'stderr Loading weights file from: '+str(network))
    assert not observe_line(data,'stderr Loading weights file from: '+str(network))
    assert not observe_line(data,'info string random network might be elsewhere')
    assert 'outside configured' in observed_fingerprint(p,str(tmp_path.parent/'private.pb.gz'))['status']
    sample={'sampled_at':1,'metrics':{'cpu_percent':0,'cpu_temperature':None,'ram_used':2},'gpus':[]}
    body={};assert add_sample(body,sample) and not add_sample(body,sample)
    assert add_sample(body,sample|{'sampled_at':2,'metrics':{'cpu_percent':80,'ram_used':4}})
    assert body['samples']['cpu_percent']=={'count':2,'sum':80.,'min':0,'max':80}
    assert 'cpu_temperature' not in body['samples']
    assert not add_sample(body,sample|{'sampled_at':3,'stale':True})


@pytest.mark.parametrize('mode',['network','network_crash'])
def test_actual_uci_network_saved_before_finish_and_in_pgn(tmp_path,mode):
    async def run():
        network=tmp_path/'fixture.pb.gz';network.write_bytes(b'test network bytes')
        db=await Database().open(tmp_path/'data');runner=Runner(db)
        engine={'path':sys.executable,'cwd':str(tmp_path),'args':[str(Path(__file__).with_name('fault_engine.py')),'--mode',mode,'--marker',str(network)],'threads':1,'hash':1}
        try:
            t=await db.call('create_tournament','Runtime',[engine|{'name':'A'},engine|{'name':'B'}],{'cycles':1,'max_plies':2,'time_control':{'kind':'nodes','nodes':77}})
            tid=t['id'];await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2);g=await db.call('claim',tid)
            runner.live[g['aid']]={};await runner._game(g,await db.call('tournament',tid))
            rows=await db.call('rows','SELECT x.*,e.body FROM attempt_engines x JOIN engine_evidence e ON e.id=x.evidence WHERE aid=?',(g['aid'],))
            assert len(rows)==2 and all(r['started'] and r['ended']>=r['started'] for r in rows)
            body=json.loads(next(r['body'] for r in rows if r['side']=='white'))
            assert body['network']['sha256']==hashlib.sha256(network.read_bytes()).hexdigest()
            assert body['backend']=='cuda-fp16' and body['gpu']=='Synthetic GPU'
            # Use the same database actor for its SQLite connection.
            import functools
            text=await asyncio.get_running_loop().run_in_executor(db.executor,functools.partial(render_attempt,db.store.db,g['aid']))
            parsed=chess.pgn.read_game(io.StringIO(text))
            assert parsed.headers['WhiteNetwork']=='fixture.pb.gz' and parsed.headers['WhiteNetworkSHA256']==body['network']['sha256']
            assert parsed.headers['TimeControl']=='-' and parsed.headers['WhiteSearchControl'].startswith('77 nodes')
            detail=await db.call('game_detail',g['id'])
            assert detail['attempts'][0]['reason']==('crash' if mode=='network_crash' else 'max_plies_adjudication')
        finally:await db.close()
        restored=Store(tmp_path/'data')
        try:assert restored.one('SELECT count(*) n FROM attempt_engines')['n']==2
        finally:restored.close()
    asyncio.run(run())


def test_run_sessions_recovery_and_deletion(tmp_path,monkeypatch):
    from arena import runtime_evidence
    monkeypatch.setattr(runtime_evidence,'system_snapshot',lambda:{'cpu':'Recorded test CPU','physical_cores':8,'logical_processors':16,'ram_gib':32,'os':'Test OS','app_version':'test','gpus':[]})
    async def run():
        db=await Database().open(tmp_path);rec=RunRecorder(db)
        try:
            t=await db.call('create_tournament','Sessions',[{'name':'A','gpu_group':'gpu0'},{'name':'B'}],{'cycles':1,'gpu_limits':{'gpu0':1}})
            await rec.begin(t['id'],t['settings'],t['settings']|{'memory_budget_mb':1234})
            await rec.update({t['id']},set(),True)
            return t['id']
        finally:await db.close()
    tid=asyncio.run(run());s=Store(tmp_path)
    try:
        row=s.one('SELECT * FROM run_sessions WHERE tid=?',(tid,));assert row['state']=='interrupted' and row['ended'] is None
        html=render(s.path,tid);assert 'Recorded test CPU' in html and '1,234' in html and 'gpu0: 1' in html
        assert 'Historical hardware snapshot not recorded' not in html
        s.delete_tournament(tid,'Sessions');assert s.one('SELECT count(*) n FROM run_sessions')['n']==0
    finally:s.close()


def test_abrupt_worker_exit_keeps_committed_runtime_evidence(tmp_path):
    code='''import json,os,sys,time
from arena.store import Store
s=Store(sys.argv[1]);t=s.create_tournament('Power loss',[{'name':'A'},{'name':'B'}],{'cycles':1});tid=t['id']
s.set_state(tid,'running');s.fill_queue(tid,2);g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','fixture');g=s.claim(tid)
s.execute('INSERT INTO run_sessions VALUES(?,?,?,?,?,?,?)',('session',tid,time.time(),time.time(),None,'running',json.dumps({'hardware':{'cpu':'Before crash'}})))
s.execute('INSERT INTO run_attempts VALUES(?,?)',(g['aid'],'session'))
s.record_engine_evidence(g['aid'],'white',{'network_file':'saved.pb.gz','network':{'sha256':'a'*64}},time.time(),None)
os._exit(73)
'''
    r=subprocess.run([sys.executable,'-c',code,str(tmp_path)],timeout=20,capture_output=True,text=True)
    assert r.returncode==73,r.stderr
    s=Store(tmp_path)
    try:
        tid=s.one('SELECT id FROM tournaments')['id'];snap=s.snapshot(tid)
        assert snap['official_games']==1 and snap['state']=='paused'
        assert s.one('SELECT state FROM run_sessions')['state']=='interrupted'
        record=s.one('SELECT e.body,a.reason FROM engine_evidence e JOIN attempt_engines x ON x.evidence=e.id JOIN attempts a ON a.id=x.aid')
        assert json.loads(record['body'])['network']['sha256']=='a'*64 and record['reason']=='interrupted'
    finally:s.close()
