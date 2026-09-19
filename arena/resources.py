"""Admission estimates are separate from tournament population and engine options."""
import os
import heapq
import psutil

def option(profile,name,default):
    return next((v for k,v in profile.get('options',{}).items() if k.casefold()==name.casefold()),profile.get(name.lower(),default))

def game_cost(white,black,ponder=False):
    threads=[int(option(p,'Threads',1)) for p in (white,black)]
    memory=sum(int(option(p,'Hash',1024))+int(p.get('extra_memory_mb',256)) for p in (white,black))
    groups={}
    for p in (white,black):
        if p.get('gpu_group'):groups[p['gpu_group']]=groups.get(p['gpu_group'],0)+1
    return {'threads':sum(threads) if ponder else max(threads),'memory_mb':memory,'gpu':groups}

def fits(cost,used,settings):
    cpu=settings.get('cpu_budget') or os.cpu_count() or 1
    memory=settings.get('memory_budget_mb') or int(psutil.virtual_memory().available/2**20*.85)
    if used['threads']+cost['threads']>cpu:return False,f'CPU budget {cpu} threads'
    if used['memory_mb']+cost['memory_mb']>memory:return False,f'Estimated engine memory exceeds {memory:,} MB budget'
    for group,count in cost['gpu'].items():
        limit=settings.get('gpu_limits',{}).get(group,2)
        if used['gpu'].get(group,0)+count>limit:return False,f'GPU group {group} exceeds {limit} simultaneous engine processes'
    return True,''

def usage(views,ponder=False):
    total={'threads':0,'memory_mb':0,'gpu':{}}
    for v in views:
        cost=game_cost(v['white'],v['black'],ponder)
        total['threads']+=cost['threads'];total['memory_mb']+=cost['memory_mb']
        for g,n in cost['gpu'].items():total['gpu'][g]=total['gpu'].get(g,0)+n
    return total


def recommend(profiles,settings,available_mb=None,logical_cpus=None):
    """Conservative admission recommendation for any pairing of the selection."""
    cpu=logical_cpus or os.cpu_count() or 1
    available_mb=int(psutil.virtual_memory().available/2**20) if available_mb is None else available_mb
    cpu_budget=settings.get('cpu_budget') or cpu
    memory_budget=settings.get('memory_budget_mb') or int(available_mb*.85)
    if not profiles:return {'recommended':None,'logical_cpus':cpu,'available_mb':available_mb,'note':'Select engine profiles to estimate concurrency.'}
    selfplay=settings.get('format')=='self_play' or len(profiles)==1
    threads=[int(option(p,'Threads',1)) for p in profiles]
    memory=[int(option(p,'Hash',1024))+int(p.get('extra_memory_mb',256)) for p in profiles]
    per_cpu=(2*max(threads) if selfplay else sum(heapq.nlargest(2,threads))) if settings.get('ponder') else max(threads)
    per_memory=2*max(memory) if selfplay else sum(heapq.nlargest(2,memory))
    bounds={'CPU threads':cpu_budget//per_cpu,'estimated engine memory':memory_budget//per_memory}
    groups={}
    for p in profiles:
        if p.get('gpu_group'):groups[p['gpu_group']]=min(2,groups.get(p['gpu_group'],0)+1)
    for group,count in groups.items():bounds['GPU '+group]=settings.get('gpu_limits',{}).get(group,2)//(2 if selfplay else count)
    count=max(0,min(bounds.values()));limiting=[name for name,value in bounds.items() if value==count]
    return {'recommended':count,'logical_cpus':cpu,'available_mb':available_mb,'cpu_budget':cpu_budget,'memory_budget_mb':memory_budget,'worst_pair_threads':per_cpu,'worst_pair_memory_mb':per_memory,'limiting':limiting,
      'note':'Conservative estimate for the most demanding pairing. Engine memory beyond Hash uses each profile’s additional-memory allowance.'}
