"""Board abstraction built on python-chess."""

from __future__ import annotations

import io

import chess
import chess.pgn


class ChessBoard(chess.Board):
    """Extension of python-chess board with helper methods."""

    def move_validation(self, move: chess.Move | str) -> bool:
        """Validate a move against legal moves."""
        move_obj = chess.Move.from_uci(move) if isinstance(move, str) else move
        return move_obj in self.legal_moves

    def get_legal_moves(self) -> list[chess.Move]:
        """Return all legal moves."""
        return list(self.legal_moves)

    def make_move(self, move: chess.Move | str) -> bool:
        """Make a legal move and return success state."""
        move_obj = chess.Move.from_uci(move) if isinstance(move, str) else move
        if move_obj not in self.legal_moves:
            return False
        self.push(move_obj)
        return True

    def undo_move(self) -> chess.Move | None:
        """Undo and return last move when available."""
        if not self.move_stack:
            return None
        return self.pop()

    def is_checkmate(self) -> bool:
        """Return whether current position is checkmate."""
        return super().is_checkmate()

    def is_stalemate(self) -> bool:
        """Return whether current position is stalemate."""
        return super().is_stalemate()

    def is_check(self) -> bool:
        """Return whether side to move is in check."""
        return super().is_check()

    def to_pgn(self) -> str:
        """Export current game move stack to PGN."""
        game = chess.pgn.Game()
        node = game
        replay = chess.Board()
        for move in self.move_stack:
            node = node.add_variation(move)
            replay.push(move)
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        return game.accept(exporter)

    @classmethod
    def from_pgn(cls, pgn_string: str) -> 'ChessBoard':
        """Create board from PGN text."""
        game = chess.pgn.read_game(io.StringIO(pgn_string))
        board = cls()
        if game is None:
            return board
        for move in game.mainline_moves():
            board.push(move)
        return board

    def to_fen(self) -> str:
        """Export board in FEN format."""
        return self.fen()

    @classmethod
    def from_fen(cls, fen: str) -> 'ChessBoard':
        """Create board from FEN string."""
        board = cls()
        board.set_fen(fen)
        return board
