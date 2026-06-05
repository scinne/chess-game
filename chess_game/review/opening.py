"""Small expandable opening repertoire manager."""

from __future__ import annotations

import chess


class OpeningRepertoire:
    """Detects simple opening lines and recommends book moves."""

    def __init__(self) -> None:
        self._entries = [
            {
                'name': 'King\'s Pawn Opening',
                'moves': ('e2e4',),
                'recommendations': ('e7e5', 'c7c5', 'e7e6'),
            },
            {
                'name': 'Open Game',
                'moves': ('e2e4', 'e7e5'),
                'recommendations': ('g1f3', 'f1c4', 'f1b5'),
            },
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
                'name': 'Queen\'s Pawn Opening',
                'moves': ('d2d4',),
                'recommendations': ('d7d5', 'g8f6', 'e7e6'),
            },
            {
                'name': 'English Opening',
                'moves': ('c2c4',),
                'recommendations': ('g1f3', 'b1c3', 'g2g3'),
            },
            {
                'name': 'Reti Opening',
                'moves': ('g1f3',),
                'recommendations': ('c2c4', 'g2g3', 'd2d4'),
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
        if not moves_uci:
            return {'name': 'Starting Position', 'family': 'Starting Position', 'in_book': True, 'book_moves': []}
        best = None
        best_length = 0
        exact_prefix = False
        for entry in self._entries:
            entry_moves = entry['moves']
            shared = 0
            for played, book in zip(moves_uci, entry_moves):
                if played != book:
                    break
                shared += 1
            entry_complete = shared == len(entry_moves)
            played_prefix = shared == len(moves_uci)
            if (entry_complete or played_prefix) and shared > best_length:
                best = entry
                best_length = shared
                exact_prefix = played_prefix
        if best is None:
            return {'name': 'Unknown Opening', 'in_book': False, 'book_moves': []}

        in_book = exact_prefix and tuple(moves_uci) == tuple(best['moves'][: len(moves_uci)])
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
        return {'name': best['name'], 'family': best['name'], 'in_book': in_book, 'book_moves': book_moves}
