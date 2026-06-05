"""Structured review and analysis models."""

from __future__ import annotations

from dataclasses import dataclass, field
import time

import chess


@dataclass(frozen=True)
class MoveNode:
    """One played move and the resulting position."""

    ply: int
    move_number: int
    side: chess.Color
    san: str
    uci: str
    before_fen: str
    after_fen: str
    node_id: str = ''
    parent_node_id: str | None = None
    child_variation_ids: tuple[str, ...] = ()
    is_mainline: bool = True
    annotation_label: str = 'pending'
    comment: str = ''
    engine_eval: int | None = None
    engine_best_move: str | None = None
    destination_square: int | None = None


@dataclass(frozen=True)
class CandidateLine:
    """A Stockfish candidate line."""

    move_uci: str
    san: str
    score_cp: int
    score_text: str
    pv_uci: tuple[str, ...]
    pv_san: tuple[str, ...]
    depth: int = 0
    multipv: int = 1


@dataclass
class AnalysisResult:
    """Engine analysis for a position."""

    fen: str
    evaluation_cp: int
    evaluation_text: str
    best_move_uci: str | None
    best_move_san: str
    lines: list[CandidateLine] = field(default_factory=list)
    depth: int = 0
    engine_name: str = 'Stockfish'
    score_type: str = 'cp'
    score_value: int = 0
    request_id: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MoveAnnotation:
    """Review label for a played move."""

    ply: int
    label: str = 'pending'
    loss_cp: int = 0
    evaluation_cp: int = 0
    reason: str = ''
    analysis: AnalysisResult | None = None
    eval_before_cp: int = 0
    best_eval_cp: int = 0
    played_eval_cp: int = 0
    move_accuracy: float = 100.0
    weight: float = 1.0
    analysed: bool = False
    estimated: bool = True
    confidence: str = 'low'
    debug: dict = field(default_factory=dict)
