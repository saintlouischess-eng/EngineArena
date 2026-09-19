import io
import json
import os
from pathlib import Path
from unittest.mock import patch
import chess.pgn
import pytest
from arena.store import Store,SavingError

def test_write_failure_stops_and_can_recover_without_reset(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Save failure',[{'name':'A','path':'a.exe'},{'name':'B','path':'b.exe'}],{'cycles':1});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,2);g=s.claim(tid)
        s.finish(g['aid'],'1-0','checkmate')
        with patch('os.fsync',side_effect=OSError('Injected disk full')):
            with pytest.raises(SavingError):s.export_pending()
        assert 'saving failed' in s.failure.lower()
        with pytest.raises(ValueError):s.set_state(tid,'running')
        s.retry_saving();assert not s.failure;assert s.snapshot(tid)['official_games']==1
        games=[];f=io.StringIO((tmp_path/'games.pgn').read_text())
        while game:=chess.pgn.read_game(f):games.append(game)
        assert len(games)==1;assert games[0].headers['AttemptId']==g['aid']
    finally:s.close()

def test_grouped_moves_roll_back_together_and_unfinished_games_requeue(tmp_path):
    s=Store(tmp_path)
    try:
        t=s.create_tournament('Batch failure',[{'name':'A','path':'a.exe'},{'name':'B','path':'b.exe'}],{'cycles':1});tid=t['id'];s.set_state(tid,'running');s.fill_queue(tid,2);g=s.claim(tid)
        clocks={c:{'remaining':1} for c in ('white','black')};item=(g['aid'],1,'e2e4','e4','fen',.1,clocks,{},[])
        with pytest.raises(SavingError):s.move_batch([item,item])
        assert s.db.execute('SELECT count(*) FROM moves').fetchone()[0]==0
        s.retry_saving();detail=s.game_detail(g['id']);assert detail['state']=='pending';assert detail['attempts'][0]['reason']=='interrupted'
        assert s.tournament(tid)['state']=='paused'
    finally:s.close()
