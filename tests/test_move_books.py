import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

import chess
import chess.pgn
import pytest

from arena.move_books import compile_book,choose,key,validate
from arena.runner import Database,Runner
from arena.store import Store
from arena.engine_readout import collect
from arena.tournament_report import render
from test_core import profile
from test_engine_readout import displayed,sessions


def import_book(store,path,text=None):
    if text is not None:path.write_text(text,encoding='utf-8')
    compiled=compile_book(path)
    try:return store.install_move_book(compiled)|{'policy':'weighted','max_plies':16}
    finally:Path(compiled['path']).unlink()


def test_pgn_transpositions_weights_validation_and_dedup(tmp_path):
    with contextlib.closing(Store(tmp_path/'data')) as s:
        path=tmp_path/'book.pgn'
        b=import_book(s,path,'1. e4 e5 2. Nf3 Nc6 *\n\n1. e4 c5 *\n\n1. d4 d5 *')
        assert b['games']==3 and b['positions']==5
        assert s.book_candidates(b['id'],key(chess.Board()))==[{'uci':'d2d4','weight':1},{'uci':'e2e4','weight':2}]
        assert import_book(s,path)['id']==b['id']
        assert s.one('SELECT count(*) n FROM move_books')['n']==1
        assert choose(chess.Board(),s.book_candidates(b['id'],key(chess.Board())),b|{'policy':'best'},1).uci()=='e2e4'
        saved=s.save_profile(profile()|{'move_book':b|{'name':'forged'}})
        assert saved['move_book']['name']=='book.pgn'
        with pytest.raises(ValueError):validate(s,b|{'id':'missing'})
        with pytest.raises(ValueError):validate(s,b|{'max_plies':-.1})
        with pytest.raises(ValueError):import_book(s,path,'[Event "No moves"]\n\n*')
        with pytest.raises(ValueError):import_book(s,path,'1. e5 *')
        path.write_bytes('[Event "Café"]\n\n1. e4 *'.encode('latin-1'))
        assert import_book(s,path)['moves']==1


def test_polyglot_castling_and_illegal_entries(tmp_path):
    board=chess.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
    raw=(chess.E1<<6)|chess.H1
    source=tmp_path/'castle.bin';source.write_bytes(struct.pack('>QHHI',int(key(board),16),raw,8,0))
    with contextlib.closing(Store(tmp_path/'data')) as s:
        b=import_book(s,source);rows=s.book_candidates(b['id'],key(board))
        assert choose(board,rows,b,1)==chess.Move.from_uci('e1g1')
        assert choose(board,[{'uci':'a1a8','weight':0},{'uci':'e1e8','weight':5}],b,1) is None
        source.write_bytes(b'x')
        with pytest.raises(ValueError,match='incomplete'):compile_book(source)


@pytest.mark.parametrize('control',[{'kind':'nodes','nodes':321},{'kind':'fischer','seconds':30,'increment':.05},{'kind':'staged','stages':[{'moves':1,'seconds':30,'increment':1},{'moves':0,'seconds':10,'increment':2}]}])
def test_each_profile_book_moves_fallback_clocks_pgn_and_readout(tmp_path,control):
    async def run():
        db=await Database().open(tmp_path/'data');r=Runner(db)
        try:
            # A chooses e4 as White; B chooses c5 as Black, overriding A's e5.
            books=[]
            for i,text in enumerate(['1. e4 e5 2. Nf3 Nc6 *','1. d4 d5 *\n\n1. d4 d5 *\n\n1. e4 c5 2. Nf3 d6 *']):
                p=tmp_path/f'{i}.pgn';p.write_text(text);c=await asyncio.to_thread(compile_book,p)
                try:b=await db.call('install_move_book',c)
                finally:Path(c['path']).unlink()
                books.append(b|{'policy':'best','max_plies':2})
            people=[profile(str(i),'strict_nodes' if control['kind']=='nodes' else 'normal',extra=['--transcript',str(tmp_path/f'{i}.log')])|{'move_book':books[i]} for i in range(2)]
            t=await db.call('create_tournament','Own books',people,{'cycles':1,'paired':True,'concurrency':1,'max_plies':6,'overhead':.1,'time_control':control});tid=t['id']
            for p in tmp_path.glob('*.pgn'):p.unlink()  # runtime uses the saved snapshot
            await db.call('set_state',tid,'running');await r.start()
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                assert not r.error,r.error
                snap=await db.call('snapshot',tid)
                if snap['state']=='completed':break
                await asyncio.sleep(.03)
            assert snap['official_games']==2 and snap['complete_pairs']==1
            rows=await db.call('rows','SELECT * FROM games ORDER BY number')
            for i,g in enumerate(rows):
                moves=await db.call('rows','SELECT * FROM moves WHERE aid=? ORDER BY ply',(g['official'],))
                assert moves[0]['uci']==('e2e4' if i==0 else 'd2d4')
                if i==0:assert moves[1]['uci']=='c7c5'
                info=json.loads(moves[0]['info']);assert info['source']=='book' and 'nodes' not in info
                c=json.loads(moves[0]['clocks'])['white']
                if control['kind']=='fischer':assert c['remaining']==pytest.approx(30.05)
                if control['kind']=='staged':assert c['remaining']==pytest.approx(41)
                if control['kind']=='nodes':assert c['remaining'] is None
            text=await db.call('export_official',tid,export_options={'preset':'testing'})
            game=chess.pgn.read_game(io.StringIO(text));assert not game.errors
            assert game.headers['WhiteBook']=='0.pgn' and game.headers['BlackBook']=='1.pgn'
            first=next(iter(game.mainline()))
            assert first.comment.startswith('Book: 0.pgn') and first.emt() is None and first.eval() is None
            if control['kind']=='fischer':assert first.clock()==pytest.approx(30.05)
            assert list(game.mainline_moves())[:2]==[chess.Move.from_uci('e2e4'),chess.Move.from_uci('c7c5')]
            clean=await db.call('export_official',tid,export_options={'preset':'clean'})
            assert not any(n.comment for n in chess.pgn.read_game(io.StringIO(clean)).mainline())
            html=await asyncio.to_thread(render,db.store.path,tid)
            assert 'Profile book moves (excluded from search metrics)' in html and '0.pgn' in html
            logs=''.join(p.read_text() for p in tmp_path.glob('*.log'))
            if control['kind']=='nodes':assert {line for line in logs.splitlines() if line.startswith('go ')}=={'go nodes 321'}
        finally:await r.close()
    asyncio.run(run())


def test_book_recovery_restarts_same_choices_and_preserves_attempt(tmp_path):
    # Abruptly kill the worker itself (os._exit), with one completed game and
    # one running attempt; no external source remains for recovery.
    script='''import sys,os,json,chess
from pathlib import Path
from arena.store import Store
from arena.move_books import compile_book,key,choose
s=Store(sys.argv[1]);p=Path(sys.argv[1])/'choices.pgn';p.write_text('1. e4 e5 *\\n\\n1. d4 d5 *')
c=compile_book(p);b=s.install_move_book(c)|{'policy':'weighted','max_plies':16};Path(c['path']).unlink();p.unlink()
t=s.create_tournament('Recover books',[{'name':'A','move_book':b},{'name':'B','move_book':b}],{'cycles':1});s.set_state(t['id'],'running');s.fill_queue(t['id'],2)
g=s.claim(t['id']);s.finish(g['aid'],'1/2-1/2','fixture');g=s.claim(t['id']);board=chess.Board(g['opening']['fen'])
seed=(t['settings']['seed'],g['number'],g['white'],b['id'],key(board),board.ply());m=choose(board,s.book_candidates(b['id'],key(board)),b,seed);san=board.san(m);board.push(m);s.move(g['aid'],1,m.uci(),san,board.fen(),0,{}, {'source':'book','book_id':b['id']})
print(json.dumps({'tid':t['id'],'gid':g['id'],'move':m.uci(),'book':b}),flush=True);os._exit(19)
'''
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path/'data')],capture_output=True,text=True)
    assert result.returncode==19,result.stderr
    data=json.loads(result.stdout)
    with contextlib.closing(Store(tmp_path/'data')) as s:
        t=s.snapshot(data['tid']);assert t['official_games']==1 and t['state']=='paused'
        attempts=s.game_detail(data['gid'])['attempts'];assert attempts[0]['reason']=='interrupted' and len(attempts[0]['moves'])==1
        s.set_state(t['id'],'running');g=s.claim(t['id']);board=chess.Board(g['opening']['fen']);b=data['book']
        seed=(t['settings']['seed'],g['number'],g['white'],b['id'],key(board),board.ply())
        assert choose(board,s.book_candidates(b['id'],key(board)),b,seed).uci()==data['move']
        s.finish(g['aid'],'1/2-1/2','fixture');s.export_pending()
        assert s.snapshot(t['id'])['official_games']==2
        assert 'interrupted' in (tmp_path/'data'/'interrupted.pgn').read_text().lower()


def test_book_metrics_do_not_count_zero_second_searches(tmp_path):
    from test_engine_readout import finish
    with contextlib.closing(Store(tmp_path)) as s:
        t=s.create_tournament('Metrics',[{'name':'A'},{'name':'B'}],{'cycles':1});s.set_state(t['id'],'running');s.fill_queue(t['id'],2)
        finish(s,t['id'],[{'source':'book'},{'source':'book'},{'nodes':100,'depth':7},{'nodes':200,'depth':8}])
        data=collect(s,t['id'],t['settings'],displayed(s,t['id']),sessions(s,t['id']))
        assert all(groups[0]['book_moves']==1 and groups[0]['moves']==1 for groups in data.values())


def test_large_bin_index_and_reference_safe_removal(tmp_path):
    source=tmp_path/'large.bin'
    with source.open('wb') as f:
        for position in range(50000):f.write(struct.pack('>QHHI',position,(chess.E2<<6)|chess.E4,1,0))
    with contextlib.closing(Store(tmp_path/'data')) as s:
        b=import_book(s,source)
        assert b['positions']==50000 and b['moves']==50000
        assert len(json.dumps(b))<1000
        assert len(s.book_candidates(b['id'],'0000000000000001'))==1
        p=s.save_profile(profile()|{'move_book':b})
        with pytest.raises(ValueError,match='used by'):s.remove_move_book(b['id'])
        t=s.create_tournament('Keep book',[p,profile('B')],{'cycles':1},backup=False)
        s.delete_profiles([p['id']])
        with pytest.raises(ValueError,match='used by'):s.remove_move_book(b['id'])
        # The deletion path removes tournament references, including backups.
        s.delete_tournament(t['id'],t['name']);s.remove_move_book(b['id'])
        assert s.one('SELECT count(*) n FROM book_moves')['n']==0


@pytest.mark.parametrize('enabled',[True,False])
def test_book_switch_and_first_miss_permanently_leave_book(tmp_path,enabled):
    async def run():
        db=await Database().open(tmp_path/'data');r=Runner(db)
        try:
            b=chess.Board();b.push_uci('e2e4');b.push_uci('e7e5');b.push_uci('g1f3');b.push_uci('b8c6')
            # Graph has White's first move and its fifth ply, but no third ply.
            path=tmp_path/'gap.pgn';path.write_text('1. e4 *\n\n[SetUp "1"]\n[FEN "'+b.fen()+'"]\n\n3. Bb5 *')
            c=compile_book(path)
            try:book=(await db.call('install_move_book',c))|{'policy':'best','max_plies':0}
            finally:Path(c['path']).unlink()
            people=[profile('A')|{'move_book':book},profile('B')]
            t=await db.call('create_tournament','Switch',people,{'cycles':1,'paired':False,'concurrency':1,'max_plies':6,'time_control':{'kind':'nodes','nodes':10},'use_engine_books':enabled})
            # Predetermined legal responses make a later book transposition
            # reachable. Patch only the fixture's choice, keeping UCI clocks.
            import unittest.mock
            from arena.uci import UciEngine
            original=UciEngine.play
            async def fixed(engine,board,*args):
                _,elapsed,info=await original(engine,board,*args)
                move=board.parse_uci(['e2e4','e7e5','g1f3','b8c6','f1c4','g8f6'][board.ply()])
                return move,elapsed,info
            with unittest.mock.patch.object(UciEngine,'play',fixed):
                await db.call('set_state',t['id'],'running');await r.start();deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    assert not r.error
                    if (await db.call('snapshot',t['id']))['state']=='completed':break
                    await asyncio.sleep(.02)
            moves=await db.call('rows','SELECT uci,info FROM moves ORDER BY ply')
            assert len(moves)==6
            assert sum(json.loads(m['info']).get('source')=='book' for m in moves)==int(enabled)
            assert moves[4]['uci']=='f1c4'  # no re-entry at the book's Bb5 position
        finally:await r.close()
    asyncio.run(run())
