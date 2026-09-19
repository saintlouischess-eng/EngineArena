import chess
from arena.referee import syzygy_decision

FEN='8/3k4/1p6/2p5/2P5/1P1K4/4P3/8 b - - 0 1'


class Probe:
    def __init__(self,wdl=-2,dtz=-2):self.wdl=wdl;self.dtz=dtz;self.dtz_calls=0
    def probe_wdl(self,board):
        if self.wdl is None:raise KeyError('missing WDL')
        return self.wdl
    def probe_dtz(self,board):
        self.dtz_calls+=1
        if self.dtz is None:raise KeyError('missing DTZ')
        return self.dtz


def test_rounded_dtz_never_certifies_the_exact_fifty_move_boundary():
    board=chess.Board(FEN);probe=Probe()
    board.halfmove_clock=97;assert syzygy_decision(probe,board)['result']=='1-0'
    board.halfmove_clock=98;assert syzygy_decision(probe,board)['result'] is None
    board.halfmove_clock=99;assert syzygy_decision(probe,board)['result'] is None
    board.turn=chess.WHITE;probe.wdl=2;probe.dtz=1
    assert syzygy_decision(probe,board)['result'] is None


def test_wdl_draws_and_zero_counter_do_not_require_dtz():
    board=chess.Board(FEN)
    for wdl in (-1,0,1):
        probe=Probe(wdl,None);assert syzygy_decision(probe,board)['result']=='1/2-1/2' and probe.dtz_calls==0
    probe=Probe(-2,None);assert syzygy_decision(probe,board)['result']=='1-0' and probe.dtz_calls==0
    board.halfmove_clock=1;decision=syzygy_decision(probe,board);assert decision['result'] is None and 'unavailable' in decision['note']
    assert 'unavailable' in syzygy_decision(Probe(None),board)['note']
