"""Verify records created through the reusable-conditions GUI acceptance flow."""
import io
import json
from pathlib import Path
import urllib.request
import chess
import chess.pgn

ROOT=Path(__file__).resolve().parent.parent
ready=json.loads((ROOT/'test-output/conditions-ready.json').read_text())
def api(path):
    req=urllib.request.Request(f"http://127.0.0.1:{ready['port']}/api/"+path,headers={'X-Arena-Token':ready['token']})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)

t=next(t for t in api('tournaments') if t['name']=='GUI saved Chess960 · node-only')
snap=api('tournaments/'+t['id']);assert snap['state']=='completed'
assert snap['official_games']==2 and snap['complete_pairs']==1
s=snap['settings'];assert s['chess960'] and s['time_control']['kind']=='nodes' and s['time_control']['nodes']==10000 and not s['ponder']
assert chess.Board(s['openings'][0]['fen'],chess960=True).chess960_pos()==42
games=api('tournaments/'+t['id']+'/games')['items'];details=[api('games/'+g['id']) for g in games]
assert details[0]['opening']==details[1]['opening'] and games[0]['white']==games[1]['black']
commands=[];moves=0
for g in details:
    a=next(a for a in g['attempts'] if a['id']==g['official'])
    assert a['reason'] not in ('crash','hang','illegal_move','timeout','protocol_error')
    moves+=len(a['moves'])
    for m in a['moves']:
        clocks=json.loads(m['clocks']) if isinstance(m['clocks'],str) else m['clocks']
        assert clocks['white']['remaining'] is None and clocks['black']['remaining'] is None
    commands.extend(x['line'] for x in a['logs'] if '> go ' in x['line'])
assert commands and all(x.endswith('go nodes 10000') for x in commands)
records=[]
with (ROOT/'test-output/conditions-ui/games.pgn').open(encoding='utf-8') as stream:
    while g:=chess.pgn.read_game(stream):records.append(g)
records=[g for g in records if g.headers['AttemptId'] in {g['official'] for g in games}]
assert len(records)==2 and len({g.headers['AttemptId'] for g in records})==2
assert all(not g.errors and g.board().chess960 and g.headers['Opening']=='Chess960 42' for g in records)
presets=api('presets');positions=api('positions')
assert any(p['name']=='GUI 10000 nodes · paired' and p['settings']['hash']==32 for p in presets)
assert any(p['name']=='After 1. e4' and p['fen'].endswith('b KQkq e3 0 1') for p in positions)
report={'tournament':t['id'],'gui_created':True,'preset_edited_and_copied':True,'positions_saved':len(positions),
  'chess960_start':42,'nodes_per_move':10000,'chess_clock':False,'official_games':2,'complete_pairs':1,
  'recorded_moves':moves,'recorded_node_only_commands':len(commands),'pgn_errors':0,'duplicate_official_attempts':0}
(ROOT/'test-output/conditions-ui-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
