"""Run real engines on top of a clearly labelled synthetic 50,000-game history.

This disposable fixture tests history size, concurrent engines, live UI, exports,
backups and forced recovery together. It is not 50,000 naturally played games.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import statistics
import sys
import time
import urllib.request

import chess
import chess.pgn
import psutil

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'test-output/history-live'
READY=DATA/'worker-ready.json'
CURRENT=ROOT/'test-output/history-live-current.json'
REPORT=ROOT/'test-output/history-live-report.json'


def api(path,body=None,timeout=120):
    info=json.loads(READY.read_text())
    req=urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/"+path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'X-Arena-Token':info['token'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)


def prepare():
    assert not DATA.exists(),'Preserve the existing history-live fixture; resume it instead.'
    DATA.mkdir();source=ROOT/'test-output/history-scale'
    with sqlite3.connect(source/'arena.sqlite3') as src,sqlite3.connect(DATA/'arena.sqlite3') as dest:src.backup(dest)
    for name in ('games.pgn','interrupted.pgn'):shutil.copy2(source/name,DATA/name)
    with sqlite3.connect(DATA/'arena.sqlite3') as db:
        tid,body=db.execute('SELECT id,settings FROM tournaments').fetchone();settings=json.loads(body)
        settings.update(cycles=26152,concurrency=32,cpu_budget=32,max_plies=0,time_control={'kind':'nodes','nodes':30000},retry_limit=0)
        lines=['e2e4 e7e5 g1f3 b8c6 f1b5','e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4',
               'd2d4 d7d5 c2c4 e7e6 b1c3 g8f6','d2d4 g8f6 c2c4 g7g6 b1c3 f8g7',
               'c2c4 e7e5 b1c3 g8f6','g1f3 d7d5 g2g3 g8f6 f1g2',
               'e2e4 e7e6 d2d4 d7d5 b1c3','e2e4 c7c6 d2d4 d7d5 b1c3']
        openings=[]
        for n,line in enumerate(lines):
            board=chess.Board()
            for uci in line.split():board.push_uci(uci)
            openings.append({'fen':board.fen(),'name':f'Live validation opening {n+1}'})
        settings.update(openings=openings,opening_order='random',seed=7970)
        # Fixture configuration, before live validation begins. Existing rows are
        # explicitly synthetic; production tournament conditions are immutable.
        db.execute('UPDATE tournaments SET name=?,settings=?,total=?,state=? WHERE id=?',
                   ('50K synthetic history + real mixed-opening validation',json.dumps(settings),52304,'paused',tid))
        db.execute('DELETE FROM preferences')
        db.execute('INSERT INTO preferences VALUES(?,?)',('ui',json.dumps({'boardCount':32,'theme':'dark','graphs':[]})))
        profiles=[]
        for slot,body in db.execute('SELECT slot,profile FROM participants WHERE tid=?',(tid,)).fetchall():
            p=json.loads(body);p['threads']=1;p['hash']=32
            for name in p.get('options',{}):
                if name.casefold()=='threads':p['options'][name]=1
                if name.casefold()=='hash':p['options'][name]=32
            db.execute('UPDATE participants SET profile=? WHERE tid=? AND slot=?',(json.dumps(p),tid,slot))
            profiles.append({'slot':slot,'name':p['name'],'path':p['path']})
    value={'tournament':tid,'synthetic_games':50000,'planned_real_games':2304,'data':str(DATA),'profiles':profiles}
    CURRENT.write_text(json.dumps(value,indent=2));print(json.dumps(value),flush=True)


def monitor():
    current=json.loads(CURRENT.read_text());tid=current['tournament'];start=time.monotonic();samples=[];last=0
    api('tournaments/'+tid+'/action',{'action':'start'})
    process=psutil.Process(json.loads(READY.read_text())['pid'])
    while time.monotonic()-start<3600:
        tick=time.perf_counter();snap=api('tournaments/'+tid);latency=1000*(time.perf_counter()-tick)
        status=api('status');elapsed=time.monotonic()-start
        assert not status['error'],status['error']
        samples.append({'elapsed':elapsed,'official':snap['official_games'],'active':status['active_games'],
            'snapshot_ms':latency,'worker_rss':process.memory_info().rss,'ui':status.get('ui_metrics')})
        if elapsed-last>=20:
            print(json.dumps({'seconds':round(elapsed,1),'new_real_games':snap['official_games']-50000,
                             'active':status['active_games'],'snapshot_ms':round(latency,2)}),flush=True);last=elapsed
        if snap['state']=='completed':break
        time.sleep(.5)
    assert snap['state']=='completed'
    current.update(elapsed_seconds=elapsed,official_games=snap['official_games'],pairs=snap['complete_pairs'],
        peak_concurrency=max(s['active'] for s in samples),peak_worker_rss=max(s['worker_rss'] for s in samples),
        snapshot_median_ms=statistics.median(s['snapshot_ms'] for s in samples),
        snapshot_p95_ms=sorted(s['snapshot_ms'] for s in samples)[int(.95*len(samples))],samples=samples)
    REPORT.write_text(json.dumps(current,indent=2));print(json.dumps({k:v for k,v in current.items() if k!='samples'}),flush=True)


def validate():
    value=json.loads(REPORT.read_text());tid=value['tournament'];count=0;moves=0;ids=set();failures={}
    with sqlite3.connect(DATA/'arena.sqlite3') as db:
        for pgn,reason in db.execute('''SELECT o.pgn,a.reason FROM games g JOIN attempts a ON a.id=g.official
              JOIN outbox o ON o.aid=a.id WHERE g.tid=? AND g.number>=50000 ORDER BY g.number''',(tid,)):
            game=chess.pgn.read_game(io.StringIO(pgn));assert game and not game.errors
            assert game.headers['AttemptId'] not in ids;ids.add(game.headers['AttemptId']);count+=1;moves+=len(list(game.mainline_moves()))
            if reason in ('max_plies_adjudication','crash','hang','timeout','illegal_move','interrupted'):failures[reason]=failures.get(reason,0)+1
        assert count==2304 and not failures,(count,failures)
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    # Stream automatic PGN headers: avoid parsing millions of duplicate fixture moves.
    all_ids=set();duplicates=0
    with (DATA/'games.pgn').open(encoding='utf-8') as f:
        for line in f:
            if line.startswith('[AttemptId "'):
                aid=line.split('"')[1];duplicates+=aid in all_ids;all_ids.add(aid)
    assert not duplicates and len(all_ids)==52304
    value.update(real_games_legally_parsed=count,real_moves=moves,unexpected_terminations=failures,
                 automatic_pgn_attempts=len(all_ids),automatic_pgn_duplicates=duplicates)
    REPORT.write_text(json.dumps(value,indent=2));print(json.dumps({k:v for k,v in value.items() if k!='samples'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','monitor','validate']);args=parser.parse_args()
    {'prepare':prepare,'monitor':monitor,'validate':validate}[args.action]()
