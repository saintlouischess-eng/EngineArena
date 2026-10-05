"""Display-only identity of original kingside pieces; never infer from a midgame FEN."""
import chess
from .pgn_format import opening_board


class CrownMarks:
    def __init__(self, board):
        self.squares = {chess.G1, chess.H1, chess.G8, chess.H8} if board.fen() == chess.STARTING_FEN else set()

    def advance(self, board, move):
        """Called before a legal move is pushed. Promotions never acquire a stamp."""
        if not self.squares:
            return
        if board.is_castling(move):
            if board.is_kingside_castling(move):
                rank = 0 if board.turn else 7
                source, target = chess.square(7, rank), chess.square(5, rank)
                if source in self.squares:
                    self.squares.remove(source)
                    self.squares.add(target)
            return
        marked = move.from_square in self.squares
        self.squares.discard(move.from_square)
        self.squares.discard(move.to_square)
        if marked and not move.promotion:
            self.squares.add(move.to_square)

    def snapshot(self):
        return [chess.square_name(s) for s in sorted(self.squares)]


def opening_marks(opening, chess960=False):
    board, history, _ = opening_board(opening, chess960)
    marks = CrownMarks(board)
    for move in history:
        marks.advance(board, move)
        board.push(move)
    return marks
