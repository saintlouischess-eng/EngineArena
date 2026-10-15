"""1.8.2 delivered UI checks; never opens the production data folder."""
from contextlib import closing
import hashlib,json,os,sqlite3,subprocess,time
from pathlib import Path
from rc_acceptance import Candidate,ROOT
from arena import __version__

def main():
    previous=json.loads((ROOT/'test-output/workflow-ready.json').read_text())
    source=Path(previous['folder']).resolve()
    assert source.is_relative_to(ROOT/'test-output') and source.name.startswith('workflow-')
    folder=ROOT/'test-output'/('workflow-polish-'+str(time.time_ns()));folder.mkdir()
    with closing(sqlite3.connect((source/'arena.sqlite3').as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(folder/'arena.sqlite3')) as dst:
        src.backup(dst)
        row=dst.execute("SELECT body FROM preferences WHERE name='ui'").fetchone();prefs=json.loads(row[0]) if row else {}
        prefs.update(focus3d=False,player3d=False,scene3d={'environment':'club','live':False})
        dst.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('ui',json.dumps(prefs)));dst.commit()
    c=Candidate(ROOT/'release/EngineArena/EngineArena.exe',folder)
    proof={'passed':False,'version':__version__,'scope':'Disposable native app and software WebGL; no production access','checks':{}}
    with closing(c.db()) as db:before=[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
    try:
        c.launch();assert c.api('status')['active_games']==0
        ready=previous|{'folder':str(folder),'url':f"http://127.0.0.1:{c.info['port']}/?token={c.info['token']}"}
        ready_path=ROOT/'test-output/polish-package-ready.json';ready_path.write_text(json.dumps(ready))
        suites=[('validate_club_motion.cjs','ARENA_SCENE_READY','ARENA_MOTION_OUT','polish-motion-packaged'),('validate_club.cjs','ARENA_SCENE_READY','ARENA_CLUB_OUT','polish-club-packaged'),('validate_camera_polish.cjs','ARENA_POLISH_READY','ARENA_POLISH_OUT','polish-camera-packaged'),('validate_graphics_recovery.cjs','ARENA_GRAPHICS_READY','ARENA_GRAPHICS_OUT','polish-recovery-packaged')]
        for script,ready_key,out_key,out in suites:
            result=subprocess.run(['node','scripts/'+script],cwd=ROOT,env=os.environ|{ready_key:str(ready_path),out_key:'test-output/'+out},creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True,text=True,encoding='utf-8',timeout=420)
            print(result.stdout,flush=True);print(result.stderr,flush=True);assert result.returncode==0,script
            proof['checks'][script]=json.loads((ROOT/'test-output'/out/'result.json').read_text());assert proof['checks'][script]['passed']
        with closing(c.db()) as db:
            assert before==[tuple(r) for r in db.execute('SELECT id,official,opening FROM games WHERE official IS NOT NULL ORDER BY id')]
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.api('status')['error']
        proof.update(passed=True,timings=c.timings,committed_results_preserved=len(before))
        with (ROOT/'release/EngineArena/worker/ArenaWorker.exe').open('rb') as f:proof['worker_sha256']=hashlib.file_digest(f,'sha256').hexdigest()
    finally:
        c.stop();(ROOT/'test-output/v182-package.json').write_text(json.dumps(proof,indent=2))
    print('Packaged club, camera and recovery passed; disposable app closed.',flush=True)

if __name__=='__main__':main()
