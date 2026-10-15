import contextlib
import json
import time
import pytest
from arena.store import Store
from arena import events,seasons
from arena.event_insights import overview,careers
from test_seasons import create,drive,step,approve


@pytest.mark.parametrize('mode',['divisions','progressive'])
def test_completed_seasons_reconcile_and_do_not_write(tmp_path,mode):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s,n=8,mode=mode)['id']);changes=s.db.total_changes
        o=overview(s,e['id'],full=True);roster=careers(s,e['id'])
        assert o['complete'] and o['champion']['name']=='0'
        assert o['all_official']==e['official_games']
        assert sum(p['games'] for p in roster['items'])==e['official_games']*2
        assert sum(len(p['titles']) for p in roster['items'])==2
        assert o['movements'] and all(not p['provisional'] for st in o['stages'] if st['role']=='division' for p in st['entries'])
        for p in roster['items']:
            c=careers(s,e['id'],identity=p['identity'])
            assert sum(r['games'] for r in c['rivals'])==c['games']
            assert sum(h['wins'] for h in c['history'])==c['wins']
        assert s.db.total_changes==changes
        assert overview(s,e['id'],season=1)['complete']
        serialized=json.dumps(o)
        assert 'fixture.exe' not in serialized and '"path"' not in serialized


def test_upgrade_keeps_identity_and_separates_versions(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,review_policy='season');approve(s,e['id'])
        for _ in range(100):
            e=step(s,e['id'])
            if e['season_state']['season']==2:break
            if e['state']=='paused':approve(s,e['id'])
        identity=e['roster'][0]['identity'];before=careers(s,e['id'],identity=identity)
        p=s.save_profile({'name':'0 revised','path':'fixture-v2.exe'})
        seasons.review(s,e['id'],e['revision'],[{'slot':0,'profile_id':p['id']}],approve=True)
        e=drive(s,e['id']);c=careers(s,e['id'],identity=identity)
        assert c['name']=='0 revised' and c['titles']==[1,2]
        assert [v['name'] for v in c['versions']]==['0','0 revised']
        assert c['versions'][0]['games']==before['games']
        assert all(h['name']=='0' for h in c['history'] if h['season']==1)
        assert careers(s,e['id'],search='revised')['total']==1


def test_replacement_excludes_superseded_stages_and_diagnostics(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s,n=5)['id']);old=overview(s,e['id'])
        g=s.one('SELECT id,tid FROM games WHERE tid=? AND official IS NOT NULL',(e['children'][0]['tid'],))
        attempts=s.one('SELECT count(*) n FROM attempts')['n']
        s.requeue(g['tid'],[g['id']],mode='replacement',invalidate=True)
        reduced=overview(s,e['id'])
        assert reduced['all_official']<old['all_official'] and not reduced['champions']
        assert s.one('SELECT count(*) n FROM attempts')['n']==attempts
        assert sum(p['games'] for p in careers(s,e['id'])['items'])==2*reduced['all_official']
        e=drive(s,e['id']);assert overview(s,e['id'])['all_official']==old['all_official']
        # Diagnostic replay must not replace the official attempt or career totals.
        c=e['children'][-1];game=s.one('SELECT id FROM games WHERE tid=? LIMIT 1',(c['tid'],))
        before=careers(s,e['id']);s.requeue(c['tid'],[game['id']],mode='diagnostic')
        s.set_state(c['tid'],'running');active=s.claim(c['tid']);s.finish(active['aid'],'1/2-1/2','fixture')
        assert careers(s,e['id'])==before


def test_new_entrant_same_name_has_distinct_career(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s,n=5)['id']);old=careers(s,e['id'],search='4')['items'][0]
        e=events.command(s,e['id'],'next_season',e['revision'])
        e=events.detail(s,e['id']);p=s.save_profile({'name':'4','path':'other.exe'})
        seasons.review(s,e['id'],e['revision'],[{'slot':4,'profile_id':p['id'],'new_entry':True}],approve=True)
        e=drive(s,e['id']);rows=careers(s,e['id'],search='4')['items']
        assert len(rows)==2 and len({p['identity'] for p in rows})==2
        assert next(p for p in rows if p['identity']==old['identity'])['games']==old['games']
        assert sum(p['active'] for p in rows)==1


def test_legacy_league_results_and_fresh_event(tmp_path):
    from test_league_update import create as legacy_create,drive as legacy_drive
    with contextlib.closing(Store(tmp_path)) as s:
        e=legacy_drive(s,legacy_create(s)['id'],ties=2)
        o=overview(s,e['id'],full=True)
        assert o['complete'] and o['final']['games']>0
        assert o['all_official']==e['official_games']
        assert sum(len(p['titles']) for p in careers(s,e['id'])['items'])==2
        fresh=events.fresh(s,e['id'],'Fresh');o=overview(s,fresh['id'])
        assert not o['champions'] and o['all_official']==0
        assert all(p['games']==0 for p in careers(s,fresh['id'])['items'])


def test_live_provisional_places_and_cache_refresh(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,qualifier={'enabled':False});approve(s,e['id']);events.tick(s)
        first=overview(s,e['id']);assert not first['complete']
        assert all(p['provisional'] for st in first['stages'] for p in st['entries'])
        e=step(s,e['id']);second=overview(s,e['id'])
        assert second['official']>first['official']
        assert overview(s,e['id'],season=2)['stages']==[]
        with pytest.raises(ValueError):overview(s,e['id'],season=99)


def test_paged_large_roster_and_no_move_log_queries(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=1000,qualifier={'enabled':False});approve(s,e['id']);events.tick(s)
        queries=[];s.db.set_trace_callback(queries.append);start=time.perf_counter()
        o=overview(s,e['id']);p=careers(s,e['id'],offset=950)
        assert p['total']==1000 and len(p['items'])==50
        assert all(len(st['entries'])==50 and st['more']==450 for st in o['stages'])
        seen=[];tid=o['stages'][0]['tid']
        for offset in range(0,500,50):
            table=next(st for st in overview(s,e['id'],entry_offsets={tid:offset})['stages'] if st['tid']==tid)
            assert table['entry_offset']==offset and table['field']==500
            assert [p['rank'] for p in table['entries']]==list(range(offset+1,offset+51))
            seen.extend(p['identity'] for p in table['entries'])
        assert len(set(seen))==500
        page=overview(s,e['id'],entry_offsets={tid:999999})['stages'][0]
        assert page['entry_offset']==450 and page['more']==0
        assert len(overview(s,e['id'],full=True,entry_offsets={tid:450})['stages'][0]['entries'])==500
        assert not any('FROM moves' in q or 'FROM logs' in q for q in queries)
        assert time.perf_counter()-start<5


def test_qualification_all_64_places_accessible_without_writes(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=64);approve(s,e['id']);events.tick(s);changes=s.db.total_changes
        first=overview(s,e['id'])['stages'][0];tid=first['tid']
        last=overview(s,e['id'],entry_offsets={tid:50})['stages'][0]
        assert first['field']==64 and first['more']==14 and len(last['entries'])==14
        assert [p['rank'] for p in first['entries']+last['entries']]==list(range(1,65))
        assert last['more']==0 and last['entry_offset']==50
        for offsets in ([],{'x':-1},{'x':'50'},{'x':True}):
            with pytest.raises(ValueError,match='standings page'):overview(s,e['id'],entry_offsets=offsets)
        assert s.db.total_changes==changes


def test_playoffs_use_played_order_without_adding_points(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=8,tie_policy='playoff',qualifier={'enabled':False});approve(s,e['id'])
        for _ in range(100):
            e=step(s,e['id'],tied=True)
            if e['season_state']['phase']=='playoff':break
        e=drive(s,e['id']);o=overview(s,e['id'],season=1,full=True)
        tables=[st for st in o['stages'] if st['role']=='division']
        assert all(p['points']==3 for st in tables for p in st['entries'])
        assert all(not p['provisional'] for st in tables for p in st['entries'])
        assert tables[0]['entries'][0]['name']=='0'


def test_duplicate_names_without_final_title_goes_to_entrant(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s,n=5,championship={'enabled':False})['id'])
        o=overview(s,e['id'])
        assert o['champion']['identity']
        assert careers(s,e['id'],identity=o['champion']['identity'])['titles']==[1,2]


def test_circuit_championship_has_bracket_order_and_separate_final_match(tmp_path):
    from test_circuits import create as make,drive as finish,stage
    with contextlib.closing(Store(tmp_path)) as s:
        e=finish(s,make(s,n=6,stages=[dict(stage('Six-engine championship'),format='knockout')],seasons=1)['id'])
        changes=s.db.total_changes;o=overview(s,e['id'],full=True);f=o['final']
        assert f['games']==10 and f['deciding_match']['games']==2
        assert f['deciding_match']['a_score']+f['deciding_match']['b_score']==2
        assert f['players'][0]['name']=='0' and f['players'][0]['rank']=='Champion'
        assert f['players'][1]['rank']=='Runner-up'
        assert sum(p['games'] for p in f['players'])==2*f['games']
        c=careers(s,e['id'],identity=f['players'][0]['identity'])
        assert c['history'][0]['rank']=='Champion'
        assert s.db.total_changes==changes


def test_legacy_circuit_playoff_labels_are_distinct_without_writes(tmp_path):
    from test_circuits import create as make,resume,step as advance,drive as finish,stage
    with contextlib.closing(Store(tmp_path)) as s:
        e=make(s,n=8,stages=[dict(stage('Groups'),groups=2,ties='playoff'),stage('Final')],seasons=1)
        resume(s,e['id'])
        for _ in range(80):
            e=advance(s,e['id'],tied=True)
            if sum(c['role']=='playoff' for c in e['children'])>=3:break
        e=finish(s,e['id']);playoffs=[c for c in e['children'] if c['role']=='playoff']
        assert len(playoffs)>=3
        # Reproduce the old stored headings, as in the owner's finished test.
        for child in playoffs:
            settings=s.tournament(child['tid'])['settings'];settings['event_context']['label']='Groups — Placement playoff'
            s.db.execute('UPDATE tournaments SET settings=? WHERE id=?',(json.dumps(settings),child['tid']))
        changes=s.db.total_changes
        o=overview(s,e['id'],full=True);labels=[st['label'] for st in o['stages'] if st['role']=='playoff']
        assert len(labels)==len(set(labels))==len(playoffs)
        assert all('Group ' in label and 'Placement playoff ' in label for label in labels)
        details=events.detail(s,e['id'],full=True)
        assert [c['display_label'] for c in details['children'] if c['role']=='playoff']==labels
        assert s.db.total_changes==changes
