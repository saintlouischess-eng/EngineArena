"""Real worker/UCI checks for saved adjudication windows and starting-position counts."""
import asyncio
from contextlib import closing
import json
import time
import chess
import pytest
from arena.runner import Database,Runner
from arena.store import Store
from test_core import profile,read_pgn


@pytest.mark.parametrize('settings,scores,plies,result,reason',[
 ({'resign_cp':500,'resign_plies':3},'500',3,'1-0','resign_adjudication'),
 ({'resign_cp':500,'resign_plies':4},'-500',4,'0-1','resign_adjudication'),
 ({'resign_cp':500,'resign_plies':3},'500,-500,500,500,500',5,'1-0','resign_adjudication'),
 ({'resign_cp':500,'resign_plies':3},'500,none,500,500,500',5,'1-0','resign_adjudication'),
 ({'resign_cp':500,'resign_plies':3},'500,499,500,500,500',5,'1-0','resign_adjudication'),
 ({'draw_cp':20,'draw_plies':3,'draw_after':0},'20,-20,0',3,'1/2-1/2','draw_adjudication'),
 ({'draw_cp':20,'draw_plies':3,'draw_after':0},'0,0,21,0,0,0',6,'1/2-1/2','draw_adjudication'),
 ({'draw_cp':20,'draw_plies':3,'draw_after':0},'0,none,0,0,0',5,'1/2-1/2','draw_adjudication'),
 ({'draw_cp':20,'draw_plies':2,'draw_after':5},'0',5,'1/2-1/2','draw_adjudication'),
 ({'draw_cp':20,'draw_plies':5,'draw_after':0},'0',5,'1/2-1/2','draw_adjudication'),
 ({'resign_cp':0,'resign_plies':1,'draw_cp':0,'draw_plies':1,'draw_after':0,'max_plies':6},'0',6,'1/2-1/2','max_plies_adjudication'),
 ({'resign_cp':0,'resign_plies':1,'draw_cp':0,'draw_plies':1,'draw_after':0,'max_plies':6},'900',6,'1/2-1/2','max_plies_adjudication'),
])
def test_uci_adjudication_at_exact_saved_boundary(tmp_path,settings,scores,plies,result,reason):
 async def run():
  db=await Database().open(tmp_path);runner=Runner(db)
  try:
   board=chess.Board();opening_moves=['e2e4','e7e5','g1f3','b8c6']
   for move in opening_moves:board.push_uci(move)
   engines=[profile(name,extra=['--white-scores',scores]) for name in ['Score A','Score B']]
   t=await db.call('create_tournament','Adjudication boundary',engines,{'cycles':1,'paired':False,'concurrency':1,
    'time_control':{'kind':'nodes','nodes':100},'claim_draws':False,'max_plies':10,**settings},
    [{'fen':board.fen(),'moves':opening_moves}],backup=False)
   await db.call('set_state',t['id'],'running');await runner.start();deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    snap=await db.call('snapshot',t['id']);assert not runner.error,runner.error
    if snap['state']=='completed':break
    await asyncio.sleep(.02)
   assert snap['state']=='completed' and snap['official_games']==1
   a=(await db.call('rows','SELECT * FROM attempts'))[0]
   assert (a['result'],a['reason'])==(result,reason)
   moves=await db.call('rows','SELECT * FROM moves WHERE aid=? ORDER BY ply',(a['id'],))
   assert len(moves)==plies  # imported opening history must not advance this counter
   expected=scores.split(',')
   for i,m in enumerate(moves):
    cp=json.loads(m['info']).get('cp');source=expected[min(i,len(expected)-1)]
    assert cp==(None if source=='none' else int(source))
   await db.call('export_pending');games=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'))
   assert len(games)==1 and games[0].headers['Result']==result
   assert games[0].headers['Termination']=='adjudication'
   assert len(list(games[0].mainline_moves()))==len(opening_moves)+plies
  finally:await runner.close()
 asyncio.run(run())


def test_counts_persist_across_edit_restart_and_report(tmp_path):
 with closing(Store(tmp_path)) as store:
  t=store.create_tournament('Editable',[profile('A'),profile('B')],{},backup=False)
  assert [t['settings'][k] for k in ['resign_plies','draw_plies','draw_after']]==[6,12,80]
  store.edit_tournament(t['id'],'Custom adjudication',{'resign_cp':650,'resign_plies':9,'draw_cp':15,'draw_plies':17,'draw_after':101},0,backup=False)
 with closing(Store(tmp_path)) as store:
  s=store.tournament_setup(t['id'])['settings']
  assert [s[k] for k in ['resign_plies','draw_plies','draw_after']]==[9,17,101]
  from arena.tournament_report import render
  report=render(store.path,t['id'],technical=False)
  assert '650 cp for 9 plies' in report
  assert 'Within 15 cp for 17 plies, after 101 played plies from the starting position' in report


@pytest.mark.parametrize('key,bad',[
 ('resign_plies',0),('resign_plies',2.5),('resign_plies',True),
 ('draw_plies',-1),('draw_plies','12'),('draw_plies',False),
 ('draw_after',-1),('draw_after',.5),('draw_after',True),('draw_after',None),
 ('resign_cp',-1),('resign_cp',float('inf')),('resign_cp',True),
 ('draw_cp',float('nan')),('draw_cp','20'),('draw_cp',None),
])
def test_invalid_adjudication_edit_keeps_original(tmp_path,key,bad):
 with closing(Store(tmp_path)) as store:
  t=store.create_tournament('Keep setup',[profile('A'),profile('B')],{},backup=False)
  with pytest.raises(ValueError):store.edit_tournament(t['id'],'Bad settings',{key:bad},0,backup=False)
  assert store.tournament(t['id'])==t
