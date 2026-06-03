from __future__ import annotations

from dataclasses import dataclass

import chess
from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from chess_game.board import ChessBoard
from chess_game.engine import StockfishEngine
from chess_game.gui.board_widget import BoardWidget
from chess_game.gui.evaluation_bar import EvaluationBar
from chess_game.gui.move_history import MoveHistory
from chess_game.gui.settings_panel import SettingsPanel
from chess_game.utils.constants import STYLES_PATH


class WorkerSignals(QObject):
    best_move = pyqtSignal(object)
    eval_cp = pyqtSignal(object)


@dataclass
class EngineTask(QRunnable):
    board: chess.Board
    engine: StockfishEngine
    want_move: bool
    signals: WorkerSignals

    def run(self) -> None:
        evaluation = self.engine.get_evaluation(self.board)
        self.signals.eval_cp.emit(evaluation)
        if self.want_move:
            self.signals.best_move.emit(self.engine.get_best_move(self.board))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Chess Game")
        self.resize(1200, 800)

        self.game = ChessBoard()
        self.engine = StockfishEngine("1000 Elo")
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(1)
        self.premove: chess.Move | None = None
        self.enable_premove = True

        self.board_widget = BoardWidget()
        self.board_widget.move_played.connect(self._on_player_move)

        self.eval_bar = EvaluationBar()
        self.move_history = MoveHistory(self._on_navigate_history)
        self.settings = SettingsPanel()
        self.settings.difficulty_changed.connect(self._on_difficulty_changed)
        self.settings.legal_moves_toggled.connect(self._on_legal_toggle)
        self.settings.premove_toggled.connect(self._on_premove_toggle)
        self.settings.eval_bar_toggled.connect(self.eval_bar.setVisible)
        self.settings.board_theme_changed.connect(self.board_widget.set_board_theme)
        self.settings.piece_theme_changed.connect(self.board_widget.set_piece_theme)
        self.settings.reset_requested.connect(self._on_new_game)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.addWidget(QLabel("Move History"))
        side_layout.addWidget(self.move_history)
        side_layout.addWidget(self.settings)

        board_container = QWidget()
        board_layout = QHBoxLayout(board_container)
        board_layout.addWidget(self.eval_bar)
        board_layout.addWidget(self.board_widget)

        controls = QWidget()
        control_layout = QHBoxLayout(controls)
        for text, callback in [
            ("New", self._on_new_game),
            ("Undo", self._on_undo),
            ("Redo", self._on_redo),
            ("Flip", self.board_widget.flip),
            ("Save PGN", self._on_save_pgn),
            ("Load PGN", self._on_load_pgn),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            control_layout.addWidget(btn)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(controls)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(board_container)
        split.addWidget(side)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        center_layout.addWidget(split)
        self.setCentralWidget(center)
        self._build_menu()

        self._refresh()

    def _build_menu(self) -> None:
        game_menu = self.menuBar().addMenu("Game")
        for title, callback, shortcut in [
            ("New Game", self._on_new_game, "Ctrl+N"),
            ("Undo", self._on_undo, "Ctrl+Z"),
            ("Redo", self._on_redo, "Ctrl+Y"),
            ("Save PGN", self._on_save_pgn, "Ctrl+S"),
            ("Load PGN", self._on_load_pgn, "Ctrl+O"),
        ]:
            action = QAction(title, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            game_menu.addAction(action)

    def _run_engine(self, want_move: bool) -> None:
        if not self.engine.is_available():
            return
        signals = WorkerSignals()
        signals.eval_cp.connect(self.eval_bar.set_evaluation)
        signals.best_move.connect(self._on_engine_move)
        self.pool.start(EngineTask(self.game.board.copy(stack=True), self.engine, want_move, signals))

    def _refresh(self) -> None:
        self.board_widget.set_board(self.game.board)
        self.move_history.set_moves(self.game.board)
        self._run_engine(want_move=not self.game.board.turn)

    def _on_player_move(self, move: chess.Move) -> None:
        if self.game.board.turn:
            if self.game.push(move):
                self._refresh()
                self._check_game_end()
                if self.enable_premove and self.premove and self.game.board.turn:
                    queued = self.premove
                    self.premove = None
                    self._on_player_move(queued)
        elif self.enable_premove:
            self.premove = move

    def _on_engine_move(self, move: chess.Move | None) -> None:
        if move and not self.game.board.turn and self.game.push(move):
            self._refresh()
            self._check_game_end()

    def _on_difficulty_changed(self, difficulty: str) -> None:
        self.engine.set_difficulty(difficulty)
        self._run_engine(want_move=False)

    def _on_legal_toggle(self, enabled: bool) -> None:
        self.board_widget.show_legal_moves = enabled
        self.board_widget.update()

    def _on_premove_toggle(self, enabled: bool) -> None:
        self.enable_premove = enabled
        if not enabled:
            self.premove = None

    def _on_new_game(self) -> None:
        self.game.reset()
        self.premove = None
        self._refresh()

    def _on_undo(self) -> None:
        self.game.undo()
        if not self.game.board.turn:
            self.game.undo()
        self._refresh()

    def _on_redo(self) -> None:
        self.game.redo()
        self.game.redo()
        self._refresh()

    def _on_save_pgn(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save PGN", "game.pgn", "PGN Files (*.pgn)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.game.to_pgn())

    def _on_load_pgn(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load PGN", "", "PGN Files (*.pgn)")
        if path:
            with open(path, encoding="utf-8") as f:
                self.game.load_pgn(f.read())
            self._refresh()

    def _check_game_end(self) -> None:
        state = self.game.result_state()
        if state:
            QMessageBox.information(self, "Game Over", state.replace("_", " ").title())

    def _on_navigate_history(self, row: int) -> None:
        replay = chess.Board()
        target_ply = min(len(self.game.board.move_stack), (row + 1) * 2)
        for idx, move in enumerate(self.game.board.move_stack):
            if idx >= target_ply:
                break
            replay.push(move)
        self.board_widget.set_board(replay)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.engine.close()
        super().closeEvent(event)


def run() -> None:
    app = QApplication([])
    if STYLES_PATH.exists():
        app.setStyleSheet(STYLES_PATH.read_text(encoding="utf-8"))
    window = MainWindow()
    window.show()
    app.exec()
