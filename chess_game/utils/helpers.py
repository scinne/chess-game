"""Helper utilities for board coordinate and display operations."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import TYPE_CHECKING, Union

import chess

if TYPE_CHECKING:
    from PyQt6.QtGui import QPixmap

BASE_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = BASE_DIR / 'resources'
PIECES_DIR = RESOURCES_DIR / 'pieces'

UNICODE_PIECES = {
    'P': '♙',
    'N': '♘',
    'B': '♗',
    'R': '♖',
    'Q': '♕',
    'K': '♔',
    'p': '♟',
    'n': '♞',
    'b': '♝',
    'r': '♜',
    'q': '♛',
    'k': '♚',
}


def square_to_coords(square: int) -> tuple[int, int]:
    """Convert a python-chess square index to board coordinates."""
    return chess.square_file(square), 7 - chess.square_rank(square)


def coords_to_square(x: int, y: int) -> int:
    """Convert board coordinates to a python-chess square index."""
    return chess.square(x, 7 - y)


def piece_to_symbol(piece: chess.Piece | None) -> str:
    """Return a unicode symbol for a piece, or empty for no piece."""
    if piece is None:
        return ''
    return UNICODE_PIECES.get(piece.symbol(), '')


@functools.lru_cache(maxsize=64)
def load_piece_image(piece_symbol: str, theme: str = 'default', size: int = 80) -> 'QPixmap':
    """Load and rasterize a themed SVG piece image into a QPixmap."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPainter, QPixmap
    from PyQt6.QtSvg import QSvgRenderer

    del theme  # single theme currently available
    color = 'white' if piece_symbol.isupper() else 'black'
    name_map = {
        'k': 'king',
        'q': 'queen',
        'r': 'rook',
        'b': 'bishop',
        'n': 'knight',
        'p': 'pawn',
    }
    piece_name = name_map[piece_symbol.lower()]
    path = PIECES_DIR / f'{color}_{piece_name}.svg'
    renderer = QSvgRenderer(str(path))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def format_evaluation(centipawns: Union[int, float, dict]) -> str:
    """Format centipawn or mate evaluation for user display."""
    if isinstance(centipawns, dict):
        if centipawns.get('type') == 'mate':
            mate = centipawns.get('value', 0)
            prefix = 'M' if mate >= 0 else '-M'
            return f'{prefix}{abs(int(mate))}'
        centipawns = centipawns.get('value', 0)

    score = float(centipawns) / 100.0
    if score > 0:
        return f'+{score:.2f}'
    return f'{score:.2f}'
