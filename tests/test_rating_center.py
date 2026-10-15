from contextlib import closing
import json
import sqlite3
import time

import pytest

from arena.store import Store
from arena.rating_center import category, nominal, RULES, entry
from arena.rating_center_report import report, history


def profile(name='Engine A',threads=1,version=None):
    return {'name':name,'sha256':version or name,'threads':threads,'hash':64,
            'advertised':{'Threads':{'type':'spin','default':1,'min':1,'max':128},'Hash':{'type':'spin','default':64,'min':1,'max':4096}},
            'options':{'Threads':threads,'Hash':64}}


def tournament(s,paired=True,profiles=None,tc=None,cycles=3):
    t=s.create_tournament('Rating test',profiles or [profile(),profile(threads=32)],
        {'cycles':cycles,'paired':paired,'time_control':tc or {'kind':'fischer','seconds':180,'increment':2}})
    s.set_state(t['id'],'running');s.fill_queue(t['id'],100);return t['id']


def finish(s,tid,results):
    games=[]
    for result in results:
        g=s.claim(tid);assert g;s.finish(g['aid'],result,'fixture');games.append(g)
    return games


def read(s,**kw):return report(s.path,{'category':'blitz',**kw})


@pytest.mark.parametrize('value,expected',[(179,'bullet'),(180,'blitz'),(600,'blitz'),(601,'rapid'),(3599,'rapid'),(3600,'classical')])
def test_category_boundaries(value,expected):
    tc={'kind':'sudden_death','seconds':value};assert category(tc,tc,RULES)==expected


def test_nominal_stages_delay_handicap_and_fixed_limits():
    assert nominal({'kind':'staged','stages':[{'moves':40,'seconds':1200,'increment':10},{'seconds':600,'increment':30}]})==2800
    assert nominal({'kind':'staged','stages':[{'moves':20,'seconds':100}],'repeat':True})==300
    assert nominal({'kind':'delay','seconds':60,'delay':2})==180
    assert category({'kind':'nodes','nodes':1000},{'kind':'nodes','nodes':100000},RULES)=='nodes'
    assert category({'kind':'fischer','seconds':180,'increment':1},{'kind':'fischer','seconds':180,'increment':2},RULES)=='handicap'


def test_identity_thread_override_hash_alias_version_and_unknown():
    p=profile();s={'ponder':False,'chess960':False};tc={'kind':'fischer','seconds':180,'increment':2}
    a=entry(p,{},s,tc);b=entry(p|{'name':'Renamed clone','id':'other'}, {},s,tc)
    # With a recorded protocol identity, editable profile labels never split a version.
    p['identity']={'name':'Engine A'};b=entry(p|{'name':'Renamed clone'}, {},s,tc);assert b[0]==a[0]
    assert entry(p|{'options':{'Threads':32,'Hash':64}}, {},s,tc)[0]!=a[0]
    assert entry(p,{'options':{'Threads':2}},s,tc)[2]==2
    assert entry({'name':'Legacy'}, {},s,tc)[2] is None
    assert entry(p,{},s,{'kind':'nodes','nodes':1000})[0]!=entry(p,{},s,{'kind':'nodes','nodes':100000})[0]


def test_pair_samples_replacement_diagnostic_restart_and_anchor(tmp_path):
    s=Store(tmp_path);tid=tournament(s);games=finish(s,tid,['1-0','1/2-1/2','0-1'])
    r=read(s);assert r['official_games']==3 and r['pairs']==1 and r['counted_games']==2
    games+=finish(s,tid,['1-0','1/2-1/2','1/2-1/2']);r=read(s)
    assert sorted(x['threads'] for x in r['items'])==[1,32] and r['pairs']==3
    reference=next(x for x in r['items'] if x['threads']==1)['id']
    s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':reference,'rating':3000})
    r=read(s);assert r['anchor']['rating']==3000 and r['anchor']['explicit']
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='diagnostic');s.set_state(tid,'running');finish(s,tid,['0-1'])
    assert read(s)['items']==r['items']
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running');finish(s,tid,['0-1'])
    changed=read(s);assert changed['pairs']==3 and changed['official_games']==6 and changed['items']!=r['items']
    assert len(s.game_detail(games[0]['id'])['attempts'])==3
    s.close();s=Store(tmp_path);assert read(s)['items']==changed['items'];s.close()


def test_unpaired_and_fixed_nodes_entries_and_exports(tmp_path):
    s=Store(tmp_path);ps=[profile(),profile()|{'time_control':{'kind':'nodes','nodes':10000}}]
    tid=tournament(s,False,ps,{'kind':'nodes','nodes':1000},3);finish(s,tid,['1-0','0-1','1/2-1/2'])
    r=read(s,category='nodes');assert r['unpaired']==3 and r['pairs']==0 and len(r['items'])==2
    assert '10000 nodes' in ' '.join(x['name'] for x in r['items'])
    assert len(read(s,category='all')['items'])==2
    assert 'Reference:' in read(s,category='nodes',export='txt')
    assert 'Configuration ID' in read(s,category='nodes',export='csv');s.close()


def test_explicit_import_reset_no_resurrection_and_backup_scrub(tmp_path):
    s=Store(tmp_path);s.rating_center_call('command',{'action':'configure','automatic':False})
    tid=tournament(s);games=finish(s,tid,['1-0','0-1','1/2-1/2','1/2-1/2']);assert read(s)['total']==0
    imported=s.rating_center_call('command',{'action':'import','tid':tid,'restart':True});assert imported['done'] and imported['games']==4
    assert read(s)['pairs']==2;s.set_state(tid,'paused')
    snapshot=tmp_path/'backups'/'recovery-1.sqlite3'
    with closing(sqlite3.connect(snapshot)) as dest:s.db.backup(dest)
    s.rating_center_call('command',{'action':'reset','category':'blitz','confirmed':True})
    assert read(s)['total']==0
    with closing(sqlite3.connect(snapshot)) as db:assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==0
    s.rating_center_call('command',{'action':'configure','automatic':True})
    s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running');finish(s,tid,['0-1'])
    assert read(s)['total']==0 # an old game replay does not bypass reset
    finish(s,tid,['1-0','0-1']);assert read(s)['official_games']==2
    s.rating_center_call('command',{'action':'import','tid':tid,'restart':True});assert read(s)['official_games']==6
    s.set_state(tid,'paused');s.close()


@pytest.mark.parametrize('keep',[False,True])
def test_delete_tournament_retention_and_backups(tmp_path,keep):
    s=Store(tmp_path);tid=tournament(s);finish(s,tid,['1-0','0-1']);s.set_state(tid,'paused')
    snapshot=tmp_path/'backups'/'recovery-1.sqlite3'
    with closing(sqlite3.connect(snapshot)) as dest:s.db.backup(dest)
    s.delete_tournament(tid,'Rating test',keep)
    assert read(s)['official_games']==(2 if keep else 0)
    with closing(sqlite3.connect(snapshot)) as db:
        assert db.execute('SELECT count(*) FROM tournaments').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM rc_games').fetchone()[0]==(2 if keep else 0)
    assert not s.one('SELECT 1 FROM attempts')
    assert s.rating_center_call('sources','main')['total']==(1 if keep else 0)
    s.close()


def test_predecessor_history_filters_new_list_and_removal(tmp_path):
    s=Store(tmp_path);tid=tournament(s);finish(s,tid,['1-0','0-1','1/2-1/2','0-1','1-0','1/2-1/2']);s.set_state(tid,'paused')
    old=next(x for x in read(s)['items'] if x['threads']==1)
    tid2=tournament(s,profiles=[profile(version='v2')|{'identity':{'name':'Engine A v2'}},profile(threads=32)])
    finish(s,tid2,['1-0']);s.set_state(tid2,'paused');new=next(x for x in read(s)['items'] if 'v2' in x['name'])
    s.rating_center_call('command',{'action':'predecessor','entry':new['id'],'predecessor':old['id']})
    r=next(x for x in read(s)['items'] if 'v2' in x['name']);assert r['rating'] is None and r['provisional_seed'] is not None and r['samples']==0
    h=history(s.path,{'category':'blitz','entry':old['id']});assert len(h['items'])==1
    assert read(s,tid=tid2)['official_games']==1
    newpool=s.rating_center_call('command',{'action':'create','name':'Controlled hardware'})['id'];assert read(s,pool=newpool)['total']==0
    s.rating_center_call('command',{'action':'import','pool':newpool,'tid':tid,'restart':True});assert read(s,pool=newpool)['official_games']==6
    s.rating_center_call('command',{'action':'remove_source','pool':newpool,'tid':tid,'confirmed':True});assert read(s,pool=newpool)['total']==0
    s.rating_center_call('command',{'action':'remove_entry','entry':new['id'],'confirmed':True});assert read(s)['official_games']==6
    s.close()


def test_matches_existing_paired_solver_and_excludes_failed_pairs(tmp_path):
    from arena.ratings import pool_report
    s=Store(tmp_path);tid=tournament(s,cycles=4)
    games=finish(s,tid,['1-0','0-1','1/2-1/2','0-1','1-0','1/2-1/2','0-1','1-0'])
    key=next(r['id'] for r in read(s)['items'] if r['threads']==1)
    s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':key,'rating':0})
    expected=pool_report(s.path,tid);actual=read(s)
    for row in actual['items']:
        value=next(x for x in expected['items'] if x['slot']==(0 if row['threads']==1 else 1))
        assert row['rating']==pytest.approx(value['rating'])
        assert row['ci']==pytest.approx(value['ci']) if value['ci'] else row['ci'] is None
    s.set_state(tid,'paused');s.requeue(tid,[games[0]['id']],mode='replacement');s.set_state(tid,'running')
    g=s.claim(tid);s.finish(g['aid'],'0-1','timeout');s.set_state(tid,'paused')
    filtered=read(s,failures='exclude');assert filtered['pairs']==3 and filtered['official_games']==7 and filtered['counted_games']==6
    s.close()


def test_paused_collection_still_tracks_official_replacements(tmp_path):
    s=Store(tmp_path);tid=tournament(s);g=finish(s,tid,['1-0','0-1'])[0];s.set_state(tid,'paused')
    s.rating_center_call('command',{'action':'configure','automatic':False})
    s.requeue(tid,[g['id']],mode='replacement');s.set_state(tid,'running');finish(s,tid,['0-1'])
    assert read(s)['official_games']==2 and read(s)['pairs']==1
    assert s.one('SELECT result FROM rc_games WHERE gid=?',(g['id'],))['result']=='0-1';s.close()


def test_receipt_survives_old_database_restore_and_no_result_transaction_gap(tmp_path,monkeypatch):
    from arena import rating_center
    from arena.deletion import ledger
    s=Store(tmp_path);tid=tournament(s);finish(s,tid,['1-0','0-1']);s.set_state(tid,'paused')
    before=s.one('SELECT count(*) n FROM rc_games')['n']
    s.set_state(tid,'running');g=s.claim(tid);original=rating_center.sync
    def fail(*a,**kw):original(*a,**kw);raise sqlite3.OperationalError('forced commit failure')
    monkeypatch.setattr(rating_center,'sync',fail)
    from arena.store import SavingError
    with pytest.raises(SavingError):s.finish(g['aid'],'1-0','fixture')
    assert s.one('SELECT official FROM games WHERE id=?',(g['id'],))['official'] is None
    assert s.one('SELECT ended FROM attempts WHERE id=?',(g['aid'],))['ended'] is None
    assert s.one('SELECT count(*) n FROM rc_games')['n']==before
    monkeypatch.setattr(rating_center,'sync',original);s.failure='';s.finish(g['aid'],'*','interrupted');s.set_state(tid,'paused')
    # Receipt committed but application killed before live/backup cleanup.
    with closing(ledger(tmp_path)) as log:
        with log:log.execute('INSERT INTO rating_actions(body) VALUES(?)',(json.dumps({'pool':'main','action':'reset','category':'all','at':time.time()}),))
    s.close();s=Store(tmp_path)
    assert read(s)['official_games']==0 and s.one('SELECT count(*) n FROM games WHERE official IS NOT NULL')['n']==2
    s.close()


def test_event_stage_invalidation_and_retained_deletion(tmp_path):
    from test_seasons import create,drive
    from arena import events
    s=Store(tmp_path);e=drive(s,create(s,n=4)['id']);all_games=s.one('SELECT count(*) n FROM rc_games')['n'];assert all_games>0
    stage=s.one('SELECT tid FROM event_children WHERE eid=? LIMIT 1',(e['id'],))['tid']
    n=s.one('SELECT count(*) n FROM rc_games WHERE tid=?',(stage,))['n'];assert n>0
    s.execute('UPDATE event_children SET valid=0 WHERE tid=?',(stage,))
    r=report(s.path,{'category':'all','export':'json'});assert sum(x['games'] for x in r['items'])==2*(all_games-n)
    preview=events.delete_preview(s,[e['id']]);events.delete_events(s,[e['id']],preview['events'],True)
    r=report(s.path,{'category':'all','export':'json'});assert sum(x['games'] for x in r['items'])==2*(all_games-n)
    s.close()


def test_fifty_thousand_pairs_compact_ledger_and_paging(tmp_path):
    s=Store(tmp_path);tid=tournament(s);finish(s,tid,['1-0','1/2-1/2']);s.set_state(tid,'paused')
    base=s.one('SELECT * FROM rc_games LIMIT 1');keys=list(base)
    with s.tx():
        s.db.execute('DELETE FROM rc_games')
        def rows():
            for i in range(100000):
                row=dict(base,gid=str(i),aid=str(i),pair_no=i//2,leg=i%2,result=['1-0','1/2-1/2','0-1'][i%3])
                if i%2:row['white'],row['black']=base['black'],base['white']
                yield tuple(row[k] for k in keys)
        s.db.executemany('INSERT INTO rc_games VALUES('+','.join('?' for _ in keys)+')',rows())
        s.db.execute('UPDATE rc_pools SET revision=revision+1')
    started=time.monotonic();r=read(s);elapsed=time.monotonic()-started
    assert r['official_games']==100000 and r['pairs']==50000 and r['total']==2
    assert all(x['games']==100000 for x in r['items'])
    assert elapsed<15 # generous regression guard, not a promised user benchmark
    print('100k compact results / 50k pairs:',round(elapsed,3),'seconds')
    plan=' '.join(str(tuple(row)) for row in s.db.execute('EXPLAIN QUERY PLAN SELECT pool FROM rc_games WHERE gid=?',('5',)))
    assert 'rc_games_identity' in plan
    s.close()
