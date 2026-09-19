"""An isolated UI fixture; never reads or modifies the user's default data."""
from pathlib import Path
import sys
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from arena.store import Store

folder=ROOT/'test-output'/'polish'
if (folder/'arena.sqlite3').exists():raise SystemExit('Fixture already exists; preserving it')
s=Store(folder)
try:
    profiles=[]
    for name in ('Reference engine','Candidate engine'):
        profiles.append(s.save_profile({'name':name,'path':sys.executable,'args':[str(ROOT/'tests'/'fault_engine.py'),'--wait','1.2'],'hash':16,'threads':1}))
    t=s.create_tournament('Workspace polish validation',profiles,{'cycles':40,'concurrency':2,'max_plies':80,'time_control':{'kind':'nodes','nodes':25000}})
    prefs={'fontSize':16,'pieceSet':'classic','theme':'dark','split':55,'panels':{'focus':{'visible':True,'column':'right','order':0,'height':750},'live':{'column':'right','order':1},'standings':{'column':'left','order':0},'games':{'column':'left','order':1}}}
    with s.tx():s.db.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('ui',json.dumps(prefs)))
    print(json.dumps({'data':str(folder),'tournament':t['id']}))
finally:s.close()
