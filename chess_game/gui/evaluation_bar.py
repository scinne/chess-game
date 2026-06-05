"""Evaluation bar widget."""

from __future__ import annotations

import math

from PyQt6.QtCore import QEasingCurve, QVariantAnimation, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget


class EvaluationBar(QWidget):
    """Vertical evaluation bar showing white/black advantage."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(52)
        self._eval = 0.0
        self._label = '0'
        self._result_label: str | None = None
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.valueChanged.connect(self._on_animate)

    def _on_animate(self, value: object) -> None:
        self._eval = float(value)
        self.update()

    def set_evaluation(self, evaluation: int | float | dict) -> None:
        """Set evaluation value and animate bar update."""
        self._result_label = None
        if isinstance(evaluation, dict) and evaluation.get('type') == 'mate':
            mate = int(evaluation.get('value', 0))
            target = 2000.0 if mate > 0 else -2000.0
        elif isinstance(evaluation, dict):
            target = float(evaluation.get('value', 0))
        else:
            target = float(evaluation)
        self._label = self._compact_label(evaluation, target)

        self._animation.stop()
        self._animation.setStartValue(self._eval)
        self._animation.setEndValue(target)
        self._animation.start()

    def set_result(self, result: str | None) -> None:
        """Show a game result instead of the numeric evaluation label."""
        self._result_label = result
        self.update()

    def _compact_label(self, evaluation: int | float | dict, target: float) -> str:
        if isinstance(evaluation, dict) and evaluation.get('type') == 'mate':
            mate = max(-99, min(99, int(evaluation.get('value', 0))))
            return f'M{mate}'
        pawns = int(round(target / 100.0))
        pawns = max(-99, min(99, pawns))
        if pawns > 0:
            return f'+{pawns}'
        return str(pawns)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(6, 6, -6, -6)
        ratio = max(-1.0, min(1.0, math.tanh(self._eval / 600.0)))
        white_ratio = (ratio + 1.0) / 2.0
        white_height = int(rect.height() * white_ratio)
        black_height = rect.height() - white_height

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 30, 30))
        painter.drawRoundedRect(rect, 6, 6)

        white_rect = rect.adjusted(0, black_height, 0, 0)
        painter.setBrush(QColor(245, 245, 245))
        painter.drawRoundedRect(white_rect, 6, 6)

        label = self._result_label or self._label
        font = QFont('Segoe UI')
        font.setPixelSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(220, 220, 220) if white_ratio < 0.35 else QColor(20, 20, 20))
        painter.drawText(rect.adjusted(1, 0, -1, 0), Qt.AlignmentFlag.AlignCenter, label)
