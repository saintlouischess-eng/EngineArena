"""Create an isolated real-engine workspace for focus/search layout checks."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from arena.store import Store
folder=ROOT/'test-output'/'focus-search'
if (folder/'arena.sqlite3').exists():raise SystemExit('Preserving the existing fixture')
s=Store(folder)
try:
    profiles=[]
    for original in json.loads((ROOT/'test-output'/'real-validation'/'report.json').read_text())['engines']:
        p={**original,'threads':1,'hash':32}
        p.pop('id',None);p.pop('time_control',None)
        for key in p.get('options',{}):
            if key.lower()=='threads':p['options'][key]=1
            if key.lower()=='hash':p['options'][key]=32
        profiles.append(s.save_profile(p))
    t=s.create_tournament('Resizable focus and search',profiles,{'cycles':10,'concurrency':2,'max_plies':30,'time_control':{'kind':'movetime','seconds':2}})
    prefs={'theme':'dark','fontSize':16,'pieceSet':'modern','split':52,'panels':{'focus':{'visible':True,'column':'right','order':0,'height':680},'search':{'visible':True,'column':'left','order':0,'height':600},'standings':{'column':'left','order':1},'games':{'column':'left','order':2},'live':{'column':'right','order':1}}}
    with s.tx():s.db.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('ui',json.dumps(prefs)))
    print(json.dumps({'data':str(folder),'tournament':t['id']}))
finally:s.close()
