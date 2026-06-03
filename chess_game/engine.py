from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import chess
import chess.engine

from chess_game.utils.constants import DIFFICULTY_PRESETS, MATE_SCORE


@dataclass(frozen=True)
class EngineLine:
    move: chess.Move
    score_cp: int


class StockfishEngine:
    def __init__(self, difficulty: str = "1000 Elo", engine_path: str | None = None) -> None:
        self._difficulty = difficulty if difficulty in DIFFICULTY_PRESETS else "1000 Elo"
        self.engine_path = engine_path or self._autodetect_stockfish()
        self._engine = None
        if self.engine_path:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            self._configure()

    @staticmethod
    def _autodetect_stockfish() -> str | None:
        candidates: Iterable[str] = (
            "stockfish",
            "/usr/games/stockfish",
            "/usr/local/bin/stockfish",
            str(Path.home() / "stockfish" / "stockfish"),
        )
        for candidate in candidates:
            resolved = shutil.which(candidate) if "/" not in candidate else candidate
            if resolved and Path(resolved).exists():
                return resolved
        return None

    def _configure(self) -> None:
        if not self._engine:
            return
        preset = DIFFICULTY_PRESETS[self._difficulty]
        options = {
            "Skill Level": preset["skill_level"],
            "UCI_LimitStrength": True,
            "UCI_Elo": preset["elo"],
        }
        self._engine.configure(options)

    def set_difficulty(self, difficulty: str) -> None:
        if difficulty not in DIFFICULTY_PRESETS:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        self._difficulty = difficulty
        self._configure()

    def is_available(self) -> bool:
        return self._engine is not None

    def _limit(self) -> chess.engine.Limit:
        return chess.engine.Limit(depth=DIFFICULTY_PRESETS[self._difficulty]["depth"])

    def get_best_move(self, board: chess.Board) -> chess.Move | None:
        if not self._engine or board.is_game_over():
            return None
        result = self._engine.play(board, self._limit())
        return result.move

    def get_evaluation(self, board: chess.Board) -> int | None:
        if not self._engine:
            return None
        info = self._engine.analyse(board, self._limit())
        score = info.get("score")
        if score is None:
            return None
        return score.white().score(mate_score=MATE_SCORE)

    def get_top_moves(self, board: chess.Board, lines: int = 3) -> list[EngineLine]:
        if not self._engine:
            return []
        infos = self._engine.analyse(board, self._limit(), multipv=max(1, lines))
        if isinstance(infos, dict):
            infos = [infos]
        top: list[EngineLine] = []
        for entry in infos:
            pv = entry.get("pv")
            score = entry.get("score")
            if not pv or score is None:
                continue
            top.append(EngineLine(move=pv[0], score_cp=score.white().score(mate_score=MATE_SCORE)))
        return top

    def close(self) -> None:
        if self._engine:
            self._engine.quit()
            self._engine = None

    def __enter__(self) -> "StockfishEngine":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
