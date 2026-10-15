"""Check packaged 3D boxwood finish using a disposable copy of a workflow fixture."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from rc_acceptance import Candidate,ROOT
from validate_knight_package import digest,read
from arena import __version__


def main():
    previous=read(ROOT/'test-output/workflow-ready.json')
    source=Path(previous['folder']).resolve()
    assert source.is_relative_to(ROOT/'test-output') and source.name.startswith('workflow-')
    folder=ROOT/'test-output'/('workflow-boxwood-'+str(time.time_ns()));folder.mkdir()
    with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:
        src.backup(dst)
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    proof={'passed':False,'version':__version__,'folder':str(folder),'scope':'Packaged boxwood review on a disposable fixture copy. No engine games or production changes.'}
    try:
        c.launch();assert c.api('status')['active_games']==0
        ready=previous|{'folder':str(folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}
        ready_path=ROOT/'test-output/boxwood-package-ready.json';ready_path.write_text(json.dumps(ready),encoding='utf-8')
        environment=os.environ|{'ARENA_BOXWOOD_READY':str(ready_path),'ARENA_BOXWOOD_OUT':'test-output/boxwood-packaged'}
        result=subprocess.run(['node','scripts/validate_boxwood.cjs'],cwd=ROOT,env=environment,creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8')
        print(result.stdout,flush=True);print(result.stderr,flush=True)
        if result.returncode:raise RuntimeError('Packaged boxwood acceptance failed')
        display=read(ROOT/'test-output/boxwood-packaged/result.json')
        assert display['passed'] and len(display['views'])==12
        proof.update(passed=True,display=display,worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'))
    finally:
        c.stop();(ROOT/'test-output/boxwood-package.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print('Packaged boxwood passed; disposable app stopped.',flush=True)


if __name__=='__main__':main()
