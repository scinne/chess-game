"""Theme loading helpers for the PyQt UI."""

from __future__ import annotations

from pathlib import Path


THEME_DIR = Path(__file__).resolve().parents[1] / 'resources'
LIGHT_THEME_PATH = THEME_DIR / 'styles.qss'


def load_stylesheet(theme: str = 'light') -> str:
    """Load the active theme stylesheet.

    The app currently ships one light theme. Keeping this indirection makes a
    future dark-theme toggle a data/config change instead of a widget rewrite.
    """

    path = LIGHT_THEME_PATH
    if theme != 'light':
        path = THEME_DIR / f'{theme}.qss'
    if path.exists():
        return path.read_text(encoding='utf-8')
    return LIGHT_THEME_PATH.read_text(encoding='utf-8') if LIGHT_THEME_PATH.exists() else ''
