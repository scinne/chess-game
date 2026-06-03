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
LIGHT_SQUARE_COLOR = QColor(240, 217, 181)  # #F0D9B5
DARK_SQUARE_COLOR = QColor(181, 136, 99)  # #B58863

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
    300: {'name': 'Easy', 'depth': 10, 'skill': 0},
    500: {'name': 'Intermediate', 'depth': 15, 'skill': 5},
    1000: {'name': 'Intermediate+', 'depth': 18, 'skill': 10},
    1500: {'name': 'Advanced', 'depth': 22, 'skill': 15},
    2000: {'name': 'Expert', 'depth': 25, 'skill': 20},
}
