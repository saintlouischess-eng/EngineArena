"""GPU identity, compact legacy evidence, and CPU/GPU rating integration."""
from contextlib import closing
import csv
import io
import json
import sqlite3

import pytest

from arena.rating_center import entry, digest, encode
from arena.rating_compute import compute_summary, continuity
from arena.rating_center_report import report
from arena.runtime_evidence import observe_line, write_engine
from arena.store import Store
from test_rating_center import profile, tournament, finish, read

TC={'kind':'fischer','seconds':180,'increment':2}
SETTINGS={'ponder':False,'chess960':False}


def gpu(backend='cuda-auto'):
    return {'name':'Lc0 test','identity':{'name':'Lc0 test'},'sha256':'lc0-binary','threads':2,
            'advertised':{'Threads':{'type':'spin','default':2},'Backend':{'type':'combo','default':backend}},
            'options':{'Threads':2,'Backend':backend,'WeightsFile':'<autodiscover>'},'gpu_group':'gpu0'}


def evidence(model='NVIDIA GeForce RTX 5080',network='a'*64,backend='cuda-fp16'):
    return {'gpu':model,'backend':backend,'network':{'sha256':network}}


def ident(p=None,e=None,h=None,scope='one'):
    return entry(p or gpu(), e if e is not None else evidence(), SETTINGS,TC,hardware=h or {},scope=scope)


def record_game(s,tid,result,e=None,hardware=None):
    g=s.claim(tid);assert g
    sid='session-'+g['aid'];hardware=hardware or {'cpu':'Fixture CPU','gpus':[{'index':'0','name':'NVIDIA GeForce RTX 5080'}]}
    with s.tx():
        s.db.execute('INSERT INTO run_sessions VALUES(?,?,?,?,?,?,?)',(sid,tid,1,2,2,'finished',encode({'hardware':hardware})))
        s.db.execute('INSERT INTO run_attempts VALUES(?,?)',(g['aid'],sid))
    side='white' if g['white']==0 else 'black'
    write_engine(s,g['aid'],side,e if e is not None else evidence(),1,2)
    s.finish(g['aid'],result,'fixture')
    return g


def test_cpu_identity_unchanged_and_lc0_cpu_backend_is_not_gpu():
    a=ident(profile(),{})
    assert 'compute' not in a[3] and a[0]==digest(a[3])
    for backend in ('blas','eigen','onednn','onnx-cpu'):
        a=ident(gpu(backend),{})
        assert compute_summary(a[3])['kind']=='cpu' and a[1].endswith('2 threads')
    # GPU reservation cannot turn a confirmed CPU backend into a GPU entry.
    assert ident(gpu('blas'),{'backend':'blas'})[0]==ident(gpu('blas')|{'gpu_group':''},{'backend':'blas'})[0]


def test_gpu_model_backend_network_and_support_threads_separate_entries():
    a=ident();assert 'GeForce RTX 5080 ×1' in a[1] and 'net aaaaaaaaaaaa' in a[1] and 'cuda-fp16' in a[1]
    assert a[2]==2 and a[3]['compute']['devices']==[{'model':'GeForce RTX 5080','count':1}]
    assert ident(e=evidence('NVIDIA GeForce RTX 4090'))[0]!=a[0]
    assert ident(e=evidence(backend='cuda'))[0]!=a[0]
    assert ident(e=evidence(network='b'*64))[0]!=a[0]
    assert ident(gpu()|{'options':gpu()['options']|{'Threads':3}})[0]!=a[0]
    assert ident(gpu()|{'gpu_group':'renamed scheduler reservation'},scope='other')[0]==a[0]
    assert ident(h={'cpu':'another CPU','gpus':[{'name':'unrelated GPU'}]})[0]==a[0]


def test_unknown_device_is_not_inferred_from_inventory_or_group_slots():
    hardware={'gpus':[{'index':'0','name':'NVIDIA GeForce RTX 5080'}]}
    a=ident(e={},h=hardware)
    assert a[3]['compute']['status']=='unverified' and 'GPU unverified' in a[1]
    assert not a[3]['compute']['devices']
    assert a[0]!=ident()[0] and a[0]!=ident(e={},h=hardware,scope='other tournament')[0]
    assert continuity(a[3],a[2]) is None


def test_multi_gpu_count_uses_distinct_configured_devices_and_observed_models():
    p=gpu('multiplexing');p['options']['BackendOptions']='backend=cuda-fp16,(gpu=0),(gpu=1),(gpu=1)'
    h={'gpus':[{'index':str(i),'name':'NVIDIA GeForce RTX 5080'} for i in range(2)]}
    e=evidence()|{'gpu_observations':[{'backend_instance':i,'model':'NVIDIA GeForce RTX 5080'} for i in range(2)]}
    a=ident(p,e,h)
    assert a[3]['compute']['devices']==[{'model':'GeForce RTX 5080','count':2}]
    assert a[3]['compute']['backend']=='multiplexing' and a[0]!=ident()[0]
    p['options']['BackendOptions']='backend=cuda-fp16,(gpu=1),(gpu=1)'
    assert ident(p,e,h)[3]['compute']['devices'][0]['count']==1
    p['options']['BackendOptions']='backend="cuda-fp16",(gpu=0),(gpu=1)'
    assert ident(p,e,h)[3]['compute']['devices'][0]['count']==2
    assert ident(p,evidence(),h)[3]['compute']['status']=='unverified'
    p['options']['BackendOptions']='backend=cuda-fp16,(gpu=0),(gpu=5)'
    assert ident(p,evidence(),h)[3]['compute']['status']=='unverified'
    p['options']['BackendOptions']='backend=opencl,(gpu=0),(gpu=1)'
    assert ident(p,evidence(),h)[3]['compute']['status']=='unverified'


def test_gpu_observation_preserves_multiple_models_and_root_backend():
    body={}
    for line in ('Creating backend [multiplexing]...','Creating backend [cuda]...',
                 'GPU: NVIDIA GeForce RTX 5080','GPU: NVIDIA GeForce RTX 4090'):
        assert observe_line(body,line)
    assert not observe_line(body,'GPU: NVIDIA GeForce RTX 4090')
    assert body['gpu_models']==['NVIDIA GeForce RTX 5080','NVIDIA GeForce RTX 4090']
    assert body['root_backend']=='multiplexing'


def test_cpu_gpu_pairs_replacements_restart_and_exports(tmp_path):
    s=Store(tmp_path);tid=tournament(s,profiles=[gpu(),profile()],cycles=4)
    games=[record_game(s,tid,r) for r in ['1-0','0-1','1/2-1/2','0-1']]
    r=read(s);assert r['pairs']==2 and r['total']==2 and r['official_games']==4
    row=next(x for x in r['items'] if x['compute']['kind']=='gpu');assert row['continuity']
    s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':row['id'],'rating':3000})
    r=read(s);assert r['anchor']['name']==row['name'] and r['anchor']['rating']==3000
    csv_rows=list(csv.DictReader(io.StringIO(read(s,export='csv'))))
    assert next(x for x in csv_rows if x['Compute type']=='gpu')['GPU models/count']=='GeForce RTX 5080 ×1'
    assert 'GeForce RTX 5080' in read(s,export='txt')
    assert all('compute' in x for x in read(s,category='all')['items'])
    # Different hardware in one leg must not become a paired sample.
    record_game(s,tid,'1-0');record_game(s,tid,'0-1',evidence('GeForce RTX 4090'))
    assert read(s)['pairs']==2 and read(s)['total']==3
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='diagnostic');s.set_state(tid,'running')
    record_game(s,tid,'0-1');assert read(s)['official_games']==6
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running')
    record_game(s,tid,'0-1');assert read(s)['official_games']==6 and read(s)['pairs']==2
    assert s.one('SELECT count(*) n FROM attempts WHERE gid=?',(games[0]['id'],))['n']==3
    s.set_state(tid,'paused');before=read(s)['items'];s.close();s=Store(tmp_path)
    assert read(s)['items']==before;s.close()


def test_gpu_predecessor_requires_matching_hardware_backend_and_threads(tmp_path):
    s=Store(tmp_path);keys=[]
    for model,version in [('GeForce RTX 5080','v1'),('GeForce RTX 5080','v2'),('GeForce RTX 4090','v3')]:
        tid=tournament(s,profiles=[gpu()|{'sha256':version},profile()],cycles=1)
        record_game(s,tid,'1-0',evidence(model));record_game(s,tid,'0-1',evidence(model));s.set_state(tid,'paused')
        keys.append(next(x['id'] for x in read(s,tid=tid)['items'] if x['compute']['kind']=='gpu'))
    s.rating_center_call('command',{'action':'predecessor','entry':keys[1],'predecessor':keys[0]})
    with pytest.raises(ValueError,match='matching CPU threads or verified GPU'):
        s.rating_center_call('command',{'action':'predecessor','entry':keys[2],'predecessor':keys[0]})
    s.close()


def test_legacy_ratings_and_anchor_preserved_exclusions_survive_reimport(tmp_path):
    s=Store(tmp_path);tid=tournament(s,profiles=[gpu(),profile()],cycles=1)
    record_game(s,tid,'1-0');record_game(s,tid,'0-1');s.set_state(tid,'paused')
    row=next(x for x in read(s)['items'] if x['compute']['kind']=='gpu')
    legacy=dict(row['configuration']);legacy.pop('compute');old=legacy.pop('legacy_identity')
    assert old==digest(legacy)
    # Simulates a pre-1.5.1 compact database; there is no new hardware identity.
    with s.tx():
        s.db.execute('INSERT INTO rc_entries VALUES(?,?,?,?,?)',(old,'Lc0 test · 2 threads',2,encode(legacy),1))
        for column in ('white','black'):s.db.execute(f'UPDATE rc_games SET {column}=? WHERE {column}=?',(old,row['id']))
        s.db.execute('UPDATE rc_refs SET entry=? WHERE entry=?',(old,row['id']))
        s.db.execute('DELETE FROM rc_entries WHERE id=?',(row['id'],))
        s.db.execute('UPDATE rc_pools SET revision=revision+1')
    s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':old,'rating':3000})
    assert read(s)['anchor']['entry']==old and 'legacy GPU' in read(s)['anchor']['name']
    s.close();s=Store(tmp_path);assert read(s)['pairs']==1 and read(s)['anchor']['entry']==old
    # Reimport is explicit, uses original evidence, and changes no attempts.
    before=s.rows('SELECT * FROM attempts')
    s.rating_center_call('command',{'action':'import','tid':tid,'restart':True})
    assert read(s)['official_games']==2 and read(s)['pairs']==1 and read(s)['anchor']['entry']==old
    assert s.rows('SELECT * FROM attempts')==before
    with closing(sqlite3.connect(tmp_path/'backups'/'recovery-1.sqlite3')) as dest:s.db.backup(dest)
    s.rating_center_call('command',{'action':'remove_entry','entry':old,'confirmed':True})
    assert read(s)['official_games']==0
    s.rating_center_call('command',{'action':'import','tid':tid,'restart':True});assert read(s)['official_games']==0
    with closing(sqlite3.connect(tmp_path/'backups'/'recovery-1.sqlite3')) as db:
        assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==0
    s.rating_center_call('command',{'action':'restore_entry','entry':old})
    s.rating_center_call('command',{'action':'import','tid':tid,'restart':True});assert read(s)['pairs']==1
    s.close()
