"""System-update pairs count without rewriting evidence or bypassing filters."""
from copy import deepcopy
from contextlib import closing
import json
import pytest
from arena.store import Store
from arena.rating_center import digest,encode
from arena.rating_center_report import report,cpu_pair_conditions
from test_rating_center import tournament,finish

HARDWARE={'cpu':'Fixture CPU','physical_cores':16,'logical_processors':32,'ram_gib':64,
          'os':'Windows-11-10.0.26200-SP0','gpus':[{'name':'RTX 5080','driver':'616.92','index':'0'}]}

def changed_pair(store,change=None,gpu=False):
    tid=tournament(store,cycles=1);finish(store,tid,['1-0','1/2-1/2']);store.set_state(tid,'paused')
    base=json.loads(store.one('SELECT body FROM rc_conditions LIMIT 1')['body']);base['hardware']=deepcopy(HARDWARE)
    after=deepcopy(base);after['hardware']['os']='Windows-11-10.0.26300-SP0';after['hardware']['gpus'][0]['driver']='617.42'
    if change:change(after)
    keys=[]
    with store.tx():
        for leg,body in enumerate((base,after)):
            key=digest(body);keys.append(key)
            store.db.execute('INSERT OR IGNORE INTO rc_conditions VALUES(?,?,?)',(key,digest(body['hardware']),encode(body)))
            store.db.execute('UPDATE rc_games SET conditions=? WHERE tid=? AND leg=?',(key,tid,leg))
        if gpu:
            r=store.one('SELECT id,body FROM rc_entries LIMIT 1');body=json.loads(r['body']);body['compute']={'kind':gpu,'status':'configured','backend':'cuda','devices':[]}
            store.db.execute('UPDATE rc_entries SET body=? WHERE id=?',(encode(body),r['id']))
        store.db.execute('UPDATE rc_pools SET revision=revision+1')
    return tid,keys,base,after

def test_cpu_maintenance_updates_count_preserve_evidence_and_exact_filters(tmp_path):
    with closing(Store(tmp_path)) as s:
        tid,keys,base,after=changed_pair(s)
        before={t:s.rows('SELECT * FROM '+t) for t in ('games','attempts','rc_games','rc_conditions','rc_entries')}
        r=report(s.path,{'export':'json'})
        assert r['official_games']==r['counted_games']==2 and r['pairs']==1
        assert r['sampling']['compatible_update_pairs']==1 and r['sampling']['excluded_games']==0
        assert 'Included CPU pairs across system updates: 1' in report(s.path,{'export':'txt'})
        for field,value in [('conditions',keys[0]),('conditions',keys[1]),('hardware',digest(base['hardware'])),('hardware',digest(after['hardware']))]:
            filtered=report(s.path,{field:value})
            assert filtered['official_games']==1 and filtered['counted_games']==0
            assert filtered['sampling']['incomplete_pair_games']==1
            assert filtered['sampling']['compatible_update_pairs']==0
        for t,rows in before.items():assert rows==s.rows('SELECT * FROM '+t)

@pytest.mark.parametrize('change',[
    lambda b:b['hardware'].update(cpu='Different CPU'),
    lambda b:b['hardware'].update(physical_cores=8),
    lambda b:b['hardware'].update(ram_gib=32),
    lambda b:b['hardware'].update(os='Windows-10-10.0.26300-SP0'),
    lambda b:b['hardware'].update(os='Windows-11-11.0.26300-SP0'),
    lambda b:b['controls'][0].update(seconds=30),
    lambda b:b['adjudication'].update(tolerance=2),
    lambda b:b.update(ponder=True),
    lambda b:b.update(future_rule='must not ignore'),
])
def test_playing_conditions_and_hardware_stay_strict(tmp_path,change):
    with closing(Store(tmp_path)) as s:
        changed_pair(s,change)
        r=report(s.path)
        assert r['official_games']==2 and r['counted_games']==0
        assert r['sampling']['incompatible_condition_games']==2

@pytest.mark.parametrize('gpu',['gpu','legacy_gpu'])
def test_gpu_pairs_do_not_use_cpu_system_update_relaxation(tmp_path,gpu):
    with closing(Store(tmp_path)) as s:
        changed_pair(s,gpu=gpu);r=report(s.path)
        assert r['pairs']==0 and r['sampling']['incompatible_condition_games']==2

def test_unknown_hardware_does_not_gain_compatibility():
    a={'hardware':{'os':'Windows-11-10.0.26200-SP0'}}
    b={'hardware':{'os':'Windows-11-10.0.26300-SP0'}}
    assert cpu_pair_conditions(encode(a))!=cpu_pair_conditions(encode(b))

def test_different_configuration_and_bad_color_pairs_still_excluded(tmp_path):
    with closing(Store(tmp_path)) as s:
        tid,_,_,_=changed_pair(s)
        with s.tx():
            first=s.one('SELECT white,black FROM rc_games WHERE tid=? AND leg=0',(tid,))
            s.db.execute('UPDATE rc_games SET white=?,black=? WHERE tid=? AND leg=1',(first['white'],first['black'],tid))
            s.db.execute('UPDATE rc_pools SET revision=revision+1')
        r=report(s.path);assert r['pairs']==0 and r['sampling']['identity_mismatch_games']==2
