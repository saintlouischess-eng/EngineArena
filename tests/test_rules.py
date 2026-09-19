import chess

def perft(board,depth):
    if depth==0:return 1
    total=0
    for move in list(board.legal_moves):
        board.push(move);total+=perft(board,depth-1);board.pop()
    return total

def test_standard_reference_perft():
    board=chess.Board();assert perft(board,1)==20;assert perft(board,2)==400;assert perft(board,3)==8902

def test_all_960_starting_positions():
    positions=set()
    for i in range(960):
        b=chess.Board.from_chess960_pos(i);row=b.board_fen().split('/')[-1];positions.add(row)
        bishops=[j for j,p in enumerate(row) if p=='B'];rooks=[j for j,p in enumerate(row) if p=='R'];king=row.index('K')
        assert bishops[0]%2!=bishops[1]%2;assert rooks[0]<king<rooks[1];assert b.is_valid();assert b.chess960_pos()==i
    assert len(positions)==960

def test_chess960_castling_when_king_already_on_destination():
    b=chess.Board('4k3/8/8/8/8/8/8/R5KR w AH - 0 1',chess960=True)
    move=b.parse_uci('g1h1');assert b.is_castling(move);b.push(move)
    assert b.king(chess.WHITE)==chess.G1;assert b.piece_at(chess.F1)==chess.Piece(chess.ROOK,chess.WHITE)

def test_promotions_en_passant_and_repetition():
    b=chess.Board('7k/P7/8/8/8/8/8/7K w - - 0 1')
    assert {m.promotion for m in b.legal_moves if m.from_square==chess.A7}=={chess.QUEEN,chess.ROOK,chess.BISHOP,chess.KNIGHT}
    b=chess.Board('8/8/8/r4pPK/8/8/8/7k w - f6 0 1');assert chess.Move.from_uci('g5f6') not in b.legal_moves
    b=chess.Board()
    for move in ['g1f3','g8f6','f3g1','f6g8']*2:b.push_uci(move)
    assert b.can_claim_threefold_repetition()

def test_checkmate_overrides_fifty_move_threshold():
    b=chess.Board('7k/5K2/6Q1/8/8/8/8/8 w - - 99 1');b.push_uci('g6g7');assert b.is_checkmate();assert b.outcome(claim_draw=True).result()=='1-0'
