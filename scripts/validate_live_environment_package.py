"""Check packaged 3D scene using a disposable copy of a workflow fixture."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import sys
from rc_acceptance import Candidate,ROOT
from validate_knight_package import digest,read
from arena import __version__


class HiddenCandidate(Candidate):
    """Exercise the delivered worker/UI without leaving a native test window open."""
    def launch(self):
        self.log=(self.folder/'worker-validation.log').open('w',encoding='utf-8')
        self.process=subprocess.Popen([str(self.exe),'--data',str(self.folder),'--ready',str(self.ready)],cwd=ROOT/'test-output',creationflags=subprocess.CREATE_NO_WINDOW,stdout=self.log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise RuntimeError('Packaged worker exited during startup')
            if self.ready.exists():
                self.info=read(self.ready);assert not self.api('status')['error'];return
            time.sleep(.1)
        raise TimeoutError('Packaged worker did not become ready')
    def stop(self):
        try:super().stop()
        finally:
            if hasattr(self,'log'):self.log.close()


def main():
    previous=read(ROOT/'test-output/workflow-ready.json')
    source=Path(previous['folder']).resolve()
    assert source.is_relative_to(ROOT/'test-output') and source.name.startswith('workflow-')
    folder=ROOT/'test-output'/('workflow-life-'+str(time.time_ns()));folder.mkdir()
    with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:
        src.backup(dst)
    c=HiddenCandidate(ROOT/'release/EngineArena/worker/ArenaWorker.exe',folder)
    proof={'passed':False,'live_only':'--live-only' in sys.argv,'version':__version__,'folder':str(folder),'scope':'Delivered worker and UI in headless Edge on a disposable fixture copy. Disposable scenery and Player Arena games only. No production changes.'}
    try:
        c.launch();assert c.api('status')['active_games']==0
        ready=previous|{'folder':str(folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}
        ready_path=ROOT/'test-output/life-package-ready.json';ready_path.write_text(json.dumps(ready),encoding='utf-8')
        environment=os.environ|{'ARENA_SCENE_READY':str(ready_path),'ARENA_LIFE_OUT':'test-output/live-environment-packaged','ARENA_SCENE_OUT':'test-output/scenes-v171-packaged','ARENA_PLAYER_READY':str(ready_path),'ARENA_PLAYER_OUT':'test-output/player-v171-packaged'}
        results={}
        suites=[('validate_live_environment.cjs','live-environment-packaged'),('validate_board3d_scenes.cjs','scenes-v171-packaged'),('validate_player.cjs','player-v171-packaged')]
        if '--live-only' in sys.argv:suites=suites[:1]
        for script,out in suites:
            result=subprocess.run(['node','scripts/'+script],cwd=ROOT,env=environment,creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8',timeout=240)
            print(result.stdout,flush=True);print(result.stderr,flush=True)
            if result.returncode:raise RuntimeError('Packaged acceptance failed: '+script)
            results[script]=read(ROOT/'test-output'/out/'result.json');assert results[script]['passed']
        proof.update(passed=True,checks=results,worker_sha256=digest(ROOT/'release/EngineArena/worker/ArenaWorker.exe'))
    finally:
        c.stop();(ROOT/'test-output/life-package.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print('Packaged live environment passed; disposable app stopped.',flush=True)


if __name__=='__main__':main()
