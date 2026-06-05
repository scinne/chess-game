"""Small expandable opening repertoire manager."""

from __future__ import annotations

import chess


class OpeningRepertoire:
    """Detects simple opening lines and recommends book moves."""

    def __init__(self) -> None:
        self._entries = [
            {
                'name': 'Italian Game',
                'moves': ('e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4'),
                'recommendations': ('f1c4', 'f8c5', 'c2c3'),
            },
            {
                'name': 'Ruy Lopez',
                'moves': ('e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5'),
                'recommendations': ('f1b5', 'a7a6', 'e1g1'),
            },
            {
                'name': 'Queen\'s Gambit',
                'moves': ('d2d4', 'd7d5', 'c2c4'),
                'recommendations': ('c2c4', 'e2e3', 'g1f3'),
            },
            {
                'name': 'Sicilian Defense',
                'moves': ('e2e4', 'c7c5'),
                'recommendations': ('g1f3', 'd2d4', 'b1c3'),
            },
            {
                'name': 'French Defense',
                'moves': ('e2e4', 'e7e6'),
                'recommendations': ('d2d4', 'b1c3', 'e4e5'),
            },
        ]

    def opening_for_moves(self, moves_uci: list[str]) -> dict:
        best = None
        for entry in self._entries:
            entry_moves = entry['moves']
            if tuple(moves_uci[: len(entry_moves)]) == entry_moves:
                best = entry
            elif tuple(entry_moves[: len(moves_uci)]) == tuple(moves_uci):
                best = entry
        if best is None:
            return {'name': 'Unknown Opening', 'in_book': False, 'book_moves': []}

        in_book = tuple(moves_uci) == tuple(best['moves'][: len(moves_uci)])
        board = chess.Board()
        for uci in moves_uci:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                break
            board.push(move)
        book_moves = []
        for uci in best['recommendations']:
            move = chess.Move.from_uci(uci)
            if move in board.legal_moves:
                book_moves.append({'uci': uci, 'san': board.san(move)})
        return {'name': best['name'], 'in_book': in_book, 'book_moves': book_moves}

