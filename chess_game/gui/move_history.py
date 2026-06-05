"""Move history panel widget."""

from __future__ import annotations

from pathlib import Path

import chess
import chess.pgn
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)


class MoveHistory(QWidget):
    """Scrollable move list with position navigation and PGN export."""

    position_selected = pyqtSignal(str)
    move_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table_widget = QTableWidget(0, 3)
        self.table_widget.setHorizontalHeaderLabels(['#', 'White', 'Black'])
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.export_button = QPushButton('Export to PGN')

        layout = QVBoxLayout(self)
        layout.addWidget(self.table_widget)
        layout.addWidget(self.export_button)

        self._positions: list[str] = [chess.STARTING_FEN]
        self._moves_san: list[str] = []
        self._cell_positions: dict[tuple[int, int], str] = {}
        self._cell_plies: dict[tuple[int, int], int] = {}
        self._board_snapshot = chess.Board()

        self.table_widget.cellClicked.connect(self._on_cell_clicked)
        self.export_button.clicked.connect(self._save_pgn)

    def update_from_board(self, board: chess.Board) -> None:
        """Refresh move history from current board stack."""
        self._board_snapshot = board.copy(stack=True)
        temp = chess.Board()
        self._positions = [temp.fen()]
        self._moves_san = []
        self._cell_positions = {}
        self._cell_plies = {}
        self.table_widget.setRowCount(0)

        for index, move in enumerate(board.move_stack, start=1):
            san = temp.san(move)
            temp.push(move)
            self._positions.append(temp.fen())
            self._moves_san.append(san)
            row = (index - 1) // 2
            column = 1 if index % 2 == 1 else 2
            move_no = row + 1

            if self.table_widget.rowCount() <= row:
                self.table_widget.insertRow(row)
                number_item = QTableWidgetItem(str(move_no))
                number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_widget.setItem(row, 0, number_item)

            move_item = QTableWidgetItem(san)
            self.table_widget.setItem(row, column, move_item)
            self._cell_positions[(row, column)] = temp.fen()
            self._cell_plies[(row, column)] = index

        if self.table_widget.rowCount():
            self.table_widget.scrollToBottom()

    def _on_cell_clicked(self, row: int, column: int) -> None:
        fen = self._cell_positions.get((row, column))
        if fen:
            self.position_selected.emit(fen)
            self.move_selected.emit(self._cell_plies[(row, column)])

    def select_ply(self, ply: int) -> None:
        if ply <= 0:
            self.table_widget.clearSelection()
            return
        row = (ply - 1) // 2
        column = 1 if ply % 2 == 1 else 2
        if row < self.table_widget.rowCount():
            self.table_widget.setCurrentCell(row, column)

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
