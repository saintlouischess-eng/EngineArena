import asyncio
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import chess
import chess.pgn
import pytest
from arena.models import Clock,TimeControl,go_command,scheduled_pairs,static_pair
from arena.store import Store,DEFAULTS
from arena.stats import summarize,sprt_llr
from arena.uci import UciEngine,EngineFailure,parse_option
from arena.runner import Database,Runner

ROOT=Path(__file__).resolve().parent.parent
FIXTURE=ROOT/'tests'/'fault_engine.py'
def profile(name='Fixture',mode='normal',wait=0,extra=None):
    return {'id':name,'name':name,'path':sys.executable,'args':[str(FIXTURE),'--mode',mode,'--wait',str(wait)]+(extra or []),'threads':1,'hash':1}

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path)
    yield s
    s.close()

def tournament(s,settings=None,n=2):
    return s.create_tournament('Acceptance',[profile(str(i)) for i in range(n)],{'format':'match' if n==2 else 'round_robin','cycles':2,**(settings or {})})

def run_claim(s,t):
    s.set_state(t['id'],'running');s.fill_queue(t['id'],4);return s.claim(t['id'])

def read_pgn(text):
    f=io.StringIO(text);games=[]
    while g:=chess.pgn.read_game(f):
        assert not g.errors;games.append(g)
    return games

def test_no_participant_cap_and_incremental_schedule(store):
    start=time.perf_counter();t=tournament(store,{'cycles':1,'concurrency':32},10000)
    assert t['total']==99_990_000
    store.set_state(t['id'],'running');store.fill_queue(t['id'],64)
    assert store.db.execute('SELECT count(*) FROM participants').fetchone()[0]==10000
    assert store.db.execute('SELECT count(*) FROM games').fetchone()[0]==64
    assert t['total']>1000000
    assert time.perf_counter()-start<30

def test_round_robin_pair_decoder():
    for n in range(2,31):
        pairs=[static_pair(i,n,'round_robin',1)[:2] for i in range(n*(n-1)//2)]
        assert len(set(pairs))==len(pairs);assert set(pairs)=={(a,b) for a in range(n) for b in range(a+1,n)}

def test_node_only_command_is_pure():
    a=Clock(TimeControl.parse({'kind':'nodes','nodes':987654321}));b=Clock(TimeControl.parse({'seconds':3,'increment':1}))
    assert go_command(a,a,b)=='go nodes 987654321';assert a.budget is None
    a.consume(100000);assert a.snapshot()['remaining'] is None

def test_clock_boundaries():
    for kind in ('delay','bronstein'):
        c=Clock(TimeControl.parse({'kind':kind,'seconds':10,'delay':2}));assert c.budget==12;c.consume(1);assert c.remaining==10;c.consume(4);assert c.remaining==8
    c=Clock(TimeControl.parse({'kind':'fischer','seconds':10,'increment':2}));c.consume(3);assert c.remaining==9
    c=Clock(TimeControl.parse({'kind':'staged','stages':[{'moves':2,'seconds':10,'increment':1},{'moves':2,'seconds':5,'increment':0}],'repeat':True}))
    c.consume(2);assert c.moves_to_go==1;c.consume(2);assert c.remaining==13 and c.stage==1
    c.consume(1);c.consume(1);assert c.remaining==16 and c.moves_to_go==2
    assert 'movestogo 2' in go_command(c,c,c)

def test_options_all_types():
    assert parse_option('option name Name With Spaces type combo default Very Calm var Normal var Very Calm')['var']==['Normal','Very Calm']
    assert parse_option('option name Flag type check default false')['default'] is False
    assert parse_option('option name Network File type string default <empty>')['default']==''

def test_replacement_diagnostic_paired_accounting(store):
    t=tournament(store);g0=run_claim(store,t);g1=store.claim(t['id'])
    store.finish(g0['aid'],'0-1','timeout');assert store.snapshot(t['id'])['standings'][0]['pairs']==0
    store.finish(g1['aid'],'1/2-1/2','stalemate')
    h=store.h2h(t['id'],0)[0];assert (h['wins'],h['draws'],h['losses'])==(0,1,1);assert h['pentanomial']==[0,1,0,0,0]
    store.set_state(t['id'],'paused');store.requeue(t['id'],[g0['id']],mode='diagnostic');store.set_state(t['id'],'running')
    diag=store.claim(t['id']);assert diag['id']==g0['id'];store.finish(diag['aid'],'1-0','checkmate')
    assert store.h2h(t['id'],0)[0]['pentanomial']==[0,1,0,0,0]
    store.set_state(t['id'],'paused');store.requeue(t['id'],[g0['id']],mode='replacement');store.set_state(t['id'],'running')
    replay=store.claim(t['id']);store.finish(replay['aid'],'1-0','checkmate')
    h=store.h2h(t['id'],0)[0];assert (h['wins'],h['draws'],h['losses'])==(1,1,0);assert h['pentanomial']==[0,0,0,1,0]
    assert len(store.game_detail(g0['id'])['attempts'])==3
    assert len(read_pgn(store.export_official(t['id'])))==2

def test_pgn_tail_repair_and_headers(store):
    t=tournament(store);g=run_claim(store,t);board=chess.Board();board.push_uci('e2e4')
    clocks={c:{'remaining':179,'stage':0,'moves':1} for c in ('white','black')}
    store.move(g['aid'],1,'e2e4','e4',board.fen(),1,clocks,{'cp':23,'depth':12,'nodes':10000})
    store.finish(g['aid'],'1-0','crash');store.export_pending();path=store.folder/'games.pgn';before=path.read_bytes()
    with path.open('ab') as f:f.write(b'[Event "incomplete write')
    store.export_pending();assert path.read_bytes()==before
    store.export_pending();assert path.read_bytes()==before
    games=read_pgn(before.decode());assert len(games)==1
    for tag in ('WhiteEngine','BlackEngine','Opening','OpeningSeed','TimeControl','WhiteThreads','GameId','AttemptId','Termination'):assert tag in games[0].headers
    assert list(games[0].mainline_moves())==[chess.Move.from_uci('e2e4')]
    assert games[0].end().comment=='+0.23/12 1s'
    archive=read_pgn(store.export_official(t['id'],style='archive'))[0]
    assert archive.end().eval().white().score()==23
    for tag in ('TournamentSettings','WhiteSettings','BlackSettings'):assert tag in archive.headers

def test_forced_termination_recovery(tmp_path):
    data=tmp_path/'crash';data.mkdir();signal=tmp_path/'signal'
    script=tmp_path/'kill_target.py'
    script.write_text('''import sys,os,time,json\nfrom pathlib import Path\nfrom arena.store import Store\nimport chess\ns=Store(sys.argv[1])\np=[{'id':str(i),'name':str(i),'path':sys.executable} for i in range(2)]\nt=s.create_tournament('Forced crash',p,{'cycles':2})\ns.set_state(t['id'],'running');s.fill_queue(t['id'],4)\ng=s.claim(t['id']);s.finish(g['aid'],'1-0','checkmate');s.export_pending()\nr=s.claim(t['id']);b=chess.Board();b.push_uci('e2e4');s.move(r['aid'],1,'e2e4','e4',b.fen(),.1,{'white':{'remaining':1},'black':{'remaining':1}}, {})\nPath(sys.argv[2]).write_text(json.dumps({'tid':t['id'],'running':r,'completed':g}))\ns.db.execute('BEGIN IMMEDIATE');s.db.execute("UPDATE tournaments SET name='UNCOMMITTED'")\ntime.sleep(120)\n''',encoding='utf-8')
    env=os.environ|{'PYTHONPATH':str(ROOT)}
    p=subprocess.Popen([sys.executable,str(script),str(data),str(signal)],env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    try:
        deadline=time.time()+20
        while not signal.exists() and time.time()<deadline:time.sleep(.05)
        assert signal.exists();p.kill();p.wait(timeout=10)
    finally:
        if p.poll() is None:p.kill();p.wait()
    info=json.loads(signal.read_text());s=Store(data)
    try:
        t=s.tournament(info['tid']);assert t['name']=='Forced crash';assert t['state']=='paused'
        assert s.snapshot(t['id'])['official_games']==1
        running=s.game_detail(info['running']['id']);assert running['state']=='pending';assert running['attempts'][0]['reason']=='interrupted';assert len(running['attempts'][0]['moves'])==1
        assert len(read_pgn((data/'games.pgn').read_text()))==1;assert len(read_pgn((data/'interrupted.pgn').read_text()))==1
        s.set_state(t['id'],'running');g=s.claim(t['id']);assert g['id']==running['id'];assert g['opening']['fen']==chess.STARTING_FEN;assert g['seq']==2
        s.finish(g['aid'],'1/2-1/2','stalemate');s.export_pending();assert s.snapshot(t['id'])['official_games']==2
    finally:s.close()

def test_rotating_backups_and_corrupt_restore(tmp_path):
    s=Store(tmp_path);t=tournament(s)
    for _ in range(7):s.backup()
    assert len(list((tmp_path/'backups').glob('recovery-*')))==5;s.close()
    (tmp_path/'arena.sqlite3').write_bytes(b'forced corruption')
    s=Store(tmp_path)
    try:assert s.tournament(t['id'])['total']==4;assert 'Restored verified backup' in s.warning;assert list(tmp_path.glob('*.damaged-*'))
    finally:s.close()

def test_stats_independent_fixture():
    s=summarize(60,20,20,[2,3,10,20,15]);mean=(3*.25+10*.5+20*.75+15)/50
    assert abs(s['elo']-400*math.log10(mean/(1-mean)))<1e-9
    assert s['score_pct']==70;assert s['draw_pct']==20;assert s['ci95'][0]<s['elo']<s['ci95'][1];assert 50<s['los']<100
    assert summarize(0,0,0)['elo'] is None;assert summarize(20,0,0)['ci95'] is None
    assert sprt_llr([0,0,0,0,10000],0,5)['decision']=='H1'
    assert sprt_llr([10000,0,0,0,0],0,5)['decision']=='H0'

@pytest.mark.parametrize('mode,reason,tc',[('crash','crash',{'kind':'nodes'}),('illegal','illegal_move',{'kind':'nodes'}),('hang','hang',{'kind':'nodes'}),('timeout','timeout',{'kind':'sudden_death','seconds':.05}),('startup','startup_timeout',{'kind':'nodes'}),('readiness','readiness_timeout',{'kind':'nodes'})])
def test_uci_failure_classifications(mode,reason,tc):
    async def run():
        s=DEFAULTS|{'startup_timeout':.7,'readiness_timeout':.3,'hang_timeout':.4,'stop_timeout':.1,'tolerance':.01};e=UciEngine(profile(mode,mode),s)
        try:
            with pytest.raises(EngineFailure) as exc:
                await e.start();c=Clock(TimeControl.parse(tc));await e.play(chess.Board(),go_command(c,c,c),c.budget)
            assert exc.value.reason==reason
        finally:await e.close()
    asyncio.run(run())

def test_node_only_tournament_32_concurrent(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            t=await db.call('create_tournament','32 concurrent pure node games',[profile('A','strict_nodes',.015),profile('B','strict_nodes',.015)],{'cycles':32,'concurrency':32,'time_control':{'kind':'nodes','nodes':100},'max_plies':8,'stop_timeout':.2})
            await db.call('set_state',t['id'],'running');await r.start();deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                s=await db.call('snapshot',t['id'])
                if s['state']=='completed':break
                if r.error:raise AssertionError(r.error)
                await asyncio.sleep(.1)
            assert s['state']=='completed';assert s['official_games']==64;assert r.max_active==32
            assert {x['reason'] for x in (await db.call('games',t['id']))['items']}=={'max_plies_adjudication'}
            games=read_pgn((tmp_path/'games.pgn').read_text(encoding='utf-8'));assert len(games)==64;assert all(len(list(g.mainline_moves()))==8 for g in games)
            assert all(g.end().clock() is None for g in games)
            assert s['standings'][0]['pairs']==32
        finally:await r.close()
    asyncio.run(run())

def test_automatic_retry_preserves_failure(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            p=profile('Once','crash_once',extra=['--marker',str(tmp_path/'marker')]);t=await db.call('create_tournament','Retry',[p,profile('Other')],{'cycles':1,'paired':False,'retry_limit':1,'concurrency':1,'time_control':{'kind':'nodes','nodes':100},'max_plies':4,'stop_timeout':.1})
            await db.call('set_state',t['id'],'running');await r.start();deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                s=await db.call('snapshot',t['id'])
                if s['state']=='completed':break
                if r.error:raise AssertionError(r.error)
                await asyncio.sleep(.1)
            assert s['state']=='completed';games=await db.call('games',t['id']);detail=await db.call('game_detail',games['items'][0]['id'])
            assert len(detail['attempts'])==2;assert detail['attempts'][0]['reason']=='crash';assert detail['attempts'][1]['mode']=='automatic';assert s['standings'][0]['draws']==1
        finally:await r.close()
    asyncio.run(run())
