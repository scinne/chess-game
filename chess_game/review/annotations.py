"""Move annotation logic."""

from __future__ import annotations

import math

import chess

from chess_game.review.models import AnalysisResult, MoveAnnotation, MoveNode


class ReviewAnnotator:
    """Classifies played moves against structured engine analysis."""

    MATE_COMPARE_CP = 3000
    LOSS_CAP_CP = 1000
    EQUAL_TOLERANCE_CP = 10

    def annotate(self, node: MoveNode, analysis: AnalysisResult | None, opening: dict | None = None) -> MoveAnnotation:
        before_board = chess.Board(node.before_fen)
        if opening and opening.get('in_book'):
            book_moves = {item['uci'] for item in opening.get('book_moves', [])}
            if node.uci in book_moves:
                evaluation = analysis.evaluation_cp if analysis else 0
                return MoveAnnotation(
                    node.ply,
                    'book',
                    0,
                    evaluation,
                    'Known book move',
                    analysis,
                    eval_before_cp=0,
                    best_eval_cp=evaluation,
                    played_eval_cp=evaluation,
                    move_accuracy=100.0,
                    weight=0.3,
                    analysed=analysis is not None,
                    estimated=analysis is None,
                    confidence='low' if analysis is None else 'medium',
                    debug=self._debug(node, analysis, 0, evaluation, evaluation, 0, 100.0, 'book', 0.3),
                )

        if analysis is None or not analysis.lines:
            return MoveAnnotation(node.ply, 'pending', 0, 0, 'Waiting for engine analysis', analysis)

        best = analysis.lines[0]
        played_line = next((line for line in analysis.lines if line.move_uci == node.uci), None)
        played_eval = played_line.score_cp if played_line else analysis.evaluation_cp
        eval_before = self._result_cp_for_compare(analysis)
        side_eval = self._side_eval(played_eval, node.side)
        best_side_eval = self._side_eval(best.score_cp, node.side)
        loss = max(0, best_side_eval - side_eval)
        if loss <= self.EQUAL_TOLERANCE_CP:
            loss = 0
        loss = min(self.LOSS_CAP_CP, loss)
        move_accuracy = self._move_accuracy(loss)
        weight = self._position_weight(before_board, loss, opening)

        played_rank = next((index for index, line in enumerate(analysis.lines, start=1) if line.move_uci == node.uci), None)

        if self._missed_forced_mate(node, analysis, played_line):
            label = 'miss'
        elif self._allowed_forced_mate(node, analysis, played_eval):
            label = 'blunder'
        elif node.uci == best.move_uci or loss <= 10:
            label = 'best'
        elif loss <= 25:
            label = 'excellent'
        elif self._is_great(node, before_board, loss, best):
            label = 'great'
        elif loss <= 70:
            label = 'good'
        elif loss <= 150:
            label = 'inaccuracy'
        elif loss <= 300:
            label = 'mistake'
        else:
            label = 'blunder'

        return MoveAnnotation(
            node.ply,
            label,
            int(loss),
            int(played_eval),
            self._reason(label, loss),
            analysis,
            eval_before_cp=int(eval_before),
            best_eval_cp=int(best.score_cp),
            played_eval_cp=int(played_eval),
            move_accuracy=move_accuracy,
            weight=weight,
            analysed=True,
            estimated=played_line is None,
            confidence='medium',
            debug=self._debug(node, analysis, eval_before, best.score_cp, played_eval, loss, move_accuracy, label, weight),
        )

    def _side_eval(self, white_eval: int, side: chess.Color) -> int:
        return white_eval if side == chess.WHITE else -white_eval

    def _result_cp_for_compare(self, analysis: AnalysisResult) -> int:
        if analysis.score_type == 'mate':
            mate = int(analysis.score_value)
            return self.MATE_COMPARE_CP if mate > 0 else -self.MATE_COMPARE_CP
        return int(analysis.evaluation_cp)

    def _move_accuracy(self, loss_cp: int) -> float:
        return max(0.0, min(100.0, 100.0 * math.exp(-max(0, loss_cp) / 120.0)))

    def _position_weight(self, board: chess.Board, loss_cp: int, opening: dict | None) -> float:
        if opening and opening.get('in_book'):
            return 0.3
        if board.legal_moves.count() <= 1:
            return 0.2
        weight = 1.0
        if abs(self._material_eval(board)) > 800:
            weight = 0.4
        if loss_cp >= 300:
            weight = max(weight, 1.5)
        return weight

    def _material_eval(self, board: chess.Board) -> int:
        values = {
            chess.PAWN: 100,
            chess.KNIGHT: 300,
            chess.BISHOP: 300,
            chess.ROOK: 500,
            chess.QUEEN: 900,
        }
        return sum(
            (len(board.pieces(piece_type, chess.WHITE)) - len(board.pieces(piece_type, chess.BLACK))) * value
            for piece_type, value in values.items()
        )

    def _missed_forced_mate(self, node: MoveNode, analysis: AnalysisResult, played_line) -> bool:
        return analysis.score_type == 'mate' and int(analysis.score_value) > 0 and node.uci != analysis.best_move_uci and played_line is None

    def _allowed_forced_mate(self, node: MoveNode, analysis: AnalysisResult, played_eval: int) -> bool:
        del node
        return analysis.score_type == 'mate' and int(analysis.score_value) < 0 and played_eval <= -self.MATE_COMPARE_CP

    def _is_great(self, node: MoveNode, board: chess.Board, loss_cp: int, best) -> bool:
        if loss_cp > 25:
            return False
        move = chess.Move.from_uci(node.uci)
        if move not in board.legal_moves:
            return False
        test = board.copy(stack=False)
        test.push(move)
        return test.is_check() or board.is_capture(move) or best.score_cp * (1 if node.side == chess.WHITE else -1) > 500

    def _debug(
        self,
        node: MoveNode,
        analysis: AnalysisResult | None,
        eval_before: int,
        best_eval: int,
        played_eval: int,
        loss: int,
        move_accuracy: float,
        category: str,
        weight: float,
    ) -> dict:
        return {
            'fen_before': node.before_fen,
            'played_move': node.uci,
            'best_move': analysis.best_move_uci if analysis else None,
            'eval_before_cp': int(eval_before),
            'eval_after_cp': int(played_eval),
            'best_eval_cp': int(best_eval),
            'centipawn_loss': int(loss),
            'move_accuracy': round(move_accuracy, 2),
            'category': category,
            'weight': round(weight, 2),
        }

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
