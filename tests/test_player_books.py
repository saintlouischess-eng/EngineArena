"""Player books must survive recovery, export and takebacks without changing profiles."""
import asyncio
import io
from pathlib import Path
import chess.pgn
import pytest
from arena.move_books import compile_book
from test_player import fixture,action,wait


async def book(db,path):
    path.write_text('1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *',encoding='utf-8')
    compiled=compile_book(path)
    try:return (await db.call('install_move_book',compiled))|{'max_plies':4,'policy':'best'}
    finally:Path(compiled['path']).unlink()


@pytest.mark.parametrize('mode',['profile','custom','none'])
def test_player_book_choice_clocks_exports_and_takeback(tmp_path,mode):
    async def run():
        db,r,p,profile=await fixture(tmp_path)
        try:
            await action(p,'abandon');b=await book(db,tmp_path/'Player opening.pgn')
            profile=await db.call('save_profile',profile|{'move_book':b})
            await p.create({'engine':profile['id'],'config':{'hash':16,'book_mode':mode,'move_book':b}})
            assert bool(p.game['engine']['move_book'])==(mode!='none')
            # Disabling a book for a game never clears the saved engine profile.
            saved=await db.call('one','SELECT body FROM profiles WHERE id=?',(profile['id'],))
            assert b['id'] in saved['body']
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'move',move='e2e4');await wait(p,lambda:len(p.game['moves'])==2)
            if mode=='none':
                assert p.game['moves'][1]['info'].get('source')!='book';return
            first=p.game['moves'][1];assert first['uci']=='e7e5' and first['info']['source']=='book'
            assert first['elapsed']==0 and first['clocks']['black']['remaining']==303
            await action(p,'takeback');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'move',move='e2e4');await wait(p,lambda:len(p.game['moves'])==2)
            assert p.game['moves'][1]['uci']==first['uci'] and len(p.game['variations'])==1
            await action(p,'pause');committed=p.game['id'];await p.close()
            from arena.player import PlayerArena
            p=PlayerArena(db,r);await p.start();assert p.game['id']==committed
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'move',move='g1f3');await wait(p,lambda:len(p.game['moves'])==4)
            assert p.game['moves'][3]['uci']=='b8c6' and p.game['moves'][3]['info']['source']=='book'
            await action(p,'move',move='f1b5');await wait(p,lambda:len(p.game['moves'])==6)
            assert p.game['moves'][5]['info'].get('source')!='book' # Absolute 4-ply cutoff.
            await action(p,'resign')
            raw=await db.call('player_call','export',p.game['id'],{'preset':'archive'})
            g=chess.pgn.read_game(io.StringIO(raw));assert not g.errors
            assert g.headers['BlackBook']=='Player opening.pgn' and g.headers['BlackBookMaxPly']=='4'
            assert 'Book: Player opening.pgn' in raw and len(list(g.mainline_moves()))==6
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_player_series_book_snapshot_and_delete_protection(tmp_path):
    async def run():
        db,r,p,profile=await fixture(tmp_path)
        try:
            await action(p,'abandon');b=await book(db,tmp_path/'series.pgn')
            series=await db.call('player_call','series',{'engines':[profile['id']],'games_each':2,'config':{'book_mode':'custom','move_book':b},'title':'Book series'})
            with pytest.raises(ValueError,match='Player Arena'):await db.call('remove_move_book',b['id'])
            await p.create({},series['id']);assert p.game['engine']['move_book']['id']==b['id']
            await action(p,'resign');await p.create({},series['id'])
            assert p.game['config']['color']=='black' and p.game['engine']['move_book']['id']==b['id']
            await action(p,'resume');await wait(p,lambda:len(p.game['moves'])==1)
            assert p.game['moves'][0]['uci']=='e2e4' and p.game['moves'][0]['info']['source']=='book'
            with pytest.raises(ValueError,match='Player Arena'):await db.call('remove_move_book',b['id'])
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_invalid_player_book_rejected_before_creating_game(tmp_path):
    async def run():
        db,r,p,profile=await fixture(tmp_path)
        try:
            await action(p,'abandon')
            for config in ({'book_mode':'bad'},{'book_mode':'custom'},{'book_mode':'custom','move_book':{'id':'missing'}}):
                with pytest.raises(ValueError):await p.create({'engine':profile['id'],'config':config})
            assert await db.call('player_call','get') is None
        finally:await p.close();await r.close()
    asyncio.run(run())


def test_book_does_not_reenter_after_engine_search(tmp_path):
    async def run():
        db,r,p,profile=await fixture(tmp_path)
        try:
            await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'move',move='e2e4');await wait(p,lambda:len(p.game['moves'])==2)
            board=p.board.copy();board.push_uci('g1f3');reply=next(iter(board.legal_moves))
            source=tmp_path/'late-entry.pgn'
            source.write_text('[SetUp "1"]\n[FEN "'+board.fen()+'"]\n\n2... '+board.san(reply)+' *',encoding='utf-8')
            compiled=compile_book(source)
            try:b=(await db.call('install_move_book',compiled))|{'max_plies':0,'policy':'best'}
            finally:Path(compiled['path']).unlink()
            # Install a test-only position lookup to prove an earlier search is
            # sufficient to prevent re-entry, including after pause/recovery.
            p.game['engine']['move_book']=b;await action(p,'pause');await p.close()
            from arena.player import PlayerArena
            p=PlayerArena(db,r);await p.start();await action(p,'resume');await wait(p,lambda:p.game['state']=='playing')
            await action(p,'move',move='g1f3');await wait(p,lambda:len(p.game['moves'])==4)
            assert p.game['moves'][3]['info'].get('source')!='book'
        finally:await p.close();await r.close()
    asyncio.run(run())
