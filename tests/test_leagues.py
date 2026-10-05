import contextlib
import random
import pytest
from arena.store import Store
from arena.leagues import validate,movement
from test_events import create,drive,command,play_current


def league(**kw):
    return {'kind':'league','groups':[[0,1],[2,3],[4,5]],'movement':[1,1],'seasons':3,'initial_cycles':1,**kw}


def test_three_divisions_three_seasons_movements_and_extension(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,league());assert e['regular_games']==18
        e=drive(s,e['id']);assert len(e['children'])==9 and len(e['decisions'])==3 and e['official_games']==18
        first=e['decisions'][0]
        assert first['next_groups']==[[0,2],[1,4],[3,5]]
        assert [(v['slot'],v['from'],v['to']) for v in first['movement']]==[(1,0,1),(2,1,0),(3,1,2),(4,2,1)]
        assert first['champion']=='0'
        command(s,e['id'],'next_season');e=s.event_call('detail',e['id']);assert e['state']=='paused' and e['regular_games']==24
        assert drive(s,e['id'])['official_games']==24


def test_unequal_divisions_and_different_boundary_counts_preserve_field():
    d=league(groups=[list(range(4)),list(range(4,9)),list(range(9,12))],movement=[2,1]);validate(d)
    rng=random.Random(22)
    for season in range(50):
        tables=[]
        for g in d['groups']:
            g=g.copy();rng.shuffle(g);tables.append([{'slot':a,'name':str(a),'points':0,'rank':i+1} for i,a in enumerate(g)])
        result=movement(d,tables,season)
        assert sorted(sum(result['next_groups'],[]))==list(range(12))
        assert list(map(len,result['next_groups']))==[4,5,3]
        assert len(result['movement'])==6
        d['groups']=result['next_groups']


@pytest.mark.parametrize('override',[{'movement':[2,1]},{'movement':[1]},{'movement':[0,1]},{'seasons':0},{'division_names':['Same','Same','Third']}])
def test_bad_league_settings(override):
    with pytest.raises(ValueError):validate(league(**override))


def test_all_divisions_must_finish_before_promotion(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,league());command(s,e['id'],'run')
        for _ in range(3):s.event_call('tick');play_current(s,e['id'])
        assert not s.event_call('detail',e['id'])['decisions']
        assert s.event_call('detail',e['id'])['stage']==0


def test_replacement_invalidates_all_later_seasons_and_keeps_attempts(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=drive(s,create(s,league())['id']);tid=e['children'][0]['tid'];g=s.one('SELECT id FROM games WHERE tid=?',(tid,))
        assert s.requeue(tid,[g['id']],mode='replacement')['dependency']
        s.requeue(tid,[g['id']],mode='replacement',invalidate=True)
        assert s.one('SELECT count(*) n FROM event_children WHERE eid=? AND valid=0',(e['id'],))['n']==6
        e=drive(s,e['id']);assert e['official_games']==18 and len(e['children'])==15
        assert s.one('SELECT count(*) n FROM attempts')['n']==31


def test_league_restart_preserves_saved_movement_and_engine_identity(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:
        e=create(s,league());command(s,e['id'],'run')
        for _ in range(5):s.event_call('tick');play_current(s,e['id'])
        e=s.event_call('detail',e['id']);assert e['stage']==1
        recorded=e['decisions'][0];eid=e['id']
    with contextlib.closing(Store(tmp_path)) as s:
        e=s.event_call('detail',eid);assert e['state']=='paused' and e['decisions'][0]==recorded
        e=drive(s,eid);assert e['official_games']==18
        for c in e['children']:
            t=s.tournament(c['tid']);slots=t['settings']['event_context']['slots']
            assert [s.participant(c['tid'],i)['name'] for i in range(t['participants'])]==list(map(str,slots))
