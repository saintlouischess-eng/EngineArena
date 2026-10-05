"""Sparse, fixed matchup lists; repetitions remain implicit at any game count."""
from bisect import bisect_right
from functools import lru_cache


def validate(n,items):
    if not isinstance(items,list) or not items:raise ValueError('Add at least one custom matchup.')
    seen=set();total=0;result=[]
    for item in items:
        if not isinstance(item,dict):raise ValueError('Each custom matchup needs two participants and a count.')
        a,b,count=(item.get(k) for k in ('a','b','count'))
        if any(type(v) is not int for v in (a,b,count)) or not (0<=a<n and 0<=b<n) or a==b or count<1:
            raise ValueError('Custom matchups need two different valid participants and a positive whole count.')
        key=tuple(sorted((a,b)))
        if key in seen:raise ValueError('Each custom opponent combination may appear only once. Increase its count instead.')
        seen.add(key);total+=count
        if total>9223372036854775807:raise ValueError('Custom schedule exceeds 64-bit game numbering capacity.')
        result.append({'a':a,'b':b,'count':count})
    return result,total


@lru_cache(maxsize=8)
def spans(key):
    ends=[];total=0
    for a,b,count in key:total+=count;ends.append(total)
    return ends


def decode(index,settings):
    # One index per decoded settings snapshot, not one scan per selected game.
    cached=settings.get('_custom_index')
    if cached is None:
        key=tuple((v['a'],v['b'],v['count']) for v in settings['custom_matchups'])
        cached=(key,spans(key));settings['_custom_index']=cached
    key,ends=cached;i=bisect_right(ends,index)
    if i>=len(key):raise ValueError('Custom game number is outside the schedule.')
    a,b,count=key[i];rep=index-(ends[i-1] if i else 0)
    if not settings['paired'] and rep%2:a,b=b,a
    return a,b,rep,ends[i]


def pair(index,n,settings):
    if settings['format']=='custom':return decode(index,settings)[:3]
    from .opening_policy import round_pair
    from .models import static_pair
    decoder=round_pair if settings.get('opening_policy')=='round' else static_pair
    return decoder(index,n,settings['format'],settings['cycles'],settings['candidates'])
