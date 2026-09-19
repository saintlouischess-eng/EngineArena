"""Real-engine ponder hit/miss and tournament integration evidence."""
import asyncio
import io
import json
from pathlib import Path
import sys
import time
import chess
import chess.pgn
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from arena.store import DEFAULTS
from arena.uci import UciEngine
from arena.runner import Database,Runner


async def main():
    profiles=json.loads((ROOT/'test-output/real-validation/report.json').read_text())['engines'];report={'engines':[]}
    for profile in profiles:
        engine=UciEngine(profile,DEFAULTS|{'ponder':True,'hang_timeout':30})
        try:
            await engine.start();board=chess.Board();move,_,_=await engine.play(board,'go nodes 20000',None);board.push(move)
            predicted=engine.ponder_candidate;assert predicted,'Expected a ponder suggestion from real engine'
            await engine.begin_ponder(board,'go nodes 20000');board.push_uci(predicted);move,elapsed,info=await engine.play(board,'go nodes 20000',None);assert move in board.legal_moves;board.push(move)
            predicted=engine.ponder_candidate;assert predicted
            await engine.begin_ponder(board,'go nodes 20000');alternative=next(m for m in board.legal_moves if m.uci()!=predicted);board.push(alternative)
            move,_,_=await engine.play(board,'go nodes 20000',None);assert move in board.legal_moves
            commands=[line for line in engine.log if line.startswith('> ')]
            assert '> ponderhit' in commands and '> stop' in commands and '> go ponder nodes 20000' in commands
            assert all('wtime' not in c and 'btime' not in c and 'movetime' not in c for c in commands if c.startswith('> go'))
            report['engines'].append({'name':engine.identity.get('name',profile['name']),'ponder_hit':True,'ponder_miss_stop':True,'legal_responses':True,'pure_nodes':True,'hit_elapsed_seconds':elapsed,'commands':commands})
        finally:await engine.close()
    db=await Database().open(ROOT/'test-output/ponder-validation');runner=Runner(db);await runner.start()
    try:
        t=await db.call('create_tournament','Real-engine pondering integration',profiles,{'cycles':4,'concurrency':2,'ponder':True,'time_control':{'kind':'nodes','nodes':20000},'max_plies':40,'cpu_budget':8})
        await db.call('set_state',t['id'],'running');started=time.monotonic()
        while time.monotonic()-started<120:
            snapshot=await db.call('snapshot',t['id'])
            if snapshot['state']=='completed':break
            assert not runner.error,runner.error;await asyncio.sleep(.1)
        assert snapshot['official_games']==8 and snapshot['complete_pairs']==4
        games=await db.call('games',t['id']);assert all(g['reason']=='max_plies_adjudication' for g in games['items'])
        stream=io.StringIO(await db.call('export_official',t['id']));ids=[]
        while game:=chess.pgn.read_game(stream):assert not game.errors;ids.append(game.headers['AttemptId'])
        assert len(ids)==len(set(ids))==8
        transcript=await db.call('rows','SELECT line FROM logs WHERE aid IN (SELECT a.id FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=?)',(t['id'],));lines=[r['line'] for r in transcript]
        hits=lines.count('> ponderhit');ponders=sum(line.startswith('> go ponder ') for line in lines)
        assert hits>0 and ponders>0
        details=[await db.call('game_detail',g['id']) for g in games['items']]
        report['tournament']={'id':t['id'],'games':8,'pairs':4,'moves':sum(len(g['attempts'][0]['moves']) for g in details),
          'retained_ponderhit_commands':hits,'retained_ponder_commands':ponders,'pgn_errors':0,'duplicate_attempts':0}
    finally:await runner.close()
    (ROOT/'test-output/ponder-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
