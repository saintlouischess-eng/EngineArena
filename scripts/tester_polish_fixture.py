"""Small isolated UI review fixture with legal move records and varied results."""
from pathlib import Path
import sys
import chess

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from arena.store import Store

folder=ROOT/'test-output/tester-polish-ui'
store=Store(folder)
try:
    if store.one('SELECT id FROM tournaments LIMIT 1'):
        raise SystemExit('Fixture already populated; no existing records changed.')
    names=['Stockfish · one thread','Berserk · reference','Candidate A · experimental evaluation','Candidate B · long engine profile name for readability']
    paths=[ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe',ROOT/'validation-engines/berserk-14-avx2.exe']
    profiles=[{'name':name,'identity':{'name':name},'path':str(paths[i%2]),'threads':1,'hash':16,'options':{'Threads':1,'Hash':16}} for i,name in enumerate(names)]
    for profile in profiles:store.save_profile(profile)
    t=store.create_tournament('Preview review · paired engine comparison',profiles,{'format':'round_robin','cycles':5,'concurrency':4,'time_control':{'kind':'nodes','nodes':5000}})
    tid=t['id'];store.set_state(tid,'running');store.fill_queue(tid,120)
    for i in range(60):
        game=store.claim(tid)
        if not game:break
        board=chess.Board()
        for ply,move in enumerate('e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6'.split(),1):
            san=board.san(chess.Move.from_uci(move));board.push_uci(move)
            store.move(game['aid'],ply,move,san,board.fen(),.075,{'white':{'remaining':None},'black':{'remaining':None}}, {'depth':14,'nodes':5000,'score':{'kind':'cp','value':25 if ply%2 else -25}})
        store.finish(game['aid'],['1-0','1/2-1/2','0-1','1/2-1/2','1-0'][i%5],'test_fixture')
    store.set_state(tid,'paused');store.export_pending();store.backup()
    print(tid)
finally:store.close()
