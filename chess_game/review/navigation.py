"""Game move navigation model."""

from __future__ import annotations

import chess

from chess_game.review.models import MoveNode


class GameNavigator:
    """Builds immutable move nodes and exposes position navigation by ply."""

    def __init__(self, board: chess.Board | None = None) -> None:
        self.nodes: list[MoveNode] = []
        self.positions: list[str] = [chess.STARTING_FEN]
        if board is not None:
            self.set_board(board)

    def set_board(self, board: chess.Board) -> None:
        replay = chess.Board()
        self.nodes = []
        self.positions = [replay.fen()]
        for ply, move in enumerate(board.move_stack, start=1):
            before_fen = replay.fen()
            san = replay.san(move)
            side = replay.turn
            replay.push(move)
            after_fen = replay.fen()
            self.positions.append(after_fen)
            self.nodes.append(
                MoveNode(
                    ply=ply,
                    move_number=(ply + 1) // 2,
                    side=side,
                    san=san,
                    uci=move.uci(),
                    before_fen=before_fen,
                    after_fen=after_fen,
                )
            )

    def clamp_ply(self, ply: int) -> int:
        return max(0, min(ply, len(self.nodes)))

    def fen_at(self, ply: int) -> str:
        return self.positions[self.clamp_ply(ply)]

    def node_at(self, ply: int) -> MoveNode | None:
        if ply <= 0 or ply > len(self.nodes):
            return None
        return self.nodes[ply - 1]

    def first_ply_with_label(self, annotations: dict[int, object], label: str, after_ply: int = -1) -> int | None:
        matches = [
            ply
            for ply, annotation in sorted(annotations.items())
            if getattr(annotation, 'label', None) == label and ply > after_ply
        ]
        if matches:
            return matches[0]
        matches = [
            ply
            for ply, annotation in sorted(annotations.items())
            if getattr(annotation, 'label', None) == label
        ]
        return matches[0] if matches else None

