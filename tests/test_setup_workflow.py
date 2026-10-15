import contextlib
import json
import pytest
from arena.store import Store
from arena.uci import parse_option
from arena.setup_draft import gauntlet_profiles
from test_core import profile


@pytest.fixture
def store(tmp_path):
    with contextlib.closing(Store(tmp_path)) as s:yield s


def engine(s, name, maximum=64, alias='Threads'):
    opts=[f'option name {alias} type spin default 1 min 1 max {maximum}',
          'option name Hash type spin default 1 min 1 max 4096',
          'option name SyzygyPath type string default <empty>',
          'option name OwnBook type check default true',
          'option name Clear Hash type button']
    return s.save_profile(profile(name)|{'options':{alias:1},'advertised':{o['name']:o for o in map(parse_option,opts)}})


def apply(s, ids, patch):
    req={'ids':ids,'patch':patch};p=s.bulk_profiles(req)
    return p,s.bulk_profiles(req|{'apply':True,'signature':p['signature']})


def test_bulk_alias_ranges_unknown_options_and_snapshots(store):
    a=engine(store,'A',alias='Max CPUs');b=engine(store,'B',maximum=1)
    t=store.create_tournament('Snapshot',[a,b],{},backup=False)
    before=store.participant(t['id'],0)
    patch={'threads':4,'hash':128,'options':{'SyzygyPath':'C:\\tables','OwnBook':'false','Missing':'x'}}
    preview,done=apply(store,['A','B'],patch)
    assert preview['changed']==done['changed']==2 and preview['skipped']==3
    a,b=store.profiles()['items']
    assert a['threads']==4 and a['options']['Max CPUs']==4
    assert b['threads']==1 and b['options']['Threads']==1
    assert a['hash']==b['hash']==128 and a['options']['OwnBook'] is False
    assert store.participant(t['id'],0)==before


def test_bulk_stale_preview_is_atomic(store):
    engine(store,'A');engine(store,'B')
    req={'ids':['A','B'],'patch':{'hash':256}}
    preview=store.bulk_profiles(req)
    p=store.profiles()['items'][1];p['name']='Changed';store.save_profile(p)
    with pytest.raises(ValueError,match='after preview'):store.bulk_profiles(req|{'apply':True,'signature':preview['signature']})
    assert all(p['hash']==1 for p in store.profiles()['items'])


def test_bulk_buttons_invalid_resource_and_missing_profile_do_not_write(store):
    engine(store,'A')
    p,done=apply(store,['A'],{'options':{'Clear Hash':''}})
    assert done['changed']==0 and done['skipped']==1
    for patch in ({'threads':0},{'options':{'Ponder':True}},{'options':{'Threads':8}},{'time_control':{'kind':'nodes','nodes':0}}):
        with pytest.raises(ValueError):store.bulk_profiles({'ids':['A'],'patch':patch})
    with pytest.raises(ValueError):store.bulk_profiles({'ids':['A','missing'],'patch':{'hash':128}})
    assert store.profiles()['items'][0]['hash']==1


def test_bulk_books_depth_control_clear_and_large_library(store):
    store.execute('INSERT INTO move_books VALUES(?,?)',('book',json.dumps({'id':'book','name':'Book'})))
    for i in range(1100):engine(store,str(i))
    ids=[str(i) for i in range(1100)]
    before=store.profiles()['items'][0]
    req={'ids':ids,'patch':{'move_book':{'id':'book','max_plies':6,'policy':'uniform'},'time_control':{'kind':'nodes','nodes':1000}}}
    p=store.bulk_profiles(req|{'offset':1050});assert len(p['items'])==50 and p['changed']==1100
    assert store.profiles()['items'][0]==before
    store.bulk_profiles(req|{'apply':True,'signature':p['signature']})
    p,_=apply(store,ids,{'move_book':{'max_plies':10}})
    assert store.profiles()['items'][0]['move_book']['id']=='book'
    assert store.profiles()['items'][0]['move_book']['max_plies']==10
    apply(store,ids,{'move_book':None,'time_control':None})
    assert store.profiles()['items'][0]['move_book'] is None and 'time_control' not in store.profiles()['items'][0]


def test_draft_persists_restart_and_rejects_stale_writer(tmp_path):
    value={'version':1,'fields':{'tname':'Keep me','tsyzygy':'C:\\tables'},'selected':['A','B']}
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.setup_draft()=={'revision':0,'value':None}
        assert s.setup_draft({'revision':0,'value':value})['revision']==1
    with contextlib.closing(Store(tmp_path)) as s:
        assert s.setup_draft()['value']==value
        with pytest.raises(ValueError,match='another window'):s.setup_draft({'revision':0,'value':None})
        assert s.setup_draft({'revision':1,'value':None})=={'revision':2,'value':None}


def test_named_candidates_determine_actual_gauntlet_pairings(store):
    ps=[engine(store,i) for i in ['A','B','C','D']]
    settings={'format':'gauntlet','candidates':2,'cycles':1,'paired':True,'seeding':'random'}
    ordered=gauntlet_profiles(ps,['C','A'],settings)
    assert [p['id'] for p in ordered]==['A','C','B','D']
    t=store.create_tournament('Named gauntlet',ordered,settings,backup=False)
    store.fill_queue(t['id'],8)
    for g in store.rows('SELECT a,b FROM games'):
        assert ordered[g['a']]['id'] in ('A','C') and ordered[g['b']]['id'] in ('B','D')
    assert t['total']==8
    for ids in ([],['A','A'],['no','A'],['A','B','C','D']):
        with pytest.raises(ValueError):gauntlet_profiles(ps,ids,settings)


def test_discovery_keeps_imported_settings_and_rejects_stale_commit(store):
    imported=store.save_profile(profile('Imported')|{'options':{'Hash':64,'OwnBook':False},'sha256':'kept','fingerprints':{'kept':'evidence'}})
    original=store.one('SELECT body FROM profiles WHERE id=?',('Imported',))['body']
    catalog=store.bulk_profiles({'ids':['Imported'],'catalog':True});assert catalog['missing']==[{'id':'Imported','name':'Imported'}]
    preview=store.bulk_profiles({'ids':['Imported'],'patch':{'hash':32}});assert 'discover options first' in preview['items'][0]['warnings'][0]
    opt=parse_option('option name Hash type spin default 16 min 1 max 4096')
    store.save_option_discovery('Imported',original,{'Hash':opt},{'name':'Imported engine'})
    result=store.profiles()['items'][0]
    assert result['options']==imported['options'] and result['sha256']=='kept' and result['fingerprints']==imported['fingerprints']
    assert not store.bulk_profiles({'ids':['Imported'],'catalog':True})['missing']
    with pytest.raises(ValueError):store.save_option_discovery('Imported',original,{}, {})


def test_option_discovery_endpoint_without_starting_a_game(tmp_path):
    import asyncio
    from aiohttp.test_utils import TestClient,TestServer
    from arena.server import create_app
    async def run():
        app=await create_app(tmp_path,'test');db=app['db']
        p=await db.call('save_profile',profile('Imported')|{'options':{'Threads':1}})
        async with TestClient(TestServer(app),headers={'X-Arena-Token':'test'}) as client:
            r=await client.post('/api/profiles/inspect-options',json={'id':p['id']});assert r.status==200,await r.text()
            result=await r.json();assert result['options']>0
            saved=(await db.call('profiles'))['items'][0]
            assert saved['options']==p['options'] and 'Threads' in saved['advertised']
            assert not await db.call('rows','SELECT * FROM games')
            app['runner'].tasks['busy']=asyncio.create_task(asyncio.sleep(10))
            try:
                r=await client.post('/api/profiles/inspect-options',json={'id':p['id']});assert r.status==400 and 'Pause and drain' in await r.text()
            finally:app['runner'].tasks.pop('busy').cancel()
    asyncio.run(run())
