from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "resources"
STYLES_PATH = RESOURCES_DIR / "styles.qss"

BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8
FILES = "abcdefgh"
RANKS = "12345678"

LIGHT_SQUARE = "#F0D9B5"
DARK_SQUARE = "#B58863"
LAST_MOVE_HIGHLIGHT = "#E6C35C"
SELECTION_HIGHLIGHT = "#6FA8DC"
LEGAL_MOVE_DOT = "#2E7D32"

PIECE_UNICODE = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",
    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}

DIFFICULTY_PRESETS = {
    "300 Elo": {"elo": 300, "skill_level": 0, "depth": 4},
    "500 Elo": {"elo": 500, "skill_level": 2, "depth": 6},
    "1000 Elo": {"elo": 1000, "skill_level": 5, "depth": 8},
    "1500 Elo": {"elo": 1500, "skill_level": 10, "depth": 10},
    "2000 Elo": {"elo": 2000, "skill_level": 15, "depth": 14},
}
