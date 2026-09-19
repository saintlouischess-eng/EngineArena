import json
from pathlib import Path
import urllib.request

root=Path(__file__).resolve().parent.parent
ready=json.loads((root/'test-output'/'desktop-data'/'worker-ready.json').read_text())
base=f"http://127.0.0.1:{ready['port']}/api/"
def api(path,body=None):
    request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'X-Arena-Token':ready['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=60) as r:return json.load(r)
report=json.loads((root/'test-output'/'real-validation'/'report.json').read_text())
profiles=[]
for p in report['engines']:
    p['discover']=False;profiles.append(api('profiles',p))
t=api('tournaments',{'name':'Stockfish 19 vs Berserk 14 · GUI validation','profiles':[p['id'] for p in profiles],'settings':{'format':'match','cycles':16,'concurrency':4,'time_control':{'kind':'nodes','nodes':1000000},'max_plies':80}})
api(f"tournaments/{t['id']}/action",{'action':'start'})
print(json.dumps({'tournament':t['id'],'total':t['total'],'profiles':[p['name'] for p in profiles]}))
