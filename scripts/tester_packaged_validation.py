"""Short functional preview acceptance in a named, isolated portable workspace."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import time
import urllib.request
import chess.pgn

ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--ready',type=Path,required=True);parser.add_argument('--check-restart',action='store_true');args=parser.parse_args()
ready=args.ready.resolve();assert ready.is_relative_to(ROOT/'test-output')
info=json.loads(ready.read_text());data=ready.parent

def request(path,body=None):
    req=urllib.request.Request(f"http://127.0.0.1:{info['port']}/"+path,
        None if body is None else json.dumps(body).encode(),{'X-Arena-Token':info['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return response.read()

def api(path,body=None):return json.loads(request('api/'+path,body))

target=ROOT/'test-output/tester-packaged-report.json'
if args.check_restart:
    report=json.loads(target.read_text());snapshot=api('tournaments/'+report['tournament'])
    assert snapshot['official_games']==report['games']
    assert hashlib.sha256((data/'games.pgn').read_bytes()).hexdigest()==report['automatic_pgn_sha256']
    assert api('preferences')['confidence']==99
    report['restart_results_pgn_preferences_retained']=True
    target.write_text(json.dumps(report,indent=2),encoding='utf-8');print('Restart retained all results, exact PGN bytes, and preferences.');raise SystemExit

profiles=[]
for name,path in [('Stockfish','validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'),('Berserk','validation-engines/berserk-14-avx2.exe')]:
    profiles.append(api('profiles',{'name':name+' · preview acceptance','path':str(ROOT/path),'threads':1,'hash':16,'discover':True}))
api('preferences',{'confidence':99,'fontSize':16,'theme':'dark'})
t=api('tournaments',{'name':'Preview functional acceptance · pure nodes','profiles':[p['id'] for p in profiles],
  'settings':{'format':'match','cycles':8,'concurrency':4,'time_control':{'kind':'nodes','nodes':150000}}})
tid=t['id'];api(f'tournaments/{tid}/action',{'action':'start'});start=time.monotonic()
print('Running 16 full real-engine games at four concurrent games.',flush=True)
while time.monotonic()-start<240:
    snapshot=api('tournaments/'+tid+'?confidence=99')
    if snapshot['state']=='completed':break
    time.sleep(.25)
assert snapshot['state']=='completed' and snapshot['official_games']==16
assert all(s['pairs']==8 for s in snapshot['standings'])
formats={}
for style in ('compact','tagged','moves','archive'):
    raw=request(f'api/export/{tid}/pgn?style={style}').decode('utf-8');reader=io.StringIO(raw);seen=[]
    while game:=chess.pgn.read_game(reader):
        assert not game.errors;board=game.board()
        for move in game.mainline_moves():assert move in board.legal_moves;board.push(move)
        seen.append(game.headers['AttemptId'])
    assert len(seen)==16 and len(set(seen))==16
    formats[style]=len(seen)
cross=api(f'tournaments/{tid}/crosstable?confidence=99');series=api(f'tournaments/{tid}/series?slot=0&confidence=99')
live=next(row for row in snapshot['standings'] if row['slot']==0)
assert live['ci']==series['points'][-1]['ci']==next(c for c in cross['cells'] if c['a']==0)['ci']
assert api(f'tournaments/{tid}/openings?slot=0')['summary']['games']==16
assert api(f'tournaments/{tid}/ratings?confidence=99')['samples']==8
html=api(f'tournaments/{tid}/report?confidence=99')['html'];assert 'Normal 99% CI' in html
assert 'ci_lower' in request(f'api/export/{tid}/csv?confidence=99').decode()
for name in ('format.js','review.js','review.css'):
    assert request('assets/'+name)==(ROOT/'ui'/name).read_bytes()
benchmark=api('experiments',{'name':'Preview thread-scaling report','kind':'benchmark','profiles':[p['id'] for p in profiles],
 'settings':{'time_control':{'kind':'nodes','nodes':100000},'thread_counts':[1,2],'repeats':2,'fen':chess.STARTING_FEN}})
api(f"experiments/{benchmark['id']}/action",{'action':'start'});deadline=time.monotonic()+60
while time.monotonic()<deadline:
    result=api('experiments/'+benchmark['id'])
    if result['state']=='completed':break
    time.sleep(.2)
assert result['completed']==8
for row in result['results']:
    assert row['official'] and row['elapsed_seconds']>0 and row['measured_nps']>0
with sqlite3.connect(data/'arena.sqlite3') as db:
    lines=[r[0] for r in db.execute('SELECT l.line FROM logs l JOIN attempts a ON a.id=l.aid JOIN games g ON g.id=a.gid WHERE g.tid=?',(tid,))]
    commands=[line for line in lines if '> go ' in line]
    assert commands and all(line.split('> ',1)[1]=='go nodes 150000' for line in commands)
    failures=db.execute("SELECT count(*) FROM attempts a JOIN games g ON g.id=a.gid WHERE g.tid=? AND a.reason IN ('crash','hang','timeout','illegal_move','protocol_error')",(tid,)).fetchone()[0]
    assert failures==0
report={'tournament':tid,'games':16,'pairs':8,'max_concurrency':api('status')['max_active_games'],
 'elapsed_seconds':time.monotonic()-start,'exact_node_commands':len(commands),'pgn_formats_legally_parsed':formats,
 'standings_crosstable_curve_agree':True,'benchmark_cases':8,'benchmark':benchmark['id'],
 'automatic_pgn_sha256':hashlib.sha256((data/'games.pgn').read_bytes()).hexdigest(),'packaged_ui_matches_source':True}
target.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
