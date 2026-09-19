"""Isolated, completed fixture for native Save As acceptance; no engines launch."""
import json
import sys
from pathlib import Path
import chess

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from arena.store import Store

folder=ROOT/'test-output/pgn-save-ui-v2'
if (folder/'arena.sqlite3').exists():raise RuntimeError('Preserve the existing fixture')
store=Store(folder)
board=chess.Board();line=['e2e4','e7e5','g1f3','b8c6','f1b5','a7a6','b5a4','g8f6','e1g1','f8e7','f1e1','b7b5','a4b3','d7d6','c2c3']
for move in line:board.push_uci(move)
opening={'fen':board.fen(),'moves':line,'name':'Ruy Lopez fixture','eco':'C84','seed':900}
profiles=[store.save_profile({'name':name,'path':sys.executable,'threads':1,'hash':32}) for name in ['Fixture White','Fixture Black']]
t=store.create_tournament('PGN export validation',profiles,{'cycles':2},[opening]);tid=t['id']
store.set_state(tid,'running');store.fill_queue(tid,4)
while g:=store.claim(tid):
    b=chess.Board(opening['fen'])
    for ply in range(1,5):
        move=next(iter(b.legal_moves));san=b.san(move);b.push(move)
        store.move(g['aid'],ply,move.uci(),san,b.fen(),3.904174,{'white':{'remaining':175.096},'black':{'remaining':177.25}}, {'cp':57,'depth':33,'nodes':500000,'nps':128000})
    store.finish(g['aid'],'1/2-1/2','threefold_repetition')
store.execute("UPDATE tournaments SET state='completed' WHERE id=?",(tid,));store.export_pending();store.close()
(folder/'fixture.json').write_text(json.dumps({'tid':tid}),encoding='utf-8')
print(json.dumps({'data':str(folder),'tid':tid}))
