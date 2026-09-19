import io
import json
from pathlib import Path
import time
import urllib.request
import chess.pgn

root=Path(__file__).resolve().parent.parent
data=root/'test-output'/'portable-data'
ready=json.loads((data/'worker-ready.json').read_text())
base=f"http://127.0.0.1:{ready['port']}/api/"
def api(path,body=None):
    request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'X-Arena-Token':ready['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=60) as r:return json.load(r)
report=json.loads((root/'test-output'/'real-validation'/'report.json').read_text());profiles=[]
for p in report['engines']:profiles.append(api('profiles',p|{'discover':False}))
stamp=str(time.time_ns())
preset=api('presets',{'name':'Packaged nodes '+stamp,'settings':{'time_control':{'kind':'nodes','nodes':2000},'threads':1,'hash':32,'paired':True,'ponder':False}})
position=api('positions',{'name':'Packaged Chess960 '+stamp,'chess960_index':42})
t=api('tournaments',{'name':'Packaged worker validation','profiles':[p['id'] for p in profiles],'resource_preset':preset['settings'],'saved_position':position['name'],'settings':{'format':'match','cycles':2,'concurrency':2,'time_control':preset['settings']['time_control'],'max_plies':20}})
api(f"tournaments/{t['id']}/action",{'action':'start'})
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    snapshot=api('tournaments/'+t['id'])
    if snapshot['state']=='completed':break
    time.sleep(.1)
assert snapshot['state']=='completed';assert snapshot['official_games']==4
assert snapshot['settings']['chess960'] and snapshot['settings']['openings'][0]['fen']==position['fen']
opening_report=api(f"tournaments/{t['id']}/openings?slot=0")
assert opening_report['summary']['games']==4 and opening_report['openings'][0]['complete_pairs']==2
api(f"tournaments/{t['id']}/ratings",{'slot':1,'rating':3000})
pool=api(f"tournaments/{t['id']}/ratings")
assert pool['samples']==2 and pool['anchor']['rating']==3000 and len(pool['items'])==2
cross=api(f"tournaments/{t['id']}/crosstable")
assert len(cross['cells'])==2 and all(c['games']==4 for c in cross['cells'])
assert all('ci95_conservative' in row for row in snapshot['standings'])
series=api(f"tournaments/{t['id']}/series?slot=0")
html=api(f"tournaments/{t['id']}/report")['html']
assert '<h1>Packaged worker validation</h1>' in html and 'no chess clock' in html
resources=api('resource-preview',{'profiles':[p['id'] for p in profiles],'settings':{'ponder':False,'cpu_budget':32,'memory_budget_mb':100000}})
assert resources['recommended']==32
games=api('tournaments/'+t['id']+'/games')['items'];assert all(g['reason']=='max_plies_adjudication' for g in games)
ids=[];f=io.StringIO((data/'games.pgn').read_text(encoding='utf-8'))
while g:=chess.pgn.read_game(f):assert not g.errors;ids.append(g.headers['AttemptId'])
assert len(ids)==len(set(ids))
request=urllib.request.Request(base+f"export/{t['id']}/pgn",headers={'X-Arena-Token':ready['token']})
with urllib.request.urlopen(request,timeout=30) as response:
    assert response.headers.get('Transfer-Encoding')=='chunked'
    f=io.StringIO(response.read().decode('utf-8'));official_ids=[]
while game:=chess.pgn.read_game(f):
    assert not game.errors;official_ids.append(game.headers['AttemptId'])
assert len(official_ids)==4 and set(official_ids)=={g['official'] for g in games}
result={'packaged_worker':True,'saved_preset':True,'saved_chess960_position':True,'opening_report_games':4,'pool_rating_samples':pool['samples'],'pool_reference':pool['anchor'],'crosstable_cells':len(cross['cells']),'conservative_intervals':True,'completed_games':snapshot['official_games'],'complete_pairs':snapshot['complete_pairs'],'pgn_parse_errors':0,'pgn_duplicate_attempts':0,'tournament':t['id']}
result.update(tournament_report=True,chart_series=bool(series),resource_recommendation=resources['recommended'],streamed_official_pgn=True)
(root/'test-output'/'packaged-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
