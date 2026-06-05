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
    'P': '\u2659',
    'N': '\u2658',
    'B': '\u2657',
    'R': '\u2656',
    'Q': '\u2655',
    'K': '\u2654',
    'p': '\u265f',
    'n': '\u265e',
    'b': '\u265d',
    'r': '\u265c',
    'q': '\u265b',
    'k': '\u265a',
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


@functools.lru_cache(maxsize=128)
def load_piece_image(piece_symbol: str, theme: str = 'default', size: int = 80) -> 'QPixmap':
    """Load and rasterize a centered themed SVG piece image."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QPainter, QPixmap
    from PyQt6.QtSvg import QSvgRenderer

    del theme
    color = 'white' if piece_symbol.isupper() else 'black'
    name_map = {
        'k': 'king',
        'q': 'queen',
        'r': 'rook',
        'b': 'bishop',
        'n': 'knight',
        'p': 'pawn',
    }
    path = PIECES_DIR / f'{color}_{name_map[piece_symbol.lower()]}.svg'
    scale = 5
    physical_size = size * scale
    pixmap = QPixmap(physical_size, physical_size)
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(str(path))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    padding = size * 0.025
    renderer.render(painter, QRectF(padding, padding, size - padding * 2, size - padding * 2))
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
