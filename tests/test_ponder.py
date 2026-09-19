import asyncio
from pathlib import Path
import sys
import chess
from arena.store import DEFAULTS
from arena.uci import UciEngine

def test_ponder_hit_and_miss_keep_pure_node_search(tmp_path):
    async def run():
        transcript=tmp_path/'wire.txt'
        profile={'path':sys.executable,'args':[str(Path(__file__).parent/'fault_engine.py'),'--mode','ponder','--transcript',str(transcript)],'hash':1}
        e=UciEngine(profile,DEFAULTS|{'ponder':True,'stop_timeout':.2})
        try:
            await e.start();b=chess.Board();move,_,_=await e.play(b,'go nodes 100',None);b.push(move)
            candidate=e.ponder_candidate;assert candidate
            await e.begin_ponder(b,'go nodes 100');b.push_uci(candidate);move,_,_=await e.play(b,'go nodes 100',None);assert move in b.legal_moves
            b.push(move);candidate=e.ponder_candidate;assert candidate
            await e.begin_ponder(b,'go nodes 100');alternative=next(m for m in b.legal_moves if m.uci()!=candidate);b.push(alternative)
            move,_,_=await e.play(b,'go nodes 100',None);assert move in b.legal_moves
            lines=transcript.read_text().splitlines();assert 'ponderhit' in lines;assert 'stop' in lines;assert 'go ponder nodes 100' in lines
            assert all('wtime' not in line and 'movetime' not in line for line in lines if line.startswith('go'))
        finally:await e.close()
    asyncio.run(run())
