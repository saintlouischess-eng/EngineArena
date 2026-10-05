import asyncio
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import chess.pgn
from arena.store import Store,DEFAULTS
from arena.knockout import base_pairs,round_matches,game_control
from arena.knockout_results import read
from arena.pgn_format import render_attempt
from arena.stat_exports import standings_csv
from arena.tournament_report import render


def profiles(n):return [{'name':f'Engine {i}'} for i in range(n)]
def config(games):return {'format':'knockout','ko_round_games':games,'knockout_tiebreak':'continuous','playoff_cycles':1,'cycles':1}
def finish(s,tid,winner=None):
    s.fill_queue(tid,100);out=[]
    while g:=s.claim(tid):
        result='1/2-1/2' if winner is None else '1-0' if g['white']==winner else '0-1'
        s.finish(g['aid'],result,'fixture');out.append(g)
    return out


def test_new_ko_defaults_continue_ties_without_seed_elimination(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Default KO',profiles(2),{'format':'knockout','cycles':1});tid=t['id'];s.set_state(tid,'running')
        for _ in range(6):assert len(finish(s,tid))==2
        assert s.tournament(tid)['state']=='running' and s.snapshot(tid)['knockout']['champion'] is None
    finally:s.close()


@pytest.mark.parametrize('n,counts',[(2,[1]),(3,[1,1]),(5,[1,2,1]),(8,[4,2,1]),(9,[1,4,2,1])])
def test_per_round_lengths_and_byes(n,counts,tmp_path):
    s=Store(tmp_path)
    try:
        lengths=[2*(i+1) for i in range(len(counts))]
        t=s.create_tournament('Lengths',profiles(n),config(lengths));tid=t['id'];s.set_state(tid,'running')
        assert round_matches(n)==counts and t['total']==sum(a*b for a,b in zip(counts,lengths))
        for r,count in enumerate(counts):
            s.fill_queue(tid,100);played=[]
            while g:=s.claim(tid):
                winner=min(g['a'],g['b']);s.finish(g['aid'],'1-0' if g['white']==winner else '0-1','fixture');played.append(g)
            assert len(played)==count*lengths[r]
        s.fill_queue(tid,100);snap=s.snapshot(tid)
        assert snap['state']=='completed' and snap['knockout']['champion']=='Engine 0'
        assert snap['official_games']==t['total'] and snap['complete_pairs']==t['total']//2
        assert sum(p['byes'] for p in snap['standings'])==2**len(counts)-n
    finally:s.close()


def test_continuous_ties_controls_pairs_and_pgn(tmp_path):
    controls=[{'kind':'fischer','seconds':60,'increment':1},{'kind':'fischer','seconds':15,'increment':.25}]
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Ties',profiles(2),config([2])|{'playoff_controls':controls});tid=t['id'];s.set_state(tid,'running');finish(s,tid)
        for stage in range(1,6):
            games=finish(s,tid)
            assert len(games)==2 and games[0]['opening']==games[1]['opening']
            assert games[0]['opening']['playoff_stage']==stage
            assert games[0]['opening']['playoff_time_control']==controls[min(stage-1,1)]
            history=s.games(tid)['items'][-1]
            assert history['competition_label']==f'KO round 1 · Tiebreak {stage}'
            assert history['clocks']['white']['control']['seconds']==controls[min(stage-1,1)]['seconds']
            pgn=chess.pgn.read_game(io.StringIO(render_attempt(s.db,games[0]['aid'])))
            assert pgn.headers['PlayoffStage']==str(stage) and pgn.headers['TimeControl']==('60+1' if stage==1 else '15+0.25')
            assert s.snapshot(tid)['knockout']['champion'] is None
        s.fill_queue(tid,2);a=s.claim(tid);s.finish(a['aid'],'1-0' if a['white']==1 else '0-1','fixture')
        assert s.snapshot(tid)['knockout']['champion'] is None  # second color must finish
        b=s.claim(tid);s.finish(b['aid'],'1/2-1/2','fixture');s.fill_queue(tid,2)
        snap=s.snapshot(tid);assert snap['state']=='completed' and snap['knockout']['champion']=='Engine 1'
        assert snap['official_games']==14 and snap['complete_pairs']==7
        assert snap['standings'][0]['name']=='Engine 1'
    finally:s.close()


def test_unpaired_odd_lengths_alternate_colors(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Odd',profiles(2),config([3])|{'paired':False});tid=t['id'];s.set_state(tid,'running')
        games=finish(s,tid);more=finish(s,tid)
        assert [g['white'] for g in games+more]==[0,1,0,1]
        assert s.snapshot(tid)['complete_pairs']==0
    finally:s.close()


def test_champion_order_is_not_total_game_points(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Bracket order',profiles(4),config([4,2]));tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,100);seen={}
        while g:=s.claim(tid):
            a=min(g['a'],g['b']);index=seen.get(a,0);seen[a]=index+1
            winner=0 if a==0 else 1 if index<2 else 2
            result='1/2-1/2' if a==1 and index==2 else '1-0' if g['white']==winner else '0-1'
            s.finish(g['aid'],result,'fixture')
        s.fill_queue(tid,100);g=s.claim(tid);s.finish(g['aid'],'1-0' if g['white']==1 else '0-1','fixture');g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','fixture');s.fill_queue(tid,100)
        snap=s.snapshot(tid);a,b=snap['standings'][:2]
        assert a['slot']==1 and a['ko_status']=='Champion' and a['points']==4
        assert b['slot']==0 and b['points']==4.5
        points=s.snapshot(tid,sort='points',direction='desc')['standings'];assert points[0]['slot']==0 and points[0]['rank']==2
        html=render(s.path,tid);assert html.index('Champion: Engine 1')<html.index('Standings</h2>')
    finally:s.close()


def test_result_replacement_invalidates_playoffs_and_later_rounds(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Replace',profiles(3),config([2,4]));tid=t['id'];s.set_state(tid,'running')
        original=finish(s,tid);tiebreak=finish(s,tid,1);final=finish(s,tid,0);s.fill_queue(tid,100)
        assert s.snapshot(tid)['knockout']['champion']=='Engine 0'
        effect=s.requeue(tid,[original[0]['id']],mode='replacement');assert effect['effects']['later_rounds'] and effect['effects']['playoffs']
        s.requeue(tid,[original[0]['id']],mode='replacement',invalidate=True);s.set_state(tid,'running')
        g=s.claim(tid);s.finish(g['aid'],'1-0' if g['white']==2 else '0-1','replacement')
        assert s.snapshot(tid)['knockout']['champion'] is None
        final2=finish(s,tid,2);s.fill_queue(tid,100);snap=s.snapshot(tid)
        assert len(final2)==4 and snap['knockout']['champion']=='Engine 2'
        assert snap['official_games']==6 and snap['complete_pairs']==3
        assert all(s.game_detail(g['id'])['invalid'] for g in tiebreak+final)
        assert len(s.game_detail(original[0]['id'])['attempts'])==2
        # Diagnostic replays must not change a champion or match counts.
        s.requeue(tid,[final2[0]['id']],mode='diagnostic')
        assert s.snapshot(tid)['knockout']['champion']=='Engine 2'
        html=render(s.path,tid);assert 'Knockout (KO) results' in html and 'Champion: Engine 2' in html and 'Game points' in html
        rows=list(csv.DictReader(io.StringIO(standings_csv(snap['standings']))));assert rows[0]['ko_status']=='Champion' and rows[0]['match_wins']=='2'
    finally:s.close()


@pytest.mark.parametrize('overrides',[{'ko_round_games':[3]},{'ko_round_games':[2,4]},{'ko_round_games':[True]},{'ko_round_games':[0]},{'playoff_controls':[{}]},{'playoff_controls':[{'kind':'fischer','seconds':-1}] }])
def test_invalid_ko_configuration_is_rejected(overrides):
    with pytest.raises(ValueError):base_pairs(2,DEFAULTS|config([2])|overrides)


def crash_fixture(path):
    s=Store(Path(path));t=s.create_tournament('Crash recovery',profiles(2),config([2])|{'playoff_controls':[{'kind':'nodes','nodes':77}]});tid=t['id'];s.set_state(tid,'running');finish(s,tid)
    s.fill_queue(tid,2);g=s.claim(tid)
    print(json.dumps({'pid':os.getpid(),'tid':tid,'gid':g['id'],'aid':g['aid'],'opening':g['opening']}),flush=True)
    sys.stdin.readline()  # parent forcibly kills this process with its writer still open


def test_forced_termination_recovers_same_playoff(tmp_path):
    code="import runpy,sys; runpy.run_path(sys.argv[1])['crash_fixture'](sys.argv[2])"
    p=subprocess.Popen([sys.executable,'-c',code,str(Path(__file__).resolve()),str(tmp_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        import psutil
        data=json.loads(p.stdout.readline());child=psutil.Process(data['pid']);child.kill();child.wait(timeout=10);p.wait(timeout=10)
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=10)
    s=Store(tmp_path)
    try:
        tid=data['tid'];assert s.snapshot(tid)['official_games']==2
        old=s.game_detail(data['gid'])['attempts'][0];assert old['reason']=='interrupted'
        s.set_state(tid,'running');g=s.claim(tid);assert g['id']==data['gid'] and g['opening']==data['opening'] and g['aid']!=data['aid']
        s.finish(g['aid'],'1-0' if g['white']==1 else '0-1','fixture')
        g=s.claim(tid);s.finish(g['aid'],'1/2-1/2','fixture');s.fill_queue(tid,2)
        snap=s.snapshot(tid);assert snap['knockout']['champion']=='Engine 1' and snap['official_games']==4 and snap['complete_pairs']==2
        assert len(s.game_detail(data['gid'])['attempts'])==2
    finally:s.close()


@pytest.mark.parametrize('control',[{'kind':'nodes','nodes':77},{'kind':'fischer','seconds':3,'increment':.1}])
def test_runner_uses_saved_playoff_control_for_both_engines(tmp_path,control):
    from arena.runner import Database,Runner
    async def run():
        db=await Database().open(tmp_path);runner=Runner(db);log=tmp_path/'uci.log'
        engine={'path':sys.executable,'args':[str(Path(__file__).with_name('fault_engine.py')),'--transcript',str(log)],'threads':1,'hash':1,'time_control':{'kind':'nodes','nodes':11}}
        try:
            t=await db.call('create_tournament','Actual controls',[engine|{'name':'A'},engine|{'name':'B'}],config([2])|{'playoff_controls':[control],'max_plies':2})
            tid=t['id'];await db.call('set_state',tid,'running');await db.call('fill_queue',tid,2)
            while g:=await db.call('claim',tid):await db.call('finish',g['aid'],'1/2-1/2','fixture')
            await db.call('fill_queue',tid,2);g=await db.call('claim',tid)
            runner.live[g['aid']]={}
            await runner._game(g,await db.call('tournament',tid))
            attempt=(await db.call('game_detail',g['id']))['attempts'][0];clocks=json.loads(attempt['clocks'])
            assert attempt['reason']=='max_plies_adjudication',attempt['detail']
            assert all(c['control']['kind']==control['kind'] for c in clocks.values())
            commands=[v for v in log.read_text().splitlines() if v.startswith('go ')]
            assert len(commands)==2
            if control['kind']=='nodes':assert commands==['go nodes 77']*2
            else:assert all('wtime ' in v and 'winc 100' in v and 'nodes' not in v for v in commands)
        finally:await db.close()
    asyncio.run(run())
