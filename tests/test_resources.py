from arena.resources import game_cost,fits,usage,recommend

def test_memory_counts_both_engines_and_ponder_counts_both_cpus():
    a={'threads':4,'hash':1024,'extra_memory_mb':300};b={'threads':8,'hash':2048,'extra_memory_mb':500}
    assert game_cost(a,b)=={'threads':8,'memory_mb':3872,'gpu':{}}
    assert game_cost(a,b,True)['threads']==12
    assert game_cost({'options':{'tHrEaDs':16,'hAsH':64}},b)['threads']==16

def test_admission_is_independent_of_participant_count():
    cost=game_cost({'threads':1,'hash':32},{'threads':1,'hash':32})
    used=usage([])
    assert fits(cost,used,{'cpu_budget':32,'memory_budget_mb':4096})[0]
    assert not fits(cost,{'threads':32,'memory_mb':0,'gpu':{}},{'cpu_budget':32})[0]
    assert not fits(cost,used,{'cpu_budget':32,'memory_budget_mb':100})[0]

def test_gpu_process_slots_are_shared():
    p={'threads':1,'hash':1,'gpu_group':'gpu0'};cost=game_cost(p,p)
    assert cost['gpu']=={'gpu0':2}
    assert not fits(cost,usage([]),{'gpu_limits':{'gpu0':1}})[0]
    assert fits(cost,usage([]),{'gpu_limits':{'gpu0':2}})[0]


def test_recommendations_respect_handicaps_ponder_memory_and_large_fields():
    a={'threads':2,'hash':1024,'extra_memory_mb':0};b={'threads':6,'hash':2048,'extra_memory_mb':0}
    r=recommend([a,b],{},available_mb=10000,logical_cpus=32)
    assert r['recommended']==2 and r['worst_pair_threads']==6 and r['worst_pair_memory_mb']==3072 and r['limiting']==['estimated engine memory']
    r=recommend([a,b],{'ponder':True,'memory_budget_mb':100000},available_mb=10000,logical_cpus=32)
    assert r['recommended']==4 and r['worst_pair_threads']==8
    assert recommend([a]*10000,{'memory_budget_mb':1000000},logical_cpus=128)['recommended']==64
    assert recommend([a,b],{'memory_budget_mb':1})['recommended']==0
    assert recommend([a,b],{'format':'self_play','ponder':True,'memory_budget_mb':100000},logical_cpus=32)['worst_pair_threads']==12
    assert recommend([],{},logical_cpus=32)['recommended'] is None


def test_recommendation_counts_gpu_engine_processes():
    a={'threads':1,'hash':32,'gpu_group':'gpu0'};b={'threads':1,'hash':32}
    assert recommend([a,b],{'gpu_limits':{'gpu0':3}},available_mb=100000,logical_cpus=32)['recommended']==3
    assert recommend([a,a],{'gpu_limits':{'gpu0':3}},available_mb=100000,logical_cpus=32)['recommended']==1
