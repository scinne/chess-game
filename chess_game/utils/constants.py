"""Application constants."""

try:
    from PyQt6.QtGui import QColor
except Exception:  # noqa: BLE001
    class QColor:  # type: ignore[override]
        """Fallback QColor for non-GUI environments."""

        def __init__(self, *_args) -> None:
            pass

# Board
BOARD_SIZE = 8
SQUARE_SIZE = 80  # pixels
LIGHT_SQUARE_COLOR = QColor(238, 238, 210)  # #EEEED2
DARK_SQUARE_COLOR = QColor(118, 150, 86)  # #769656

# Pieces
PIECE_SYMBOLS = {
    'K': 'King',
    'Q': 'Queen',
    'R': 'Rook',
    'B': 'Bishop',
    'N': 'Knight',
    'P': 'Pawn',
}

# Difficulty levels
DIFFICULTY_LEVELS = {
    250: {'name': 'Newcomer', 'skill': 0, 'move_time': 0.8, 'analysis_time': 0.04, 'randomness': 1.0},
    300: {'name': 'Easy', 'skill': 0, 'move_time': 0.9, 'analysis_time': 0.05, 'randomness': 1.0},
    500: {'name': 'Casual', 'skill': 0, 'move_time': 1.1, 'analysis_time': 0.05, 'randomness': 0.75},
    550: {'name': 'Learner', 'skill': 0, 'move_time': 1.0, 'analysis_time': 0.05, 'randomness': 0.78},
    650: {'name': 'Beginner', 'skill': 1, 'move_time': 1.1, 'analysis_time': 0.05, 'randomness': 0.62},
    800: {'name': 'Improver', 'skill': 1, 'move_time': 1.2, 'analysis_time': 0.05, 'randomness': 0.48},
    1000: {'name': 'Club', 'skill': 2, 'move_time': 1.5, 'analysis_time': 0.03, 'randomness': 0.35},
    1200: {'name': 'Intermediate', 'skill': 4, 'move_time': 1.7, 'analysis_time': 0.05, 'randomness': 0.25},
    1500: {'name': 'Advanced', 'skill': 8, 'move_time': 2.2, 'analysis_time': 0.07, 'randomness': 0.12},
    1600: {'name': 'Advanced+', 'skill': 9, 'move_time': 2.4, 'analysis_time': 0.07, 'randomness': 0.09},
    2000: {'name': 'Expert', 'skill': 14, 'move_time': 3.0, 'analysis_time': 0.08, 'randomness': 0.0},
    2200: {'name': 'Master', 'skill': 18, 'move_time': 3.2, 'analysis_time': 0.08, 'randomness': 0.0},
}
