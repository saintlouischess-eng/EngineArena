"""Real-engine smoke on the explicitly isolated polish workspace."""
import io
import json
from pathlib import Path
import time
import urllib.request
import chess.pgn

root=Path(__file__).resolve().parents[1]
data=root/'test-output'/'polish'
ready=json.loads((data/'worker-ready.json').read_text())
base=f"http://127.0.0.1:{ready['port']}/"
def api(path,body=None):
    request=urllib.request.Request(base+'api/'+path,data=json.dumps(body).encode() if body is not None else None,headers={'X-Arena-Token':ready['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=60) as response:return json.load(response)

assert api('status')['active_games']==0
sets=api('pieces')
assert len(sets)==6
for entry in sets:
    for side in 'wb':
        for piece in 'KQRBNP':
            path=f"pieces/{entry['id']}/{side}{piece}.svg"
            with urllib.request.urlopen(base+path,timeout=10) as response:
                assert response.read()==(root/'ui'/path).read_bytes()
profiles=[]
count=api('profiles')['total']
for p in json.loads((root/'test-output'/'real-validation'/'report.json').read_text())['engines']:
    p.pop('id',None)
    discovered=api('profiles/discover',p)
    assert api('profiles')['total']==count+len(profiles)
    profiles.append(api('profiles',discovered|{'discover':False}))
results=[]
for control in ({'kind':'nodes','nodes':25000},{'kind':'fischer','seconds':5,'increment':.05}):
    t=api('tournaments',{'name':'Packaged polish '+control['kind'],'profiles':[p['id'] for p in profiles],'settings':{'format':'match','cycles':1,'paired':True,'concurrency':2,'max_plies':12,'time_control':control}})
    api('tournaments/'+t['id']+'/action',{'action':'start'})
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        snapshot=api('tournaments/'+t['id'])
        if snapshot['state']=='completed':break
        time.sleep(.1)
    assert snapshot['official_games']==2 and snapshot['complete_pairs']==1
    games=api('tournaments/'+t['id']+'/games')['items']
    for game in games:
        attempt=api('games/'+game['id'])['attempts'][-1]
        assert len(attempt['moves'])==12 and attempt['reason']=='max_plies_adjudication'
    request=urllib.request.Request(base+'api/export/'+t['id']+'/pgn',headers={'X-Arena-Token':ready['token']})
    with urllib.request.urlopen(request,timeout=20) as response:stream=io.StringIO(response.read().decode('utf-8'))
    ids=[]
    while game:=chess.pgn.read_game(stream):
        assert not game.errors and len(list(game.mainline_moves()))==12
        ids.append(game.headers['AttemptId'])
    assert len(ids)==len(set(ids))==2
    results.append({'control':control,'tournament':t['id'],'official_games':2,'complete_pairs':1,'saved_plies':24,'unique_legal_pgn_games':2})
report={'packaged_worker':True,'piece_assets_served_and_match_source':72,'unsaved_discovery_preserves_library':True,'controls':results,'preferences':api('preferences'),'worker_error':api('status')['error']}
(root/'test-output'/'polish-packaged-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
