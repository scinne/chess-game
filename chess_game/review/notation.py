"""Clickable notation row rendering data."""

from __future__ import annotations

import chess

from chess_game.review.move_tree import MoveTree, TreeMoveNode


class NotationRenderer:
    """Converts a move tree into table-friendly notation rows."""

    def rows(self, tree: MoveTree, markers: dict[str, str]) -> list[dict]:
        rows: list[dict] = []
        for node in tree.mainline_nodes():
            rows.append(self._row(node, markers, depth=0))
            for child in tree.children(node.node_id):
                if child.node_id == node.mainline_child_id:
                    continue
                self._append_variation(rows, tree, child, markers, depth=1)
        return rows

    def _append_variation(self, rows: list[dict], tree: MoveTree, node: TreeMoveNode, markers: dict[str, str], depth: int) -> None:
        rows.append(self._row(node, markers, depth=depth))
        for child in tree.children(node.node_id):
            self._append_variation(rows, tree, child, markers, depth=depth + 1)

    def _row(self, node: TreeMoveNode, markers: dict[str, str], depth: int) -> dict:
        side = 'White' if node.color == chess.WHITE else 'Black'
        marker = markers.get(node.annotation_label, '')
        prefix = '  ' * depth
        kind = 'Main' if node.is_mainline and depth == 0 else node.source.title()
        return {
            'node_id': node.node_id,
            'move_no': node.move_number,
            'side': side,
            'move': f'{prefix}{marker} {node.san}'.strip(),
            'kind': kind,
            'eval': node.engine_evaluation,
            'depth': depth,
            'fen': node.after_fen,
        }
