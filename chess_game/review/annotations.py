"""Move annotation logic."""

from __future__ import annotations

import chess

from chess_game.review.models import AnalysisResult, MoveAnnotation, MoveNode


class ReviewAnnotator:
    """Classifies played moves against structured engine analysis."""

    def annotate(self, node: MoveNode, analysis: AnalysisResult | None, opening: dict | None = None) -> MoveAnnotation:
        if opening and opening.get('in_book'):
            book_moves = {item['uci'] for item in opening.get('book_moves', [])}
            if node.uci in book_moves or node.ply <= 4:
                return MoveAnnotation(node.ply, 'book', 0, analysis.evaluation_cp if analysis else 0, 'Known book move', analysis)

        if analysis is None or not analysis.lines:
            return MoveAnnotation(node.ply, 'pending', 0, 0, 'Waiting for engine analysis', analysis)

        best = analysis.lines[0]
        played_line = next((line for line in analysis.lines if line.move_uci == node.uci), None)
        played_eval = played_line.score_cp if played_line else analysis.evaluation_cp
        side_eval = played_eval if node.side == chess.WHITE else -played_eval
        best_side_eval = best.score_cp if node.side == chess.WHITE else -best.score_cp
        loss = max(0, best_side_eval - side_eval)

        played_rank = next((index for index, line in enumerate(analysis.lines, start=1) if line.move_uci == node.uci), None)

        if node.uci == best.move_uci:
            label = 'best'
        elif played_rank in (2, 3):
            label = 'excellent'
        elif played_line and loss <= 80:
            label = 'good'
        elif loss <= 160:
            label = 'inaccuracy'
        elif loss <= 320:
            label = 'mistake'
        else:
            label = 'blunder'

        return MoveAnnotation(node.ply, label, int(loss), int(played_eval), self._reason(label, loss), analysis)

    def _reason(self, label: str, loss: int) -> str:
        if label == 'best':
            return 'Matches the engine top choice.'
        if label == 'good':
            return 'Playable move close to engine suggestions.'
        if label == 'inaccuracy':
            return f'Slightly worse than the top line by about {loss / 100:.1f} pawns.'
        if label == 'mistake':
            return f'Noticeable drop from the top line by about {loss / 100:.1f} pawns.'
        if label == 'blunder':
            return f'Major drop from the top line by about {loss / 100:.1f} pawns.'
        return ''
