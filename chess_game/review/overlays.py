"""Board overlay state for review and analysis."""

from __future__ import annotations

from dataclasses import dataclass

import chess


MOVE_QUALITY_BADGES = {
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

MOVE_QUALITY_COLORS = {
    'brilliant': '#24c9b0',
    'great': '#5b93bd',
    'book': '#c89a64',
    'best': '#73ad43',
    'excellent': '#6fb65f',
    'good': '#8eb36d',
    'inaccuracy': '#d5ad32',
    'mistake': '#df8b43',
    'miss': '#e35d54',
    'blunder': '#d73a31',
    'pending': '#7a886f',
}


@dataclass(frozen=True)
class BoardOverlayState:
    selected_move: chess.Move | None = None
    best_move: chess.Move | None = None
    badge_square: int | None = None
    badge_label: str = ''


class BoardOverlayManager:
    """Builds centralized overlay state for board widgets."""

    def state_for(self, played_move: chess.Move | None, label: str, best_move_uci: str | None) -> BoardOverlayState:
        best_move = None
        if best_move_uci:
            try:
                best_move = chess.Move.from_uci(best_move_uci)
            except ValueError:
                best_move = None
        return BoardOverlayState(
            selected_move=played_move,
            best_move=best_move,
            badge_square=played_move.to_square if played_move else None,
            badge_label=label,
        )
