"""Coach comments derived from structured review data."""

from __future__ import annotations

from chess_game.review.models import AnalysisResult, MoveAnnotation


class CoachBotService:
    """Creates short review comments from annotations and engine lines."""

    def comment(self, annotation: MoveAnnotation | None, analysis: AnalysisResult | None) -> str:
        if annotation is None:
            if analysis and analysis.best_move_san:
                return f'Stockfish prefers {analysis.best_move_san} in this position.'
            return 'Select a move and I will look at it with Stockfish.'
        label = annotation.label
        best = analysis.best_move_san if analysis and analysis.best_move_san else None
        if label == 'book':
            return 'That was a book move.'
        if label in {'best', 'excellent'}:
            return 'This move lines up well with Stockfish.'
        if label == 'good':
            return 'This keeps the position playable.'
        if label == 'inaccuracy':
            return f'This is a little loose. Stockfish prefers {best} here.' if best else 'This is a little loose.'
        if label == 'mistake':
            return f'This worsens the position. Stockfish wanted {best}.' if best else 'This worsens the position.'
        if label == 'blunder':
            return f'This drops too much. The better move was {best}.' if best else 'This drops too much.'
        if label == 'miss':
            return f'There was a stronger chance here, usually {best}.' if best else 'There was a stronger chance here.'
        return 'Stockfish is checking this move.'
