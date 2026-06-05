"""Analysis controller for selected review positions."""

from __future__ import annotations

from chess_game.review.engine_manager import StockfishAnalysisManager


class AnalysisController:
    """Coordinates selected-position analysis requests."""

    def __init__(self, manager: StockfishAnalysisManager) -> None:
        self.manager = manager
        self.current_fen: str | None = None

    def analyze_selected(self, fen: str, *, lines: int, time_seconds: float, threads: int) -> None:
        self.current_fen = fen
        self.manager.analyze(fen, lines=lines, time_seconds=time_seconds, threads=threads)

    def stop(self) -> None:
        self.manager.stop()

    def clear_cache(self) -> None:
        self.manager.clear_cache()
