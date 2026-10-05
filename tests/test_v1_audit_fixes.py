import asyncio
import json

import chess
import pytest

from arena.uci import UciEngine,EngineFailure
from arena.store import DEFAULTS,Store
from arena.telemetry import clean
from arena.resources import game_cost
from arena.report_evidence import configured_option,observation_rows
from arena.log_storage import read,pack_completed
from arena.standings import read_snapshot


@pytest.mark.parametrize('reply,clocked,expected', [(.019,True,None),(.021,True,'timeout'),(.021,False,'hang'),(None,True,'timeout')])
def test_early_event_loop_wakeup_does_not_cancel_search(monkeypatch,reply,clocked,expected):
    async def run():
        tick=[100.0];wakeups=[]
        monkeypatch.setattr('arena.uci.time.perf_counter',lambda:tick[0])
        async def send(engine,command):pass
        async def wait(futures,timeout):
            f=next(iter(futures));assert not f.cancelled()
            wakeups.append(timeout);tick[0]+=.004
            if len(wakeups)==3:
                tick[0]=100.021
                if reply is not None:f.set_result(('e2e4',100+reply,None))
            return ({f},set()) if f.done() else (set(),{f})
        monkeypatch.setattr(UciEngine,'send',send);monkeypatch.setattr('arena.uci.asyncio.wait',wait)
        e=UciEngine({},DEFAULTS|{'hang_timeout':.02,'tolerance':0})
        if expected:
            with pytest.raises(EngineFailure) as exc:await e.play(chess.Board(),'go nodes 100',.02 if clocked else None)
            assert exc.value.reason==expected and 'allowance 0.020000s' in str(exc.value)
        else:
            move,elapsed,_=await e.play(chess.Board(),'go nodes 100',.02)
            assert move.uci()=='e2e4' and elapsed==pytest.approx(.019)
        assert len(wakeups)==3 and not e.search.cancelled()
    asyncio.run(run())


def test_invalid_telemetry_has_no_fabricated_replacement():
    raw={'nps':-123,'nodes':12345,'time':0,'hashfull':1001,'cp':-91,'pv':'e2e4 e7e5 hashfull 1001 nps -123'}
    data=clean(raw,.9)
    assert data['nodes']==12345 and data['cp']==-91 and data['pv']=='e2e4 e7e5'
    assert not {'nps','time','hashfull'} & data.keys()
    assert set(data['invalid_metrics'])=={'nps','time','hashfull'}
    assert raw['nps']==-123 and clean({'time':0},.0001)=={'time':0}
    engine=UciEngine({},DEFAULTS)
    engine._info('info nps 100 nodes 10');engine._info('info nps -1 nodes 20')
    assert 'nps' not in engine.last_info
    engine._info('info nps 200 nodes 40')
    assert engine.last_info['nps']==200 and 'nps' not in engine.last_info.get('invalid_metrics',{})


@pytest.mark.parametrize('alias',['Threads','Number of Threads','MaxThreads','Max CPUs'])
def test_thread_alias_reports_and_budget_agree(alias):
    p={'threads':1,'options':{alias:6},'advertised':{alias:{'default':1}}}
    assert game_cost(p,p)['threads']==6 and game_cost(p,p,True)['threads']==12
    assert configured_option(p,'Threads')==6
    rows=observation_rows({'observed':[{'options':{alias:6}}],'legacy':False,'truncated':False})
    assert any(label=='Observed search threads' and str(value).startswith('6') for label,value in rows)
    assert game_cost({'options':{'CPU Usage':100}},p)['threads']==6


def test_completed_logs_pack_losslessly_and_restart(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('packing',[{'name':'A'},{'name':'B'}],{'cycles':1},backup=False)
        s.set_state(t['id'],'running');s.fill_queue(t['id'],2);g=s.claim(t['id'])
        for i in range(60):s.log(g['aid'],['info depth '+str(j)+' pv '+('e2e4 e7e5 '*12)+str(i) for j in range(30)])
        before=read(s.db,g['aid'],10000,False);old=s.one('SELECT sum(length(body)) n FROM log_blocks')['n']
        s.finish(g['aid'],'1-0','fixture')
        assert read(s.db,g['aid'],10000,False)==before
        assert s.one('SELECT sum(length(body)) n FROM log_blocks')['n']<old*.75
        # Later appended evidence must invalidate the per-attempt packing cursor.
        s.log(g['aid'],['late preserved evidence']);before=read(s.db,g['aid'],10000,False)
        pack_completed(s.db,transaction=s.tx)
        assert read(s.db,g['aid'],10000,False)==before
        assert read(s.db,g['aid'],300)==before[-300:][::-1]
        s.set_state(t['id'],'paused')
    finally:s.close()
    s=Store(tmp_path)
    try:assert read(s.db,g['aid'],10000,False)==before
    finally:s.close()


def test_compact_snapshot_omits_inventory_but_keeps_setup_and_statistics(tmp_path):
    s=Store(tmp_path)
    try:
        items=[{'fen':chess.STARTING_FEN,'name':'Opening '+str(i)+' '+('x'*100)} for i in range(3000)]
        t=s.create_tournament('large book',[{'name':'A'},{'name':'B'}],{},items,backup=False)
        compact=read_snapshot(s.path,t['id'],compact=True);full=read_snapshot(s.path,t['id'])
        assert compact['opening_count']==3000 and 'openings' not in compact['settings']
        assert compact['standings']==full['standings']
        assert full['settings']['openings']==items
        assert len(json.dumps(compact))<len(json.dumps(full))*.05
    finally:s.close()


def test_packing_failure_rolls_back_logs_and_official_result(tmp_path):
    from arena.store import SavingError
    s=Store(tmp_path)
    try:
        t=s.create_tournament('rollback',[{'name':'A'},{'name':'B'}],{},backup=False)
        s.set_state(t['id'],'running');s.fill_queue(t['id'],2);g=s.claim(t['id']);s.log(g['aid'],['original evidence'])
        before=read(s.db,g['aid'])
        s.db.execute("CREATE TRIGGER reject_packing BEFORE INSERT ON log_packing BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(SavingError):s.finish(g['aid'],'1-0','fixture')
        assert read(s.db,g['aid'])==before
        assert not s.one('SELECT ended FROM attempts WHERE id=?',(g['aid'],))['ended']
        assert not s.one('SELECT official FROM games WHERE id=?',(g['id'],))['official']
        s.db.execute('DROP TRIGGER reject_packing');s.failure='';s.finish(g['aid'],'1-0','fixture')
        s.set_state(t['id'],'paused')
    finally:s.close()


def test_historical_invalid_metrics_are_filtered_from_exports_and_replay(tmp_path):
    from test_pgn_readable import make_game
    from arena.trends import game_series
    s=Store(tmp_path)
    try:
        t,g=make_game(s,{'fen':chess.STARTING_FEN})
        # Model already-recorded engine overflow, not sanitized by the new reader.
        s.execute("UPDATE moves SET info=json_set(info,'$.nps',-999,'$.time',0) WHERE aid=?",(g['aid'],))
        pgn=s.export_official(t['id'],export_options={'preset':'archive','annotations':['nps','nodes','elapsed']})
        assert '[%nps -999]' not in pgn and '[%nodes ' in pgn
        detail=s.game_detail(g['id'])
        assert all('nps' not in json.loads(m['info']) for m in detail['attempts'][0]['moves'])
        series=game_series(s.path,t['id'],g['number']+1)
        assert all('nps' not in point for point in series['points'])
        assert all(json.loads(r['info'])['nps']==-999 for r in s.rows('SELECT info FROM moves WHERE aid=?',(g['aid'],)))
    finally:s.close()
