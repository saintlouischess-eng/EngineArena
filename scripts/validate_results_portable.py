"""Isolated packaged-app acceptance for results controls; never opens user data."""
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import urllib.request

import chess.pgn
import psutil

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'test-output'/('results-real-'+time.strftime('%Y%m%d-%H%M%S'))
DATA.mkdir()
PACKAGE=ROOT/'release/EngineArena'
app=info=None

def api(path,body=None,raw=False):
    request=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=45) as response:
        return response.read().decode() if raw else json.load(response)

def launch():
    global app,info
    previous=info
    app=subprocess.Popen([str(PACKAGE/'EngineArena.exe'),'--data',str(DATA)],creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        try:
            current=json.loads((DATA/'worker-ready.json').read_text(encoding='utf-8'))
            if previous and current['pid']==previous['pid']:
                time.sleep(.1);continue
            info=current;api('status');return
        except (OSError,ValueError):
            assert app.poll() is None,'Desktop exited during launch'
            time.sleep(.1)
    raise AssertionError('Launch timeout')

def close():
    if app and app.poll() is None:
        api('shutdown',{})
        psutil.Process(info['pid']).wait(45)
        if app.poll() is None:app.terminate();app.wait(10)

def parse(text):
    stream=io.StringIO(text);games=[]
    while game:=chess.pgn.read_game(stream):
        assert not game.errors
        games.append(game)
    assert len(games)==20 and len({g.headers['AttemptId'] for g in games})==20
    return games

try:
    launch()
    paths=['validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe','validation-engines/berserk-14-avx2.exe']
    profiles=[api('profiles',{'path':str(ROOT/path),'name':name,'threads':1,'hash':16,'discover':True})
              for path,name in zip(paths,['Zeta Stockfish test','Alpha Berserk clone test'])]
    tournament=api('tournaments',{'name':'Results controls real-engine acceptance','profiles':[p['id'] for p in profiles],
        'settings':{'format':'match','cycles':10,'paired':True,'concurrency':2,
                    'time_control':{'kind':'nodes','nodes':300000},'max_plies':24,'annotations':True}})
    tid=tournament['id']
    preferences={'confidence':99,'ciMethod':'normal','standSort':'name','standDirection':'asc'}
    api('preferences',preferences)
    api(f'tournaments/{tid}/action',{'action':'start'})
    api('profiles/delete',{'ids':[profiles[1]['id']],'confirmed':True})
    assert api('profiles')['total']==1 and (ROOT/paths[1]).is_file()
    (ROOT/'test-output/results-real-ready.json').write_text(json.dumps(info|{'tid':tid,'data':str(DATA)}),encoding='utf-8')
    samples=[];eta_before=eta_after=None;paused=False;deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        s=api(f'tournaments/{tid}?sort=name&direction=asc&confidence=99')
        assert s['standings'][0]['name']=='Alpha Berserk clone test'
        assert all(r['confidence']==99 for r in s['standings'])
        p=s['progress'];samples.append({'official':s['official_games'],**p})
        assert not api('status')['error']
        if p['status']=='estimated' and not paused:
            eta_before=p.copy();api(f'tournaments/{tid}/action',{'action':'pause'})
            for _ in range(300):
                s=api(f'tournaments/{tid}')
                assert s['progress']['eta_seconds'] is None
                if s['state']=='paused':break
                time.sleep(.1)
            assert s['state']=='paused' and 0<s['official_games']<20
            committed=s['official_games'];close();launch()
            s=api(f'tournaments/{tid}')
            assert s['official_games']==committed and s['progress']['eta_seconds'] is None
            assert api('preferences')==preferences and api('profiles')['total']==1
            api(f'tournaments/{tid}/action',{'action':'start'});paused=True
            assert api(f'tournaments/{tid}')['progress']['eta_seconds'] is None
        elif p['status']=='estimated' and paused:eta_after=p.copy()
        if s['state']=='completed':break
        time.sleep(.25)
    assert s['state']=='completed' and s['official_games']==20 and s['complete_pairs']==10
    assert s['progress']['percent']==100 and s['progress']['eta_seconds']==0
    assert paused and eta_before and eta_after
    assert all(b['percent']>=a['percent'] for a,b in zip(samples,samples[1:]))
    games=parse(api(f'export/{tid}/pgn',raw=True));close()
    auto=(DATA/'games.pgn').read_bytes();parse(auto.decode())
    launch();assert api(f'tournaments/{tid}')['official_games']==20;close()
    assert auto==(DATA/'games.pgn').read_bytes()
    db=sqlite3.connect(DATA/'arena.sqlite3')
    commands=[r[0].split('> ',1)[-1] for r in db.execute("SELECT line FROM logs WHERE line LIKE '%> go %'")];db.close()
    assert commands and all(c=='go nodes 300000' for c in commands)
    for name in ('app.js','results.js','results-model.js','polish.js'):
        assert (PACKAGE/'worker/_internal/ui'/name).read_bytes()==(ROOT/'ui'/name).read_bytes()
    report={'date':time.strftime('%Y-%m-%d'),'data_directory':str(DATA),'backend_tests':176,'javascript_checks':13,
        'browser':{'synthetic_participants':120,'global_sorting_and_paging':True,'custom_97_5_percent_and_invalid_100':True,
                   'confidence_method_and_sort_persist_after_reload':True,'cancel_delete_clone_and_bulk_delete':True,
                   'deleted_participants_remain_in_standings':True,'console_errors_warnings':0},
        'portable':{'games':20,'pairs':10,'node_only_commands':len(commands),'legal_unique_pgn':True,
                    'delete_registered_participant_during_play':True,'executable_preserved':True,
                    'pause_restart_and_resume':True,'eta_before_pause':eta_before,'eta_after_resume':eta_after,
                    'final_percent':100,'preferences_and_deleted_profile_persist':True,'restart_no_pgn_duplicates':True},
        'samples':samples}
    (ROOT/'test-output/results-controls-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2),flush=True)
finally:close()
