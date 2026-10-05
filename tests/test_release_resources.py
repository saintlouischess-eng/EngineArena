"""Admission must match the options actually delivered to the UCI process."""
import asyncio
import pytest
from arena.profile_import import preview,commit
from arena.resources import game_cost,recommend
from arena.store import DEFAULTS
from arena.uci import UciEngine,validated_options,parse_option,discover
from test_core import profile,store


@pytest.mark.parametrize('key',['Threads','threads','THREADS'])
def test_launch_uses_saved_option_not_differently_cased_fallback(key):
    async def run():
        p=profile('case')|{'threads':8,'hash':32,'options':{key:2,'hash':16,'ponder':True,'uci_chess960':True}}
        e=UciEngine(p,DEFAULTS|{'ponder':False,'chess960':False})
        try:
            await e.start()
            assert e.runtime['options']['Threads']==game_cost(p,p)['threads']==2
            assert e.runtime['options']['Hash']==16
            assert e.runtime['options']['Ponder'] is False
            assert e.runtime['options']['UCI_Chess960'] is False
            assert sum(line.startswith('> setoption name Threads ') for line in e.log)==1
        finally:await e.close()
    asyncio.run(run())


def test_conflicting_case_duplicates_fail_before_sending():
    option=parse_option('option name Threads type spin default 1 min 1 max 128')
    with pytest.raises(ValueError,match='Conflicting'):
        validated_options({'Threads':1,'threads':8},{'Threads':option})
    assert validated_options({'Threads':2,'threads':2},{'Threads':option})=={'Threads':2}


def test_discovery_returns_canonical_saved_options():
    p=profile('case')|{'threads':8,'options':{'threads':2,'hAsH':16,'sTyLe':'Very Aggressive'}}
    discovered=asyncio.run(discover(p,DEFAULTS))
    assert discovered['options']=={'Threads':2,'Hash':16,'Style':'Very Aggressive'}
    assert p['options']['threads']==2  # caller's saved profile is untouched


@pytest.mark.parametrize('key',['Threads','threads','Number of Threads','MaxThreads','Max CPUs'])
def test_import_previews_explicit_threads_without_mutating_source(store,key):
    p=profile('automatic')|{'threads':0,'options':{key:0}}
    result=preview(store,{'source':[p]})
    item=result['items'][0]
    assert result['ready']==1 and item['profile']['threads']==item['profile']['options'][key]==1
    assert any('changed to 1' in m for m in item['messages'])
    assert p['options'][key]==p['threads']==0
    assert commit(store,{'source':[p],'selected':[0]})['count']==1
    assert commit(store,{'source':[p],'selected':[0]})['count']==0


def test_import_reserves_advertised_alias_over_stale_fallback(store):
    p=profile('alias')|{'threads':1,'options':{'Max CPUs':8,'hash':64}}
    item=preview(store,{'source':[p]})['items'][0]
    assert item['profile']['threads']==8 and item['profile']['hash']==64
    assert game_cost(item['profile'],item['profile'])['threads']==8


def test_no_zero_cpu_budget_for_new_or_legacy_profiles(store,monkeypatch):
    p=profile('auto')|{'options':{'threads':0}}
    with pytest.raises(ValueError,match='explicit positive'):store.save_profile(p)
    monkeypatch.setattr('arena.resources.os.cpu_count',lambda:16)
    assert game_cost(p,p)['threads']==16
    assert game_cost(p,p,True)['threads']==32
    assert recommend([p,p],{'cpu_budget':8},available_mb=10000)['recommended']==0
