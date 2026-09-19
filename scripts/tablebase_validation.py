"""Read-only validation against the user's existing seven-piece Syzygy files."""
import asyncio
import io
import json
from pathlib import Path
import sys
import chess
import chess.pgn
import chess.syzygy
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from arena.runner import Database,Runner

ROOT=Path(__file__).resolve().parent.parent
TABLES=Path('D:/New Tablebase')
FENS=['8/3k4/1p6/2p5/2P5/1P1K4/4P3/8 w - - 0 1',
      '8/3k4/1p6/2p5/2P5/1P1K4/4P3/8 b - - 0 1',
      '7k/8/7p/8/8/8/PPP5/QK6 w - - 0 1']

async def main():
    report={'tablebase_directory':str(TABLES),'probes':[]}
    with chess.syzygy.open_tablebase(TABLES) as tb:
        for fen in FENS:
            board=chess.Board(fen);assert board.is_valid() and len(board.piece_map())==7
            try:wdl=tb.probe_wdl(board);dtz=tb.probe_dtz(board)
            except KeyError as e:report['probes'].append({'fen':fen,'missing':str(e)});continue
            report['probes'].append({'fen':fen,'wdl':wdl,'dtz':dtz})
    db=await Database().open(ROOT/'test-output'/'tablebase-validation');runner=Runner(db);await runner.start()
    profiles=json.loads((ROOT/'test-output'/'real-validation'/'report.json').read_text())['engines']
    try:
        for probe in report['probes']:
            if 'wdl' not in probe:continue
            t=await db.call('create_tournament','Seven-piece referee validation',profiles,{'cycles':1,'paired':False,'concurrency':1,'time_control':{'kind':'nodes','nodes':1000},'syzygy_path':str(TABLES),'max_plies':4},[{'fen':probe['fen'],'name':'Seven-piece acceptance'}])
            await db.call('set_state',t['id'],'running')
            for _ in range(600):
                snap=await db.call('snapshot',t['id'])
                if snap['state']=='completed':break
                if runner.error:raise AssertionError(runner.error)
                await asyncio.sleep(.1)
            assert snap['official_games']==1
            games=await db.call('games',t['id']);game=games['items'][0];probe['result']=game['result'];probe['reason']=game['reason']
            expected='1/2-1/2' if abs(probe['wdl'])<2 else '1-0' if (probe['wdl']>0)==chess.Board(probe['fen']).turn else '0-1'
            assert game['result']==expected and game['reason'].startswith('syzygy_')
            detail=await db.call('game_detail',game['id']);assert not detail['attempts'][0]['moves']
            pgn=chess.pgn.read_game(io.StringIO(await db.call('export_official',t['id'])));assert not pgn.errors and pgn.headers['Result']==expected
    finally:await runner.close()
    (ROOT/'test-output'/'tablebase-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

asyncio.run(main())
