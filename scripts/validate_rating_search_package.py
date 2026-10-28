"""Exercise multi-engine search and counter preferences in a disposable workspace, never production."""
from contextlib import closing
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from arena.store import Store
from test_rating_search import seed

args=argparse.ArgumentParser();args.add_argument('--packaged',action='store_true');args=args.parse_args()
out=ROOT/'test-output/rating-search-1106';out.mkdir(exist_ok=True)
mode='packaged' if args.packaged else 'source'
folder=out/(mode+'-'+time.strftime('%Y%m%d-%H%M%S'));folder.mkdir()
with closing(Store(folder)) as s:
    seed(s)
    tid=s.one('SELECT id FROM tournaments')['id']
    gid=s.one('SELECT id FROM games ORDER BY number LIMIT 1')['id']
ready=folder/'ready.json';log=(folder/'worker.log').open('w')
command=[str(ROOT/'release/EngineArena/worker/ArenaWorker.exe')] if args.packaged else [sys.executable,str(ROOT/'worker.py')]
p=subprocess.Popen(command+['--data',str(folder),'--ready',str(ready)],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
try:
    for _ in range(600):
        if ready.exists():break
        assert p.poll() is None,'Fixture worker exited'
        time.sleep(.1)
    r=json.loads(ready.read_text());(out/'ready.json').write_text(json.dumps(dict(url=f"http://127.0.0.1:{r['port']}/?token={r['token']}",tid=tid,gid=gid,mode=mode)))
    checked=subprocess.run(['node',str(ROOT/'scripts/validate_rating_search_ui.cjs')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
    print(checked.stdout);print(checked.stderr);assert checked.returncode==0
finally:
    if ready.exists():
        r=json.loads(ready.read_text());req=urllib.request.Request(f"http://127.0.0.1:{r['port']}/api/shutdown",data=b'{}',headers={'X-Arena-Token':r['token'],'Content-Type':'application/json'})
        urllib.request.urlopen(req,timeout=20).close()
    p.wait(45);log.close()
