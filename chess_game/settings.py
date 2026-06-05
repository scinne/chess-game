"""Application settings model."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class GameSettings:
    """Runtime settings that can later be persisted."""

    show_eval_bar: bool = True
    enable_stockfish_analysis: bool = True
    analysis_time_seconds: float = 0.15
    deep_analysis_time_seconds: float = 0.8
    analysis_lines: int = 3
    analysis_depth: int = 14
    analysis_threads: int = 2
    cloud_analysis: bool = False
    show_move_quality_icons: bool = True
    show_board_overlays: bool = True
    enable_premove: bool = True
    show_legal_moves: bool = True
    auto_queen: bool = True
    show_coordinates: bool = True
    debug_review_logging: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class SettingsManager:
    """Small settings holder used by the UI."""

    def __init__(self) -> None:
        self.settings = GameSettings()

    def update(self, **values) -> GameSettings:
        for key, value in values.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        return self.settings
