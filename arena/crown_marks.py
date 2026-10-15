"""Display-only identities and starting orientations, reconstructed from legal moves."""
import chess
from .pgn_format import opening_board


class CrownMarks:
    def __init__(self, board):
        self.squares = {chess.G1, chess.H1, chess.G8, chess.H8} if board.fen() == chess.STARTING_FEN else set()
        # A signed board-file direction toward the starting king. Never make a
        # knight turn around merely because it crosses the centre of the board.
        self.knights = {}
        self.captured = []
        if board.chess960_pos() is not None:
            for color in (chess.WHITE, chess.BLACK):
                king_file = chess.square_file(board.king(color))
                for square in board.pieces(chess.KNIGHT, color):
                    self.knights[square] = 1 if chess.square_file(square) < king_file else -1

    def advance(self, board, move):
        """Called before a legal move is pushed. Promotions never acquire a stamp."""
        if board.is_capture(move) and not board.is_castling(move):
            square = move.to_square + (-8 if board.turn else 8) if board.is_en_passant(move) else move.to_square
            piece = board.piece_at(square)
            if piece:self.captured.append(piece.symbol())
        facing = self.knights.pop(move.from_square, None)
        self.knights.pop(move.to_square, None)
        if facing is not None and not move.promotion:
            self.knights[move.to_square] = facing
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

    def knight_snapshot(self):
        return {chess.square_name(s): direction for s, direction in sorted(self.knights.items())}

    def capture_snapshot(self):
        return list(self.captured)

    def clear(self):
        self.squares.clear()
        self.knights.clear()
        self.captured.clear()


def opening_marks(opening, chess960=False):
    board, history, _ = opening_board(opening, chess960)
    marks = CrownMarks(board)
    for move in history:
        marks.advance(board, move)
        board.push(move)
    return marks
