from __future__ import annotations

from io import StringIO

import chess
import chess.pgn


class ChessBoard:
    def __init__(self, fen: str | None = None) -> None:
        self.board = chess.Board(fen) if fen else chess.Board()
        self._redo_stack: list[chess.Move] = []

    def reset(self) -> None:
        self.board.reset()
        self._redo_stack.clear()

    def set_fen(self, fen: str) -> None:
        self.board.set_fen(fen)
        self._redo_stack.clear()

    def get_fen(self) -> str:
        return self.board.fen()

    def legal_moves(self, square: chess.Square | None = None) -> list[chess.Move]:
        if square is None:
            return list(self.board.legal_moves)
        return [m for m in self.board.legal_moves if m.from_square == square]

    def is_legal(self, move: chess.Move) -> bool:
        return move in self.board.legal_moves

    def push(self, move: chess.Move) -> bool:
        if not self.is_legal(move):
            return False
        self.board.push(move)
        self._redo_stack.clear()
        return True

    def undo(self) -> chess.Move | None:
        if not self.board.move_stack:
            return None
        move = self.board.pop()
        self._redo_stack.append(move)
        return move

    def redo(self) -> chess.Move | None:
        if not self._redo_stack:
            return None
        move = self._redo_stack.pop()
        if move not in self.board.legal_moves:
            return None
        self.board.push(move)
        return move

    def result_state(self) -> str | None:
        if self.board.is_checkmate():
            return "checkmate"
        if self.board.is_stalemate():
            return "stalemate"
        if self.board.is_insufficient_material():
            return "draw_insufficient_material"
        if self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            return "draw_forced"
        return None

    def in_check(self) -> bool:
        return self.board.is_check()

    def to_pgn(self) -> str:
        game = chess.pgn.Game()
        current = game
        replay = chess.Board()
        for move in self.board.move_stack:
            current = current.add_variation(move)
            replay.push(move)
        game.headers["Result"] = replay.result(claim_draw=True)
        return str(game)

    def load_pgn(self, pgn_text: str) -> None:
        game = chess.pgn.read_game(StringIO(pgn_text))
        if game is None:
            raise ValueError("Invalid PGN data")
        self.reset()
        for move in game.mainline_moves():
            self.board.push(move)
        self._redo_stack.clear()

    def san(self, move: chess.Move) -> str:
        return self.board.san(move)
