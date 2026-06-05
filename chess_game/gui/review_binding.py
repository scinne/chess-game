"""Binding helpers for the review panel UI."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem

from chess_game.review.models import AnalysisResult, MoveAnnotation


class ReviewPanelBinding:
    """Keeps existing review widgets in sync with structured review state."""

    def __init__(self, window) -> None:
        self.window = window

    def show_analysis(self, result: AnalysisResult, annotation: MoveAnnotation | None = None, opening: dict | None = None) -> None:
        label = annotation.label.title() if annotation else 'Analysis'
        details = [
            f'{label} | Eval {result.evaluation_text} | Best {result.best_move_san} | Depth {result.depth or "-"} | {result.engine_name}'
        ]
        if annotation and annotation.reason:
            details.append(annotation.reason)
        if opening:
            book_moves = ', '.join(item['san'] for item in opening.get('book_moves', [])) or '-'
            state = 'in book' if opening.get('in_book') else 'out of book'
            details.append(f"{opening.get('name', 'Unknown Opening')} | {state} | Book moves: {book_moves}")
        self.window.review_analysis_box.setPlainText('\n'.join(details))
        table = self.window.review_lines_table
        table.setRowCount(len(result.lines))
        for row, line in enumerate(result.lines):
            values = (line.score_text, line.san, ' '.join(line.pv_san))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, line)
                table.setItem(row, column, item)

    def show_waiting(self, message: str) -> None:
        self.window.review_analysis_box.setPlainText(message)
        table = self.window.review_lines_table
        table.setRowCount(1)
        values = ('...', 'Loading', message)
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.UserRole, None)
            table.setItem(0, column, item)
