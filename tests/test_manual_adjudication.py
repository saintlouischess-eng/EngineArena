import asyncio
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import chess
import chess.pgn
import pytest

from arena.runner import Database,Runner
from arena.store import Store
from test_core import profile


def setup_game(store):
    t=store.create_tournament('Manual decision',[{'name':'White'},{'name':'Black'}],{'cycles':1,'retry_limit':2,'retry_reasons':['manual_adjudication']})
    store.set_state(t['id'],'running');store.fill_queue(t['id'],2)
    return t,store.claim(t['id'])


@pytest.mark.parametrize('result',['1-0','1/2-1/2','0-1'])
def test_manual_decision_is_attempt_specific_idempotent_and_pair_safe(tmp_path,result):
    s=Store(tmp_path)
    try:
        t,g=setup_game(s)
        for bad in ('*','White',None):
            with pytest.raises(ValueError):s.request_adjudication(t['id'],g['id'],g['aid'],bad,'Reason')
        with pytest.raises(ValueError):s.request_adjudication(t['id'],g['id'],g['aid'],result,' ')
        with pytest.raises(ValueError):s.request_adjudication(t['id'],g['id'],'stale-attempt',result,'Reason')
        with pytest.raises(ValueError):s.request_adjudication('wrong-tournament',g['id'],g['aid'],result,'Reason')
        for _ in range(2):s.request_adjudication(t['id'],g['id'],g['aid'],result,'Manual test reason')
        # An in-flight engine result cannot overwrite the already committed decision.
        s.finish(g['aid'],'0-1','timeout');s.finish(g['aid'],'1-0','checkmate')
        snap=s.snapshot(t['id']);assert snap['official_games']==1 and snap['complete_pairs']==0
        a=s.game_detail(g['id'])['attempts'][0]
        assert (a['result'],a['reason'],a['detail'])==(result,'manual_adjudication','Manual test reason')
        with pytest.raises(ValueError):s.request_adjudication(t['id'],g['id'],g['aid'],result,'Too late')
        other=s.claim(t['id']);s.finish(other['aid'],'1/2-1/2','fixture')
        assert s.snapshot(t['id'])['complete_pairs']==1
        assert s.one("SELECT count(*) n FROM audit WHERE action='manual_adjudication_requested'")['n']==1
        s.export_pending();text=(tmp_path/'games.pgn').read_text(encoding='utf-8')
        parsed=chess.pgn.read_game(io.StringIO(text));assert not parsed.errors
        assert parsed.headers['Result']==result and parsed.headers['Termination']=='adjudication'
        assert parsed.headers['TerminationDetails']=='manual adjudication: Manual test reason'
    finally:s.close()


def test_diagnostic_and_replacement_manual_decisions_preserve_attempts(tmp_path):
    s=Store(tmp_path)
    try:
        t,g=setup_game(s);s.finish(g['aid'],'1-0','fixture')
        other=s.claim(t['id']);s.finish(other['aid'],'0-1','fixture')
        original=s.snapshot(t['id'])['standings'][0]
        for mode in ('diagnostic','replacement'):
            s.set_state(t['id'],'paused');s.requeue(t['id'],[g['id']],mode=mode);s.set_state(t['id'],'running')
            replay=s.claim(t['id']);s.request_adjudication(t['id'],g['id'],replay['aid'],'0-1',mode+' review')
            s.finish(replay['aid'],'*','interrupted')
            snap=s.snapshot(t['id']);assert snap['official_games']==2 and snap['complete_pairs']==1
            if mode=='diagnostic':assert snap['standings'][0]==original
            else:assert s.game_detail(g['id'])['official']==replay['aid']
        assert len(s.game_detail(g['id'])['attempts'])==3
        aggregate=s.one('SELECT * FROM aggregates WHERE tid=? AND a=0 AND b=-1',(t['id'],))
        assert aggregate['w']==1 and aggregate['l']==1 and aggregate['p2']==1 and aggregate['p4']==0
    finally:s.close()


def test_committed_manual_request_survives_forced_process_termination(tmp_path):
    root=Path(__file__).resolve().parents[1];ready=tmp_path/'ready.json';data=tmp_path/'data'
    script=tmp_path/'crash.py'
    script.write_text("""import json,sys,time
import chess
from pathlib import Path
from arena.store import Store
s=Store(sys.argv[1]);t=s.create_tournament('Crash decision',[{'name':'A'},{'name':'B'}],{'cycles':1})
s.set_state(t['id'],'running');s.fill_queue(t['id'],2);g=s.claim(t['id'])
b=chess.Board();b.push_uci('e2e4');s.move(g['aid'],1,'e2e4','e4',b.fen(),.2,{}, {})
s.request_adjudication(t['id'],g['id'],g['aid'],'1/2-1/2','Decision before forced termination')
Path(sys.argv[2]).write_text(json.dumps({'tid':t['id'],'gid':g['id']}))
time.sleep(120)
""",encoding='utf-8')
    p=subprocess.Popen([sys.executable,str(script),str(data),str(ready)],env=os.environ|{'PYTHONPATH':str(root)},creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    try:
        deadline=time.monotonic()+15
        while not ready.exists() and time.monotonic()<deadline:time.sleep(.02)
        assert ready.exists();p.kill();p.wait(timeout=5)
    finally:
        if p.poll() is None:p.kill();p.wait()
    ids=json.loads(ready.read_text());s=Store(data)
    try:
        g=s.game_detail(ids['gid']);assert g['state']=='completed' and len(g['attempts'])==1
        a=g['attempts'][0];assert a['reason']=='manual_adjudication' and a['result']=='1/2-1/2' and len(a['moves'])==1
        assert s.snapshot(ids['tid'])['official_games']==1
        parsed=chess.pgn.read_game(io.StringIO((data/'games.pgn').read_text(encoding='utf-8')))
        assert not parsed.errors and len(list(parsed.mainline_moves()))==1
    finally:s.close()
    s=Store(data)
    try:assert s.snapshot(ids['tid'])['official_games']==1 and s.one('SELECT count(*) n FROM outbox')['n']==1
    finally:s.close()


def test_live_adjudication_stops_only_selected_game_and_freezes_clock(tmp_path):
    async def run():
        db=await Database().open(tmp_path);r=Runner(db)
        try:
            t=await db.call('create_tournament','Live manual',[profile('A',wait=.12),profile('B',wait=.12)],{'cycles':1,'concurrency':2,'max_plies':12,'stop_timeout':.1,'time_control':{'kind':'fischer','seconds':60,'increment':2}})
            await db.call('set_state',t['id'],'running');await r.start()
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                eligible=[(a,v) for a,v in r.live.items() if v.get('ply',0)>=2 and 'thinking' in v['status']]
                if eligible:break
                assert not r.error;await asyncio.sleep(.01)
            assert eligible;aid,view=eligible[0];gid=view['game']
            response=await r.adjudicate(t['id'],gid,aid,'1/2-1/2','Live test decision')
            assert response['reason']=='manual_adjudication' and aid not in r.tasks
            g=await db.call('game_detail',gid);a=g['attempts'][-1]
            assert len(a['moves'])>=2 and a['result']=='1/2-1/2'
            clocks=json.loads(a['clocks']);assert all(50<c['remaining']<80 for c in clocks.values())
            while time.monotonic()<deadline:
                snap=await db.call('snapshot',t['id'])
                if snap['state']=='completed':break
                assert not r.error;await asyncio.sleep(.05)
            assert snap['official_games']==2 and snap['complete_pairs']==1
            reasons={g['reason'] for g in (await db.call('games',t['id']))['items']}
            assert reasons=={'manual_adjudication','max_plies_adjudication'}
            with pytest.raises(ValueError):await r.adjudicate(t['id'],gid,aid,'1-0','Stale click')
        finally:await r.close()
    asyncio.run(run())
