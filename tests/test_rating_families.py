from contextlib import closing
import copy,csv,io,json
import pytest
from arena.store import Store
from arena.rating_families import automatic,describe,select
from test_rating_center import profile,tournament,finish,read


@pytest.mark.parametrize('name,expected',[
 ('Stockfish 18','Stockfish'),('Stockfish dev-20261013','Stockfish'),('Lc0 v0.32','Lc0'),
 ('Chess System Tal 2.00','Chess System Tal'),('Alexandria-9.0.0','Alexandria'),
 ('Stockfish-DV','Stockfish-DV'),('Some Long Engine','Some Long Engine'),('Reckless_0.10','Reckless'),
 ('Integral v8','Integral'),('Engine2','Engine2')])
def test_conservative_family_suffixes(name,expected):assert automatic(name)==expected


def row(id,version,rating,threads=1,compute=None,limit=None):
 r={'id':id,'name':version,'threads':threads,'configuration':{'version':version,'limit':limit,**({'compute':compute} if compute else {})},'rating':rating,'samples':20,'games':40}
 describe(r,{});return r


def test_thread_gpu_backend_limits_and_unverified_stay_distinct():
 gpu={'kind':'gpu','threads':1,'devices':[{'model':'RTX 5080','count':1}],'backend':'cuda','status':'engine_reported'}
 rows=[row('a','Engine 1',3000),row('b','Engine 2',3010),row('c','Engine 2',3200,32),
       row('d','Engine 2',3500,1,gpu),row('e','Engine 3',3510,1,gpu),
       row('f','Engine 3',3600,1,gpu|{'backend':'cudnn'}),row('g','Engine 3',3600,1,gpu|{'devices':[{'model':'RTX 4090','count':1}]}),
       row('h','Engine 1',3000,None),row('i','Engine 2',3001,None),
       row('j','Engine 2',3000,1,limit={'kind':'nodes','nodes':1000}),row('k','Engine 2',3300,1,limit={'kind':'nodes','nodes':100000}),
       row('l','Engine 2',3400,None,gpu),row('m','Engine 3',3450,None,gpu)]
 assert {r['id'] for r in select(rows)}=={'b','c','e','f','g','h','i','j','k','m'}


def test_ties_unavailable_and_huge_list_stable_before_pagination():
 a=row('a','Engine 1',None);b=row('b','Engine 2',3000);c=row('c','Engine 3',3000+1e-12);c['samples']=21
 assert select([a,b,c])[0]['id']=='c'
 c['rating']=None;b['rating']=None
 assert select([a,b,c])[0]['id']=='c'
 rows=[row(str(i),f'Family{i//3} {i%3+1}',i%3) for i in range(1500)]
 assert len(select(rows))==500 and all(r['rating']==2 for r in select(rows))


def seed(s):
 for name,threads,results in [('Swift 1.0',1,['1-0','1/2-1/2']*3),('Swift 2.0',1,['1-0','0-1','1/2-1/2']*2),('Swift 2.0',32,['1/2-1/2']*6),('Other 1.0',1,['1/2-1/2']*6)]:
  tid=tournament(s,profiles=[profile(name,threads),profile('Anchor 1.0')]);finish(s,tid,results);s.set_state(tid,'paused')


def test_best_view_preserves_fit_anchor_ledger_ci_sort_search_exports(tmp_path):
 with closing(Store(tmp_path)) as s:
  seed(s);baseline=read(s);old=next(r for r in baseline['items'] if r['name'].startswith('Swift 1.0'))
  s.rating_center_call('command',{'action':'anchor','category':'blitz','entry':old['id'],'rating':3000})
  baseline=read(s);before=s.rows('SELECT * FROM rc_games ORDER BY gid');best=read(s,versions='best')
  assert best['total']==4 and best['anchor']['entry']==old['id']
  expected=max((r for r in baseline['items'] if r['family']=='Swift' and r['threads']==1),key=lambda r:r['rating'])
  winner=next(r for r in best['items'] if r['family']=='Swift' and r['threads']==1);assert winner['id']==expected['id']
  byid={r['id']:r for r in baseline['items']}
  for r in best['items']:
   for field in ('rating','ci','los','games','samples','wins','draws','losses'):assert r[field]==byid[r['id']][field]
  ranks={r['id']:r['rank'] for r in best['items']}
  assert read(s,versions='best',q=winner['id'])['items'][0]['rank']==winner['rank']
  assert {r['id']:r['rank'] for r in read(s,versions='best',sort='name')['items']}==ranks
  assert read(s,versions='best',offset=1)['items']==best['items'][1:]
  exported=list(csv.DictReader(io.StringIO(read(s,versions='best',export='csv'))));assert len(exported)==4 and all(r['Version view']=='best' for r in exported)
  assert 'Best version per family' in read(s,versions='best',export='txt')
  assert s.rows('SELECT * FROM rc_games ORDER BY gid')==before
  with pytest.raises(ValueError,match='time category'):read(s,versions='best',category='all')


def test_family_override_persists_without_changing_ratings_and_reset_cleans(tmp_path):
 s=Store(tmp_path)
 try:
  seed(s);old=next(r for r in read(s)['items'] if r['name'].startswith('Other'))
  before=read(s,versions='best');s.rating_center_call('command',{'action':'family','entry':old['id'],'family':'Swift'})
  assert read(s,versions='best')['total']==3
  s.close();s=Store(tmp_path);assert next(r for r in read(s)['items'] if r['id']==old['id'])['family_override']=='Swift'
  s.rating_center_call('command',{'action':'family','entry':old['id'],'family':''});assert read(s,versions='best')['items']==before['items']
  s.rating_center_call('command',{'action':'family','entry':old['id'],'family':'Swift'})
  s.backup();s.rating_center_call('command',{'action':'reset','category':'all','confirmed':True});assert not s.one('SELECT 1 FROM rc_families')
 finally:s.close()
