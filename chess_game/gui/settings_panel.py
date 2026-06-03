from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from chess_game.utils.constants import DIFFICULTY_PRESETS


class SettingsPanel(QWidget):
    difficulty_changed = pyqtSignal(str)
    legal_moves_toggled = pyqtSignal(bool)
    premove_toggled = pyqtSignal(bool)
    eval_bar_toggled = pyqtSignal(bool)
    sounds_toggled = pyqtSignal(bool)
    board_theme_changed = pyqtSignal(str)
    piece_theme_changed = pyqtSignal(str)
    reset_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        form = QFormLayout()

        self.difficulty = QComboBox()
        self.difficulty.addItems(DIFFICULTY_PRESETS.keys())
        self.difficulty.setCurrentText("1000 Elo")
        self.difficulty.currentTextChanged.connect(self.difficulty_changed.emit)

        self.show_legal = QCheckBox("Show legal move indicators")
        self.show_legal.setChecked(True)
        self.show_legal.toggled.connect(self.legal_moves_toggled.emit)

        self.allow_premove = QCheckBox("Enable premove")
        self.allow_premove.setChecked(True)
        self.allow_premove.toggled.connect(self.premove_toggled.emit)

        self.show_eval = QCheckBox("Show evaluation bar")
        self.show_eval.setChecked(True)
        self.show_eval.toggled.connect(self.eval_bar_toggled.emit)

        self.sounds = QCheckBox("Enable sounds")
        self.sounds.setChecked(True)
        self.sounds.toggled.connect(self.sounds_toggled.emit)

        self.board_theme = QComboBox()
        self.board_theme.addItems(["Classic", "Blue", "Green", "Gray"])
        self.board_theme.currentTextChanged.connect(self.board_theme_changed.emit)

        self.piece_theme = QComboBox()
        self.piece_theme.addItems(["Unicode", "Classic"])
        self.piece_theme.currentTextChanged.connect(self.piece_theme_changed.emit)

        form.addRow("AI difficulty", self.difficulty)
        form.addRow("Board theme", self.board_theme)
        form.addRow("Piece theme", self.piece_theme)
        form.addRow(self.show_legal)
        form.addRow(self.allow_premove)
        form.addRow(self.show_eval)
        form.addRow(self.sounds)

        reset_btn = QPushButton("Reset game")
        reset_btn.clicked.connect(self.reset_requested.emit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(reset_btn)
        layout.addStretch(1)
