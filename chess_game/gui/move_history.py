from __future__ import annotations

from typing import Callable

import chess
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem


class MoveHistory(QListWidget):
    navigate_to_ply = pyqtSignal(int)

    def __init__(self, on_click: Callable[[int], None] | None = None) -> None:
        super().__init__()
        if on_click:
            self.navigate_to_ply.connect(on_click)
        self.itemClicked.connect(self._emit_selected)

    def set_moves(self, board: chess.Board) -> None:
        self.clear()
        replay = chess.Board()
        san_moves: list[str] = []
        for move in board.move_stack:
            san_moves.append(replay.san(move))
            replay.push(move)

        for index in range(0, len(san_moves), 2):
            white = san_moves[index]
            black = san_moves[index + 1] if index + 1 < len(san_moves) else ""
            self.addItem(f"{(index // 2) + 1}. {white} {black}".strip())

    def _emit_selected(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        self.navigate_to_ply.emit(row)
