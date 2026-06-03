"""Main application window."""

from __future__ import annotations

from pathlib import Path

import chess
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from chess_game.board import ChessBoard
from chess_game.engine import StockfishEngine, StockfishNotFoundError
from chess_game.gui.board_widget import BoardWidget
from chess_game.gui.evaluation_bar import EvaluationBar
from chess_game.gui.move_history import MoveHistory
from chess_game.gui.settings_panel import SettingsPanel


class AIWorker(QObject):
    """Background worker for AI move selection."""

    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, engine: StockfishEngine, board: chess.Board, difficulty: int) -> None:
        super().__init__()
        self.engine = engine
        self.board = board.copy(stack=False)
        self.difficulty = difficulty

    def run(self) -> None:
        """Calculate AI move in worker thread."""
        try:
            move = self.engine.get_best_move(self.board, self.difficulty)
            self.finished.emit(move.uci() if move else '')
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    """Main game window with board, evaluation, history, and settings."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Chess Game')
        self.board = ChessBoard()
        self.difficulty = 300
        self.enable_premove = True
        self.pending_premove: chess.Move | None = None
        self.ai_thread: QThread | None = None
        self.ai_worker: AIWorker | None = None
        self._thinking = False

        self.engine: StockfishEngine | None = None
        self.analysis_engine: StockfishEngine | None = None
        self._init_engine()
        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._update_status('Waiting for move')

    def _init_engine(self) -> None:
        try:
            self.engine = StockfishEngine()
            self.analysis_engine = StockfishEngine(self.engine.stockfish_path)
        except StockfishNotFoundError as exc:
            self.engine = None
            self.analysis_engine = None
            QMessageBox.warning(
                self,
                'Stockfish not found',
                f'{exc}\n\nSet STOCKFISH_PATH to a valid binary to enable AI moves.',
            )

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        self.board_widget = BoardWidget(self.board)
        self.eval_bar = EvaluationBar()
        self.move_history = MoveHistory()

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel('Evaluation'))
        right_layout.addWidget(self.eval_bar, 1)
        right_layout.addWidget(QLabel('Move History'))
        right_layout.addWidget(self.move_history, 2)

        splitter = QSplitter()
        board_container = QWidget()
        board_layout = QHBoxLayout(board_container)
        board_layout.addWidget(self.board_widget)
        splitter.addWidget(board_container)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(central)
        layout.addWidget(splitter)

        self.settings_panel = SettingsPanel()
        self.settings_dock = QDockWidget('Settings', self)
        self.settings_dock.setWidget(self.settings_panel)
        self.settings_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(self.DockWidgetArea.RightDockWidgetArea, self.settings_dock)

        self.eval_timer = QTimer(self)
        self.eval_timer.setInterval(600)
        self.eval_timer.timeout.connect(self._refresh_eval)

        style_path = Path(__file__).resolve().parents[1] / 'resources' / 'styles.qss'
        if style_path.exists():
            self.setStyleSheet(style_path.read_text(encoding='utf-8'))

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu('File')
        file_menu.addAction('New Game', self._new_game)
        file_menu.addAction('Export PGN', self.move_history._save_pgn)
        file_menu.addAction('Exit', self.close)

        edit_menu = menu.addMenu('Edit')
        edit_menu.addAction('Undo Move', self._undo_move)
        edit_menu.addAction('Flip Board', self._flip_board)

        view_menu = menu.addMenu('View')
        view_menu.addAction(self.settings_dock.toggleViewAction())

        help_menu = menu.addMenu('Help')
        help_menu.addAction('About', lambda: QMessageBox.information(self, 'About', 'Desktop Chess Game'))

    def _connect_signals(self) -> None:
        self.board_widget.move_dropped.connect(self._on_user_move)
        self.move_history.position_selected.connect(self._on_position_selected)
        self.settings_panel.difficulty_changed.connect(self._on_difficulty_changed)
        self.settings_panel.options_changed.connect(self._on_options_changed)
        self.settings_panel.new_game_requested.connect(self._new_game)

    def _on_difficulty_changed(self, value: int) -> None:
        self.difficulty = value

    def _on_options_changed(self, options: dict) -> None:
        self.enable_premove = options['enable_premove']
        self.board_widget.set_show_legal_moves(options['show_legal_moves'])
        self.board_widget.set_theme(options['board_theme'])
        self.eval_bar.setVisible(options['show_evaluation'])

    def _on_position_selected(self, fen: str) -> None:
        self.board = ChessBoard.from_fen(fen)
        self.board_widget.set_board(self.board)

    def _on_user_move(self, move_uci: str) -> None:
        move = chess.Move.from_uci(move_uci)

        if self._thinking:
            if self.enable_premove:
                self.pending_premove = move
                self.board_widget.set_premove(move)
                self._update_status('Premove queued')
            return

        if not self.board.make_move(move):
            return

        self.board_widget.set_last_move(move)
        self.board_widget.set_premove(None)
        self.pending_premove = None
        self._sync_board_state()

        if self.board.is_checkmate() or self.board.is_stalemate():
            self._finish_game_status()
            return

        self._start_ai_turn()

    def _start_ai_turn(self) -> None:
        if self.engine is None:
            self._update_status('Stockfish unavailable')
            return

        self._thinking = True
        self._update_status('AI thinking...')
        self.eval_timer.start()

        self.ai_thread = QThread(self)
        self.ai_worker = AIWorker(self.engine, self.board, self.difficulty)
        self.ai_worker.moveToThread(self.ai_thread)
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.finished.connect(self._on_ai_move)
        self.ai_worker.failed.connect(self._on_ai_failed)
        self.ai_worker.finished.connect(self.ai_thread.quit)
        self.ai_worker.failed.connect(self.ai_thread.quit)
        self.ai_thread.finished.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_thread.start()

    def _on_ai_move(self, move_uci: str) -> None:
        self._thinking = False
        self.eval_timer.stop()
        if move_uci:
            move = chess.Move.from_uci(move_uci)
            self.board.make_move(move)
            self.board_widget.set_last_move(move)
            self._sync_board_state()

        self._refresh_eval()

        if self.board.is_checkmate() or self.board.is_stalemate():
            self._finish_game_status()
            return

        if self.pending_premove and self.pending_premove in self.board.legal_moves:
            premove = self.pending_premove
            self.pending_premove = None
            self.board_widget.set_premove(None)
            self._on_user_move(premove.uci())
            return

        if self.board.is_check():
            self._update_status('Check')
        else:
            self._update_status('Waiting for move')

    def _on_ai_failed(self, message: str) -> None:
        self._thinking = False
        self.eval_timer.stop()
        self._update_status(f'AI error: {message}')

    def _refresh_eval(self) -> None:
        if not self.analysis_engine:
            return
        try:
            evaluation = self.analysis_engine.get_evaluation(self.board, self.difficulty)
            self.eval_bar.set_evaluation(evaluation)
        except Exception:  # noqa: BLE001
            pass

    def _sync_board_state(self) -> None:
        self.board_widget.set_board(self.board)
        self.move_history.update_from_board(self.board)

    def _finish_game_status(self) -> None:
        if self.board.is_checkmate():
            winner = 'White' if self.board.turn == chess.BLACK else 'Black'
            self._update_status(f'Checkmate - {winner} wins')
        elif self.board.is_stalemate():
            self._update_status('Stalemate')

    def _update_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def _new_game(self) -> None:
        self.board = ChessBoard()
        self.pending_premove = None
        self.board_widget.set_premove(None)
        self.board_widget.set_last_move(None)
        self.board_widget.set_board(self.board)
        self.move_history.update_from_board(self.board)
        self.eval_bar.set_evaluation(0)
        self._update_status('New game started')

    def _undo_move(self) -> None:
        if self._thinking:
            return
        self.board.undo_move()
        self.board.undo_move()
        self._sync_board_state()
        self._update_status('Move undone')

    def _flip_board(self) -> None:
        self.board_widget.set_flipped(self.board_widget.show_from_white)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.engine:
            self.engine.shutdown()
        if self.analysis_engine:
            self.analysis_engine.shutdown()
        super().closeEvent(event)
