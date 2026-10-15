"""Native Player Arena recovery, legal PGNs and mouse workflow on disposable data."""
from contextlib import closing
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import sys
import chess.pgn
from rc_acceptance import Candidate,ROOT
from validate_knight_package import digest,read
from arena import __version__


def main():
    previous=read(ROOT/'test-output/workflow-ready.json');source=Path(previous['folder']).resolve()
    assert source.is_relative_to(ROOT/'test-output') and source.name.startswith('workflow-')
    folder=ROOT/'test-output'/('workflow-player-'+str(time.time_ns()));folder.mkdir()
    with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:src.backup(dst)
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    proof={'passed':False,'version':__version__,'folder':str(folder),'scope':'Disposable native application only; no production changes.'}
    def game():return c.api('player/state')['game']
    def action(verb,**kwargs):
        g=game();return c.api('player/action',{'id':g['id'],'revision':g['revision'],'action':verb,**kwargs})['game']
    def wait(predicate):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            g=game()
            if predicate(g):return g
            time.sleep(.1)
        raise AssertionError(g)
    try:
        c.launch();assert c.api('status')['active_games']==0
        with c.db() as db:testing_before=db.execute('SELECT count(*) FROM games').fetchone()[0]
        ready=previous|{'folder':str(folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}
        ready_path=ROOT/'test-output/player-package-ready.json';ready_path.write_text(json.dumps(ready),encoding='utf-8')
        env=os.environ|{'ARENA_PLAYER_READY':str(ready_path),'ARENA_PLAYER_OUT':'test-output/player-packaged'}
        result=subprocess.run(['node','scripts/validate_player.cjs'],cwd=ROOT,env=env,creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8')
        print(result.stdout,flush=True);print(result.stderr,flush=True)
        assert result.returncode==0,'Packaged player UI failed'
        proof['ui']=read(ROOT/'test-output/player-packaged/result.json')
        if '--workspace' in sys.argv:
            env=env|{'ARENA_WORKSPACE_OUT':'test-output/player-workspace-packaged','ARENA_PLAYER_LANGUAGES':'1'}
            result=subprocess.run(['node','scripts/validate_player_workspace.cjs'],cwd=ROOT,env=env,creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8',timeout=240)
            print(result.stdout,flush=True);print(result.stderr,flush=True)
            assert result.returncode==0,'Packaged player workspace failed'
            proof['workspace']=read(ROOT/'test-output/player-workspace-packaged/result.json')
        current=game()
        if current and current['state'] in ('playing','starting','paused'):action('abandon')
        # Use a real engine for a committed move sequence and forced native-process loss.
        profile=c.api('profiles',{'name':'Stockfish player recovery validation','path':str(ROOT/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),'threads':1,'hash':16,'discover':True})
        book=next((b for b in c.api('move-books') if b['name']=='player-review.pgn'),None)
        book_config={'book_mode':'custom','move_book':book|{'max_plies':4,'policy':'best'}} if book else {}
        c.api('player/create',{'name':'Recovery player','engine':profile['id'],'config':{'hash':16,'rated':True,**book_config,'human_control':{'kind':'fischer','seconds':60,'increment':1},'engine_control':{'kind':'fischer','seconds':60,'increment':1}}})
        action('resume');wait(lambda g:g['state']=='playing')
        for i in range(2):
            g=game();move='e2e4' if i==0 else 'g1f3' if book else g['legal'][0]['uci'];action('move',move=move);wait(lambda g:len(g['moves'])==(i+1)*2)
        before=game();assert before['rated'] and before['result']=='*'
        if book:assert all(before['moves'][i]['info']['source']=='book' for i in (1,3))
        # Allow one active-clock checkpoint, then kill the native app's entire job tree.
        time.sleep(5.3)
        with c.db() as db:committed=json.loads(db.execute('SELECT body FROM player_games WHERE id=?',(before['id'],)).fetchone()[0])
        c.kill();c.launch();after=game()
        assert after['id']==before['id'] and after['state']=='paused' and after['result']=='*' and not after['rated']
        for key in ('fen','moves','clocks','turn_elapsed'):assert after[key]==committed[key],key
        assert any(e['action']=='recovered' for e in after['sessions'])
        action('resume');wait(lambda g:g['state']=='playing');action('move',move=game()['legal'][0]['uci']);wait(lambda g:len(g['moves'])==6);action('resign')
        proof['recovery']={'committed_plies':4,'continued_plies':6,'result':'0-1','reason':'resignation','no_forced_recovery_result':True}
        proof['pgn']={}
        for preset in ('clean','annotated','testing','archive'):
            raw=c.api('player/pgn?id='+before['id']+'&preset='+preset,raw=True);stream=io.StringIO(raw.decode())
            pgn=chess.pgn.read_game(stream);assert pgn and not pgn.errors and not chess.pgn.read_game(stream)
            assert pgn.headers['Result']=='0-1' and len(list(pgn.mainline_moves()))==6
            assert pgn.headers['Rated']=='No' and pgn.headers['WhiteType']=='human'
            if book and preset=='archive':assert pgn.headers['BlackBook']=='player-review.pgn'
            board=pgn.board()
            for move in pgn.mainline_moves():assert move in board.legal_moves;board.push(move)
            proof['pgn'][preset]={'plies':6,'bytes':len(raw),'legal':True}
        # A new rated result remains exactly once across a clean restart.
        c.api('player/create',{'name':'Rated validation','engine':profile['id'],'config':{'hash':16,'rated':True}})
        action('resign');rating=c.api('player/overview')['ratings'];c.stop();c.launch()
        assert c.api('player/overview')['ratings']==rating
        with c.db() as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert db.execute('SELECT count(*) FROM games').fetchone()[0]==testing_before
            assert db.execute('SELECT count(*) FROM player_exports').fetchone()[0]==0
            assert db.execute('SELECT count(*) FROM player_rating_games WHERE name=?',('Rated validation',)).fetchone()[0]==1
        proof.update(passed=True,ratings_exactly_once=True,worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'),startup_seconds=c.timings)
    finally:
        c.stop();(ROOT/'test-output/player-package.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print('Player Arena package and forced recovery passed. Disposable app stopped.',flush=True)


if __name__=='__main__':main()
