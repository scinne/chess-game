"""Stockfish-backed chess engine wrapper."""

from __future__ import annotations

import os
import random
import shutil
import time
from pathlib import Path

import chess
import chess.engine

from chess_game.utils.constants import DIFFICULTY_LEVELS

class StockfishNotFoundError(RuntimeError):
    """Raised when a Stockfish binary cannot be initialized."""


class StockfishEngine:
    """Wrapper around a UCI Stockfish engine process."""

    def __init__(self, stockfish_path: str | None = None) -> None:
        self.stockfish_path = self._resolve_stockfish_path(stockfish_path)
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        except Exception as exc:  # noqa: BLE001
            raise StockfishNotFoundError(
                'Stockfish could not be started. Install the stockfish package or set STOCKFISH_PATH.'
            ) from exc

    def _resolve_stockfish_path(self, manual_path: str | None) -> str:
        """Resolve stockfish path from manual, env, package, or PATH."""
        candidates: list[str] = []
        if manual_path:
            candidates.append(manual_path)

        env_path = os.getenv('STOCKFISH_PATH')
        if env_path:
            candidates.append(env_path)

        path_cmd = shutil.which('stockfish')
        if path_cmd:
            candidates.append(path_cmd)

        try:
            import stockfish

            package_dir = Path(stockfish.__file__).resolve().parent
            for match in package_dir.rglob('*'):
                if match.is_file() and 'stockfish' in match.name.lower() and os.access(match, os.X_OK):
                    candidates.append(str(match))
        except Exception:  # noqa: BLE001
            pass

        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return str(candidate)

        raise StockfishNotFoundError(
            'Stockfish binary was not found. Install via `pip install stockfish` or provide a valid '
            'path in STOCKFISH_PATH.'
        )

    @staticmethod
    def _difficulty_settings(difficulty: int) -> dict:
        """Return mapped skill/depth settings for a difficulty."""
        if difficulty in DIFFICULTY_LEVELS:
            return DIFFICULTY_LEVELS[difficulty]
        closest = min(DIFFICULTY_LEVELS.keys(), key=lambda level: abs(level - difficulty))
        return DIFFICULTY_LEVELS[closest]

    def _configure(self, difficulty: int, threads: int | None = None) -> dict:
        settings = self._difficulty_settings(difficulty)
        options = {
            'Skill Level': settings['skill'],
            'UCI_LimitStrength': True,
            'UCI_Elo': max(1320, difficulty),
        }
        if threads is not None:
            options['Threads'] = max(1, int(threads))
        for name, value in options.items():
            try:
                self.engine.configure({name: value})
            except chess.engine.EngineError:
                continue
        return settings

    def _beginner_move(self, board: chess.Board, settings: dict) -> chess.Move | None:
        """Return an intentionally fallible move for lower difficulty levels."""
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None

        start = time.perf_counter()
        randomness = float(settings.get('randomness', 0.0))
        if random.random() > randomness:
            return None

        captures = [move for move in legal_moves if board.is_capture(move)]
        checks = []
        for move in legal_moves:
            test_board = board.copy(stack=False)
            test_board.push(move)
            if test_board.is_check():
                checks.append(move)

        if randomness >= 0.95:
            pool = legal_moves
        elif captures and random.random() < 0.45:
            pool = captures
        elif checks and random.random() < 0.25:
            pool = checks
        else:
            pool = legal_moves

        remaining = float(settings['move_time']) - (time.perf_counter() - start)
        if remaining > 0:
            time.sleep(remaining)
        return random.choice(pool)

    def get_best_move(self, board: chess.Board, difficulty: int = 1000) -> chess.Move | None:
        """Return the best move at configured Elo difficulty."""
        settings = self._configure(difficulty)
        beginner_move = self._beginner_move(board, settings)
        if beginner_move is not None:
            return beginner_move
        result = self.engine.play(board, chess.engine.Limit(time=settings['move_time']))
        return result.move

    def get_evaluation(self, board: chess.Board, difficulty: int = 1000, analysis_time: float | None = None, threads: int | None = None) -> dict:
        """Return position evaluation from White's perspective."""
        settings = self._configure(difficulty, threads=threads)
        info = self.engine.analyse(board, chess.engine.Limit(time=analysis_time or settings['analysis_time']))
        score = info['score'].white()
        if score.is_mate():
            return {'type': 'mate', 'value': score.mate() or 0}
        return {'type': 'cp', 'value': score.score(mate_score=100000) or 0}

    def get_top_moves(
        self,
        board: chess.Board,
        n: int = 3,
        difficulty: int = 1000,
        analysis_time: float | None = None,
        threads: int | None = None,
    ) -> list[dict]:
        """Return top N candidate moves with centipawn or mate scores."""
        settings = self._configure(difficulty, threads=threads)
        infos = self.engine.analyse(
            board,
            chess.engine.Limit(time=analysis_time or settings['analysis_time']),
            multipv=max(1, n),
        )
        if isinstance(infos, dict):
            infos = [infos]

        top_moves = []
        for item in infos[:n]:
            score = item['score'].white()
            entry = {
                'move': item['pv'][0].uci() if item.get('pv') else None,
                'line': [move.uci() for move in item.get('pv', [])[:8]],
                'type': 'mate' if score.is_mate() else 'cp',
                'score': score.mate() if score.is_mate() else (score.score(mate_score=100000) or 0),
                'depth': int(item.get('depth') or 0),
                'multipv': int(item.get('multipv') or len(top_moves) + 1),
            }
            top_moves.append(entry)
        return top_moves

    def shutdown(self) -> None:
        """Shutdown engine process safely."""
        try:
            self.engine.quit()
        except Exception:  # noqa: BLE001
            pass

    def __del__(self) -> None:
        self.shutdown()
