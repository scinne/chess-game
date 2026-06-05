"""Main application window."""

from __future__ import annotations

import io
import logging
import random
import time
from pathlib import Path

import chess
import chess.pgn
from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from chess_game.board import ChessBoard
from chess_game.engine import StockfishEngine, StockfishNotFoundError
from chess_game.gui.board_widget import BoardWidget
from chess_game.gui.evaluation_bar import EvaluationBar
from chess_game.gui.move_history import MoveHistory
from chess_game.gui.review_binding import ReviewPanelBinding
from chess_game.review.annotations import ReviewAnnotator
from chess_game.review.coach import BotPersonalityService, CoachService
from chess_game.review.controller import AnalysisController
from chess_game.review.engine_manager import StockfishAnalysisManager
from chess_game.review.models import AnalysisResult, MoveAnnotation
from chess_game.review.move_tree import MoveTree, VariationManager
from chess_game.review.navigation import GameNavigator
from chess_game.review.notation import NotationRenderer
from chess_game.review.opening import OpeningRepertoire
from chess_game.review.overlays import BoardOverlayManager
from chess_game.settings import SettingsManager

LOGGER = logging.getLogger(__name__)

BOT_PROFILES = (
    {'name': 'Nora Nook', 'elo': 250, 'group': 'Beginner', 'color': '#d99568', 'dialogue': 'I still hang queens, but I do it with confidence.'},
    {'name': 'Benji Bean', 'elo': 550, 'group': 'Beginner', 'color': '#7fb3d5', 'dialogue': 'I know forks exist. Sometimes I even see them.'},
    {'name': 'Lina Leaf', 'elo': 650, 'group': 'Beginner', 'color': '#91c788', 'dialogue': 'Careful, I have discovered development.'},
    {'name': 'Rafa Reed', 'elo': 800, 'group': 'Intermediate', 'color': '#c4a484', 'dialogue': 'One clean tactic and I become unbearable.'},
    {'name': 'Maya Vale', 'elo': 1000, 'group': 'Intermediate', 'color': '#b48ead', 'dialogue': 'I play principled chess until temptation arrives.'},
    {'name': 'Theo Flint', 'elo': 1200, 'group': 'Intermediate', 'color': '#e0b15d', 'dialogue': 'I will trade into an endgame and pretend it was planned.'},
    {'name': 'Iris Stone', 'elo': 1500, 'group': 'Advanced', 'color': '#6fa8a6', 'dialogue': 'Loose pieces make me very interested.'},
    {'name': 'Caden Knox', 'elo': 1600, 'group': 'Advanced', 'color': '#a36d90', 'dialogue': 'I like pressure, pins, and making you solve things.'},
    {'name': 'Serena Pike', 'elo': 2000, 'group': 'Master', 'color': '#789262', 'dialogue': 'Tiny weaknesses are still weaknesses.'},
    {'name': 'Victor Sage', 'elo': 2200, 'group': 'Master', 'color': '#607d9c', 'dialogue': 'I will not rush. That is usually the problem.'},
)
COACH_PROFILES = (
    {
        'name': 'Beginner Coach',
        'elo': 400,
        'group': 'Coach',
        'color': '#6f9fd8',
        'description': 'Gentle guidance on development, safety, and simple tactics.',
        'dialogue': 'I will explain the ideas as we play.',
    },
    {
        'name': 'Novice Coach',
        'elo': 800,
        'group': 'Coach',
        'color': '#73aa6f',
        'description': 'Practical help with opening plans and loose pieces.',
        'dialogue': 'We will build habits one move at a time.',
    },
    {
        'name': 'Intermediate Coach',
        'elo': 1200,
        'group': 'Coach',
        'color': '#c39a4b',
        'description': 'Teaches tactics, candidate moves, and positional tradeoffs.',
        'dialogue': 'I will point out what changed after each move.',
    },
    {
        'name': 'Advanced Coach',
        'elo': 1600,
        'group': 'Coach',
        'color': '#9a7bc2',
        'description': 'Sharper review of plans, weaknesses, and missed chances.',
        'dialogue': 'Let us connect tactics to the position.',
    },
    {
        'name': 'Expert Coach',
        'elo': 2000,
        'group': 'Coach',
        'color': '#607d9c',
        'description': 'Deeper explanations for engine choices and strategic themes.',
        'dialogue': 'I will show why the engine move works.',
    },
)

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}
PIECE_SYMBOLS = {
    (chess.WHITE, chess.PAWN): '♙',
    (chess.WHITE, chess.KNIGHT): '♘',
    (chess.WHITE, chess.BISHOP): '♗',
    (chess.WHITE, chess.ROOK): '♖',
    (chess.WHITE, chess.QUEEN): '♕',
    (chess.BLACK, chess.PAWN): '♟',
    (chess.BLACK, chess.KNIGHT): '♞',
    (chess.BLACK, chess.BISHOP): '♝',
    (chess.BLACK, chess.ROOK): '♜',
    (chess.BLACK, chess.QUEEN): '♛',
}
INITIAL_COUNTS = {
    chess.PAWN: 8,
    chess.KNIGHT: 2,
    chess.BISHOP: 2,
    chess.ROOK: 2,
    chess.QUEEN: 1,
}
REVIEW_CATEGORIES_FULL = ('brilliant', 'great', 'book', 'best', 'excellent', 'good', 'inaccuracy', 'mistake', 'miss', 'blunder')
REVIEW_CATEGORIES_MIN = ('brilliant', 'great', 'best', 'inaccuracy', 'mistake', 'miss', 'blunder')
REVIEW_MARKERS = {
    'brilliant': '!!',
    'great': '!',
    'book': 'book',
    'best': '*',
    'excellent': '+',
    'good': 'ok',
    'inaccuracy': '?!',
    'mistake': '?',
    'miss': 'x',
    'blunder': '??',
    'pending': '',
}


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
    """Main game window with start menu, play board, analysis, and review."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Chess Game')
        self.resize(1320, 860)
        self.setMinimumSize(1080, 720)
        self.board = ChessBoard()
        self.bot_profile = BOT_PROFILES[0]
        self.coach_profile = COACH_PROFILES[1]
        self.difficulty = int(self.bot_profile['elo'])
        self.game_mode = 'bot'
        self.player_side: chess.Color = chess.WHITE
        self.pending_side_choice = 'white'
        self.enable_premove = True
        self.pending_premove: chess.Move | None = None
        self.review_board_state = ChessBoard()
        self.selected_bot_profile = BOT_PROFILES[0]
        self.review_rows: list[dict] = []
        self.review_index = 0
        self.review_navigator = GameNavigator()
        self.review_annotations: dict[int, MoveAnnotation] = {}
        self.review_category_positions: dict[str, int] = {}
        self.review_binding: ReviewPanelBinding | None = None
        self.opening_repertoire = OpeningRepertoire()
        self.review_annotator = ReviewAnnotator()
        self.move_tree = MoveTree()
        self.variation_manager = VariationManager(self.move_tree)
        self.notation_renderer = NotationRenderer()
        self.overlay_manager = BoardOverlayManager()
        self.coach_service = CoachService()
        self.bot_personality_service = BotPersonalityService()
        self.settings_manager = SettingsManager()
        self.selected_engine_line = None
        self.selected_review_node_id: str | None = None
        self.selected_variation_fen: str | None = None
        self.selected_analysis_fen: str | None = None
        self.active_analysis: StockfishAnalysisManager | None = None
        self.analysis_controller: AnalysisController | None = None
        self.analysis_line_count = 3
        self.analysis_time_seconds = 0.15
        self.deep_analysis_time_seconds = 0.8
        self.analysis_depth = 14
        self.analysis_threads = 2
        self.cloud_stockfish_enabled = False
        self.cloud_target_depth = 41
        self.ai_thread: QThread | None = None
        self.ai_worker: AIWorker | None = None
        self._thinking = False
        self._game_over = False
        self._hint_stage = 0
        self._analysis_enabled = False
        self._active_analysis_fen: str | None = None
        self._shallow_analysis_timer = QTimer(self)
        self._shallow_analysis_timer.setSingleShot(True)
        self._deep_analysis_timer = QTimer(self)
        self._deep_analysis_timer.setSingleShot(True)
        self._ui_update_timer = QTimer(self)
        self._ui_update_timer.setSingleShot(True)

        self.engine: StockfishEngine | None = None
        self.analysis_engine: StockfishEngine | None = None
        self._init_engine()
        self.active_analysis = StockfishAnalysisManager(self.analysis_engine.stockfish_path if self.analysis_engine else None)
        self.active_analysis.analysis_ready.connect(self._on_active_analysis_ready)
        self.active_analysis.analysis_failed.connect(self._on_active_analysis_failed)
        self.analysis_controller = AnalysisController(self.active_analysis)
        self._build_ui()
        self.review_binding = ReviewPanelBinding(self)
        self._apply_runtime_settings()
        self._build_menu()
        self._connect_signals()
        self._apply_bot_profile()
        self._show_start_menu()

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
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.start_page = self._build_start_page()
        self.new_game_page = self._build_new_game_page()
        self.learn_page = self._build_learn_page()
        self.coach_select_page = self._build_coach_select_page()
        self.bot_select_page = self._build_bot_select_page()
        self.game_page = self._build_game_page()
        self.review_page = self._build_review_page()
        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.new_game_page)
        self.stack.addWidget(self.learn_page)
        self.stack.addWidget(self.coach_select_page)
        self.stack.addWidget(self.bot_select_page)
        self.stack.addWidget(self.game_page)
        self.stack.addWidget(self.review_page)

        self.eval_timer = QTimer(self)
        self.eval_timer.setInterval(250)
        self.eval_timer.timeout.connect(self._refresh_eval)
        self._shallow_analysis_timer.timeout.connect(lambda: self._request_active_analysis(self.analysis_time_seconds))
        self._deep_analysis_timer.timeout.connect(lambda: self._request_active_analysis(self.deep_analysis_time_seconds))

        style_path = Path(__file__).resolve().parents[1] / 'resources' / 'styles.qss'
        if style_path.exists():
            self.setStyleSheet(style_path.read_text(encoding='utf-8'))

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName('StartPage')
        layout = QHBoxLayout(page)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(24)

        menu = QFrame()
        menu.setObjectName('MainMenuPanel')
        menu_layout = QVBoxLayout(menu)
        menu_layout.setContentsMargins(24, 24, 24, 24)
        menu_layout.setSpacing(10)
        title = QLabel('Chess')
        title.setObjectName('MenuTitle')
        player = QLabel('Player')
        player.setObjectName('MenuPlayer')
        menu_layout.addWidget(title)
        menu_layout.addWidget(player)
        menu_layout.addSpacing(18)

        self.menu_play_tab = self._menu_button('Play', 'Quick start and opponents')
        self.learn_button = self._menu_button('Learn', 'Coach, lessons, training')
        self.analysis_menu_button = self._menu_button('Analysis', 'PGN and review tools')
        self.settings_menu_button = self._menu_button('Settings', 'Board and engine options')
        for button in (self.menu_play_tab, self.learn_button, self.analysis_menu_button, self.settings_menu_button):
            button.setMinimumSize(260, 70)
            menu_layout.addWidget(button)
        menu_layout.addStretch(1)

        context = QFrame()
        context.setObjectName('StartSide')
        context_layout = QVBoxLayout(context)
        context_layout.setContentsMargins(24, 24, 24, 24)
        context_layout.setSpacing(16)
        self.start_context_title = QLabel('Play')
        self.start_context_title.setObjectName('PanelHeader')
        context_layout.addWidget(self.start_context_title)
        self.start_context_stack = QStackedWidget()
        context_layout.addWidget(self.start_context_stack, 1)

        play_page = QWidget()
        play_layout = QVBoxLayout(play_page)
        play_layout.setContentsMargins(0, 0, 0, 0)
        play_layout.setSpacing(12)
        self.quick_play_button = self._context_card('Play 10 min', 'Start the last played time control.')
        self.new_game_button = self._context_card('New Game', 'Choose friend or bot.')
        self.play_bots_button = self._context_card('Play Bots', 'Pick an opponent and side.')
        self.play_friend_button = self._context_card('Play a Friend', 'Local same-device game.')
        for button in (self.quick_play_button, self.new_game_button, self.play_bots_button, self.play_friend_button):
            play_layout.addWidget(button)
        play_layout.addStretch(1)

        learn_page = QWidget()
        learn_layout = QVBoxLayout(learn_page)
        learn_layout.setContentsMargins(0, 0, 0, 0)
        learn_layout.setSpacing(12)
        self.play_coach_home_button = self._context_card('Play Coach', 'Teaching opponent with guided comments.')
        self.lessons_home_button = self._context_card('Lessons', 'Coming soon.')
        self.training_home_button = self._context_card('Training', 'Coming soon.')
        self.lessons_home_button.setEnabled(False)
        self.training_home_button.setEnabled(False)
        for button in (self.play_coach_home_button, self.lessons_home_button, self.training_home_button):
            learn_layout.addWidget(button)
        learn_layout.addStretch(1)

        analysis_page = QWidget()
        analysis_layout = QVBoxLayout(analysis_page)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        analysis_layout.setSpacing(12)
        self.upload_pgn_button = self._context_card('Upload PGN', 'Import a game for analysis.')
        self.review_from_menu_button = self._context_card('Review Finished Game', 'Open review for the latest finished game.')
        self.free_analysis_button = self._context_card('Free Analysis Board', 'Coming soon.')
        self.review_from_menu_button.setVisible(False)
        self.free_analysis_button.setEnabled(False)
        for button in (self.upload_pgn_button, self.review_from_menu_button, self.free_analysis_button):
            analysis_layout.addWidget(button)
        analysis_layout.addStretch(1)

        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(12)
        self.board_settings_button = self._context_card('Board Settings', 'Coordinates, overlays, and move hints.')
        self.engine_settings_home_button = self._context_card('Engine Settings', 'Stockfish time, lines, and cloud toggle.')
        self.sound_settings_button = self._context_card('Sound Settings', 'Coming soon.')
        self.sound_settings_button.setEnabled(False)
        for button in (self.board_settings_button, self.engine_settings_home_button, self.sound_settings_button):
            settings_layout.addWidget(button)
        settings_layout.addStretch(1)

        for page_widget in (play_page, learn_page, analysis_page, settings_page):
            self.start_context_stack.addWidget(page_widget)

        layout.addWidget(menu, 0)
        layout.addWidget(context, 1)
        return page

    def _context_card(self, title: str, subtitle: str) -> QPushButton:
        button = QPushButton(f'{title}\n{subtitle}')
        button.setObjectName('ContextCard')
        button.setMinimumHeight(84)
        return button

    def _build_learn_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName('StartPage')
        layout = QHBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(24)

        panel = QFrame()
        panel.setObjectName('MainMenuPanel')
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(28, 28, 28, 28)
        panel_layout.setSpacing(14)
        title = QLabel('Learn')
        title.setObjectName('MenuTitle')
        panel_layout.addWidget(title)
        self.play_coach_button = self._menu_button('Play Coach', 'Teaching opponent')
        self.lessons_placeholder_button = self._menu_button('Lessons', 'Coming soon')
        self.training_placeholder_button = self._menu_button('Training', 'Coming soon')
        self.learn_back_button = QPushButton('Menu')
        self.learn_back_button.setObjectName('GhostButton')
        self.lessons_placeholder_button.setEnabled(False)
        self.training_placeholder_button.setEnabled(False)
        panel_layout.addWidget(self.play_coach_button)
        panel_layout.addWidget(self.lessons_placeholder_button)
        panel_layout.addWidget(self.training_placeholder_button)
        panel_layout.addSpacing(8)
        panel_layout.addWidget(self.learn_back_button)
        panel_layout.addStretch(1)

        layout.addStretch(1)
        layout.addWidget(panel)
        layout.addStretch(1)
        return page

    def _build_coach_select_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName('StartPage')
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 28, 38, 32)
        layout.setSpacing(14)

        top = QHBoxLayout()
        title = QLabel('Play Coach')
        title.setObjectName('MenuTitle')
        self.coach_select_back_button = QPushButton('Learn')
        self.coach_select_back_button.setObjectName('GhostButton')
        top.addWidget(self.coach_select_back_button)
        top.addStretch(1)
        top.addWidget(title)
        top.addStretch(1)
        layout.addLayout(top)

        selected_panel = QFrame()
        selected_panel.setObjectName('SelectedBotPanel')
        selected_layout = QHBoxLayout(selected_panel)
        selected_layout.setContentsMargins(16, 14, 16, 14)
        selected_layout.setSpacing(14)
        self.selected_coach_icon = QLabel()
        self.selected_coach_name = QLabel('')
        self.selected_coach_name.setObjectName('SelectedBotName')
        self.selected_coach_dialogue = QLabel('')
        self.selected_coach_dialogue.setObjectName('SelectedBotDialogue')
        self.selected_coach_dialogue.setWordWrap(True)
        selected_text = QVBoxLayout()
        selected_text.setSpacing(4)
        selected_text.addWidget(self.selected_coach_name)
        selected_text.addWidget(self.selected_coach_dialogue)
        self.coach_play_button = QPushButton('Play')
        self.coach_play_button.setObjectName('StartAction')
        selected_layout.addWidget(self.selected_coach_icon)
        selected_layout.addLayout(selected_text, 1)
        selected_layout.addWidget(self.coach_play_button)
        layout.addWidget(selected_panel)

        grid_panel = QFrame()
        grid_panel.setObjectName('BotGroupPanel')
        grid = QGridLayout(grid_panel)
        grid.setContentsMargins(18, 16, 18, 18)
        grid.setSpacing(12)
        for index, coach in enumerate(COACH_PROFILES):
            grid.addWidget(self._coach_card(coach), index // 3, index % 3)
        layout.addWidget(grid_panel, 1)
        self._select_coach(COACH_PROFILES[1])
        return page

    def _menu_button(self, title: str, subtitle: str) -> QPushButton:
        button = QPushButton(f'{title}\n{subtitle}')
        button.setObjectName('MenuButton')
        button.setMinimumSize(300, 76)
        return button

    def _build_new_game_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName('StartPage')
        layout = QHBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(24)

        panel = QFrame()
        panel.setObjectName('MainMenuPanel')
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(28, 28, 28, 28)
        panel_layout.setSpacing(14)
        title = QLabel('New Game')
        title.setObjectName('MenuTitle')
        panel_layout.addWidget(title)

        self.new_friend_button = self._menu_button('Play a Friend', 'Local same-device game')
        self.new_bots_button = self._menu_button('Play Bots', 'Choose bot and side')
        self.new_back_button = QPushButton('Menu')
        self.new_back_button.setObjectName('GhostButton')
        panel_layout.addWidget(self.new_friend_button)
        panel_layout.addWidget(self.new_bots_button)
        panel_layout.addSpacing(8)
        panel_layout.addWidget(self.new_back_button)
        panel_layout.addStretch(1)

        layout.addStretch(1)
        layout.addWidget(panel)
        layout.addStretch(1)
        return page

    def _build_bot_select_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName('StartPage')
        layout = QVBoxLayout(page)
        layout.setContentsMargins(38, 28, 38, 32)
        layout.setSpacing(14)

        top = QHBoxLayout()
        title = QLabel('Play Bots')
        title.setObjectName('MenuTitle')
        self.bot_select_back_button = QPushButton('Menu')
        self.bot_select_back_button.setObjectName('GhostButton')
        top.addWidget(self.bot_select_back_button)
        top.addStretch(1)
        top.addWidget(title)
        top.addStretch(1)
        layout.addLayout(top)

        side_panel = QFrame()
        side_panel.setObjectName('SideChoicePanel')
        side_layout = QHBoxLayout(side_panel)
        side_layout.setContentsMargins(16, 12, 16, 12)
        side_layout.setSpacing(10)
        side_label = QLabel('Play as')
        side_label.setObjectName('SideChoiceLabel')
        self.side_white_button = QPushButton('White')
        self.side_black_button = QPushButton('Black')
        self.side_random_button = QPushButton('Random')
        for button in (self.side_white_button, self.side_black_button, self.side_random_button):
            button.setObjectName('SideButton')
            side_layout.addWidget(button)
        side_layout.insertWidget(0, side_label)
        side_layout.addStretch(1)
        layout.addWidget(side_panel)

        selected_panel = QFrame()
        selected_panel.setObjectName('SelectedBotPanel')
        selected_layout = QHBoxLayout(selected_panel)
        selected_layout.setContentsMargins(16, 14, 16, 14)
        selected_layout.setSpacing(14)
        self.selected_bot_icon = QLabel()
        self.selected_bot_icon.setObjectName('SelectedBotIcon')
        self.selected_bot_name = QLabel('')
        self.selected_bot_name.setObjectName('SelectedBotName')
        self.selected_bot_dialogue = QLabel('')
        self.selected_bot_dialogue.setObjectName('SelectedBotDialogue')
        self.selected_bot_dialogue.setWordWrap(True)
        selected_text = QVBoxLayout()
        selected_text.setSpacing(4)
        selected_text.addWidget(self.selected_bot_name)
        selected_text.addWidget(self.selected_bot_dialogue)
        self.bot_play_button = QPushButton('Play')
        self.bot_play_button.setObjectName('StartAction')
        selected_layout.addWidget(self.selected_bot_icon)
        selected_layout.addLayout(selected_text, 1)
        selected_layout.addWidget(self.bot_play_button)
        layout.addWidget(selected_panel)

        scroll = QScrollArea()
        scroll.setObjectName('BotScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)
        for group in ('Beginner', 'Intermediate', 'Advanced', 'Master'):
            content_layout.addWidget(self._bot_group_panel(group))
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self._select_side('white')
        self._select_bot(BOT_PROFILES[0])
        return page

    def _bot_group_panel(self, group: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName('BotGroupPanel')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel(group)
        title.setObjectName('BotGroupTitle')
        count = QLabel(f"{sum(1 for bot in BOT_PROFILES if bot['group'] == group)} bots")
        count.setObjectName('BotGroupCount')
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(count)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(12)
        group_bots = [bot for bot in BOT_PROFILES if bot['group'] == group]
        for index, bot in enumerate(group_bots):
            grid.addWidget(self._bot_card(bot), index // 3, index % 3)
        layout.addLayout(grid)
        return panel

    def _bot_card(self, bot: dict) -> QPushButton:
        button = QPushButton(f"{bot['name']}  {bot['elo']}\n{bot['dialogue']}")
        button.setObjectName('BotCardButton')
        avatar = self._bot_avatar(bot)
        button.setIcon(QIcon(avatar))
        button.setIconSize(avatar.size())
        button.setMinimumSize(260, 96)
        button.clicked.connect(lambda _checked=False, value=bot: self._select_bot(value))
        return button

    def _select_bot(self, bot: dict) -> None:
        self.selected_bot_profile = bot
        self.selected_bot_icon.setPixmap(self._bot_avatar(bot))
        self.selected_bot_name.setText(f"{bot['name']}  {bot['elo']} Elo")
        self.selected_bot_dialogue.setText(str(bot['dialogue']))

    def _coach_card(self, coach: dict) -> QPushButton:
        button = QPushButton(f"{coach['name']}  {coach['elo']}\n{coach['description']}")
        button.setObjectName('BotCardButton')
        avatar = self._bot_avatar(coach)
        button.setIcon(QIcon(avatar))
        button.setIconSize(avatar.size())
        button.setMinimumSize(260, 112)
        button.clicked.connect(lambda _checked=False, value=coach: self._select_coach(value))
        return button

    def _select_coach(self, coach: dict) -> None:
        self.coach_profile = coach
        self.selected_coach_icon.setPixmap(self._bot_avatar(coach))
        self.selected_coach_name.setText(f"{coach['name']}  {coach['elo']} Elo")
        self.selected_coach_dialogue.setText(str(coach['description']))

    def _bot_avatar(self, bot: dict) -> QPixmap:
        pixmap = QPixmap(56, 56)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(str(bot['color'])))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 4, 48, 48, 12, 12)
        painter.setBrush(QColor('#fff8ee'))
        painter.drawEllipse(18, 10, 20, 20)
        painter.setBrush(QColor('#263126'))
        painter.drawEllipse(23, 18, 3, 3)
        painter.drawEllipse(31, 18, 3, 3)
        painter.setBrush(QColor('#5b4636'))
        painter.drawRoundedRect(15, 30, 26, 20, 8, 8)
        painter.setPen(QColor('#ffffff'))
        font = QFont('Segoe UI')
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        initials = ''.join(part[0] for part in str(bot['name']).split()[:2])
        painter.drawText(pixmap.rect().adjusted(0, 33, 0, 0), Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        return pixmap

    def _build_game_page(self) -> QWidget:
        page = QWidget()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_panel.setObjectName('BoardColumn')
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(26, 18, 26, 18)
        left_layout.setSpacing(10)

        self.board_widget = BoardWidget(self.board)
        self.eval_bar = EvaluationBar()
        self.eval_bar.setFixedWidth(34)
        self.move_history = MoveHistory()
        self.move_history.export_button.hide()

        self.bot_strip = self._player_strip('Bot', '300 Elo')
        self.bot_name_label = self.bot_strip.findChild(QLabel, 'StripName')
        self.bot_rating_label = self.bot_strip.findChild(QLabel, 'StripRating')
        self.bot_captures_label = self.bot_strip.findChild(QLabel, 'CapturedPieces')

        board_row = QWidget()
        board_row_layout = QHBoxLayout(board_row)
        board_row_layout.setContentsMargins(0, 0, 0, 0)
        board_row_layout.setSpacing(8)
        board_row_layout.addWidget(self.eval_bar)
        board_row_layout.addWidget(self.board_widget, 1)

        self.player_strip = self._player_strip('Player', '')
        self.player_captures_label = self.player_strip.findChild(QLabel, 'CapturedPieces')

        left_layout.addWidget(self.bot_strip)
        left_layout.addWidget(board_row, 1)
        left_layout.addWidget(self.player_strip)

        right_panel = QWidget()
        right_panel.setObjectName('CoachPanel')
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)

        self.panel_title = QLabel('Play Bot')
        self.panel_title.setObjectName('PanelHeader')
        self.status_label = QLabel('Waiting for move')
        self.status_label.setObjectName('GameStatus')
        self.opening_label = QLabel('Opening: Starting position')
        self.opening_label.setObjectName('OpeningLabel')

        self.analysis_box = QTextEdit()
        self.analysis_box.setObjectName('AnalysisBox')
        self.analysis_box.setReadOnly(True)
        self.analysis_box.setMaximumHeight(150)

        moves_title = QLabel('Moves')
        moves_title.setObjectName('MovesTitle')

        self.resign_button = QPushButton('Resign')
        self.resign_button.setObjectName('ActionButton')
        self.hint_button = QPushButton('Hint')
        self.hint_button.setObjectName('ActionButton')
        self.undo_button = QPushButton('Undo')
        self.undo_button.setObjectName('ActionButton')
        self.review_button = QPushButton('Review')
        self.review_button.setObjectName('ActionButton')
        self.review_button.setVisible(False)
        self.game_settings_button = QPushButton('Settings')
        self.game_settings_button.setObjectName('ActionButton')
        self.menu_button = QPushButton('Menu')
        self.menu_button.setObjectName('ActionButton')

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        for button in (self.resign_button, self.hint_button, self.undo_button):
            action_row.addWidget(button)

        utility_row = QHBoxLayout()
        utility_row.setSpacing(10)
        utility_row.addWidget(self.review_button)
        utility_row.addWidget(self.game_settings_button)
        utility_row.addWidget(self.menu_button)

        right_layout.addWidget(self.panel_title)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.analysis_box)
        right_layout.addWidget(self.opening_label)
        right_layout.addWidget(moves_title)
        right_layout.addWidget(self.move_history, 1)
        right_layout.addLayout(action_row)
        right_layout.addLayout(utility_row)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([840, 480])

        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        return page

    def _build_review_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName('ReviewPage')
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(10)

        control_row = QHBoxLayout()
        control_row.setSpacing(10)
        self.review_menu_button = QPushButton('Menu')
        self.review_menu_button.setObjectName('ReviewTopButton')
        self.review_settings_button = QPushButton('Settings')
        self.review_settings_button.setObjectName('ReviewTopButton')
        self.review_cloud_button = QPushButton('Cloud Off')
        self.review_cloud_button.setObjectName('ReviewTopButton')
        self.review_toggle_button = QPushButton('Summary')
        self.review_toggle_button.setObjectName('ReviewTopButton')
        control_row.addWidget(self.review_menu_button)
        control_row.addStretch(1)
        control_row.addWidget(self.review_cloud_button)
        control_row.addWidget(self.review_settings_button)
        control_row.addWidget(self.review_toggle_button)

        self.review_is_full = True
        content = QSplitter(Qt.Orientation.Horizontal)
        board_panel = QWidget()
        board_panel.setObjectName('ReviewBoardColumn')
        board_layout = QVBoxLayout(board_panel)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(10)

        self.review_bot_strip = self._player_strip('Bot', '')
        self.review_bot_name_label = self.review_bot_strip.findChild(QLabel, 'StripName')
        self.review_bot_rating_label = self.review_bot_strip.findChild(QLabel, 'StripRating')
        self.review_bot_captures_label = self.review_bot_strip.findChild(QLabel, 'CapturedPieces')

        self.review_board_widget = BoardWidget(self.review_board_state)
        self.review_eval_bar = EvaluationBar()
        self.review_eval_bar.setFixedWidth(34)

        review_board_row = QWidget()
        review_board_row_layout = QHBoxLayout(review_board_row)
        review_board_row_layout.setContentsMargins(0, 0, 0, 0)
        review_board_row_layout.setSpacing(8)
        review_board_row_layout.addWidget(self.review_eval_bar)
        review_board_row_layout.addWidget(self.review_board_widget, 1)

        self.review_player_strip = self._player_strip('Player', '')
        self.review_player_captures_label = self.review_player_strip.findChild(QLabel, 'CapturedPieces')

        board_layout.addWidget(self.review_bot_strip)
        board_layout.addWidget(review_board_row, 1)
        board_layout.addWidget(self.review_player_strip)

        self.review_side_stack = QStackedWidget()
        self.review_side_stack.setObjectName('ReviewSide')

        summary_page = QWidget()
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(14)
        summary_title = QLabel('Game Review')
        summary_title.setObjectName('PanelHeader')
        summary_layout.addWidget(summary_title)
        review_cards = QHBoxLayout()
        review_cards.setSpacing(10)
        self.review_player_card = self._review_stat_card('Player', '0.0', 'Accuracy')
        self.review_bot_card = self._review_stat_card(str(self.bot_profile['name']), '0.0', 'Accuracy')
        self.review_rating_card = self._review_stat_card('Game Rating', '100', 'Player / Bot')
        review_cards.addWidget(self.review_player_card)
        review_cards.addWidget(self.review_bot_card)
        review_cards.addWidget(self.review_rating_card)
        summary_layout.addLayout(review_cards)

        self.review_summary_table = QTableWidget(0, 4)
        self.review_summary_table.setObjectName('ReviewSummaryTable')
        self.review_summary_table.setHorizontalHeaderLabels(['Type', 'Player', 'Mark', 'Bot'])
        self.review_summary_table.verticalHeader().setVisible(False)
        self.review_summary_table.setAlternatingRowColors(True)
        self.review_summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.review_summary_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.review_summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 4):
            self.review_summary_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        summary_layout.addWidget(self.review_summary_table, 1)
        self.review_opening_summary = QLabel('Opening: Starting position')
        self.review_opening_summary.setObjectName('OpeningLabel')
        self.review_opening_summary.setWordWrap(True)
        self.review_start_button = QPushButton('Start Review')
        self.review_start_button.setObjectName('StartAction')
        summary_layout.addWidget(self.review_opening_summary)
        summary_layout.addWidget(self.review_start_button)

        move_page = QWidget()
        right_layout = QVBoxLayout(move_page)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        coach_card = QFrame()
        coach_card.setObjectName('ReviewCoachPanel')
        coach_layout = QHBoxLayout(coach_card)
        coach_layout.setContentsMargins(14, 14, 14, 14)
        coach_layout.setSpacing(12)
        self.review_coach_avatar = QLabel()
        self.review_coach_avatar.setPixmap(self._bot_avatar(self.bot_profile))
        coach_text = QVBoxLayout()
        coach_text.setSpacing(6)
        self.review_move_header = QLabel('Select a move')
        self.review_move_header.setObjectName('SelectedBotName')
        self.review_coach_label = QLabel('Select a move and I will look at it with Stockfish.')
        self.review_coach_label.setObjectName('CoachComment')
        self.review_coach_label.setWordWrap(True)
        coach_text.addWidget(self.review_move_header)
        coach_text.addWidget(self.review_coach_label)
        coach_layout.addWidget(self.review_coach_avatar)
        coach_layout.addLayout(coach_text, 1)
        right_layout.addWidget(coach_card)

        self.review_analysis_box = QTextEdit()
        self.review_analysis_box.setObjectName('AnalysisBox')
        self.review_analysis_box.setReadOnly(True)
        self.review_analysis_box.setMaximumHeight(130)
        self.review_analysis_box.hide()

        self.review_lines_table = QTableWidget(0, 3)
        self.review_lines_table.setObjectName('ReviewLinesTable')
        self.review_lines_table.setHorizontalHeaderLabels(['Eval', 'Best', 'Line'])
        self.review_lines_table.verticalHeader().setVisible(False)
        self.review_lines_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.review_lines_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.review_lines_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.review_lines_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.review_lines_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.review_lines_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.review_lines_table.setMaximumHeight(130)
        right_layout.addWidget(self.review_lines_table)

        self.review_moves_table = QTableWidget(0, 4)
        self.review_moves_table.setObjectName('ReviewMovesTable')
        self.review_moves_table.setHorizontalHeaderLabels(['#', 'White', 'Black', 'Result'])
        self.review_moves_table.verticalHeader().setVisible(False)
        self.review_moves_table.setAlternatingRowColors(True)
        self.review_moves_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.review_moves_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.review_moves_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.review_moves_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.review_moves_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.review_moves_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.review_moves_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.review_box = QTextEdit()
        self.review_box.setObjectName('ReviewBox')
        self.review_box.setReadOnly(True)
        self.review_box.hide()
        self.review_add_line_button = QPushButton('Add Line')
        self.review_add_line_button.setObjectName('GhostButton')
        self.review_promote_button = QPushButton('Promote Variation')
        self.review_promote_button.setObjectName('GhostButton')
        line_actions = QHBoxLayout()
        line_actions.setSpacing(10)
        line_actions.addWidget(self.review_add_line_button)
        line_actions.addWidget(self.review_promote_button)
        right_layout.addWidget(self.review_moves_table, 4)
        right_layout.addLayout(line_actions)

        review_nav = QHBoxLayout()
        review_nav.setSpacing(10)
        self.review_first_button = QPushButton('|<')
        self.review_prev_button = QPushButton('<')
        self.review_next_button = QPushButton('>')
        self.review_final_button = QPushButton('>|')
        for button in (self.review_first_button, self.review_prev_button, self.review_next_button, self.review_final_button):
            button.setObjectName('ReviewNavButton')
            review_nav.addWidget(button)
        right_layout.addLayout(review_nav)
        self.review_side_stack.addWidget(summary_page)
        self.review_side_stack.addWidget(move_page)

        content.addWidget(board_panel)
        content.addWidget(self.review_side_stack)
        content.setSizes([760, 560])

        layout.addLayout(control_row)
        layout.addWidget(content, 1)
        return page

    def _review_stat_card(self, title: str, value: str, caption: str) -> QFrame:
        card = QFrame()
        card.setObjectName('ReviewStatCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setObjectName('ReviewCardTitle')
        value_label = QLabel(value)
        value_label.setObjectName('ReviewCardValue')
        caption_label = QLabel(caption)
        caption_label.setObjectName('ReviewCardCaption')

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(caption_label)
        return card

    def _player_strip(self, name: str, rating: str) -> QFrame:
        strip = QFrame()
        strip.setObjectName('PlayerStrip')
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        name_label = QLabel(name)
        name_label.setObjectName('StripName')
        rating_label = QLabel(rating)
        rating_label.setObjectName('StripRating')
        pieces_label = QLabel('')
        pieces_label.setObjectName('CapturedPieces')

        layout.addWidget(name_label)
        layout.addWidget(rating_label)
        layout.addStretch(1)
        layout.addWidget(pieces_label)
        return strip

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu('File')
        file_menu.addAction('Return to Menu', self._show_start_menu)
        file_menu.addAction('New Game', self._new_game)
        file_menu.addAction('Upload PGN', self._upload_pgn)
        file_menu.addAction('Export PGN', self.move_history._save_pgn)
        file_menu.addAction('Exit', self.close)

        edit_menu = menu.addMenu('Edit')
        edit_menu.addAction('Undo Move', self._undo_move)
        edit_menu.addAction('Hint', self._hint)
        edit_menu.addAction('Flip Board', self._flip_board)
        menu.hide()

    def _connect_signals(self) -> None:
        self.menu_play_tab.clicked.connect(lambda: self._show_start_context(0, 'Play'))
        self.learn_button.clicked.connect(lambda: self._show_start_context(1, 'Learn'))
        self.analysis_menu_button.clicked.connect(lambda: self._show_start_context(2, 'Analysis'))
        self.settings_menu_button.clicked.connect(lambda: self._show_start_context(3, 'Settings'))
        self.quick_play_button.clicked.connect(self._start_friend_game)
        self.new_game_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.new_game_page))
        self.play_bots_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.bot_select_page))
        self.play_friend_button.clicked.connect(self._start_friend_game)
        self.play_coach_home_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.coach_select_page))
        self.board_settings_button.clicked.connect(self._show_stockfish_settings)
        self.engine_settings_home_button.clicked.connect(self._show_stockfish_settings)
        self.new_friend_button.clicked.connect(self._start_friend_game)
        self.new_bots_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.bot_select_page))
        self.new_back_button.clicked.connect(self._show_start_menu)
        self.play_coach_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.coach_select_page))
        self.lessons_placeholder_button.clicked.connect(lambda: self._update_status('Lessons placeholder is ready for future expansion'))
        self.training_placeholder_button.clicked.connect(lambda: self._update_status('Training placeholder is ready for future expansion'))
        self.learn_back_button.clicked.connect(self._show_start_menu)
        self.coach_select_back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.learn_page))
        self.coach_play_button.clicked.connect(lambda: self._start_coach_game(self.coach_profile))
        self.bot_select_back_button.clicked.connect(self._show_start_menu)
        self.bot_play_button.clicked.connect(lambda: self._start_bot_game(self.selected_bot_profile))
        self.side_white_button.clicked.connect(lambda: self._select_side('white'))
        self.side_black_button.clicked.connect(lambda: self._select_side('black'))
        self.side_random_button.clicked.connect(lambda: self._select_side('random'))
        self.upload_pgn_button.clicked.connect(self._upload_pgn)
        self.review_from_menu_button.clicked.connect(self._review_game)
        self.board_widget.move_dropped.connect(self._on_user_move)
        self.review_board_widget.move_dropped.connect(self._on_review_board_move)
        self.move_history.position_selected.connect(self._on_position_selected)
        self.move_history.move_selected.connect(self._on_move_history_ply_selected)
        self.resign_button.clicked.connect(self._resign)
        self.hint_button.clicked.connect(self._hint)
        self.undo_button.clicked.connect(self._undo_move)
        self.review_button.clicked.connect(self._review_game)
        self.game_settings_button.clicked.connect(self._show_stockfish_settings)
        self.menu_button.clicked.connect(self._show_start_menu)
        self.review_menu_button.clicked.connect(self._show_start_menu)
        self.review_settings_button.clicked.connect(self._show_stockfish_settings)
        self.review_cloud_button.clicked.connect(self._toggle_cloud_analysis)
        self.review_toggle_button.clicked.connect(self._toggle_review_mode)
        self.review_start_button.clicked.connect(self._start_move_review)
        self.review_add_line_button.clicked.connect(self._add_selected_engine_line)
        self.review_promote_button.clicked.connect(self._promote_selected_variation)
        self.review_moves_table.cellClicked.connect(self._on_review_move_clicked)
        self.review_summary_table.cellClicked.connect(self._on_review_category_clicked)
        self.review_lines_table.cellClicked.connect(self._on_review_line_clicked)
        self.review_first_button.clicked.connect(lambda: self._jump_review_move(0))
        self.review_prev_button.clicked.connect(lambda: self._jump_review_move(self.review_index - 1))
        self.review_next_button.clicked.connect(lambda: self._jump_review_move(self.review_index + 1))
        self.review_final_button.clicked.connect(lambda: self._jump_review_move(len(self.review_rows) - 1))

    def _show_start_menu(self) -> None:
        self.stack.setCurrentWidget(self.start_page)

    def _show_start_context(self, index: int, title: str) -> None:
        self.start_context_stack.setCurrentIndex(index)
        self.start_context_title.setText(title)

    def _show_stockfish_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle('Settings')
        dialog.setObjectName('SettingsDialog')
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 20, 22, 22)
        layout.setSpacing(14)

        title = QLabel('Analysis Settings')
        title.setObjectName('MenuTitle')
        layout.addWidget(title)

        local_label = QLabel('Local Stockfish works offline. Cloud is optional and falls back to local analysis if unavailable.')
        local_label.setObjectName('StartSubtitle')
        local_label.setWordWrap(True)
        layout.addWidget(local_label)

        self.settings_cloud_check = QCheckBox('Use cloud Stockfish when available')
        self.settings_cloud_check.setChecked(self.cloud_stockfish_enabled)
        layout.addWidget(self.settings_cloud_check)

        self.settings_analysis_check = QCheckBox('Enable Stockfish analysis')
        self.settings_analysis_check.setChecked(self.settings_manager.settings.enable_stockfish_analysis)
        layout.addWidget(self.settings_analysis_check)

        self.settings_eval_check = QCheckBox('Show evaluation bar')
        self.settings_eval_check.setChecked(self.settings_manager.settings.show_eval_bar)
        layout.addWidget(self.settings_eval_check)

        self.settings_quality_check = QCheckBox('Show move quality icons')
        self.settings_quality_check.setChecked(self.settings_manager.settings.show_move_quality_icons)
        layout.addWidget(self.settings_quality_check)

        self.settings_overlays_check = QCheckBox('Show board overlays')
        self.settings_overlays_check.setChecked(self.settings_manager.settings.show_board_overlays)
        layout.addWidget(self.settings_overlays_check)

        self.settings_premove_check = QCheckBox('Enable premove')
        self.settings_premove_check.setChecked(self.enable_premove)
        layout.addWidget(self.settings_premove_check)

        self.settings_legal_check = QCheckBox('Show legal move hints')
        self.settings_legal_check.setChecked(self.board_widget.show_legal_moves)
        layout.addWidget(self.settings_legal_check)

        self.settings_coordinates_check = QCheckBox('Show board coordinates')
        self.settings_coordinates_check.setChecked(self.settings_manager.settings.show_coordinates)
        layout.addWidget(self.settings_coordinates_check)

        self.settings_debug_review_check = QCheckBox('Log review accuracy debug data')
        self.settings_debug_review_check.setChecked(self.settings_manager.settings.debug_review_logging)
        layout.addWidget(self.settings_debug_review_check)

        line_row = QHBoxLayout()
        line_label = QLabel('Number of lines')
        self.settings_lines = QSpinBox()
        self.settings_lines.setRange(1, 5)
        self.settings_lines.setValue(self.analysis_line_count)
        line_row.addWidget(line_label)
        line_row.addWidget(self.settings_lines)
        layout.addLayout(line_row)

        time_row = QHBoxLayout()
        time_label = QLabel('Local max time')
        self.settings_time = QComboBox()
        for seconds in (0.15, 0.3, 0.5, 1, 2, 5):
            self.settings_time.addItem(f'{seconds} sec', seconds)
        self.settings_time.setCurrentIndex(max(0, self.settings_time.findData(self.analysis_time_seconds)))
        time_row.addWidget(time_label)
        time_row.addWidget(self.settings_time)
        layout.addLayout(time_row)

        deep_time_row = QHBoxLayout()
        deep_time_label = QLabel('Paused analysis time')
        self.settings_deep_time = QComboBox()
        for seconds in (0.5, 0.8, 1, 2, 5):
            self.settings_deep_time.addItem(f'{seconds} sec', seconds)
        self.settings_deep_time.setCurrentIndex(max(0, self.settings_deep_time.findData(self.deep_analysis_time_seconds)))
        deep_time_row.addWidget(deep_time_label)
        deep_time_row.addWidget(self.settings_deep_time)
        layout.addLayout(deep_time_row)

        depth_row = QHBoxLayout()
        depth_label = QLabel('Analysis depth')
        self.settings_depth = QSpinBox()
        self.settings_depth.setRange(1, 30)
        self.settings_depth.setValue(self.analysis_depth)
        depth_row.addWidget(depth_label)
        depth_row.addWidget(self.settings_depth)
        layout.addLayout(depth_row)

        thread_row = QHBoxLayout()
        thread_label = QLabel('Threads')
        self.settings_threads = QSpinBox()
        self.settings_threads.setRange(1, 8)
        self.settings_threads.setValue(self.analysis_threads)
        thread_row.addWidget(thread_label)
        thread_row.addWidget(self.settings_threads)
        layout.addLayout(thread_row)

        cloud_row = QHBoxLayout()
        cloud_label = QLabel('Cloud target depth')
        self.settings_cloud_depth = QComboBox()
        for depth in (24, 32, 36, 41):
            self.settings_cloud_depth.addItem(f'depth {depth}', depth)
        self.settings_cloud_depth.setCurrentIndex(max(0, self.settings_cloud_depth.findData(self.cloud_target_depth)))
        cloud_row.addWidget(cloud_label)
        cloud_row.addWidget(self.settings_cloud_depth)
        layout.addLayout(cloud_row)

        buttons = QHBoxLayout()
        save = QPushButton('Save')
        save.setObjectName('StartAction')
        close = QPushButton('Cancel')
        close.setObjectName('GhostButton')
        buttons.addStretch(1)
        buttons.addWidget(close)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        close.clicked.connect(dialog.reject)
        save.clicked.connect(lambda: self._apply_stockfish_settings(dialog))
        dialog.exec()

    def _apply_stockfish_settings(self, dialog: QDialog) -> None:
        self.cloud_stockfish_enabled = self.settings_cloud_check.isChecked()
        self.review_cloud_button.setText('Cloud On' if self.cloud_stockfish_enabled else 'Cloud Off')
        self.analysis_line_count = int(self.settings_lines.value())
        self.analysis_time_seconds = float(self.settings_time.currentData())
        self.deep_analysis_time_seconds = float(self.settings_deep_time.currentData())
        self.analysis_depth = int(self.settings_depth.value())
        self.analysis_threads = int(self.settings_threads.value())
        self.cloud_target_depth = int(self.settings_cloud_depth.currentData())
        self.enable_premove = self.settings_premove_check.isChecked()
        self.settings_manager.update(
            show_eval_bar=self.settings_eval_check.isChecked(),
            enable_stockfish_analysis=self.settings_analysis_check.isChecked(),
            analysis_time_seconds=self.analysis_time_seconds,
            deep_analysis_time_seconds=self.deep_analysis_time_seconds,
            analysis_lines=self.analysis_line_count,
            analysis_depth=self.analysis_depth,
            analysis_threads=self.analysis_threads,
            cloud_analysis=self.cloud_stockfish_enabled,
            show_move_quality_icons=self.settings_quality_check.isChecked(),
            show_board_overlays=self.settings_overlays_check.isChecked(),
            enable_premove=self.enable_premove,
            show_legal_moves=self.settings_legal_check.isChecked(),
            show_coordinates=self.settings_coordinates_check.isChecked(),
            debug_review_logging=self.settings_debug_review_check.isChecked(),
        )
        self._apply_runtime_settings()
        if self.analysis_controller:
            self.analysis_controller.clear_cache()
        self._rerun_selected_analysis()
        self._update_status('Cloud Stockfish enabled; local fallback ready' if self.cloud_stockfish_enabled else 'Local Stockfish analysis ready')
        dialog.accept()

    def _toggle_cloud_analysis(self) -> None:
        self.cloud_stockfish_enabled = not self.cloud_stockfish_enabled
        self.settings_manager.update(cloud_analysis=self.cloud_stockfish_enabled)
        self.review_cloud_button.setText('Cloud On' if self.cloud_stockfish_enabled else 'Cloud Off')
        self._update_status('Cloud analysis enabled; local fallback ready' if self.cloud_stockfish_enabled else 'Local Stockfish analysis ready')
        if self.stack.currentWidget() == self.review_page and self.review_rows:
            self._rerun_selected_analysis()

    def _apply_runtime_settings(self) -> None:
        settings = self.settings_manager.settings
        self.eval_bar.setVisible(settings.show_eval_bar)
        self.review_eval_bar.setVisible(settings.show_eval_bar)
        self.board_widget.set_show_legal_moves(settings.show_legal_moves)
        self.review_board_widget.set_show_legal_moves(settings.show_legal_moves)
        self.board_widget.set_show_board_overlays(settings.show_board_overlays)
        self.review_board_widget.set_show_board_overlays(settings.show_board_overlays)
        self.board_widget.set_show_move_quality_icons(settings.show_move_quality_icons)
        self.review_board_widget.set_show_move_quality_icons(settings.show_move_quality_icons)
        self.board_widget.set_show_coordinates(settings.show_coordinates)
        self.review_board_widget.set_show_coordinates(settings.show_coordinates)
        self.review_coach_label.setVisible(True)

    def _select_side(self, side: str) -> None:
        self.pending_side_choice = side
        for value, button in (
            ('white', self.side_white_button),
            ('black', self.side_black_button),
            ('random', self.side_random_button),
        ):
            button.setProperty('selected', value == side)
            button.style().unpolish(button)
            button.style().polish(button)

    def _set_review_available(self, available: bool) -> None:
        self.review_button.setVisible(available)
        self.review_from_menu_button.setVisible(available)

    def _start_bot_game(self, bot: dict) -> None:
        self.game_mode = 'bot'
        self.bot_profile = bot
        self.difficulty = int(bot['elo'])
        if self.pending_side_choice == 'random':
            self.player_side = random.choice((chess.WHITE, chess.BLACK))
        else:
            self.player_side = chess.WHITE if self.pending_side_choice == 'white' else chess.BLACK
        self._apply_bot_profile()
        self._analysis_enabled = True
        self._new_game()
        self.stack.setCurrentWidget(self.game_page)
        if self.player_side == chess.BLACK:
            QTimer.singleShot(250, self._start_ai_turn)

    def _start_coach_game(self, coach: dict) -> None:
        self.game_mode = 'coach'
        self.coach_profile = coach
        self.bot_profile = coach
        self.difficulty = int(coach['elo'])
        self.player_side = chess.WHITE
        self._apply_bot_profile()
        self._analysis_enabled = True
        self._new_game()
        self.analysis_box.setPlainText(str(coach.get('dialogue', 'I will explain the ideas as we play.')))
        self.stack.setCurrentWidget(self.game_page)

    def _start_friend_game(self) -> None:
        self.game_mode = 'local'
        self.player_side = chess.WHITE
        self.bot_profile = {'name': 'Friend', 'elo': 'Local', 'group': 'Local', 'color': '#789262', 'dialogue': 'Same board, same room.'}
        self.difficulty = 1000
        self._apply_bot_profile()
        self._analysis_enabled = True
        self._new_game()
        self.stack.setCurrentWidget(self.game_page)

    def _apply_bot_profile(self) -> None:
        name = str(self.bot_profile['name'])
        rating = 'Local' if self.game_mode == 'local' else f"{self.bot_profile['elo']} Elo"
        self.bot_name_label.setText(name)
        self.bot_rating_label.setText(rating)
        self.review_bot_name_label.setText(name)
        self.review_bot_rating_label.setText(rating)
        self.review_bot_card.findChild(QLabel, 'ReviewCardTitle').setText(name)
        if self.game_mode == 'local':
            self.panel_title.setText('Play a Friend')
        elif self.game_mode == 'coach':
            self.panel_title.setText(f'Play Coach: {name}')
        else:
            self.panel_title.setText(f'Play {name}')

    def _on_position_selected(self, fen: str) -> None:
        if self.stack.currentWidget() == self.review_page:
            return
        self.board = ChessBoard.from_fen(fen)
        self.board_widget.set_board(self.board)
        self.board_widget.clear_marks()
        self._hint_stage = 0
        self._update_material_display()

    def _on_move_history_ply_selected(self, ply: int) -> None:
        if self.stack.currentWidget() != self.review_page:
            return
        self._jump_review_move(ply - 1)

    def _on_user_move(self, move_uci: str) -> None:
        if self._game_over:
            return

        move = chess.Move.from_uci(move_uci)
        if self.game_mode in {'bot', 'coach'} and self.board.turn != self.player_side:
            if self._thinking and self.enable_premove and self._move_starts_player_piece(move):
                self.pending_premove = move
                self.board_widget.set_premove(move)
                self._update_status('Premove queued')
            return
        if self._thinking:
            if self.enable_premove:
                self.pending_premove = move
                self.board_widget.set_premove(move)
                self._update_status('Premove queued')
            return

        if not self.board.make_move(move):
            return

        self._hint_stage = 0
        self.board_widget.clear_marks()
        self.board_widget.set_last_move(move)
        self.board_widget.set_premove(None)
        self.pending_premove = None
        self._sync_board_state()

        if self.board.is_checkmate() or self.board.is_stalemate():
            self._finish_game_status()
            return

        if self.game_mode in {'bot', 'coach'}:
            self._start_ai_turn()
        else:
            self._update_status('Check' if self.board.is_check() else ('Black to move' if self.board.turn == chess.BLACK else 'White to move'))

    def _move_starts_player_piece(self, move: chess.Move) -> bool:
        piece = self.board.piece_at(move.from_square)
        return piece is not None and piece.color == self.player_side

    def _start_ai_turn(self) -> None:
        if self.game_mode not in {'bot', 'coach'}:
            return
        if self.engine is None:
            self._update_status('Stockfish unavailable')
            return

        self._thinking = True
        self.board_widget.set_premove_color(self.player_side if self.enable_premove else None)
        self._update_status(f"{self.bot_profile['name']} thinking...")
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
        self.board_widget.set_premove_color(None)
        self.eval_timer.stop()
        if move_uci:
            move = chess.Move.from_uci(move_uci)
            self.board.make_move(move)
            self.board_widget.clear_marks()
            self.board_widget.set_last_move(move)
            self._sync_board_state()

        self._schedule_active_analysis()

        if self.board.is_checkmate() or self.board.is_stalemate():
            self._finish_game_status()
            return

        if self.pending_premove and self.pending_premove in self.board.legal_moves:
            premove = self.pending_premove
            self.pending_premove = None
            self.board_widget.set_premove(None)
            self._on_user_move(premove.uci())
            return
        if self.pending_premove:
            self.pending_premove = None
            self.board_widget.set_premove(None)
            self._update_status('Premove unavailable')
            return

        self._update_status('Check' if self.board.is_check() else 'Player to move')

    def _on_ai_failed(self, message: str) -> None:
        self._thinking = False
        self.board_widget.set_premove_color(None)
        self.eval_timer.stop()
        self._update_status(f'AI error: {message}')

    def _hint(self) -> None:
        if self._thinking or self._game_over or not self.analysis_engine:
            return
        top_moves = self._top_moves_for_board(self.board, n=1)
        if not top_moves or not top_moves[0].get('move'):
            return

        move = chess.Move.from_uci(top_moves[0]['move'])
        self._hint_stage = 1 if self._hint_stage >= 2 else self._hint_stage + 1
        if self._hint_stage == 1:
            self.board_widget.set_hint_move(move, 'square')
            self._update_status('Hint: piece highlighted')
        else:
            self.board_widget.set_hint_move(move, 'arrow')
            self._update_status('Hint: move arrow shown')

    def _resign(self) -> None:
        if self._game_over:
            return
        self._game_over = True
        self.review_button.setVisible(True)
        self.review_from_menu_button.setVisible(True)
        self.pending_premove = None
        self.board_widget.set_premove(None)
        self.board_widget.set_premove_color(None)
        message = f'Player resigned. {self.bot_profile["name"]} wins.'
        bot_side = not self.player_side
        self.eval_bar.set_result('1-0' if bot_side == chess.WHITE else '0-1')
        self._update_status(message)
        self._show_game_over('You Lost', message, reason='Resignation')

    def _refresh_eval(self) -> None:
        if self.settings_manager.settings.show_eval_bar:
            self.eval_bar.set_evaluation(self._material_eval(self.board))

    def _schedule_active_analysis(self, shallow_delay: int = 80) -> None:
        if (
            not self.active_analysis
            or self._game_over
            or self.stack.currentWidget() != self.review_page
            or not self.settings_manager.settings.enable_stockfish_analysis
        ):
            return
        fen = self.board.fen()
        if fen == self._active_analysis_fen:
            return
        self._active_analysis_fen = fen
        self._shallow_analysis_timer.start(shallow_delay)
        self._deep_analysis_timer.start(650)

    def _request_active_analysis(self, time_seconds: float) -> None:
        if not self.active_analysis or not self.settings_manager.settings.enable_stockfish_analysis:
            return
        if self.stack.currentWidget() != self.game_page or not self._active_analysis_fen:
            return
        self.active_analysis.analyze(
            self._active_analysis_fen,
            lines=self.analysis_line_count,
            time_seconds=time_seconds,
            threads=self.analysis_threads,
        )

    def _top_moves_for_board(self, board: chess.Board, n: int = 3, analysis_time: float | None = None) -> list[dict]:
        if not self.analysis_engine or not self.settings_manager.settings.enable_stockfish_analysis:
            return []
        try:
            return self.analysis_engine.get_top_moves(
                board,
                n=n,
                difficulty=2000,
                analysis_time=self.analysis_time_seconds if analysis_time is None else analysis_time,
                threads=self.analysis_threads,
            )
        except Exception:  # noqa: BLE001
            return []

    def _refresh_analysis(self) -> None:
        top_moves = self._top_moves_for_board(self.board, n=self.analysis_line_count)
        if not top_moves:
            self.analysis_box.setPlainText('Analysis unavailable')
            return
        lines = []
        for index, item in enumerate(top_moves, start=1):
            score = self._format_score(item)
            pv = self._format_pv(self.board, item.get('line', []))
            lines.append(f'{index}. {score}  {pv}')
        self.analysis_box.setPlainText('\n'.join(lines))

    def _format_score(self, item: dict) -> str:
        if item.get('type') == 'mate':
            return f"M{item.get('score', 0)}"
        value = int(item.get('score', 0))
        return f'{value / 100:+.2f}'

    def _format_pv(self, board: chess.Board, line: list[str]) -> str:
        temp = board.copy(stack=False)
        san_moves = []
        for uci in line[:8]:
            move = chess.Move.from_uci(uci)
            if move not in temp.legal_moves:
                break
            san_moves.append(temp.san(move))
            temp.push(move)
        return ' '.join(san_moves) or '-'

    def _sync_board_state(self) -> None:
        start = time.perf_counter()
        self.board_widget.set_board(self.board)
        self.move_history.update_from_board(self.board)
        self._update_material_display()
        if self.board.move_stack:
            opening = self.opening_repertoire.opening_for_moves([move.uci() for move in self.board.move_stack])
            self.opening_label.setText(f"Opening: {opening.get('name', 'Game in progress')}")
        else:
            self.opening_label.setText('Opening: Starting position')
        self._schedule_active_analysis()
        LOGGER.info('Board redraw cost %.1f ms', (time.perf_counter() - start) * 1000)

    def _captured_by(self, capturer_color: chess.Color) -> tuple[str, int]:
        opponent = not capturer_color
        captured = []
        score = 0
        for piece_type, initial_count in INITIAL_COUNTS.items():
            remaining = len(self.board.pieces(piece_type, opponent))
            missing = max(0, initial_count - remaining)
            captured.extend([PIECE_SYMBOLS[(opponent, piece_type)]] * missing)
            score += missing * PIECE_VALUES[piece_type]
        return ' '.join(captured), score

    def _update_material_display(self) -> None:
        player_pieces, player_score = self._captured_by(chess.WHITE)
        bot_pieces, bot_score = self._captured_by(chess.BLACK)
        diff = player_score - bot_score
        player_plus = f' +{diff}' if diff > 0 else ''
        bot_plus = f' +{-diff}' if diff < 0 else ''
        self.player_captures_label.setText(f'{player_pieces}{player_plus}'.strip())
        self.bot_captures_label.setText(f'{bot_pieces}{bot_plus}'.strip())

    def _finish_game_status(self) -> None:
        self._game_over = True
        self._set_review_available(True)
        if self.board.is_checkmate():
            winner_color = not self.board.turn
            if self.game_mode == 'local':
                winner = 'White' if winner_color == chess.WHITE else 'Black'
                title = f'{winner} Wins'
            else:
                winner = 'Player' if winner_color == self.player_side else str(self.bot_profile['name'])
                title = 'You Won' if winner == 'Player' else 'You Lost'
            result = '1-0' if winner_color == chess.WHITE else '0-1'
            message = f'Checkmate - {winner} wins'
            self.eval_bar.set_result(result)
            self._update_status(message)
            self._show_game_over(title, message, reason='Checkmate')
        elif self.board.is_stalemate():
            self.eval_bar.set_result('1/2')
            self._update_status('Stalemate')
            self._show_game_over('Draw', 'Stalemate. Neither side can make a legal move.', reason='Stalemate')

    def _show_game_over(self, title: str, detail: str, reason: str | None = None) -> None:
        self._review_game(allow_live=False)
        dialog = QDialog(self)
        dialog.setWindowTitle('Game Over')
        dialog.setObjectName('GameOverDialog')
        dialog.setModal(False)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(14)

        top = QHBoxLayout()
        avatar = QLabel()
        avatar.setPixmap(self._bot_avatar(self.bot_profile))
        title_box = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName('GameOverTitle')
        reason_label = QLabel(reason or detail)
        reason_label.setObjectName('GameOverDetail')
        title_box.addWidget(title_label)
        title_box.addWidget(reason_label)
        top.addWidget(avatar)
        top.addLayout(title_box, 1)
        layout.addLayout(top)

        dialogue = QLabel(self._game_result_dialogue(title, reason or detail))
        dialogue.setObjectName('CoachComment')
        dialogue.setWordWrap(True)
        layout.addWidget(dialogue)

        counts = self._game_review_counts()
        summary = QLabel(
            '  '.join(
                f"{label} {counts.get(label.lower(), 0)}"
                for label in ('Best', 'Excellent', 'Great', 'Good', 'Inaccuracy', 'Mistake', 'Blunder')
            )
        )
        summary.setObjectName('GameOverDetail')
        summary.setWordWrap(True)
        layout.addWidget(summary)

        game_review = QPushButton('Game Review')
        game_review.setObjectName('StartAction')
        actions = QHBoxLayout()
        rematch = QPushButton('Rematch')
        rematch.setObjectName('GhostButton')
        menu = QPushButton('Menu')
        menu.setObjectName('GhostButton')
        actions.addWidget(rematch)
        actions.addWidget(menu)
        layout.addWidget(game_review)
        layout.addLayout(actions)

        game_review.clicked.connect(dialog.close)
        rematch.clicked.connect(lambda: self._rematch_from_modal(dialog))
        menu.clicked.connect(lambda: self._menu_from_modal(dialog))
        dialog.show()

    def _review_game(self, _checked: bool = False, *, allow_live: bool = True) -> None:
        if not self._game_over and not allow_live:
            return
        if not self._game_over:
            self._update_status('Review unlocks after the game ends')
            return
        if not self.board.move_stack:
            self._reset_review_board()
            self.review_analysis_box.clear()
            self.review_box.setPlainText('No moves to review.')
            self.review_summary_table.setRowCount(0)
            self.review_moves_table.setRowCount(0)
            self.stack.setCurrentWidget(self.review_page)
            return
        self.review_navigator.set_board(self.board)
        self.move_tree.build_from_board(self.board)
        self.review_annotations = self._initial_review_annotations()
        self._sync_tree_annotations()
        self.review_rows = self._review_rows_from_annotations()
        self.selected_review_node_id = self.move_tree.selected_node_id if self.move_tree.selected_node_id != self.move_tree.root_id else None
        self.review_analysis_box.setPlainText('Select a move to analyze.')
        self.review_lines_table.setRowCount(0)
        self.selected_engine_line = None
        self.selected_variation_fen = None
        self.review_cloud_button.setText('Cloud On' if self.cloud_stockfish_enabled else 'Cloud Off')
        self.stack.setCurrentWidget(self.review_page)
        self.review_side_stack.setCurrentIndex(0)
        self.review_toggle_button.setText('Review')
        self._refresh_review_tables()
        self._jump_review_move(len(self.review_rows) - 1)
        if self.analysis_controller and self.settings_manager.settings.enable_stockfish_analysis:
            self.selected_variation_fen = self.board.fen()
            self.analysis_controller.analyze_selected(
                self.board.fen(),
                lines=self.analysis_line_count,
                time_seconds=self.deep_analysis_time_seconds,
                threads=self.analysis_threads,
            )

    def _game_review_counts(self) -> dict:
        if not self.review_annotations:
            return {}
        counts = {key: 0 for key in REVIEW_CATEGORIES_FULL}
        for annotation in self.review_annotations.values():
            if annotation.label in counts:
                counts[annotation.label] += 1
        return counts

    def _game_result_dialogue(self, title: str, reason: str) -> str:
        if self.game_mode == 'coach':
            return self.coach_service.game_result_comment(title, reason)
        event = 'draw' if title == 'Draw' else ('loss' if title == 'You Won' else 'win')
        return self.bot_personality_service.comment(self.bot_profile, event)

    def _rematch_from_modal(self, dialog: QDialog) -> None:
        dialog.close()
        if self.game_mode == 'coach':
            self._start_coach_game(self.coach_profile)
        elif self.game_mode == 'local':
            self._start_friend_game()
        else:
            self._start_bot_game(self.bot_profile)

    def _menu_from_modal(self, dialog: QDialog) -> None:
        dialog.close()
        self._show_start_menu()

    def _toggle_review_mode(self) -> None:
        if self.review_side_stack.currentIndex() == 0:
            self._start_move_review()
            return
        self.review_side_stack.setCurrentIndex(0)
        self.review_toggle_button.setText('Review')
        if self._game_over and self.board.move_stack:
            self.review_rows = self._review_rows_from_annotations()
            self._refresh_review_tables()

    def _start_move_review(self) -> None:
        self.review_side_stack.setCurrentIndex(1)
        self.review_toggle_button.setText('Summary')
        if self.review_rows:
            self._jump_review_move(self.review_index)

    def _initial_review_annotations(self) -> dict[int, MoveAnnotation]:
        annotations = {}
        moves = []
        for node in self.review_navigator.nodes:
            opening = self.opening_repertoire.opening_for_moves(moves)
            if opening.get('in_book') and node.ply <= 8:
                annotations[node.ply] = MoveAnnotation(node.ply, 'book', 0, 0, 'Known opening book move')
            else:
                before = chess.Board(node.before_fen)
                move = chess.Move.from_uci(node.uci)
                loss = self._heuristic_move_loss(before, move)
                annotations[node.ply] = MoveAnnotation(
                    node.ply,
                    self._category_for_loss(loss, before, move, node.ply),
                    loss,
                    self._material_eval_after(before, move),
                    'Initial estimate; engine analysis updates when selected.',
                )
            moves.append(node.uci)
        return annotations

    def _review_rows_from_annotations(self) -> list[dict]:
        rows = []
        tree_nodes = self.move_tree.mainline_nodes()
        for node in self.review_navigator.nodes:
            annotation = self.review_annotations.get(node.ply, MoveAnnotation(node.ply))
            tree_node = tree_nodes[node.ply - 1] if node.ply <= len(tree_nodes) else None
            rows.append(
                {
                    'index': node.ply,
                    'node_id': tree_node.node_id if tree_node else '',
                    'side': node.side,
                    'san': node.san,
                    'category': annotation.label,
                    'eval': annotation.evaluation_cp,
                    'fen': node.after_fen,
                    'before_fen': node.before_fen,
                    'move': node.uci,
                    'lines': annotation.analysis.lines if annotation.analysis else [],
                }
            )
        return rows

    def _sync_tree_annotations(self) -> None:
        tree_nodes = self.move_tree.mainline_nodes()
        for node in self.review_navigator.nodes:
            if node.ply > len(tree_nodes):
                continue
            annotation = self.review_annotations.get(node.ply, MoveAnnotation(node.ply))
            tree_node = tree_nodes[node.ply - 1]
            tree_node.annotation_label = annotation.label
            tree_node.comment = annotation.reason
            tree_node.engine_evaluation = annotation.evaluation_cp
            tree_node.engine_best_move = annotation.analysis.best_move_uci if annotation.analysis else None

    def _stats_from_annotations(self) -> dict:
        stats = {chess.WHITE: self._empty_review_stats(), chess.BLACK: self._empty_review_stats()}
        for node in self.review_navigator.nodes:
            annotation = self.review_annotations.get(node.ply, MoveAnnotation(node.ply))
            label = annotation.label if annotation.label in REVIEW_CATEGORIES_FULL else 'good'
            stats[node.side]['moves'] += 1
            stats[node.side]['loss'] += annotation.loss_cp
            if annotation.analysed:
                stats[node.side]['analysed_moves'] += 1
                stats[node.side]['weighted_accuracy'] += annotation.move_accuracy * annotation.weight
                stats[node.side]['weight'] += annotation.weight
                stats[node.side]['weighted_loss'] += annotation.loss_cp * annotation.weight
                stats[node.side]['weighted_loss_weight'] += annotation.weight
                if annotation.estimated:
                    stats[node.side]['estimated_moves'] += 1
                if self.settings_manager.settings.debug_review_logging:
                    LOGGER.info('Review debug ply %s: %s', node.ply, annotation.debug)
            stats[node.side][label] += 1
        return stats

    def _refresh_review_tables(self) -> None:
        start = time.perf_counter()
        review = {'categories': self._stats_from_annotations(), 'rows': self.review_rows}
        self._populate_review_tables(review)
        self.review_box.setPlainText(self._review_report_text(review))
        LOGGER.info('Move tree update cost %.1f ms', (time.perf_counter() - start) * 1000)

    def _opening_for_ply(self, ply: int) -> dict:
        moves = [node.uci for node in self.review_navigator.nodes[: max(0, ply)]]
        return self.opening_repertoire.opening_for_moves(moves)

    def _sync_review_row_for_ply(self, ply: int) -> None:
        node = self.review_navigator.node_at(ply)
        if node is None:
            return
        annotation = self.review_annotations.get(ply, MoveAnnotation(ply))
        row = next((item for item in self.review_rows if item.get('index') == ply), None)
        if row is None:
            return
        row.update(
            {
                'category': annotation.label if annotation.label in REVIEW_MARKERS else 'good',
                'eval': annotation.evaluation_cp,
                'lines': annotation.analysis.lines if annotation.analysis else [],
            }
        )
        tree_node = self.move_tree.node_at_mainline_ply(ply)
        if tree_node:
            tree_node.annotation_label = annotation.label
            tree_node.comment = annotation.reason
            tree_node.engine_evaluation = annotation.evaluation_cp
            tree_node.engine_best_move = annotation.analysis.best_move_uci if annotation.analysis else None

    def _current_review_node(self):
        if not self.review_rows:
            return None
        return self.review_navigator.node_at(int(self.review_rows[self.review_index]['index']))

    def _build_review_data(self) -> dict:
        replay = chess.Board()
        categories = {chess.WHITE: self._empty_review_stats(), chess.BLACK: self._empty_review_stats()}
        rows = []

        for index, move in enumerate(self.board.move_stack, start=1):
            side = replay.turn
            review_info = self._classify_review_move(replay, move, index)
            loss = review_info['loss']
            category = review_info['category']
            san = replay.san(move)
            replay.push(move)
            eval_score = review_info['eval']
            categories[side]['moves'] += 1
            categories[side]['loss'] += loss
            categories[side][category] += 1
            rows.append(
                {
                    'index': index,
                    'side': side,
                    'san': san,
                    'category': category,
                    'eval': eval_score,
                    'fen': replay.fen(),
                    'move': move.uci(),
                    'lines': review_info.get('lines', []),
                }
            )

        return {'categories': categories, 'rows': rows}

    def _empty_review_stats(self) -> dict:
        stats = {key: 0 for key in (*REVIEW_CATEGORIES_FULL, 'moves', 'loss', 'analysed_moves', 'estimated_moves')}
        stats.update({'weighted_accuracy': 0.0, 'weight': 0.0, 'weighted_loss': 0.0, 'weighted_loss_weight': 0.0})
        return stats

    def _classify_review_move(self, board: chess.Board, move: chess.Move, index: int) -> dict:
        if self.analysis_engine is None:
            loss = self._heuristic_move_loss(board, move)
            return {
                'category': self._category_for_loss(loss, board, move, index),
                'loss': loss,
                'eval': self._material_eval_after(board, move),
                'lines': [],
            }

        top_moves = self._top_moves_for_board(board, n=self.analysis_line_count, analysis_time=self.analysis_time_seconds)
        if not top_moves:
            loss = self._heuristic_move_loss(board, move)
            return {
                'category': self._category_for_loss(loss, board, move, index),
                'loss': loss,
                'eval': self._material_eval_after(board, move),
                'lines': [],
            }

        actual_board = board.copy(stack=False)
        actual_board.push(move)
        if actual_board.is_checkmate():
            actual_eval = -100000 if actual_board.turn == chess.WHITE else 100000
            return {
                'category': 'brilliant' if self._is_sacrifice(board, move) else 'best',
                'loss': 0,
                'eval': actual_eval,
                'lines': self._analysis_lines_for_board(board, top_moves),
            }
        ranked = self._ranked_lines_for_side(top_moves, board.turn)
        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None
        actual_uci = move.uci()
        actual_rank = next((rank for rank, item in enumerate(ranked, start=1) if item['move'] == actual_uci), None)
        actual_eval = ranked[actual_rank - 1]['cp_score'] if actual_rank is not None else self._material_eval(actual_board)
        mover_eval = self._side_eval(actual_eval, board.turn)
        best_eval = best['side_score']
        next_eval = second['side_score'] if second else best_eval
        loss = max(0, int(best_eval - mover_eval))

        if self._is_missed_opportunity(board, move, best):
            category = 'miss'
        elif self._is_blunder(board, move, mover_eval, loss, best):
            category = 'blunder'
        elif actual_rank == 1 and self._is_sacrifice(board, move):
            category = 'brilliant'
        elif actual_rank == 1 and self._is_great_move(ranked):
            category = 'great'
        elif actual_rank == 1:
            category = 'best'
        elif actual_rank in (2, 3):
            category = 'excellent'
        elif mover_eval >= -80 and loss <= 130:
            category = 'good'
        elif loss <= 230 and best_eval <= -120:
            category = 'mistake'
        elif loss <= 180:
            category = 'inaccuracy'
        elif best_eval <= -120:
            category = 'mistake'
        else:
            category = 'blunder'

        if category in {'best', 'great'} and self._is_sacrifice(board, move):
            category = 'brilliant'

        return {'category': category, 'loss': loss, 'eval': actual_eval, 'lines': self._analysis_lines_for_board(board, top_moves)}

    def _engine_eval_cp(self, board: chess.Board) -> int:
        if board.is_checkmate():
            return -100000 if board.turn == chess.WHITE else 100000
        if board.is_stalemate():
            return 0
        try:
            evaluation = (
                self.analysis_engine.get_evaluation(
                    board,
                    2000,
                    analysis_time=self.analysis_time_seconds,
                    threads=self.analysis_threads,
                )
                if self.analysis_engine
                else None
            )
        except Exception:  # noqa: BLE001
            evaluation = None
        if not evaluation:
            return self._material_eval(board)
        if evaluation.get('type') == 'mate':
            mate = int(evaluation.get('value', 0))
            return 100000 if mate > 0 else -100000
        return int(evaluation.get('value', 0))

    def _analysis_lines_for_board(self, board: chess.Board, top_moves: list[dict]) -> list[str]:
        lines = []
        prefix = f'cloud depth {self.cloud_target_depth}' if self.cloud_stockfish_enabled else 'local'
        for index, item in enumerate(top_moves, start=1):
            score = self._format_score(item)
            pv = self._format_pv(board, item.get('line', []))
            lines.append(f'{index}. {score}  {pv}  ({prefix})')
        return lines

    def _ranked_lines_for_side(self, top_moves: list[dict], side: chess.Color) -> list[dict]:
        ranked = []
        for item in top_moves:
            score = self._line_score_cp(item)
            ranked.append({**item, 'side_score': self._side_eval(score, side), 'cp_score': score})
        return sorted(ranked, key=lambda item: item['side_score'], reverse=True)

    def _line_score_cp(self, item: dict) -> int:
        if item.get('type') == 'mate':
            mate = int(item.get('score') or 0)
            return 100000 if mate > 0 else -100000
        return int(item.get('score') or 0)

    def _side_eval(self, white_eval: int, side: chess.Color) -> int:
        return white_eval if side == chess.WHITE else -white_eval

    def _is_great_move(self, ranked: list[dict]) -> bool:
        positive_lines = sum(1 for item in ranked if item['side_score'] > 80)
        if positive_lines == 1 and ranked[0]['side_score'] > 80:
            return True
        if len(ranked) >= 2 and ranked[0]['side_score'] - ranked[1]['side_score'] >= 250:
            return True
        return False

    def _is_sacrifice(self, board: chess.Board, move: chess.Move) -> bool:
        moving_piece = board.piece_at(move.from_square)
        if moving_piece is None or moving_piece.piece_type == chess.KING:
            return False
        before_material = self._material_balance_for(board, board.turn)
        after = board.copy(stack=False)
        after.push(move)
        after_material = self._material_balance_for(after, moving_piece.color)
        if after_material <= before_material - 300 and moving_piece.piece_type != chess.PAWN:
            return True
        target_piece = after.piece_at(move.to_square)
        if target_piece is None or target_piece.color != moving_piece.color:
            return False
        attackers = after.attackers(not moving_piece.color, move.to_square)
        defenders = after.attackers(moving_piece.color, move.to_square)
        return moving_piece.piece_type != chess.PAWN and bool(attackers) and len(defenders) < len(attackers)

    def _is_blunder(self, board: chess.Board, move: chess.Move, mover_eval: int, loss: int, best: dict) -> bool:
        actual = board.copy(stack=False)
        actual.push(move)
        if actual.is_checkmate():
            return False
        was_equal = abs(self._material_eval(board)) <= 120
        lost_material = self._material_balance_for(actual, board.turn) <= self._material_balance_for(board, board.turn) - 300
        hangs_material = self._hangs_material(actual, board.turn)
        missed_mate_defense = best.get('type') == 'mate' and self._side_eval(self._line_score_cp(best), board.turn) > 0 and mover_eval < -900
        return (was_equal and (lost_material or hangs_material or loss >= 300)) or missed_mate_defense

    def _hangs_material(self, board: chess.Board, side: chess.Color) -> bool:
        for move in board.legal_moves:
            if not board.is_capture(move):
                continue
            captured = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if captured is None or attacker is None or captured.color != side:
                continue
            captured_value = PIECE_VALUES.get(captured.piece_type, 0)
            attacker_value = PIECE_VALUES.get(attacker.piece_type, 0)
            if captured_value >= 3 and captured_value > attacker_value:
                return True
            defenders = board.attackers(side, move.to_square)
            if captured_value >= 3 and not defenders:
                return True
        return False

    def _is_missed_opportunity(self, board: chess.Board, move: chess.Move, best: dict) -> bool:
        best_uci = best.get('move')
        if not best_uci or best_uci == move.uci():
            return False
        best_score = best['side_score']
        if best.get('type') == 'mate' and best_score > 0:
            return True
        best_move = chess.Move.from_uci(best_uci)
        if best_move not in board.legal_moves:
            return False
        if not board.is_capture(best_move):
            return False
        captured = board.piece_at(best_move.to_square)
        attacker = board.piece_at(best_move.from_square)
        if captured is None or attacker is None:
            return False
        victim_value = PIECE_VALUES.get(captured.piece_type, 0) * 100
        attacker_value = PIECE_VALUES.get(attacker.piece_type, 0) * 100
        defenders = board.attackers(captured.color, best_move.to_square)
        return victim_value >= 300 and (victim_value > attacker_value or not defenders)

    def _material_balance_for(self, board: chess.Board, side: chess.Color) -> int:
        white_score = self._material_eval(board)
        return white_score if side == chess.WHITE else -white_score

    def _material_eval_after(self, board: chess.Board, move: chess.Move) -> int:
        test_board = board.copy(stack=False)
        test_board.push(move)
        return self._material_eval(test_board)

    def _category_for_loss(self, loss: int, board: chess.Board, move: chess.Move, index: int) -> str:
        test_board = board.copy(stack=False)
        test_board.push(move)
        if test_board.is_checkmate() or move.promotion:
            return 'brilliant'
        if index <= 4:
            return 'book'
        if loss <= 10 and (board.is_capture(move) or test_board.is_check()):
            return 'great'
        if loss <= 20:
            return 'best'
        if loss <= 45:
            return 'excellent'
        if loss <= 80:
            return 'good'
        if loss <= 150:
            return 'inaccuracy'
        if loss <= 300:
            return 'mistake'
        if board.is_capture(move):
            return 'miss'
        return 'blunder'

    def _material_eval(self, board: chess.Board) -> int:
        score = 0
        for piece_type, value in PIECE_VALUES.items():
            score += len(board.pieces(piece_type, chess.WHITE)) * value
            score -= len(board.pieces(piece_type, chess.BLACK)) * value
        return score * 100

    def _populate_review_tables(self, review: dict) -> None:
        categories = REVIEW_CATEGORIES_FULL
        stats = review['categories']
        player_accuracy = self._accuracy_for(stats[chess.WHITE])
        bot_accuracy = self._accuracy_for(stats[chess.BLACK])
        player_elo, player_confidence, player_reason = self._rating_estimate(stats[chess.WHITE])
        bot_elo, bot_confidence, bot_reason = self._rating_estimate(stats[chess.BLACK])
        self._set_review_card(self.review_player_card, 'Player', player_accuracy, 'Accuracy')
        self._set_review_card(self.review_bot_card, str(self.bot_profile['name']), bot_accuracy, 'Accuracy')
        self._set_review_card(self.review_rating_card, 'Estimated Rating', f'{player_elo} / {bot_elo}', f'{player_confidence} / {bot_confidence}')
        opening = self.opening_repertoire.opening_for_moves([move.uci() for move in self.board.move_stack])
        self.review_opening_summary.setText(
            f"Opening: {opening.get('name', 'Game in progress')}\n"
            f'Player: {player_reason}\n'
            f"{self.bot_profile['name']}: {bot_reason}"
        )
        self.review_summary_table.setRowCount(len(categories))
        row = 0
        for category in categories:
            self._set_review_summary_row(
                row,
                category.title(),
                str(stats[chess.WHITE][category]),
                REVIEW_MARKERS[category],
                str(stats[chess.BLACK][category]),
            )
            row += 1

        move_count = (len(review['rows']) + 1) // 2
        self.review_moves_table.setRowCount(move_count)
        for row in range(move_count):
            self.review_moves_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        for item in review['rows']:
            row = (item['index'] - 1) // 2
            column = 1 if item['side'] == chess.WHITE else 2
            label = self._review_move_list_label(item)
            move_item = QTableWidgetItem(label)
            move_item.setData(Qt.ItemDataRole.UserRole, item)
            self.review_moves_table.setItem(row, column, move_item)
            eval_item = QTableWidgetItem(f"{item['category'].title()} ({self._delta_text(self._move_eval_delta(item))})")
            eval_item.setData(Qt.ItemDataRole.UserRole, item)
            self.review_moves_table.setItem(row, 3, eval_item)
        self._append_variation_rows(move_count)

    def _review_move_list_label(self, item: dict) -> str:
        move_no = (int(item['index']) + 1) // 2
        prefix = f'{move_no}.' if item['side'] == chess.WHITE else f'{move_no}...'
        marker = REVIEW_MARKERS.get(item['category'], '')
        return f"{prefix} {item['san']} {marker} ({self._delta_text(self._move_eval_delta(item))})"

    def _move_eval_delta(self, item: dict) -> float:
        annotation = self.review_annotations.get(int(item.get('index', 0)))
        if annotation is None:
            return 0.0
        if annotation.label in {'book', 'best', 'brilliant', 'great'}:
            return 0.0
        return -float(annotation.loss_cp) / 100.0

    def _delta_text(self, delta: float) -> str:
        if abs(delta) < 0.05:
            delta = 0.0
        return f'{delta:+.1f}'

    def _eval_text(self, cp: int | float) -> str:
        if abs(float(cp)) >= 100000:
            return '+M' if float(cp) > 0 else '-M'
        pawns = max(-9.9, min(9.9, float(cp) / 100.0))
        if abs(pawns) < 0.05:
            pawns = 0.0
        return f'{pawns:+.1f}'

    def _before_eval_for_item(self, item: dict) -> int:
        index = int(item.get('index', 1))
        if index <= 1:
            return 0
        previous = next((row for row in self.review_rows if int(row.get('index', 0)) == index - 1), None)
        return int(previous.get('eval', 0)) if previous else 0

    def _specific_coach_comment(self, item: dict, annotation: MoveAnnotation, opening: dict) -> str:
        best = annotation.analysis.best_move_san if annotation.analysis and annotation.analysis.best_move_san else None
        san = str(item.get('san', 'This move'))
        label = annotation.label
        before = self._eval_text(annotation.eval_before_cp if annotation.analysed else self._before_eval_for_item(item))
        after = self._eval_text(annotation.played_eval_cp if annotation.analysed else int(item.get('eval', 0)))
        delta = self._delta_text(self._move_eval_delta(item))
        main_line = ''
        if annotation.analysis and annotation.analysis.lines:
            main_line = ' Stockfish main line is ' + (' '.join(annotation.analysis.lines[0].pv_san) or annotation.analysis.lines[0].san) + '.'
        if label == 'book':
            return f"{san} was a book move in {opening.get('name', 'the opening')}. Keep developing pieces and protecting your king.{main_line}"
        if label in {'brilliant', 'great'}:
            return f'{san} was a strong practical move. The evaluation moved from {before} to {after} ({delta}). It creates a concrete problem while keeping your position coordinated.{main_line}'
        if label in {'best', 'excellent'}:
            return f'{san} was {label}. The evaluation changed from {before} to {after}, so there was no meaningful loss.{main_line}'
        if label == 'good':
            return f'{san} is playable. The evaluation changed from {before} to {after} ({delta}), so your position remains healthy.{main_line}'
        if best and label in {'inaccuracy', 'mistake', 'blunder', 'miss'}:
            if label == 'miss':
                return f'{san} missed a stronger chance. The evaluation changed from {before} to {after} ({delta}). Stockfish preferred {best}, which creates more immediate pressure.{main_line}'
            return f'{san} was a {label}. The evaluation changed from {before} to {after}, a {delta} swing. Stockfish preferred {best}.{main_line}'
        return self.coach_service.comment(annotation, annotation.analysis, board=self.review_board_state, opening=opening)

    def _set_review_engine_loading(self, fen: str, message: str = 'Analyzing with Stockfish...') -> None:
        self.selected_analysis_fen = chess.Board(fen).fen()
        self.selected_engine_line = None
        self.review_lines_table.setRowCount(0)
        self.review_binding.show_waiting(message)

    def _request_review_analysis(self, fen: str, message: str = 'Analyzing with Stockfish...') -> None:
        self._set_review_engine_loading(fen, message)
        if not self.analysis_controller or not self.settings_manager.settings.enable_stockfish_analysis:
            return
        self.analysis_controller.analyze_selected(
            self.selected_analysis_fen,
            lines=self.analysis_line_count,
            time_seconds=self.analysis_time_seconds,
            threads=self.analysis_threads,
        )

    def _rerun_selected_analysis(self) -> None:
        if self.stack.currentWidget() != self.review_page:
            return
        if self.selected_variation_fen:
            self._request_review_analysis(self.selected_variation_fen, 'Analyzing selected variation...')
            return
        if self.review_rows:
            self._show_review_position(self.review_rows[self.review_index])

    def _append_variation_rows(self, start_row: int) -> None:
        original_ids = {row.get('node_id') for row in self.review_rows}
        rows = [row for row in self.notation_renderer.rows(self.move_tree, REVIEW_MARKERS) if row['depth'] > 0 or row['node_id'] not in original_ids]
        if not rows:
            return
        self.review_moves_table.setRowCount(start_row + len(rows))
        for offset, row_data in enumerate(rows):
            row = start_row + offset
            node = self.move_tree.nodes.get(row_data['node_id'])
            item_data = {
                'node_id': row_data['node_id'],
                'fen': row_data['fen'],
                'move': node.move_uci if node else '',
                'san': node.san if node else row_data['move'],
                'category': node.annotation_label if node else 'pending',
                'eval': node.engine_evaluation or 0,
                'variation': True,
            }
            number_item = QTableWidgetItem(f"({row_data['move_no']})")
            number_item.setData(Qt.ItemDataRole.UserRole, item_data)
            self.review_moves_table.setItem(row, 0, number_item)
            move_item = QTableWidgetItem(row_data['move'])
            move_item.setData(Qt.ItemDataRole.UserRole, item_data)
            self.review_moves_table.setItem(row, 1 if node and node.color == chess.WHITE else 2, move_item)
            kind_item = QTableWidgetItem(row_data['kind'])
            kind_item.setData(Qt.ItemDataRole.UserRole, item_data)
            self.review_moves_table.setItem(row, 3, kind_item)

    def _set_review_card(self, card: QFrame, title: str, value: str, caption: str) -> None:
        card.findChild(QLabel, 'ReviewCardTitle').setText(title)
        card.findChild(QLabel, 'ReviewCardValue').setText(value)
        card.findChild(QLabel, 'ReviewCardCaption').setText(caption)

    def _on_review_move_clicked(self, row: int, column: int) -> None:
        item = self.review_moves_table.item(row, column)
        if item is None or item.data(Qt.ItemDataRole.UserRole) is None:
            for fallback_column in (2, 1, 3):
                item = self.review_moves_table.item(row, fallback_column)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) is not None:
                    break
        if item is None:
            return
        review_item = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(review_item, dict):
            if review_item.get('variation') and review_item.get('node_id'):
                self._show_tree_node(review_item['node_id'])
                return
            target_index = max(0, int(review_item['index']) - 1)
            self._jump_review_move(target_index)

    def _on_review_category_clicked(self, row: int, _column: int) -> None:
        item = self.review_summary_table.item(row, 0)
        if item is None:
            return
        category = item.data(Qt.ItemDataRole.UserRole) or item.text().strip().lower()
        if category not in REVIEW_CATEGORIES_FULL:
            return
        current_ply = self.review_rows[self.review_index]['index'] if self.review_rows else -1
        ply = self.review_navigator.first_ply_with_label(self.review_annotations, category, after_ply=current_ply)
        if ply is None:
            self._update_status(f'No {category} moves found')
            return
        self._jump_review_move(ply - 1)

    def _on_review_line_clicked(self, row: int, column: int) -> None:
        item = self.review_lines_table.item(row, column)
        if item is None:
            item = self.review_lines_table.item(row, 0)
        line = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        node = self._current_review_node()
        if line is None or node is None:
            return
        self.selected_engine_line = line
        preview = ChessBoard.from_fen(node.before_fen)
        first_move = None
        for uci in line.pv_uci:
            move = chess.Move.from_uci(uci)
            if move not in preview.legal_moves:
                break
            if first_move is None:
                first_move = move
            preview.push(move)
        self.review_board_state = preview
        self.review_board_widget.set_board(preview)
        self.review_board_widget.clear_arrows()
        self.review_board_widget.set_last_move(first_move)
        if first_move is not None:
            self.review_board_widget.set_hint_move(first_move, 'arrow')
        self.review_eval_bar.set_result(None)
        self.review_eval_bar.set_evaluation(int(line.score_cp))
        self._update_review_material_display()
        self.selected_variation_fen = preview.fen()
        self._request_review_analysis(preview.fen(), 'Previewing and analyzing Stockfish line...')
        self.selected_engine_line = line
        self._update_status('Previewing Stockfish line')

    def _on_review_board_move(self, move_uci: str) -> None:
        parent_id = self.move_tree.selected_node_id
        if parent_id == self.move_tree.root_id and self.selected_review_node_id:
            parent_id = self.selected_review_node_id
        self.move_tree.select(parent_id)
        node = self.variation_manager.play_from_selected(move_uci)
        if node is None:
            return
        self._refresh_review_tables()
        self._show_tree_node(node.node_id)
        self._update_status('Variation saved')

    def _add_selected_engine_line(self) -> None:
        if self.selected_engine_line is None:
            self._update_status('Select a Stockfish line first')
            return
        parent_id = self.move_tree.root_id
        if self.selected_review_node_id and self.selected_review_node_id in self.move_tree.nodes:
            parent_id = self.move_tree.nodes[self.selected_review_node_id].parent_node_id or self.move_tree.root_id
        elif self.move_tree.selected_node_id in self.move_tree.nodes:
            parent_id = self.move_tree.selected_node_id
        created = self.variation_manager.save_engine_line(parent_id, self.selected_engine_line.pv_uci)
        if not created:
            self._update_status('No legal line to add')
            return
        self._refresh_review_tables()
        self._show_tree_node(created[-1].node_id)
        self._update_status('Engine line saved as a variation')

    def _promote_selected_variation(self) -> None:
        node_id = self.move_tree.selected_node_id
        node = self.move_tree.nodes.get(node_id)
        if node is None or node.is_mainline:
            self._update_status('Select a variation move to promote')
            return
        self.move_tree.promote_to_mainline(node_id)
        self._refresh_review_tables()
        self._update_status('Variation promoted in the analysis tree')

    def _jump_review_move(self, index: int) -> None:
        if not self.review_rows:
            return
        self.review_index = max(0, min(index, len(self.review_rows) - 1))
        item = self.review_rows[self.review_index]
        row = (item['index'] - 1) // 2
        column = 1 if item['side'] == chess.WHITE else 2
        self.review_moves_table.setCurrentCell(row, column)
        self._show_review_position(item)

    def _show_tree_node(self, node_id: str) -> None:
        node = self.move_tree.select(node_id)
        if node is None:
            return
        self.selected_review_node_id = node.node_id
        self.review_board_state = ChessBoard.from_fen(node.after_fen)
        move = chess.Move.from_uci(node.move_uci)
        self.review_board_widget.set_board(self.review_board_state)
        self.review_board_widget.set_last_move(move)
        self.review_board_widget.clear_arrows()
        overlay = self.overlay_manager.state_for(move, node.annotation_label, node.engine_best_move)
        self.review_board_widget.set_review_overlay(overlay)
        self.review_eval_bar.set_result(None)
        self.review_eval_bar.set_evaluation(int(node.engine_evaluation or 0))
        self.review_binding.show_waiting(f'{node.source.title()} variation: {node.san}')
        self.review_coach_label.setText('This is a saved analysis branch. It does not change the original game.')
        self.selected_variation_fen = node.after_fen
        self._request_review_analysis(node.after_fen, 'Analyzing selected variation...')
        self._update_review_material_display()

    def _show_review_position(self, item: dict, analyze: bool = True) -> None:
        self.review_index = max(0, next((index for index, row in enumerate(self.review_rows) if row is item or row.get('index') == item.get('index')), self.review_index))
        self.selected_engine_line = None
        self.selected_variation_fen = None
        self.selected_review_node_id = item.get('node_id') or None
        if self.selected_review_node_id:
            self.move_tree.select(self.selected_review_node_id)
        self.review_board_state = ChessBoard.from_fen(item['fen'])
        move = chess.Move.from_uci(item['move'])
        self.review_board_widget.set_board(self.review_board_state)
        self.review_board_widget.set_last_move(move)
        self.review_board_widget.clear_arrows()
        if item['category'] in {'inaccuracy', 'mistake', 'miss', 'blunder'}:
            self.review_board_widget.set_hint_move(move, 'arrow')
        else:
            self.review_board_widget.set_hint_move(None, None)
        self.review_eval_bar.set_result(None)
        self.review_eval_bar.set_evaluation(int(item['eval']))
        self.move_history.select_ply(int(item['index']))
        node = self.review_navigator.node_at(int(item['index']))
        annotation = self.review_annotations.get(int(item['index']), MoveAnnotation(int(item['index'])))
        opening = self._opening_for_ply(max(0, int(item['index']) - 1))
        best_move_uci = annotation.analysis.best_move_uci if annotation.analysis else None
        self.review_board_widget.set_review_overlay(self.overlay_manager.state_for(move, annotation.label, best_move_uci))
        if annotation.analysis and not analyze:
            self.review_binding.show_analysis(annotation.analysis, annotation, opening)
        elif not analyze:
            self.review_lines_table.setRowCount(0)
        self.review_move_header.setText(
            f"{REVIEW_MARKERS.get(item['category'], '')} {item['category'].title()} ({self._delta_text(self._move_eval_delta(item))})"
        )
        self.review_coach_label.setText(
            self._specific_coach_comment(item, annotation, opening)
        )
        if analyze and node:
            self._request_review_analysis(node.before_fen, f'Analyzing position before {item["san"]}...')
        self._update_review_material_display()

    def _review_analysis_text(self, item: dict) -> str:
        label = item['category'].title()
        score = f"{item['eval'] / 100:+.2f}"
        header = f"{REVIEW_MARKERS[item['category']]} {item['san']} is {label}   {score}"
        lines = item.get('lines') or ['Stockfish lines unavailable']
        cloud_note = '\nCloud enabled: using local fallback unless a cloud provider is configured.' if self.cloud_stockfish_enabled else ''
        return '\n'.join([header, *lines]) + cloud_note

    def _on_active_analysis_ready(self, result: AnalysisResult) -> None:
        if self.stack.currentWidget() == self.game_page:
            if result.fen != self.board.fen():
                return
            start = time.perf_counter()
            self.eval_bar.set_evaluation({'score_type': result.score_type, 'score_value': result.score_value, 'value': result.score_value})
            if self.game_mode == 'coach' and self.board.move_stack:
                opening = self.opening_repertoire.opening_for_moves([move.uci() for move in self.board.move_stack])
                self.analysis_box.setPlainText(self.coach_service.move_reaction(self.board, self.board.peek(), result, opening))
            LOGGER.info('UI update cost %.1f ms', (time.perf_counter() - start) * 1000)
            return
        if result.fen != self.selected_analysis_fen:
            return
        node = self._current_review_node()
        if self.selected_variation_fen and result.fen == self.selected_variation_fen:
            self.review_binding.show_analysis(result, None, self.opening_repertoire.opening_for_moves([]))
            self.review_coach_label.setText(self.coach_service.comment(None, result, board=self.review_board_state))
            return
        if node is None or result.fen != node.before_fen:
            return
        opening = self._opening_for_ply(node.ply - 1)
        annotation = self.review_annotator.annotate(node, result, opening)
        self.review_annotations[node.ply] = annotation
        self._sync_review_row_for_ply(node.ply)
        self._refresh_review_tables()
        item = next((row for row in self.review_rows if row.get('index') == node.ply), None)
        if item:
            self._show_review_position(item, analyze=False)

    def _on_active_analysis_failed(self, message: str) -> None:
        if self.review_binding:
            self.review_binding.show_waiting(f'Analysis unavailable: {message}')

    def _captured_by_on(self, board: chess.Board, capturer_color: chess.Color) -> tuple[str, int]:
        opponent = not capturer_color
        captured = []
        score = 0
        for piece_type, initial_count in INITIAL_COUNTS.items():
            remaining = len(board.pieces(piece_type, opponent))
            missing = max(0, initial_count - remaining)
            captured.extend([PIECE_SYMBOLS[(opponent, piece_type)]] * missing)
            score += missing * PIECE_VALUES[piece_type]
        return ' '.join(captured), score

    def _update_review_material_display(self) -> None:
        player_pieces, player_score = self._captured_by_on(self.review_board_state, chess.WHITE)
        bot_pieces, bot_score = self._captured_by_on(self.review_board_state, chess.BLACK)
        diff = player_score - bot_score
        player_plus = f' +{diff}' if diff > 0 else ''
        bot_plus = f' +{-diff}' if diff < 0 else ''
        self.review_player_captures_label.setText(f'{player_pieces}{player_plus}'.strip())
        self.review_bot_captures_label.setText(f'{bot_pieces}{bot_plus}'.strip())

    def _set_review_summary_row(self, row: int, label: str, player: str, marker: str, bot: str) -> None:
        values = (label, str(player), marker, str(bot))
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if column else Qt.AlignmentFlag.AlignLeft)
            if column == 0:
                item.setData(Qt.ItemDataRole.UserRole, label.lower())
            self.review_summary_table.setItem(row, column, item)

    def _accuracy_for(self, stats: dict) -> str:
        if stats['analysed_moves'] == 0 or stats['weight'] <= 0:
            return 'Pending'
        accuracy = stats['weighted_accuracy'] / stats['weight']
        suffix = ' partial' if stats['analysed_moves'] < stats['moves'] else ''
        return f'{max(0, min(100, accuracy)):.1f}%{suffix}'

    def _elo_for(self, stats: dict) -> str:
        rating, confidence, _reason = self._rating_estimate(stats)
        return f'{rating} ({confidence})'

    def _rating_estimate(self, stats: dict) -> tuple[int, str, str]:
        if stats['analysed_moves'] == 0 or stats['weighted_loss_weight'] <= 0:
            return 0, 'pending', 'Waiting for analysed moves.'
        avg_loss = stats['weighted_loss'] / stats['weighted_loss_weight']
        rating_points = (
            (8, 2700),
            (12, 2400),
            (18, 2100),
            (25, 1800),
            (35, 1500),
            (50, 1200),
            (70, 1000),
            (100, 800),
            (150, 600),
            (200, 400),
            (300, 200),
        )
        rating = 150
        for loss, elo in rating_points:
            if avg_loss <= loss:
                rating = elo
                break
        rating -= stats['blunder'] * 90
        rating -= stats['mistake'] * 45
        rating += min(120, (stats['best'] + stats['excellent']) * 10)
        if stats['moves'] < 20:
            rating = min(rating, 1400)
        if stats['moves'] < 10:
            rating = min(rating, 1000)
        rating = max(100, min(2800, int(round(rating / 25) * 25)))
        if stats['analysed_moves'] < 10 or stats['moves'] < 20:
            confidence = 'Low'
        elif stats['analysed_moves'] < stats['moves']:
            confidence = 'Medium'
        else:
            confidence = 'High'
        if stats['moves'] < 20:
            reason = 'Short game; rating confidence is capped.'
        elif stats['blunder'] or stats['mistake']:
            reason = f"Average loss {avg_loss:.0f} cp with {stats['mistake']} mistakes and {stats['blunder']} blunders."
        else:
            reason = f'Average loss {avg_loss:.0f} cp across analysed moves.'
        return rating, confidence, reason

    def _review_report_text(self, review: dict) -> str:
        stats = review['categories']
        return '\n\n'.join(
            [
                self._review_line('Player', stats[chess.WHITE]),
                self._review_line(str(self.bot_profile['name']), stats[chess.BLACK]),
                'Select any reviewed move row to inspect its marker and eval.',
            ]
        )

    def _heuristic_move_loss(self, board: chess.Board, move: chess.Move) -> int:
        loss = 75
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if captured:
                loss -= PIECE_VALUES.get(captured.piece_type, 0) * 28
            if attacker and captured and PIECE_VALUES.get(attacker.piece_type, 0) > PIECE_VALUES.get(captured.piece_type, 0):
                loss += 90

        test_board = board.copy(stack=False)
        test_board.push(move)
        if test_board.is_check():
            loss -= 35
        if test_board.is_checkmate():
            loss = 0
        if move.promotion:
            loss -= 80

        moved_piece = board.piece_at(move.from_square)
        if moved_piece and moved_piece.piece_type in (chess.KNIGHT, chess.BISHOP) and len(board.move_stack) < 12:
            loss -= 25
        if moved_piece and moved_piece.piece_type == chess.QUEEN and len(board.move_stack) < 8:
            loss += 70
        return max(0, loss)

    def _review_line(self, name: str, stats: dict) -> str:
        accuracy = self._accuracy_for(stats)
        estimated_elo, confidence, reason = self._rating_estimate(stats)
        return (
            f'{name}: Accuracy {accuracy}, Estimated Rating {estimated_elo}, Confidence {confidence}\n'
            f'{reason}\n'
            f"Best {stats['best']} | Good {stats['good']} | Inaccuracies {stats['inaccuracy']} | "
            f"Mistakes {stats['mistake']} | Blunders {stats['blunder']}"
        )

    def _upload_pgn(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Upload PGN', str(Path.home()), 'PGN Files (*.pgn);;All Files (*)')
        if not path:
            return
        with open(path, 'r', encoding='utf-8') as handle:
            game = chess.pgn.read_game(io.StringIO(handle.read()))
        if game is None:
            QMessageBox.warning(self, 'Upload PGN', 'No PGN game found in that file.')
            return
        self.board = ChessBoard()
        for move in game.mainline_moves():
            self.board.push(move)
        self._game_over = self.board.is_game_over()
        self._set_review_available(self._game_over)
        if self.board.is_checkmate():
            self.eval_bar.set_result('1-0' if self.board.turn == chess.BLACK else '0-1')
        elif self.board.is_stalemate():
            self.eval_bar.set_result('1/2')
        self.stack.setCurrentWidget(self.game_page)
        self.board_widget.set_board(self.board)
        self.board_widget.clear_marks()
        self.move_history.update_from_board(self.board)
        self._sync_board_state()
        self._update_status('PGN uploaded')
        self._review_game()

    def _update_status(self, message: str) -> None:
        self.status_label.setText(message)
        self.statusBar().showMessage(message)

    def _new_game(self) -> None:
        self.board = ChessBoard()
        self._game_over = False
        self._set_review_available(False)
        self._thinking = False
        self._hint_stage = 0
        self.pending_premove = None
        self.eval_bar.set_result(None)
        self.board_widget.set_premove_color(None)
        self.board_widget.set_premove(None)
        self.board_widget.set_last_move(None)
        self.board_widget.set_hint_move(None, None)
        self.board_widget.clear_marks()
        self.board_widget.set_flipped(self.game_mode == 'bot' and self.player_side == chess.BLACK)
        self.board_widget.set_board(self.board)
        self.move_history.update_from_board(self.board)
        self.eval_bar.set_evaluation(0)
        self.analysis_box.clear()
        self.review_box.clear()
        self.review_analysis_box.clear()
        self._reset_review_board()
        self._sync_board_state()
        if self.game_mode == 'local':
            self._update_status('White to move')
        elif self.player_side == chess.BLACK:
            self._update_status(f"{self.bot_profile['name']} to move")
        else:
            self._update_status('Player to move')

    def _reset_review_board(self) -> None:
        self.review_board_state = ChessBoard()
        self.review_board_widget.set_board(self.review_board_state)
        self.review_board_widget.set_last_move(None)
        self.review_board_widget.clear_marks()
        self.review_eval_bar.set_result(None)
        self.review_eval_bar.set_evaluation(0)
        self._update_review_material_display()

    def _undo_move(self) -> None:
        if self._thinking or self._game_over:
            return
        if self.game_mode == 'local':
            self.board.undo_move()
        else:
            self.board.undo_move()
            self.board.undo_move()
        self._hint_stage = 0
        self.pending_premove = None
        self.board_widget.set_premove(None)
        self.board_widget.clear_marks()
        self._sync_board_state()
        self._update_status('Move undone')

    def _flip_board(self) -> None:
        self.board_widget.set_flipped(self.board_widget.show_from_white)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.active_analysis:
            self.active_analysis.shutdown()
        if self.engine:
            self.engine.shutdown()
        if self.analysis_engine:
            self.analysis_engine.shutdown()
        super().closeEvent(event)
