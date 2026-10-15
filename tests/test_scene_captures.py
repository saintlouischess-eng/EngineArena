import chess
from arena.crown_marks import CrownMarks,opening_marks
from arena.game_moves import read_moves,presentation
from test_core import profile,run_claim,store


def play(board,marks,uci):
    move=board.parse_uci(uci);marks.advance(board,move);board.push(move)


def test_recorded_captures_include_openings_and_en_passant():
    board=chess.Board();marks=CrownMarks(board)
    moves=['e2e4','a7a6','e4e5','d7d5','e5d6']
    for uci in moves:play(board,marks,uci)
    assert marks.capture_snapshot()==['p']
    restored=opening_marks({'start_fen':chess.STARTING_FEN,'moves':moves,'fen':board.fen()})
    assert restored.capture_snapshot()==['p']
    copy=marks.capture_snapshot();copy.clear();assert marks.capture_snapshot()==['p']


def test_custom_start_does_not_invent_captured_pieces_and_promotion_records_victim():
    board=chess.Board('1r5k/P7/8/8/8/8/8/7K w - - 0 1');marks=CrownMarks(board)
    assert marks.capture_snapshot()==[]
    play(board,marks,'a7b8q');assert marks.capture_snapshot()==['r']
    marks.clear();assert marks.capture_snapshot()==[]


def test_chess960_castling_never_counts_own_rook_as_capture():
    board=chess.Board('4k3/8/8/8/8/8/8/4K2R w H - 0 1',chess960=True);marks=CrownMarks(board)
    play(board,marks,'e1h1');assert marks.capture_snapshot()==[]


def test_capture_reconstruction_is_paginated_and_attempt_specific(store):
    board=chess.Board();history=['e2e4','d7d5','e4d5']
    for uci in history:board.push_uci(uci)
    t=store.create_tournament('Capture history',[profile('A'),profile('B')],{'cycles':1},[{'fen':board.fen(),'moves':history}]);g=run_claim(store,t)
    for ply,uci in enumerate(['d8d5','b1c3','d5e5','f1e2'],1):
        move=board.parse_uci(uci);san=board.san(move);board.push(move);store.move(g['aid'],ply,uci,san,board.fen(),.1,{}, {})
    page=read_moves(store.path,g['id'],after=2,limit=2)
    assert page['items'][0]['captured']==['p','P'] and page['opening_captured']==['p']
    store.finish(g['aid'],'0-1','timeout');store.set_state(t['id'],'paused')
    store.requeue(t['id'],[g['id']],mode='diagnostic');store.set_state(t['id'],'running');store.claim(t['id'])
    assert read_moves(store.path,g['id'])['opening_captured']==['p']
    assert read_moves(store.path,g['id'],aid=g['aid'])['items'][-1]['captured']==['p','P']


def test_nameplate_scores_follow_official_replacements_without_diagnostic_double_counting(store):
    t=store.create_tournament('Nameplates',[profile('A'),profile('B')],{'cycles':1},[]);g=run_claim(store,t)
    assert presentation(store.path,g['id'])['score'] is None
    store.finish(g['aid'],'1-0','checkmate')
    assert presentation(store.path,g['id'])['score']==[1,0]
    store.set_state(t['id'],'paused');store.requeue(t['id'],[g['id']],mode='diagnostic');store.set_state(t['id'],'running');retry=store.claim(t['id'])
    store.finish(retry['aid'],'0-1','checkmate');assert presentation(store.path,g['id'])['score']==[1,0]
    store.set_state(t['id'],'paused');store.requeue(t['id'],[g['id']],mode='replacement');store.set_state(t['id'],'running');retry=store.claim(t['id'])
    store.finish(retry['aid'],'1/2-1/2','stalemate');assert presentation(store.path,g['id'])['score']==[.5,.5]
