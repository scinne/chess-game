from __future__ import annotations

import chess

from chess_game.utils.constants import FILES


def square_name(square: chess.Square) -> str:
    return chess.square_name(square)


def parse_uci(move_text: str) -> chess.Move:
    return chess.Move.from_uci(move_text)


def file_rank_to_square(file_idx: int, rank_idx: int) -> chess.Square:
    return chess.parse_square(f"{FILES[file_idx]}{rank_idx + 1}")
