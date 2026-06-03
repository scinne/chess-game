from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class EvaluationBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._cp = 0
        self.setMinimumWidth(48)
        self._label = QLabel("+0.00")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    def set_evaluation(self, centipawns: int | None) -> None:
        self._cp = centipawns or 0
        self._label.setText(f"{self._cp / 100:+.2f}")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        ratio = max(0.0, min(1.0, 0.5 + (self._cp / 1600)))
        white_height = int(self.height() * ratio)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        painter.fillRect(0, self.height() - white_height, self.width(), white_height, Qt.GlobalColor.white)
        super().paintEvent(event)
