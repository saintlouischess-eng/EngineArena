"""Validate the packaged renderer with software graphics and disposable worker data."""
from contextlib import closing
import hashlib,json,os,sqlite3,subprocess,time
from pathlib import Path
from rc_acceptance import Candidate,ROOT
from arena import __version__

def main():
    previous=json.loads((ROOT/'test-output/workflow-ready.json').read_text())
    source=Path(previous['folder']).resolve()
    assert source.is_relative_to(ROOT/'test-output') and source.name.startswith('workflow-')
    folder=ROOT/'test-output'/('workflow-graphics-'+str(time.time_ns()));folder.mkdir()
    with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:src.backup(dst)
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    proof={'passed':False,'version':__version__,'scope':'Disposable workspace; software WebGL context loss, no system GPU reset.'}
    with closing(c.db()) as db:before=[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
    try:
        c.launch();assert c.api('status')['active_games']==0
        ready=previous|{'folder':str(folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}
        ready_path=ROOT/'test-output/graphics-package-ready.json';ready_path.write_text(json.dumps(ready))
        result=subprocess.run(['node','scripts/validate_graphics_recovery.cjs'],cwd=ROOT,env=os.environ|{'ARENA_GRAPHICS_READY':str(ready_path),'ARENA_GRAPHICS_OUT':'test-output/graphics-packaged'},creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8',timeout=240)
        print(result.stdout,flush=True);print(result.stderr,flush=True);assert result.returncode==0
        with closing(c.db()) as db:
            assert before==[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.api('status')['error']
        proof.update(passed=True,startup_seconds=c.timings,display=json.loads((ROOT/'test-output/graphics-packaged/result.json').read_text()),committed_results_preserved=len(before))
        with (ROOT/'release/EngineArena/worker/ArenaWorker.exe').open('rb') as f:proof['worker_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
    finally:
        c.stop();(ROOT/'test-output/v181-package.json').write_text(json.dumps(proof,indent=2))
    print('Packaged graphics recovery passed; disposable app closed.',flush=True)

if __name__=='__main__':main()
