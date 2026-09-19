"""Seven-piece fifty-move margins and missing-file behavior with real engines."""
import asyncio
import io
import json
from pathlib import Path
import sys
import chess
import chess.pgn
import chess.syzygy
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from arena.referee import syzygy_decision
from arena.runner import Database,Runner

FEN='8/3k4/1p6/2p5/2P5/1P1K4/4P3/8 b - - 0 1'
TABLES='D:/New Tablebase'


async def main():
    report={'tablebase_directory':TABLES,'probes':[],'games':[]};board=chess.Board(FEN)
    with chess.syzygy.open_tablebase(TABLES) as tb:
        for counter in (0,97,98,99):
            board.halfmove_clock=counter;decision=syzygy_decision(tb,board)
            assert (decision['result']=='1-0')==(counter<98)
            report['probes'].append({'halfmove_clock':counter,'wdl':tb.probe_wdl(board),'dtz':tb.probe_dtz(board),'decision':decision})
    with chess.syzygy.open_tablebase(TABLES,load_dtz=False) as tb:
        board.halfmove_clock=0;assert syzygy_decision(tb,board)['result']=='1-0'
        board.halfmove_clock=97;decision=syzygy_decision(tb,board);assert decision['result'] is None and 'unavailable' in decision['note']
        report['wdl_only_collection']={'zero_counter_decisive':True,'nonzero_counter_deferred':True}
    empty=ROOT/'test-output/missing-tablebase';empty.mkdir(exist_ok=True)
    profiles=json.loads((ROOT/'test-output/real-validation/report.json').read_text())['engines']
    db=await Database().open(ROOT/'test-output/tablebase-edge-validation');runner=Runner(db);await runner.start()
    try:
        for counter,path in [(0,TABLES),(97,TABLES),(98,TABLES),(99,TABLES),(100,TABLES),(0,str(empty))]:
            board=chess.Board(FEN);board.halfmove_clock=counter
            t=await db.call('create_tournament',f'Syzygy edge {counter}',profiles,{'cycles':1,'paired':False,'concurrency':1,'time_control':{'kind':'nodes','nodes':2000},'syzygy_path':path,'max_plies':4},[{'fen':board.fen(),'name':'Seven-piece fifty-move edge'}]);await db.call('set_state',t['id'],'running')
            for _ in range(600):
                snapshot=await db.call('snapshot',t['id'])
                if snapshot['state']=='completed':break
                assert not runner.error,runner.error;await asyncio.sleep(.1)
            assert snapshot['official_games']==1
            game=(await db.call('games',t['id']))['items'][0];detail=await db.call('game_detail',game['id']);attempt=detail['attempts'][0];moves=len(attempt['moves'])
            if path==str(empty):assert moves==4 and game['reason']=='max_plies_adjudication' and any('file unavailable' in r['line'] for r in attempt['logs'])
            elif counter<98:assert moves==0 and game['result']=='1-0' and game['reason'].startswith('syzygy_')
            elif counter<100:assert moves>0 and any('fifty-move boundary' in r['line'] for r in attempt['logs'])
            else:assert moves==0 and game['reason']=='fifty_moves' and game['result']=='1/2-1/2'
            pgn=chess.pgn.read_game(io.StringIO(await db.call('export_official',t['id'])));assert not pgn.errors
            report['games'].append({'id':game['id'],'counter':counter,'missing_collection':path==str(empty),'result':game['result'],'reason':game['reason'],'moves':moves,'legal_pgn':True})
    finally:await runner.close()
    (ROOT/'test-output/tablebase-edge-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
