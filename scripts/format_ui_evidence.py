"""Verify durable evidence produced by the GUI format acceptance workflow."""
import json
from pathlib import Path
import sqlite3
import urllib.request
import chess.pgn

ROOT=Path(__file__).resolve().parent.parent
data=ROOT/'test-output'/'format-ui';ready=json.loads((data/'worker-ready.json').read_text())
def api(path):
    req=urllib.request.Request(f"http://127.0.0.1:{ready['port']}/api/"+path,headers={'X-Arena-Token':ready['token']})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)

t=next(t for t in api('tournaments') if t['name']=='GUI node-only playoff validation');tid=t['id'];snap=api('tournaments/'+tid);review=api('tournaments/'+tid+'/pairings')
assert snap['state']=='paused' and snap['official_games']==4 and snap['complete_pairs']==2
assert snap['settings']['time_control']['kind']=='nodes' and snap['settings']['time_control']['nodes']==2000
assert snap['settings']['tiebreaks']==['buchholz','sonneborn_berger','seed'] and snap['settings']['seeding']=='random'
assert review['matches'][0]['playoff_stages']==1 and len(review['manual_ties'])==1
ids={g['official'] for g in api('tournaments/'+tid+'/games')['items'] if g['official']};records=[]
with (data/'games.pgn').open(encoding='utf-8') as stream:
    while game:=chess.pgn.read_game(stream):
        if game.headers['AttemptId'] in ids:records.append(game)
assert len(records)==len(ids)==4 and not any(g.errors for g in records)
stages=[g.headers['CompetitionStage'] for g in records];assert stages.count('regular')==stages.count('playoff')==2
with sqlite3.connect((data/'arena.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
    events=[json.loads(r[0]) for r in db.execute("SELECT body FROM audit WHERE tid=? AND action='round_paired'",(tid,))]
result={'tournament':tid,'gui_created':True,'nodes_per_move':2000,'chess_clock':False,'official_games':4,'complete_pairs':2,'regular_games':2,'playoff_games':2,'manual_fallback_paused':True,'pgn_parse_errors':0,'pgn_duplicates':0,'recorded_rounds':len(events)}
(ROOT/'test-output'/'format-ui-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
