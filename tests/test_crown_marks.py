import chess
from arena.crown_marks import CrownMarks, opening_marks


def play(board, marks, san):
    move=board.parse_san(san);marks.advance(board,move);board.push(move)


def test_original_identity_survives_moves_and_both_kingside_castles():
    board=chess.Board();marks=CrownMarks(board)
    for san in 'e4 e5 Nf3 Nc6 Bc4 Nf6 O-O Be7 d3 O-O'.split():play(board,marks,san)
    assert marks.snapshot()==['f1','f3','f6','f8']
    # The unmarked queenside knight is on c6, not the crowned one on f6.
    assert 'c6' not in marks.snapshot()


def test_capture_removes_stamp_and_unmarked_capturer_does_not_inherit():
    board=chess.Board();marks=CrownMarks(board)
    for san in 'e4 e5 Nf3 Nc6 Bb5 Nf6 Bxc6 dxc6 Nxe5 Nxe4'.split():play(board,marks,san)
    assert marks.snapshot()==['h1','e4','e5','h8']
    for san in 'Qe2 Qd4 Nf3 Qxf2+'.split():play(board,marks,san)
    # Test a legal rook capture directly with identities carried from an earlier position.
    board=chess.Board('4k2r/8/8/8/8/8/8/4K2R w - - 0 1');marks.squares={chess.H1,chess.H8}
    play(board,marks,'Rxh8+')
    assert marks.snapshot()==['h8']
    board=chess.Board('4k2r/8/8/8/8/8/8/4K2R b - - 0 1');marks.squares={chess.H1}
    play(board,marks,'Rxh1+')
    assert marks.snapshot()==[]


def test_promoted_rook_does_not_gain_mark():
    board=chess.Board('4k3/7P/8/8/8/8/8/4K3 w - - 0 1');marks=CrownMarks(board)
    play(board,marks,'h8=R+')
    assert marks.snapshot()==[]


def test_verified_opening_history_tracks_knights_and_castling():
    board=chess.Board();moves=[]
    for san in 'e4 e5 Nf3 Nc6 Bc4 Nf6 O-O'.split():
        move=board.parse_san(san);moves.append(move.uci());board.push(move)
    assert opening_marks({'fen':board.fen(),'moves':moves}).snapshot()==['f1','f3','f6','h8']
    assert opening_marks({'fen':board.fen()}).snapshot()==[]
    assert opening_marks({'fen':board.fen(),'moves':['e2e4']}).snapshot()==[]


def test_chess960_never_guesses_origin_from_nonstandard_start():
    board=chess.Board.from_chess960_pos(0)
    assert CrownMarks(board).snapshot()==[]
    # Standard arrangement in Chess960 mode uses king-to-rook UCI castling.
    board=chess.Board(chess960=True);marks=CrownMarks(board)
    for san in 'e4 e5 Nf3 Nc6 Bc4 Nf6 O-O'.split():play(board,marks,san)
    assert marks.snapshot()==['f1','f3','f6','h8']


def test_knight_orientation_follows_identity_across_centre_and_captures():
    board=chess.Board();marks=CrownMarks(board)
    assert marks.knight_snapshot()=={'b1':1,'g1':-1,'b8':1,'g8':-1}
    for san in 'Nf3 Nf6 Nd4 Nd5 Nb5 Nb4'.split():play(board,marks,san)
    assert marks.knight_snapshot()=={'b1':1,'b4':-1,'b5':-1,'b8':1}
    for san in 'Nxc7+ Qxc7'.split():play(board,marks,san)
    assert marks.knight_snapshot()=={'b1':1,'b4':-1,'b8':1}


def test_knights_use_verified_opening_history_and_unknowns_stay_unknown():
    board=chess.Board();moves=['g1f3','b8c6','f3d4']
    for move in moves:board.push_uci(move)
    assert opening_marks({'fen':board.fen(),'moves':moves}).knight_snapshot()=={'b1':1,'d4':-1,'c6':1,'g8':-1}
    assert opening_marks({'fen':board.fen()}).knight_snapshot()=={}
    assert opening_marks({'fen':board.fen(),'moves':['e2e4']}).knight_snapshot()=={}
    board=chess.Board('4k3/7P/8/8/8/8/8/4K3 w - - 0 1');marks=CrownMarks(board)
    play(board,marks,'h8=N')
    assert marks.knight_snapshot()=={}


def test_chess960_knights_face_their_starting_king_and_clear_is_complete():
    for number in (0,17,518,959):
        board=chess.Board.from_chess960_pos(number);marks=CrownMarks(board)
        for color in (chess.WHITE,chess.BLACK):
            for square in board.pieces(chess.KNIGHT,color):
                assert marks.knight_snapshot()[chess.square_name(square)]==(1 if chess.square_file(square)<chess.square_file(board.king(color)) else -1)
        marks.clear()
        assert marks.knight_snapshot()=={} and marks.snapshot()==[]
