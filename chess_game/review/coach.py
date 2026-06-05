"""Coach and bot dialogue services."""

from __future__ import annotations

import chess

from chess_game.review.models import AnalysisResult, MoveAnnotation


class CoachService:
    """Creates teaching comments from position, opening, annotation, and engine data."""

    def comment(
        self,
        annotation: MoveAnnotation | None,
        analysis: AnalysisResult | None,
        *,
        board: chess.Board | None = None,
        opening: dict | None = None,
    ) -> str:
        if annotation is None:
            if analysis and analysis.best_move_san:
                return self._engine_preference(analysis, board)
            if opening and opening.get('in_book'):
                return f"{opening.get('name', 'This opening')} follows known development ideas."
            return 'Select a move and I will look at it with Stockfish.'
        label = annotation.label
        best = analysis.best_move_san if analysis and analysis.best_move_san else None
        if label == 'book':
            name = opening.get('name') if opening else None
            return f'That was a book move in {name}. Keep developing pieces and contesting the center.' if name else 'That was a book move. Keep developing pieces and contesting the center.'
        if label in {'best', 'excellent'}:
            return self._positive_comment(analysis, board)
        if label == 'good':
            return 'This keeps the position playable and avoids giving your opponent an obvious target.'
        if label == 'inaccuracy':
            return f'This is a little loose. Stockfish prefers {best} because it improves the position without creating as many weaknesses.' if best else 'This is a little loose.'
        if label == 'mistake':
            return f'This worsens the position. Stockfish wanted {best}, which better protects your pieces or king.' if best else 'This worsens the position.'
        if label == 'blunder':
            return f'This drops too much. The better move was {best}; look for checks, captures, and threats before committing.' if best else 'This drops too much. Look for checks, captures, and threats before committing.'
        if label == 'miss':
            return f'There was a stronger chance here, usually {best}. That kind of move often wins material or creates a tactical threat.' if best else 'There was a stronger chance here.'
        return 'Stockfish is checking this move.'

    def move_reaction(self, board: chess.Board, move: chess.Move, analysis: AnalysisResult | None, opening: dict | None) -> str:
        piece = board.piece_at(move.to_square)
        if opening and opening.get('in_book') and len(board.move_stack) <= 8:
            return f"{opening.get('name', 'The opening')} is still familiar territory. Focus on development and king safety."
        if board.is_check():
            return 'That move gives check, so your opponent must answer the immediate threat.'
        if piece and piece.piece_type in (chess.KNIGHT, chess.BISHOP) and len(board.move_stack) <= 10:
            return 'Developing a minor piece early helps control central squares and prepares castling.'
        if analysis and analysis.best_move_san:
            return self._engine_preference(analysis, board)
        return 'Good moment to ask what your opponent is threatening before choosing a plan.'

    def game_result_comment(self, result_title: str, reason: str, stats: dict | None = None) -> str:
        if result_title == 'You Won':
            return f'Nice finish. In review, look for the moves that turned {reason.lower()} into a forced result.'
        if result_title == 'You Lost':
            return f'{reason} decided it. We will review the largest mistakes first, then pick one theme to practice.'
        return f'{reason} ended the game. Review will show where either side could have pressed harder.'

    def _positive_comment(self, analysis: AnalysisResult | None, board: chess.Board | None) -> str:
        if board and len(board.move_stack) <= 10:
            return 'This fits the opening principles: develop, fight for the center, and keep your king safe.'
        if analysis and analysis.best_move_san:
            return f'This lines up well with Stockfish. {analysis.best_move_san} is strong because it improves coordination without losing time.'
        return 'This move lines up well with Stockfish.'

    def _engine_preference(self, analysis: AnalysisResult, board: chess.Board | None) -> str:
        best = analysis.best_move_san or '-'
        if board and board.is_check():
            return f'Stockfish prefers {best} while handling the check and keeping the position stable.'
        return f'Stockfish prefers {best} because it improves piece activity and limits counterplay.'


class BotPersonalityService:
    """Creates non-instructional bot flavor dialogue."""

    def comment(
        self,
        bot: dict,
        event: str = 'move',
        *,
        board: chess.Board | None = None,
        move: chess.Move | None = None,
        opening: dict | None = None,
        label: str | None = None,
    ) -> str:
        name = str(bot.get('name', 'Bot'))
        if event == 'mistake' or label in {'mistake', 'blunder', 'miss'}:
            event = 'mistake'
        line = self._line_from_pool(bot, event, board=board, move=move)
        if line:
            if opening and event == 'opening':
                return line.format(opening=opening.get('name', 'this opening'))
            return line
        if board and board.is_check():
            return self._line_from_pool(bot, 'check', board=board, move=move) or 'Your king has paperwork to do.'
        if move and board:
            before = board.copy(stack=True)
            try:
                before.pop()
                if before.is_capture(move):
                    return self._line_from_pool(bot, 'capture', board=board, move=move) or 'Pieces are leaving the board.'
            except IndexError:
                pass
        return str(bot.get('dialogue', f'{name} is ready.'))

    def _line_from_pool(
        self,
        bot: dict,
        event: str,
        *,
        board: chess.Board | None = None,
        move: chess.Move | None = None,
    ) -> str:
        pool = bot.get('dialogue_pool')
        if not isinstance(pool, dict):
            return ''
        lines = pool.get(event) or pool.get('move') or ()
        if not lines:
            return ''
        ply = len(board.move_stack) if board else 0
        move_seed = move.to_square if move else 0
        return str(lines[(ply + move_seed) % len(lines)])


# Backwards-compatible alias for older call sites while the UI migrates.
CoachBotService = CoachService
