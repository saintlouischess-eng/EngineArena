import contextlib,json,sqlite3
import pytest
from arena.store import Store
from arena import events,seasons


def create(s,n=8,**kw):
    t=s.create_tournament('Source',[{'name':str(i),'path':'fixture.exe'} for i in range(n)],{'format':'round_robin','cycles':1},backup=False)
    d=dict(kind='season',sizes=[n//2,n-n//2],movement=[1],seasons=2,cycles=1,review_policy='automatic',tie_policy='standings',
        qualifier={'enabled':True,'format':'round_robin','rounds':3,'cycles':1},championship={'enabled':True,'games':4,'tiebreak_games':2},
        resources={'cpu_budget':2,'memory_budget_mb':4096,'concurrency':2,'gpu_limits':{}})|kw
    return events.create(s,'Season test',t['id'],d)


def approve(s,eid):
    e=events.detail(s,eid)
    if e['season_state']['review']:seasons.review(s,eid,e['revision'],approve=True)
    e=events.detail(s,eid);events.command(s,eid,'run',e['revision'])


def step(s,eid,tied=False):
    events.tick(s)
    e=events.detail(s,eid,full=True)
    for c in e['children']:
        if not c['valid'] or c['state']!='running':continue
        t=s.tournament(c['tid']);s.fill_queue(t['id'],64)
        while g:=s.claim(t['id']):
            a=int(s.participant(t['id'],g['white'])['name'].split()[0]);b=int(s.participant(t['id'],g['black'])['name'].split()[0])
            s.finish(g['aid'],'1/2-1/2' if tied else '1-0' if a<b else '0-1','fixture')
        t=s.tournament(t['id'])
        if t['settings']['format']=='round_robin' and t['cursor']*2>=t['total']:
            s.execute("UPDATE tournaments SET state='completed' WHERE id=?",(t['id'],))
    return events.detail(s,eid,full=True)


def drive(s,eid):
    e=events.detail(s,eid)
    if e['state']=='paused':approve(s,eid)
    for _ in range(500):
        e=step(s,eid)
        if e['state']=='completed':return e
        if e['state']=='paused':approve(s,eid)
    raise AssertionError(e)


@pytest.mark.parametrize('mode',['divisions','progressive'])
@pytest.mark.parametrize('n',[5,8,17])
def test_seasons_qualification_progression_and_recovery(tmp_path,mode,n):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n,mode=mode);total=e['regular_games'];e=drive(s,e['id'])
        assert e['official_games']==total==e['scheduled_games']
        assert len(e['season_state']['history'])==2
        assert [len(g) for g in e['season_state']['groups']]==[n//2,n-n//2]
        assert sorted(v for g in e['season_state']['groups'] for v in g)==list(range(n))
        assert all(h['champion']=='0' for h in e['season_state']['history'])
        assert e['decisions'][0]['placements']==[list(range(n//2)),list(range(n//2,n))]
        counts=[(c['tid'],s.snapshot(c['tid'])['official_games']) for c in e['children']]
    with contextlib.closing(Store(tmp_path)) as s:
        assert [(tid,s.snapshot(tid)['official_games']) for tid,_ in counts]==counts


def test_boundary_playoffs_and_replacement(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,tie_policy='playoff');approve(s,e['id'])
        for _ in range(100):
            e=step(s,e['id'],tied=True)
            if e['season_state']['phase']=='playoff':break
        assert e['season_state']['phase']=='playoff'
        e=drive(s,e['id']);assert e['scheduled_games']==e['official_games']>e['regular_games']
        child=e['children'][0];g=s.one('SELECT id FROM games WHERE tid=? AND official IS NOT NULL',(child['tid'],))
        assert s.requeue(child['tid'],[g['id']],mode='replacement')['dependency']
        before=s.one('SELECT count(*) n FROM attempts')['n']
        s.requeue(child['tid'],[g['id']],mode='replacement',invalidate=True)
        assert s.one('SELECT count(*) n FROM attempts')['n']==before
        e=drive(s,e['id']);assert e['state']=='completed'


def test_upgrade_season_window_and_fresh_copy(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,review_policy='season');approve(s,e['id'])
        for _ in range(100):
            e=step(s,e['id'])
            if e['season_state']['season']==2:break
            if e['state']=='paused':approve(s,e['id'])
        assert e['season_state']['review']
        p=s.save_profile({'name':'0 v2','path':'fixture-v2.exe'})
        old=s.participant(e['children'][0]['tid'],0)
        e=seasons.review(s,e['id'],e['revision'],[{'slot':0,'profile_id':p['id']}],approve=True)
        assert s.participant(e['children'][0]['tid'],0)==old
        e=drive(s,e['id']);assert e['season_state']['history'][-1]['champion']=='0 v2'
        copied=events.fresh(s,e['id'],'Fresh');assert copied['official_games']==copied['child_count']==0
        assert copied['season_state']['review'] and not copied['season_state']['history']


def test_event_deletion_scrubs_backups_empty_drafts_and_other_records(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        keep=create(s);empty=create(s);played=drive(s,create(s)['id']);s.export_pending();s.backup()
        ids=[empty['id'],played['id']];preview=events.delete_preview(s,ids)
        result=events.delete_events(s,ids,preview['events']);assert result['recovered_bytes']>0
        assert events.detail(s,keep['id'])['state']=='paused'
        for path in [s.path,*s.folder.glob('backups/*.sqlite3')]:
            with sqlite3.connect(path) as db:
                for eid in ids:
                    assert not db.execute('SELECT 1 FROM events WHERE id=?',(eid,)).fetchone()
                    assert not db.execute('SELECT 1 FROM event_children WHERE eid=?',(eid,)).fetchone()
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_clinched_final_preserves_pairs_and_total(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,championship={'enabled':True,'games':8,'tiebreak_games':2,'play_all':False})
        e=drive(s,e['id']);finals=[c for c in e['children'] if c['role']=='championship']
        assert all(c['total']==6 for c in finals)
        assert e['scheduled_games']==e['official_games']==e['regular_games']-4
        for c in finals:assert s.snapshot(c['tid'])['complete_pairs']==3


def test_new_entrant_withdrawals_extension_and_version_policy(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,review_policy='season');e=drive(s,e['id'])
        old_count=e['official_games'];events.command(s,e['id'],'next_season',e['revision']);e=events.detail(s,e['id'])
        p=s.save_profile({'name':'99 newcomer','path':'new.exe'})
        e=seasons.review(s,e['id'],e['revision'],[{'slot':None,'division':1,'new_entry':True,'profile_id':p['id']}])
        assert sum(map(len,e['season_state']['groups']))==9
        assert e['roster'][-1]['name']=='99 newcomer'
        groups=e['season_state']['groups'];groups[1].remove(7)
        e=seasons.review(s,e['id'],e['revision'],groups=groups,approve=True)
        assert sum(map(len,e['season_state']['groups']))==8
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']>old_count
        old=[c for c in e['children'] if s.tournament(c['tid'])['settings']['event_context']['season']==1]
        assert all('99 newcomer' not in [s.participant(c['tid'],i)['name'] for i in range(s.tournament(c['tid'])['participants'])] for c in old)


def test_large_unknown_field_bounded_materialization(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=1000,qualifier={'enabled':True,'format':'swiss','rounds':7,'cycles':1})
        assert e['participants']==1000;assert e['regular_games']>900000
        approve(s,e['id']);events.tick(s)
        assert s.one('SELECT count(*) n FROM games')['n']==0
        child=events.detail(s,e['id'])['children'][0]
        s.set_state(child['tid'],'running');s.fill_queue(child['tid'],32)
        assert s.one('SELECT count(*) n FROM games')['n']<=32


def test_retire_empty_event_and_restore_older_backup_cannot_resurrect(tmp_path):
    import shutil
    from arena.deletion import ledger
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);s.backup();backup=s.backup_file
        saved=tmp_path/'restore-fixture.sqlite3';shutil.copy2(backup,saved)
        # Simulated interrupted cleanup: only the independently committed intent.
        with contextlib.closing(ledger(tmp_path)) as log:
            with log:log.execute('INSERT INTO deleted_events VALUES(?)',(e['id'],))
    with contextlib.closing(Store(tmp_path)) as s:assert not s.one('SELECT 1 FROM events WHERE id=?',(e['id'],))
    shutil.copy2(saved,tmp_path/'arena.sqlite3')
    with contextlib.closing(Store(tmp_path)) as s:
        assert not s.one('SELECT 1 FROM events WHERE id=?',(e['id'],))
        assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_three_divisions_progressive_preserves_population(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=9,sizes=[2,3,4],movement=[1,2],mode='progressive')
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']
        for season in e['season_state']['history']:
            assert list(map(len,season['groups']))==[2,3,4]
            assert sorted(v for g in season['groups'] for v in g)==list(range(9))


def test_stage_conditions_opening_cursor_and_pair_integrity(tmp_path):
    import chess
    with contextlib.closing(Store(tmp_path)) as s:
        openings=[]
        for move in chess.Board().legal_moves:
            board=chess.Board();board.push(move);openings.append({'fen':board.fen(),'moves':[move.uci()],'start_fen':chess.STARTING_FEN,'name':move.uci()})
        t=s.create_tournament('Distinct conditions',[{'name':'0'},{'name':'1'}],{'time_control':{'kind':'nodes','nodes':12345},'seed':77},openings,backup=False)
        e=create(s,stage_sources={'championship':t['id']},stage_cycles={'0':2,'1':1});e=drive(s,e['id'])
        finals=[s.tournament(c['tid']) for c in e['children'] if c['role']=='championship']
        assert [f['settings']['event_opening_offset'] for f in finals]==[0,2]
        assert all(f['settings']['time_control']['nodes']==12345 for f in finals)
        assert e['official_games']==e['scheduled_games']
        for final in finals:
            assert s.snapshot(final['id'])['complete_pairs']==2
            for pair in s.rows('SELECT pair_no,count(*) n,count(DISTINCT opening) d FROM games WHERE tid=? AND invalid=0 GROUP BY pair_no',(final['id'],)):
                assert pair['n']==2


def test_forced_exit_season_and_deletion_recovery(tmp_path):
    import subprocess,sys
    root=__import__('pathlib').Path(__file__).resolve().parents[1]
    script='''import sys,os,json
sys.path.insert(0,'tests')
from arena.store import Store
from test_seasons import create,approve,step
s=Store(sys.argv[1]);e=create(s);approve(s,e['id']);step(s,e['id']);step(s,e['id'])
print(json.dumps({'id':e['id'],'official':s.one('SELECT count(*) n FROM games WHERE official IS NOT NULL')['n']}),flush=True)
os._exit(73)
'''
    p=subprocess.run([sys.executable,'-c',script,str(tmp_path)],cwd=root,capture_output=True,text=True,timeout=30)
    assert p.returncode==73,p.stderr;saved=json.loads(p.stdout)
    with contextlib.closing(Store(tmp_path)) as s:
        assert events.detail(s,saved['id'])['state']=='paused'
        assert s.one('SELECT count(*) n FROM games WHERE official IS NOT NULL')['n']==saved['official']>0
        e=drive(s,saved['id']);assert e['official_games']==e['scheduled_games']
    script='''import sys,os
from arena.store import Store
from arena.deletion import ledger
s=Store(sys.argv[1]);s.backup()
with ledger(s.folder) as db:db.execute('INSERT INTO deleted_events VALUES(?)',(sys.argv[2],))
os._exit(74)
'''
    p=subprocess.run([sys.executable,'-c',script,str(tmp_path),saved['id']],cwd=root,capture_output=True,text=True,timeout=30)
    assert p.returncode==74,p.stderr
    with contextlib.closing(Store(tmp_path)) as s:assert not s.one('SELECT 1 FROM events WHERE id=?',(saved['id'],))



def test_review_window_policy_and_atomic_rejection(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,review_policy='stage',update_policy='season',qualifier={'enabled':False,'format':'round_robin','rounds':3,'cycles':1})
        p=s.save_profile({'name':'0 new','path':'new.exe'})
        e=seasons.review(s,e['id'],e['revision'],[{'slot':0,'profile_id':p['id']}])
        assert e['roster'][0]['name']=='0 new'
        approve(s,e['id'])
        with pytest.raises(ValueError,match='review window'):
            seasons.review(s,e['id'],events.detail(s,e['id'])['revision'],[{'slot':0,'profile_id':p['id']}])
        for _ in range(100):
            e=step(s,e['id'])
            if e['state']=='paused':break
        assert e['season_state']['phase']=='championship'
        before=events.get(s,e['id'])
        with pytest.raises(ValueError,match='not allowed'):
            seasons.review(s,e['id'],e['revision'],[{'slot':0,'profile_id':p['id']}])
        assert events.get(s,e['id'])==before
        # Approving unchanged versions is allowed even when updates are frozen.
        e=seasons.review(s,e['id'],e['revision'],approve=True)
        assert not e['season_state']['review']


def test_stage_override_applies_to_boundary_playoff_and_report(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        source=s.create_tournament('Override',[{'name':'a'},{'name':'b'}],{'time_control':{'kind':'nodes','nodes':77}},backup=False)
        e=create(s,stage_sources={'qualification':source['id']},tie_policy='playoff',qualifier={'enabled':True,'format':'round_robin','rounds':3,'cycles':2})
        assert e['stage_conditions']['qualification']['cycles']==2
        assert e['stage_conditions']['championship']['cycles']==2
        b=events.get(s,e['id'])['body']
        for p in b['profiles']:p['time_control']={'kind':'depth','depth':1}
        with s.tx():events.change(s,e['id'],body=json.dumps(b))
        approve(s,e['id'])
        for _ in range(100):
            e=step(s,e['id'],tied=True)
            playoffs=[c for c in e['children'] if c['role']=='playoff']
            if playoffs:break
        child=playoffs[0];t=s.tournament(child['tid'])
        assert t['settings']['time_control']['nodes']==77
        for slot in range(t['participants']):assert 'time_control' not in s.participant(t['id'],slot)


def test_event_delete_preview_stale_and_active_guards(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s);p=events.delete_preview(s,[e['id']]);approve(s,e['id'])
        with pytest.raises(ValueError,match='Preview deletion again'):
            events.delete_events(s,[e['id']],p['events'])
        p=events.delete_preview(s,[e['id']])
        with pytest.raises(ValueError,match='Pause and drain'):
            events.delete_events(s,[e['id']],p['events'])
        assert events.get(s,e['id'])['state']=='running'
