import io
import json
import os
import subprocess
import sys
from pathlib import Path

import chess
import chess.pgn
import pytest
import psutil

from arena.store import Store,DEFAULTS
from arena.opening_policy import capacity,select
from arena.pgn_format import render_attempt
from arena.tournament_report import render


def pool():
    b=chess.Board();items=[]
    for m in list(b.legal_moves):
        b.push(m);items.append({'fen':b.fen(),'name':m.uci(),'start_fen':chess.STARTING_FEN,'moves':[m.uci()]});b.pop()
    return items


def create(s,n=4,**settings):
    return s.create_tournament('Shared KO',[{'name':str(i)} for i in range(n)],
        {'format':'knockout','cycles':3,'ko_round_games':[6]*((n-1).bit_length()),'opening_policy':'round','playoff_cycles':2,**settings},pool())


def stage(s,tid,decide=False,window=100):
    # Fill a single saved stage, with bounded materialization and no dependency advance.
    s.fill_queue(tid,window);out=[]
    while True:
        g=s.claim(tid)
        if not g:break
        out.append(g);winner=min(g['white'],g['black'])
        s.finish(g['aid'],('1-0' if g['white']==winner else '0-1') if decide else '1/2-1/2','fixture')
        from arena.rounds import materialize
        materialize(s,s.tournament(tid),window)
    return out


def sequence(games):
    grouped={}
    for g in games:
        grouped.setdefault(tuple(sorted((g['a'],g['b']))),[]).append(g['opening']['assignment'])
    return list(grouped.values())


@pytest.mark.parametrize('policy',['round','cycle'])
@pytest.mark.parametrize('fmt',['knockout','double_elimination'])
def test_shared_suites_advance_for_regular_pairs_ties_and_next_round(tmp_path,policy,fmt):
    s=Store(tmp_path)
    try:
        t=create(s,format=fmt,ko_round_games=[6,6] if fmt=='knockout' else [],opening_policy=policy);tid=t['id'];s.set_state(tid,'running')
        assert 'Shared sequence across KO matches; new position per reversed-color pair' in render(s.path,tid)
        assert sequence(stage(s,tid,window=2))==[[0,0,1,1,2,2]]*2
        first=stage(s,tid,window=2);assert sequence(first)==[[3,3,4,4]]*2
        s.set_state(tid,'paused');s.close();s=Store(tmp_path);s.set_state(tid,'running')
        second=stage(s,tid,True,window=2);assert sequence(second)==[[5,5,6,6]]*2
        more=stage(s,tid,True,window=2);assert all(v==[7,7,8,8,9,9] for v in sequence(more))
        assert all(g['opening']['ko_opening_progression']=='shared_pairs_v1' for g in more)
        pgn=chess.pgn.read_game(io.StringIO(render_attempt(s.db,more[0]['aid'])))
        assert pgn.headers['OpeningPosition']=='8' and pgn.headers['OpeningAssignment']=='8' and not pgn.errors
        assert 'including tiebreaks and later rounds' in render(s.path,tid)
    finally:s.close()


def test_unpaired_shared_sequence_by_stage_and_reuse_only_at_exhaustion(tmp_path):
    s=Store(tmp_path)
    try:
        t=create(s,2,paired=False,ko_round_games=[3],playoff_cycles=2);tid=t['id'];s.set_state(tid,'running')
        games=stage(s,tid)+stage(s,tid)
        assert [g['opening']['selection'] for g in games]==list(range(5))
        assert [g['white'] for g in games]==[0,1,0,1,0]
        for _ in range(9):games+=stage(s,tid)
        assert [g['opening']['selection'] for g in games]==[i%20 for i in range(23)]
        assert games[-1]['opening']['pool_pass']==1
    finally:s.close()


def test_legacy_pending_games_keep_openings_then_new_ties_advance(tmp_path,monkeypatch):
    from arena import opening_policy
    reserve=opening_policy.reserve_ko_suite
    s=Store(tmp_path)
    try:
        monkeypatch.setattr(opening_policy,'reserve_ko_suite',lambda *a:None)
        t=create(s,ko_round_games=[2,2],playoff_cycles=1);tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,2)
        old=s.rows('SELECT id,opening FROM games WHERE tid=?',(tid,))
        s.set_state(tid,'paused');s.close();s=Store(tmp_path)
        monkeypatch.setattr(opening_policy,'reserve_ko_suite',reserve);s.set_state(tid,'running')
        regular=stage(s,tid,window=2);assert sequence(regular)==[[0,0]]*2
        assert s.rows('SELECT id,opening FROM games WHERE tid=? ORDER BY number LIMIT 2',(tid,))==old
        assert sequence(stage(s,tid))==[[1,1]]*2
        assert sequence(stage(s,tid))==[[2,2]]*2
        assert 'earlier recorded stages retain their legacy openings' in render(s.path,tid)
    finally:s.close()


def test_replacement_retains_shared_suite_and_other_match_openings(tmp_path):
    s=Store(tmp_path)
    try:
        t=create(s,ko_round_games=[2,2],playoff_cycles=1);tid=t['id'];s.set_state(tid,'running')
        regular=stage(s,tid);tie=stage(s,tid,True);later=stage(s,tid,True);s.fill_queue(tid,100)
        before=[dict(r) for r in s.rows('SELECT * FROM opening_suites WHERE tid=? ORDER BY round,stage',(tid,))]
        s.requeue(tid,[regular[0]['id']],mode='replacement',invalidate=True);s.set_state(tid,'running')
        g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','replacement')
        replay=stage(s,tid,True)
        assert sequence(replay)==[[1,1]]
        assert all(g['opening']==tie[i]['opening'] for i,g in enumerate(replay))
        assert s.rows('SELECT * FROM opening_suites WHERE tid=? ORDER BY round,stage',(tid,))==before
        next_round=stage(s,tid,True);assert sequence(next_round)==[[2,2]]
    finally:s.close()


def crash_fixture(folder):
    s=Store(folder);t=create(s,2,ko_round_games=[2],playoff_cycles=1,opening_order='shuffle');tid=t['id'];s.set_state(tid,'running');stage(s,tid)
    s.fill_queue(tid,2);g=s.claim(tid)
    print(json.dumps({'pid':os.getpid(),'tid':tid,'gid':g['id'],'opening':g['opening']}),flush=True)
    sys.stdin.readline()


def test_forced_exit_keeps_assigned_suite_and_recovered_pair(tmp_path):
    p=subprocess.Popen([sys.executable,'-c',"import runpy,sys;runpy.run_path(sys.argv[1])['crash_fixture'](sys.argv[2])",str(Path(__file__).resolve()),str(tmp_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        data=json.loads(p.stdout.readline())
        # Windows venv python.exe can be a launcher with a separate interpreter.
        # Kill the process actually holding SQLite, not just its launcher.
        child=psutil.Process(data['pid']);child.kill();child.wait(timeout=10);p.wait(timeout=10)
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=10)
    s=Store(tmp_path)
    try:
        tid=data['tid'];s.set_state(tid,'running');games=stage(s,tid)
        assert games[0]['id']==data['gid'] and games[0]['opening']==data['opening']==games[1]['opening']
        assert sequence(stage(s,tid))==[[2,2]]
        s.set_state(tid,'paused');s.delete_tournament(tid,'Shared KO')
        assert not s.rows('SELECT * FROM opening_suites WHERE tid=?',(tid,))
    finally:s.close()


def test_capacity_counts_shared_regular_suites_and_tiebreak_upper_bound():
    s=DEFAULTS|{'format':'knockout','opening_policy':'round','ko_round_games':[4,6,8]}
    c=capacity(20,8,s);assert c['required_positions']=='9' and c['unbounded'] and c['games_before_reuse'] is None
    assert 'Tiebreaks and later KO rounds continue with new positions' in c['note'] and 'reuse the round' not in c['note']
    c=capacity(20,8,s|{'knockout_tiebreak':'playoff','playoff_limit':3,'playoff_cycles':2})
    assert c['required_positions']=='27' and c['reuse_expected']
