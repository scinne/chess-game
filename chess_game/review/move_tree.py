"""Move tree and variation management."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import chess


@dataclass
class TreeMoveNode:
    """A played or analysis move in a PGN-style move tree."""

    node_id: str
    move_uci: str
    san: str
    before_fen: str
    after_fen: str
    parent_node_id: str | None
    child_variation_ids: list[str] = field(default_factory=list)
    mainline_child_id: str | None = None
    is_mainline: bool = True
    source: str = 'mainline'
    move_number: int = 1
    color: chess.Color = chess.WHITE
    annotation_label: str = 'pending'
    comment: str = ''
    engine_evaluation: int | None = None
    engine_best_move: str | None = None
    destination_square: int | None = None


class MoveTree:
    """Stores the original game plus saved analysis variations."""

    def __init__(self) -> None:
        self.root_id = 'root'
        self.nodes: dict[str, TreeMoveNode] = {}
        self.selected_node_id = self.root_id
        self._root_fen = chess.STARTING_FEN

    def build_from_board(self, board: chess.Board) -> None:
        self.nodes.clear()
        replay = chess.Board()
        self._root_fen = replay.fen()
        parent_id: str | None = None
        for move in board.move_stack:
            node = self._create_node(replay, move, parent_id, is_mainline=True, source='mainline')
            self.nodes[node.node_id] = node
            if parent_id is not None:
                self.nodes[parent_id].mainline_child_id = node.node_id
                self.nodes[parent_id].child_variation_ids.append(node.node_id)
            replay.push(move)
            parent_id = node.node_id
        self.selected_node_id = parent_id or self.root_id

    def _create_node(
        self,
        board: chess.Board,
        move: chess.Move,
        parent_id: str | None,
        *,
        is_mainline: bool,
        source: str,
    ) -> TreeMoveNode:
        before_fen = board.fen()
        san = board.san(move)
        temp = board.copy(stack=False)
        temp.push(move)
        return TreeMoveNode(
            node_id=str(uuid4()),
            move_uci=move.uci(),
            san=san,
            before_fen=before_fen,
            after_fen=temp.fen(),
            parent_node_id=parent_id,
            is_mainline=is_mainline,
            source=source,
            move_number=board.fullmove_number,
            color=board.turn,
            destination_square=move.to_square,
        )

    def mainline_nodes(self) -> list[TreeMoveNode]:
        nodes = []
        node_id = self.first_mainline_id()
        while node_id:
            node = self.nodes[node_id]
            nodes.append(node)
            node_id = node.mainline_child_id
        return nodes

    def first_mainline_id(self) -> str | None:
        for node in self.nodes.values():
            if node.parent_node_id is None and node.is_mainline:
                return node.node_id
        return None

    def node_at_mainline_ply(self, ply: int) -> TreeMoveNode | None:
        if ply <= 0:
            return None
        nodes = self.mainline_nodes()
        return nodes[ply - 1] if ply <= len(nodes) else None

    def fen_for_node(self, node_id: str) -> str:
        if node_id == self.root_id:
            return self._root_fen
        return self.nodes[node_id].after_fen

    def board_for_node(self, node_id: str) -> chess.Board:
        return chess.Board(self.fen_for_node(node_id))

    def select(self, node_id: str) -> TreeMoveNode | None:
        if node_id == self.root_id or node_id in self.nodes:
            self.selected_node_id = node_id
        return self.nodes.get(node_id)

    def children(self, node_id: str) -> list[TreeMoveNode]:
        if node_id == self.root_id:
            return [node for node in self.nodes.values() if node.parent_node_id is None]
        return [self.nodes[child_id] for child_id in self.nodes[node_id].child_variation_ids if child_id in self.nodes]

    def add_or_select_move(self, parent_id: str, move: chess.Move, source: str = 'user') -> TreeMoveNode:
        parent_fen = self.fen_for_node(parent_id)
        board = chess.Board(parent_fen)
        for child in self.children(parent_id):
            if child.move_uci == move.uci():
                self.selected_node_id = child.node_id
                return child
        is_mainline = source == 'mainline'
        node = self._create_node(board, move, None if parent_id == self.root_id else parent_id, is_mainline=is_mainline, source=source)
        self.nodes[node.node_id] = node
        if parent_id != self.root_id:
            self.nodes[parent_id].child_variation_ids.append(node.node_id)
            if is_mainline:
                self.nodes[parent_id].mainline_child_id = node.node_id
        self.selected_node_id = node.node_id
        return node

    def add_line(self, parent_id: str, moves_uci: tuple[str, ...] | list[str], source: str = 'engine') -> list[TreeMoveNode]:
        created = []
        current_id = parent_id
        for uci in moves_uci:
            board = chess.Board(self.fen_for_node(current_id))
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                break
            node = self.add_or_select_move(current_id, move, source=source)
            created.append(node)
            current_id = node.node_id
        return created

    def promote_to_mainline(self, node_id: str) -> None:
        node = self.nodes.get(node_id)
        if node is None:
            return
        parent_id = node.parent_node_id
        if parent_id is not None and parent_id in self.nodes:
            self.nodes[parent_id].mainline_child_id = node_id
        while node:
            node.is_mainline = True
            if node.mainline_child_id is None:
                break
            node = self.nodes.get(node.mainline_child_id)


class VariationManager:
    """High-level variation operations for the UI."""

    def __init__(self, tree: MoveTree) -> None:
        self.tree = tree

    def play_from_selected(self, move_uci: str) -> TreeMoveNode | None:
        board = self.tree.board_for_node(self.tree.selected_node_id)
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            return None
        mainline_nodes = self.tree.mainline_nodes()
        latest_mainline_id = mainline_nodes[-1].node_id if mainline_nodes else self.tree.root_id
        source = 'mainline' if self.tree.selected_node_id == latest_mainline_id else 'user'
        return self.tree.add_or_select_move(self.tree.selected_node_id, move, source=source)

    def save_engine_line(self, parent_id: str, moves_uci: tuple[str, ...] | list[str]) -> list[TreeMoveNode]:
        return self.tree.add_line(parent_id, moves_uci, source='engine')
