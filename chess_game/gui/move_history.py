"""Move history panel widget."""

from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MoveHistory(QWidget):
    """Scrollable move list with position navigation and PGN export."""

    position_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.list_widget = QListWidget()
        self.export_button = QPushButton('Export to PGN')

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.export_button)

        self._positions: list[str] = [chess.STARTING_FEN]
        self._moves_san: list[str] = []
        self._board_snapshot = chess.Board()

        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.export_button.clicked.connect(self._save_pgn)

    def update_from_board(self, board: chess.Board) -> None:
        """Refresh move history from current board stack."""
        self._board_snapshot = board.copy(stack=True)
        temp = chess.Board()
        self._positions = [temp.fen()]
        self._moves_san = []
        self.list_widget.clear()

        for index, move in enumerate(board.move_stack, start=1):
            san = temp.san(move)
            temp.push(move)
            self._positions.append(temp.fen())
            self._moves_san.append(san)
            move_no = (index + 1) // 2
            prefix = f'{move_no}. ' if index % 2 == 1 else '   '
            self.list_widget.addItem(f'{prefix}{san}')

        self.list_widget.scrollToBottom()

    def _on_item_clicked(self, item) -> None:
        row = self.list_widget.row(item) + 1
        if 0 <= row < len(self._positions):
            self.position_selected.emit(self._positions[row])

    def _save_pgn(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Save PGN', str(Path.home() / 'game.pgn'), 'PGN Files (*.pgn)')
        if not path:
            return
        game = chess.pgn.Game()
        node = game
        for move in self._board_snapshot.move_stack:
            node = node.add_variation(move)
        with open(path, 'w', encoding='utf-8') as pgn_file:
            exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
            pgn_file.write(game.accept(exporter))
