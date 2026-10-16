"""Isolated fixture + actual worker API/UI; never read or write production."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from arena.rating_center_report import report
from test_rating_range import seed


def evidence(path):
    import sqlite3
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        data={t:db.execute('SELECT * FROM '+t+' ORDER BY 1,2').fetchall() for t in ('rc_games','rc_entries','rc_sources','rc_anchors')}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def main():
    packaged='--packaged' in sys.argv;kind='package' if packaged else 'source'
    folder=ROOT/'test-output'/('v1912-range-'+kind+'-'+time.strftime('%Y%m%d-%H%M%S'));folder.mkdir()
    with closing(Store(folder)) as s:_,ids=seed(s,55)
    path=folder/'arena.sqlite3';before=evidence(path)
    expected=report(path,{'opponent_range':250,'export':'json'})
    executable=[str(ROOT/'release/EngineArena/worker/ArenaWorker.exe')] if packaged else [sys.executable,str(ROOT/'worker.py')]
    ready=folder/'ready.json';log=(folder/'worker.log').open('w',encoding='utf-8')
    proof={'passed':False,'kind':kind,'folder':str(folder)}
    try:
        for restart in range(2):
            ready.unlink(missing_ok=True)
            p=subprocess.Popen(executable+['--data',str(folder),'--ready',str(ready)],cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                deadline=time.monotonic()+90
                while not ready.exists():
                    assert p.poll() is None,'Worker stopped during startup'
                    if time.monotonic()>deadline:raise TimeoutError('Worker startup')
                    time.sleep(.1)
                info=json.loads(ready.read_text());url=f"http://127.0.0.1:{info['port']}"
                def api(route,raw=False):
                    req=urllib.request.Request(url+'/api/'+route,headers={'X-Arena-Token':info['token']})
                    with urllib.request.urlopen(req,timeout=90) as r:return r.read() if raw else json.load(r)
                got=api('rating-center?opponent_range=250&export=json')
                assert got['items']==expected['items'] and got['opponent_range']==expected['opponent_range']
                assert api('rating-center?opponent_range=250&export=csv',True).startswith(b'Rank,Engine,')
                assert b'+/-250 Elo' in api('rating-center?opponent_range=250&export=txt',True)
                if not restart:
                    ui_ready=folder/'ui-ready.json';ui_ready.write_text(json.dumps({'url':url+'/?token='+info['token'],'disconnected':ids['D']}))
                    subprocess.run(['node',str(ROOT/'scripts/validate_rating_range_ui.cjs'),str(ui_ready),str(folder/'ui')],check=True,cwd=ROOT)
                with urllib.request.urlopen(urllib.request.Request(url+'/api/shutdown',data=b'{}',headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'}),timeout=30):pass
                p.wait(45);assert p.returncode==0
            finally:
                if p.poll() is None:p.terminate();p.wait(20)
        assert evidence(path)==before
        proof.update(passed=True,restart=True,evidence_unchanged=True,configurations=expected['total'],counted_games=expected['counted_games'])
    finally:
        log.close();(folder/'validation.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof),flush=True)


if __name__=='__main__':main()
