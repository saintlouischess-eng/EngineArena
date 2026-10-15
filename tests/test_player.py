import asyncio
import io
import json
import sys
from pathlib import Path
import chess
import chess.pgn
import pytest
from arena.runner import Database, Runner
from arena.player import PlayerArena
from arena.uci import UciEngine


async def fixture(tmp_path,config=None):
    db=await Database().open(tmp_path);runner=Runner(db);player=PlayerArena(db,runner)
    profile=await db.call('save_profile',{'name':'Player test engine','path':sys.executable,'args':[str(Path(__file__).with_name('fault_engine.py'))],'hash':16,'threads':1})
    await player.start()
    await player.create({'name':'Test player','engine':profile['id'],'config':{'hash':16,**(config or {})}})
    return db,runner,player,profile


async def action(p,verb,**kwargs):return await p.action({'id':p.game['id'],'revision':p.game['revision'],'action':verb,**kwargs})


async def wait(p,condition):
    for _ in range(300):
        async with p.lock:
            if condition():return
        await asyncio.sleep(.01)
    raise AssertionError(p.view())


def test_real_uci_human_game_and_all_pgn_presets(tmp_path):
    async def run():
        db,r,p,_=await fixture(tmp_path)
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            assert 'player' in r.external_resources
            for _ in range(4):
                await action(p,'move',move=next(iter(p.board.legal_moves)).uci())
                await wait(p,lambda:p.board.turn==p.human or p.game['state']!='playing')
            assert len(p.game['moves'])==8
            await action(p,'resign');assert p.game['result']=='0-1';assert not r.external_resources
            for preset in ('clean','annotated','testing','archive'):
                text=await db.call('player_call','export',p.game['id'],{'preset':preset})
                game=chess.pgn.read_game(io.StringIO(text));assert not game.errors;assert len(list(game.mainline_moves()))==8
                assert game.headers['WhiteType']=='human';assert game.headers['Result']=='0-1'
                assert 'WhiteThreads' not in game.headers
            assert (tmp_path/'PlayerArena/PGN'/f'{p.game["id"]}.pgn').exists()
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_rating_idempotency_and_reset(tmp_path):
    async def run():
        db,r,p,_=await fixture(tmp_path,{'rated':True})
        try:
            await action(p,'resign');assert p.game['rating_change']['after']==1484
            await db.call('player_call','save',p.game,p.game['revision'])
            rows=(await db.call('player_call','overview'))['ratings'];assert rows[0]['games']==1
            await db.call('player_call','reset_ratings','Test player');assert not (await db.call('player_call','overview'))['ratings']
            await db.call('player_call','save',p.game,p.game['revision']+1)
            assert not (await db.call('player_call','overview'))['ratings']
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_pause_takeback_recovery_and_analysis(tmp_path):
    async def run():
        db,r,p,_=await fixture(tmp_path,{'rated':True})
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'analysis',enabled=True);assert not p.game['rated']
            await action(p,'move',move='e2e4');await wait(p,lambda:len(p.game['moves'])==2)
            await action(p,'takeback');await wait(p,lambda:p.game['state']=='playing')
            assert not p.game['moves'];assert len(p.game['variations'][0]['moves'])==2
            await action(p,'move',move='d2d4');await wait(p,lambda:len(p.game['moves'])==2)
            await action(p,'pause');assert p.game['state']=='paused';assert not r.external_resources
            committed=p.game['fen'];gid=p.game['id']
            # Simulate an unclean exit from the last committed playing checkpoint.
            g=await db.call('player_call','get',gid);g['state']='playing'
            await db.call('player_call','save',g,g['revision'])
            recovered=await db.call('player_call','recover')
            assert recovered['state']=='paused' and recovered['fen']==committed and recovered['result']=='*'
        finally:await p.close();await r.close()
    asyncio.run(run())


@pytest.mark.parametrize('fen,move,reason',[
    ('7k/P7/6K1/8/8/8/8/8 w - - 0 1','a7a8q','checkmate'),
    ('7k/P7/6K1/8/8/8/8/8 w - - 0 1','a7a8n','insufficient_material'),
])
def test_underpromotion_and_mate(tmp_path,fen,move,reason):
    async def run():
        db,r,p,_=await fixture(tmp_path,{'fen':fen})
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            assert len([m for m in p.view()['game']['legal'] if m['from']=='a7'])==4
            await action(p,'move',move=move);assert p.game['reason']==reason
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_series_colors_and_no_testing_contamination(tmp_path):
    async def run():
        db,r,p,profile=await fixture(tmp_path)
        try:
            await action(p,'abandon')
            series=await db.call('player_call','series',{'name':'Test player','engines':[profile['id']],'games_each':2})
            for side in ('white','black'):
                await p.create({},series['id']);assert p.game['config']['color']==side;await action(p,'resign')
            data=await db.call('player_call','overview');s=data['series'][0];assert s['played']==2 and s['complete']
            assert (await db.call('one','SELECT count(*) n FROM games'))['n']==0
            assert (await db.call('one','SELECT count(*) n FROM aggregates'))['n']==0
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_human_clock_and_resource_budget(tmp_path):
    async def run():
        db,r,p,_=await fixture(tmp_path,{'human_control':{'kind':'fischer','seconds':.12,'increment':0}})
        try:
            r.external_resources['test']={'resource_cost':{'threads':100000,'memory_mb':0,'gpu':{}}}
            with pytest.raises(ValueError,match='resources'):await action(p,'resume')
            r.external_resources.clear();await action(p,'resume');await wait(p,lambda:p.game['state']=='completed')
            assert p.game['result']=='0-1' and p.game['reason']=='timeout'
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_stale_and_illegal_moves_do_not_mutate(tmp_path):
    async def run():
        db,r,p,_=await fixture(tmp_path)
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            revision=p.game['revision']
            with pytest.raises(ValueError):await action(p,'move',move='e2e5')
            assert not p.game['moves'] and p.game['revision']==revision
            with pytest.raises(ValueError,match='changed'):await p.action({'id':p.game['id'],'revision':-1,'action':'resign'})
        finally:await p.close();await r.close()
    asyncio.run(run())


@pytest.mark.parametrize('policy,cp,depth,expected',[('balanced',12,12,'completed'),('balanced',80,18,'playing'),('balanced',0,4,'playing'),('always',500,1,'completed')])
def test_draw_offer_is_decided_by_explicit_policy(tmp_path,monkeypatch,policy,cp,depth,expected):
    async def run():
        async def reply(engine,board,command,budget):return next(iter(board.legal_moves)),.001,{'cp':cp,'depth':depth,'score_bound':'exact'}
        monkeypatch.setattr(UciEngine,'play',reply)
        fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 22'
        db,r,p,_=await fixture(tmp_path,{'fen':fen,'draw_policy':policy})
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'offer_draw');assert p.game['draw_offer']
            await action(p,'move',move='e2e4');await wait(p,lambda:p.game['state']=='completed' or len(p.game['moves'])==2)
            assert p.game['state']==expected
            if expected=='completed':assert p.game['result']=='1/2-1/2' and p.game['reason']=='draw_agreement'
            else:assert not p.game['draw_offer']
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_special_moves_and_draw_claim(tmp_path):
    async def run():
        db,r,p,profile=await fixture(tmp_path,{'fen':'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1'})
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'move',move='e1g1');assert p.game['moves'][0]['san']=='O-O';await action(p,'abandon')
            await p.create({'name':'Test','engine':profile['id'],'config':{'fen':'4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1'}})
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing');await action(p,'move',move='e5d6')
            assert p.game['moves'][0]['capture'];assert p.marks.captured==['p'];await action(p,'abandon')
            await p.create({'name':'Test','engine':profile['id'],'config':{'fen':'4k2r/8/8/8/8/8/8/R3K3 w - - 100 51'}})
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing');assert p.view()['game']['claim_draw']
            await action(p,'claim_draw');assert p.game['result']=='1/2-1/2' and p.game['reason']=='draw_claim'
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_additional_pgn_failure_is_visible_and_retryable(tmp_path):
    async def run():
        db,r,p,_=await fixture(tmp_path)
        try:
            target=tmp_path/'extra';target.mkdir();await db.call('player_call','settings',{'pgn_folder':str(target)})
            # A file standing in for the folder makes the selected destination unwritable.
            target.rmdir();target.write_text('blocked')
            await action(p,'resign');assert p.game['state']=='completed'
            assert (await db.call('player_call','overview'))['export_error']
            target.unlink();target.mkdir();assert not (await db.call('player_call','retry_exports'))['error_message']
            assert len(list(target.glob('*.pgn')))==1
            await db.call('player_call','retry_exports');assert len(list(target.glob('*.pgn')))==1
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_node_engine_untimed_human_and_chess960_castling(tmp_path):
    async def run():
        db,r,p,profile=await fixture(tmp_path,{'untimed':True,'engine_control':{'kind':'nodes','nodes':1234}})
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing');await action(p,'move',move='e2e4');await wait(p,lambda:len(p.game['moves'])==2)
            assert '> go nodes 1234' in p.engine.log
            assert p.game['clocks']['white']['remaining'] is None
            text=await db.call('player_call','export',p.game['id'],{'preset':'clean'});game=chess.pgn.read_game(io.StringIO(text))
            assert game.headers['WhiteTimeControl']=='-' and game.headers['BlackSearchControl'].startswith('1234 nodes')
            await action(p,'abandon')
            await p.create({'engine':profile['id'],'config':{'chess960':True,'fen':'4k3/8/8/8/8/8/8/R5KR w AH - 0 1'}})
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            legal=p.view()['game']['legal'];assert any(m['uci']=='g1h1' and m['to']=='h1' for m in legal)
            await action(p,'move',move='g1h1');assert p.game['moves'][0]['san']=='O-O';assert p.board.piece_at(chess.F1)==chess.Piece(chess.ROOK,chess.WHITE)
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_real_stockfish_game_finishes_by_chess_rules(tmp_path):
    stockfish=Path(__file__).resolve().parents[1]/'validation-engines/stockfish/stockfish/stockfish-windows-x86-64-universal.exe'
    if not stockfish.exists():pytest.skip('Local validation engine is unavailable')
    async def run():
        import random
        db=await Database().open(tmp_path);r=Runner(db);p=PlayerArena(db,r);await p.start()
        try:
            profile=await db.call('save_profile',{'name':'Stockfish validation','path':str(stockfish),'threads':1,'hash':16})
            await p.create({'engine':profile['id'],'config':{'hash':16,'untimed':True,'engine_control':{'kind':'nodes','nodes':2000}}})
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing');rng=random.Random(1849)
            for _ in range(500):
                if p.game['state']=='completed':break
                await action(p,'move',move=rng.choice(list(p.board.legal_moves)).uci())
                await wait(p,lambda:p.board.turn==p.human or p.game['state']!='playing')
                assert p.game['state']!='paused',p.game['note']
            assert p.game['state']=='completed' and p.game['reason'] in ('checkmate','stalemate','insufficient_material','fivefold_repetition','seventyfive_moves','draw_claim')
            text=await db.call('player_call','export',p.game['id'],{'preset':'archive'});game=chess.pgn.read_game(io.StringIO(text));assert not game.errors
            assert len(list(game.mainline_moves()))==len(p.game['moves']);assert game.headers['BlackEngine'].startswith('Stockfish')
            print('Real Stockfish result:',p.game['result'],p.game['reason'],'plies',len(p.game['moves']))
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_failed_move_save_restores_committed_position(tmp_path,monkeypatch):
    async def run():
        db,r,p,_=await fixture(tmp_path)
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            original=db.call
            async def failing(method,*args):
                if method=='player_call' and args[0]=='save':raise OSError('Injected disk failure')
                return await original(method,*args)
            monkeypatch.setattr(db,'call',failing)
            with pytest.raises(OSError):await action(p,'move',move='e2e4')
            assert p.board.fen()==chess.STARTING_FEN and not p.game['moves']
            assert p.game['state']=='paused' and p.game['result']=='*'
            assert 'saving failed' in p.error and not r.external_resources
            monkeypatch.setattr(db,'call',original)
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'move',move='e2e4');await wait(p,lambda:len(p.game['moves'])==2)
            assert not p.error
        finally:await p.close();await r.close()
    asyncio.run(run())
