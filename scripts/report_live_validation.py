"""Measure live opening reports during an isolated real-engine tournament."""
import json
from pathlib import Path
import time
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
ready=json.loads((ROOT/'test-output/conditions-ready.json').read_text())
tid=json.loads((ROOT/'test-output/report-live-tournament.json').read_text())['id']
def api(path,body=None):
    req=urllib.request.Request(f"http://127.0.0.1:{ready['port']}/api/"+path,data=json.dumps(body).encode() if body is not None else None,headers={'X-Arena-Token':ready['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)

api('tournaments/'+tid+'/action',{'action':'start'});observations=[];deadline=time.monotonic()+120
while time.monotonic()<deadline:
    snap=api('tournaments/'+tid);start=time.perf_counter();r=api('tournaments/'+tid+'/openings?slot=0');ms=1000*(time.perf_counter()-start)
    observations.append({'official':snap['official_games'],'active':snap['counts'].get('running',0),'reported':r['summary']['games'],'pairs':sum(o['complete_pairs'] for o in r['openings']),'latency_ms':round(ms,2)})
    assert snap['official_games']<=r['summary']['games']<=snap['total']
    if snap['state']=='completed':break
    time.sleep(.5)
assert snap['state']=='completed' and r['summary']['games']==16 and observations[-1]['pairs']==8
assert any(0<x['official']<16 and x['active'] for x in observations)
latencies=sorted(x['latency_ms'] for x in observations)
report={'tournament':tid,'official_games':16,'complete_pairs':8,'samples':len(observations),
  'report_latency_median_ms':latencies[len(latencies)//2],'report_latency_p95_ms':latencies[int(.95*(len(latencies)-1))],
  'observed_results_while_games_running':True,'observations':observations}
(ROOT/'test-output/report-live-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='observations'}))
