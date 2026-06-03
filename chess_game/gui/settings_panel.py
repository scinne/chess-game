"""Game settings panel."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SettingsPanel(QWidget):
    """Configurable settings panel with immediate application."""

    difficulty_changed = pyqtSignal(int)
    options_changed = pyqtSignal(dict)
    new_game_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.defaults = {
            'difficulty': 300,
            'show_legal_moves': True,
            'enable_premove': True,
            'show_evaluation': True,
            'sound_effects': False,
            'board_theme': 'Light',
            'piece_theme': 'Default',
        }
        self._build_ui()
        self._apply_defaults()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        group = QGroupBox('Settings')
        form = QFormLayout(group)

        self.difficulty = QComboBox()
        self.difficulty.addItem('Easy (300 Elo)', 300)
        self.difficulty.addItem('Intermediate (500 Elo)', 500)
        self.difficulty.addItem('Intermediate+ (1000 Elo)', 1000)
        self.difficulty.addItem('Advanced (1500 Elo)', 1500)
        self.difficulty.addItem('Expert (2000 Elo)', 2000)

        self.show_legal_moves = QCheckBox('Show Legal Moves')
        self.enable_premove = QCheckBox('Enable Premove')
        self.show_evaluation = QCheckBox('Show Evaluation Bar')
        self.sound_effects = QCheckBox('Sound Effects')

        sounds_dir = Path(__file__).resolve().parents[1] / 'resources' / 'sounds'
        has_sounds = any(sounds_dir.glob('*'))
        self.sound_effects.setEnabled(has_sounds)

        self.board_theme = QComboBox()
        self.board_theme.addItems(['Light', 'Dark'])

        self.piece_theme = QComboBox()
        self.piece_theme.addItems(['Default'])

        self.new_game = QPushButton('New Game')
        self.reset = QPushButton('Reset Settings')

        form.addRow('AI Difficulty', self.difficulty)
        form.addRow(self.show_legal_moves)
        form.addRow(self.enable_premove)
        form.addRow(self.show_evaluation)
        form.addRow(self.sound_effects)
        form.addRow('Board Theme', self.board_theme)
        form.addRow('Piece Theme', self.piece_theme)

        layout.addWidget(group)
        layout.addWidget(self.new_game)
        layout.addWidget(self.reset)
        layout.addStretch(1)

        self.difficulty.currentIndexChanged.connect(self._emit_all)
        self.show_legal_moves.toggled.connect(self._emit_all)
        self.enable_premove.toggled.connect(self._emit_all)
        self.show_evaluation.toggled.connect(self._emit_all)
        self.sound_effects.toggled.connect(self._emit_all)
        self.board_theme.currentIndexChanged.connect(self._emit_all)
        self.piece_theme.currentIndexChanged.connect(self._emit_all)
        self.new_game.clicked.connect(self.new_game_requested.emit)
        self.reset.clicked.connect(self._reset_settings)

    def _apply_defaults(self) -> None:
        self.difficulty.setCurrentIndex(self.difficulty.findData(self.defaults['difficulty']))
        self.show_legal_moves.setChecked(self.defaults['show_legal_moves'])
        self.enable_premove.setChecked(self.defaults['enable_premove'])
        self.show_evaluation.setChecked(self.defaults['show_evaluation'])
        self.sound_effects.setChecked(self.defaults['sound_effects'])
        self.board_theme.setCurrentText(self.defaults['board_theme'])
        self.piece_theme.setCurrentText(self.defaults['piece_theme'])
        self._emit_all()

    def _reset_settings(self) -> None:
        self._apply_defaults()

    def _emit_all(self) -> None:
        difficulty = int(self.difficulty.currentData())
        self.difficulty_changed.emit(difficulty)
        self.options_changed.emit(
            {
                'show_legal_moves': self.show_legal_moves.isChecked(),
                'enable_premove': self.enable_premove.isChecked(),
                'show_evaluation': self.show_evaluation.isChecked(),
                'sound_effects': self.sound_effects.isChecked(),
                'board_theme': self.board_theme.currentText(),
                'piece_theme': self.piece_theme.currentText(),
            }
        )
