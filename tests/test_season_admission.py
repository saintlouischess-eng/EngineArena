import contextlib
import copy
import json

import pytest
from arena.store import Store
from arena import events, seasons, season_admission as admission
from test_seasons import create, drive, approve, step


def make(s, **kw):
    return create(s,n=12,sizes=[4,4],movement=[1],admission={'policy':'challenge','places':2},**kw)


def boundary(s,e):
    approve(s,e['id'])
    for _ in range(200):
        e=step(s,e['id'])
        if e['season_state']['season']==2:return e
        if e['state']=='paused':approve(s,e['id'])
    raise AssertionError('No season boundary')


@pytest.mark.parametrize('mode',['divisions','progressive'])
@pytest.mark.parametrize('policy',['full','challenge'])
def test_two_seasons_bounded_admission_games_and_reports(tmp_path,mode,policy):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=12,sizes=[4,4],movement=[1],mode=mode,admission={'policy':policy,'places':2})
        total=e['regular_games'];e=drive(s,e['id'])
        assert total==e['official_games']==e['scheduled_games']
        decisions=[v for v in e['decisions'] if 'admission' in v]
        assert len(decisions)==2
        assert decisions[0]['admission']['qualified']==list(range(8))
        assert decisions[0]['admission']['not_qualified']==list(range(8,12))
        assert len(decisions[1]['admission']['protected'])==(6 if policy=='challenge' else 0)
        assert e['season_state']['candidates']==list(range(12))
        for h in e['season_state']['history']:
            assert [len(g) for g in h['groups']]==[4,4]
            assert len({v for g in h['groups'] for v in g})==8
        for c in e['children']:
            assert s.snapshot(c['tid'])['complete_pairs']*2==c['official_games']
        from arena.event_insights import overview
        assert overview(s,e['id'])
        saved=events.detail(s,e['id'],full=True)
    with contextlib.closing(Store(tmp_path)) as s:
        assert events.detail(s,e['id'],full=True)==saved


def test_challenger_replaces_loser_without_inheriting_place(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=boundary(s,make(s,review_policy='season'))
        before=s.one('SELECT count(*) n FROM attempts')['n']
        p=s.save_profile({'name':'-1 newcomer','path':'fixture-new.exe'})
        e=seasons.review(s,e['id'],e['revision'],[{'slot':None,'new_entry':True,'profile_id':p['id']}])
        assert e['admission']['candidate_count']==13 and e['admission']['field_size']==8
        assert 12 in e['season_state']['admission_plan']['contestants']
        assert len(e['season_state']['admission_plan']['contestants'])==7
        assert s.one('SELECT count(*) n FROM attempts')['n']==before
        e=drive(s,e['id']);last=[v for v in e['decisions'] if 'admission' in v][-1]
        assert 12 in last['admission']['qualified']
        assert 7 in last['admission']['not_qualified']
        assert len({v for g in e['season_state']['groups'] for v in g})==8
        assert e['scheduled_games']==e['official_games']


def test_upgrade_waiting_candidate_and_withdrawal(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=boundary(s,make(s,review_policy='season'))
        identity=e['roster'][11]['identity']
        p=s.save_profile({'name':'-2 improved','path':'fixture-updated.exe'})
        e=seasons.review(s,e['id'],e['revision'],[{'slot':11,'profile_id':p['id']}])
        assert e['roster'][11]['identity']==identity
        candidates=[v for v in e['season_state']['candidates'] if v!=0]
        e=seasons.review(s,e['id'],e['revision'],candidates=candidates)
        assert e['admission']['protected_count']==5 and e['admission']['places']==3
        e=drive(s,e['id'])
        assert 11 in [v for g in e['season_state']['groups'] for v in g]
        assert 0 not in e['season_state']['candidates']
        assert e['scheduled_games']==e['official_games']


def test_multiple_new_candidates_and_replacement_are_atomic(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=boundary(s,make(s,review_policy='season'));old=copy.deepcopy(e)
        profiles=[s.save_profile({'name':str(-i-1),'path':f'fixture-new-{i}.exe'}) for i in range(2)]
        replacements=[{'slot':None,'profile_id':p['id'],'new_entry':True} for p in profiles]
        e=seasons.review(s,e['id'],e['revision'],replacements)
        assert e['admission']['candidate_count']==14
        e=seasons.review(s,e['id'],e['revision'],[{'slot':0,'profile_id':profiles[0]['id'],'new_entry':True}])
        assert 14 not in {v for g in e['season_state']['admission_plan']['protected'] for v in g}
        assert 14 in e['season_state']['admission_plan']['contestants']
        before=events.get(s,e['id'])
        with pytest.raises(ValueError):seasons.review(s,e['id'],e['revision'],candidates=[1,2])
        assert before==events.get(s,e['id'])
        with pytest.raises(ValueError,match='earned'):seasons.review(s,e['id'],e['revision'],groups=[[0,1,2,3],[4,5,6,7]])
        assert before==events.get(s,e['id'])


def test_admission_cutoff_playoff_replacement_and_fresh_copy(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=make(s,tie_policy='playoff');approve(s,e['id'])
        for _ in range(100):
            e=step(s,e['id'],tied=True)
            if e['season_state']['phase']=='playoff':break
        resolution=events.get(s,e['id'])['body']['season_state']['resolution']
        assert resolution['tasks'][0]['cuts']==[4,8]
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']
        count=s.one('SELECT count(*) n FROM attempts')['n']
        g=s.one('SELECT id FROM games WHERE tid=? AND official IS NOT NULL',(e['children'][0]['tid'],))
        assert s.requeue(e['children'][0]['tid'],[g['id']],mode='replacement')['dependency']
        s.requeue(e['children'][0]['tid'],[g['id']],mode='replacement',invalidate=True)
        assert s.one('SELECT count(*) n FROM attempts')['n']==count
        e=drive(s,e['id']);assert e['official_games']==e['scheduled_games']
        fresh=events.fresh(s,e['id'],'New test')
        assert fresh['admission']['candidate_count']==12
        assert fresh['admission']['protected_count']==0
        assert fresh['child_count']==fresh['official_games']==0
        events.command(s,e['id'],'next_season',e['revision'])
        e=drive(s,e['id']);assert e['season_state']['season']==3
        assert e['official_games']==e['scheduled_games']


def test_one_uncontested_place_creates_no_fictitious_game(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=8,admission={'policy':'challenge','places':1})
        e=drive(s,e['id'])
        decision=[v for v in e['decisions'] if 'admission' in v][-1]
        assert len(decision['admission']['qualified'])==1
        assert decision['standings']==[]
        assert e['scheduled_games']==e['official_games']


@pytest.mark.parametrize('n,field,policy',[(300,64,'full'),(500,128,'challenge'),(1000,32,'challenge')])
def test_large_candidate_pools_preview_and_simulated_seasons(tmp_path,n,field,policy):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,n=n,sizes=[field//4]*4,movement=[2,2,2],seasons=5,
                 qualifier={'enabled':True,'format':'swiss','rounds':7,'cycles':1},admission={'policy':policy,'places':8})
        assert not s.one('SELECT 1 FROM attempts')
        assert e['admission']['candidate_count']==n and e['admission']['field_size']==field
        b=events.get(s,e['id'])['body']
        for season in range(1,6):
            b['season_state']['season']=season;admission.begin(b)
            p=b['season_state']['admission_plan'];decision={}
            order=sorted(p['contestants'],key=lambda v:(v+season*13)%n)
            admission.place(b,order,decision)
            groups=b['season_state']['groups']
            assert len({s for g in groups for s in g})==field
            assert len(decision['admission']['not_qualified'])==n-field
            assert len(b['season_state']['candidates'])==n


def test_swiss_rounds_adapt_to_smaller_later_qualifier(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=make(s,review_policy='season',qualifier={'enabled':True,'format':'swiss','rounds':11,'cycles':1})
        b=events.get(s,e['id'])['body'];b['season_state']['season']=2;admission.begin(b)
        p,settings,total=seasons.prepared(s,b,b['season_state']['admission_plan']['contestants'],'qualification')
        assert len(p)==6 and settings['rounds']==5


def test_legacy_definition_does_not_enable_admission(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s)
        assert 'admission' not in e
        assert not admission.enabled(e['definition'])
        with pytest.raises(ValueError,match='candidate pool'):
            create(s,n=6,sizes=[4,4],admission={'policy':'full'})


def test_protected_boundary_uses_placement_tiebreaks(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=make(s);b=events.get(s,e['id'])['body'];r=b['season_state'];r['phase']='division'
        assert 2 in seasons.cuts_for(b['definition'],r,1,[{'points':0}]*4)


def test_admission_survives_forced_exit_without_forcing_a_result(tmp_path):
    import subprocess,sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    script='''import sys,os,json
sys.path.insert(0,'tests')
from arena.store import Store
from arena import events
from test_season_admission import make
from test_seasons import approve
s=Store(sys.argv[1]);e=make(s);approve(s,e['id']);events.tick(s);events.tick(s)
e=events.detail(s,e['id']);tid=e['active_tid'];s.fill_queue(tid,16)
g=s.claim(tid);s.finish(g['aid'],'1-0','fixture');unfinished=s.claim(tid)
print(json.dumps({'eid':e['id'],'tid':tid,'finished':g['aid'],'unfinished':unfinished['aid']}),flush=True)
os._exit(73)
'''
    p=subprocess.run([sys.executable,'-c',script,str(tmp_path)],cwd=root,capture_output=True,text=True,timeout=40)
    assert p.returncode==73,p.stderr
    saved=json.loads(p.stdout)
    with contextlib.closing(Store(tmp_path)) as s:
        assert events.detail(s,saved['eid'])['state']=='paused'
        assert s.one('SELECT result FROM attempts WHERE id=?',(saved['finished'],))['result']=='1-0'
        row=s.one('SELECT * FROM attempts WHERE id=?',(saved['unfinished'],))
        assert row['result'] is None or row['result']=='*'
        assert s.snapshot(saved['tid'])['official_games']==1
        e=drive(s,saved['eid'])
        assert e['official_games']==e['scheduled_games']
        assert s.one('SELECT result FROM attempts WHERE id=?',(saved['finished'],))['result']=='1-0'
        assert len(e['season_state']['candidates'])==12
