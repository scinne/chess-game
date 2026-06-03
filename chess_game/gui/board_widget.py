"""Chessboard rendering and interaction widget."""

from __future__ import annotations

from dataclasses import dataclass

import chess
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from chess_game.board import ChessBoard
from chess_game.utils.constants import (
    BOARD_SIZE,
    DARK_SQUARE_COLOR,
    LIGHT_SQUARE_COLOR,
    SQUARE_SIZE,
)
from chess_game.utils.helpers import load_piece_image


@dataclass(frozen=True)
class Arrow:
    """Arrow descriptor on board."""

    start: int
    end: int
    color: str


class BoardWidget(QWidget):
    """Interactive chessboard widget with dragging and arrows."""

    move_dropped = pyqtSignal(str)
    right_arrow_changed = pyqtSignal()

    def __init__(self, board: ChessBoard, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.board = board
        self.setFixedSize(BOARD_SIZE * SQUARE_SIZE, BOARD_SIZE * SQUARE_SIZE)
        self.selected_square: int | None = None
        self.dragging_square: int | None = None
        self.dragging_piece: chess.Piece | None = None
        self.drag_pos: QPointF | None = None
        self.legal_targets: list[int] = []
        self.show_legal_moves = True
        self.show_from_white = True
        self.last_move: chess.Move | None = None
        self.premove_move: chess.Move | None = None
        self.arrows: set[Arrow] = set()
        self.light_square_color = LIGHT_SQUARE_COLOR
        self.dark_square_color = DARK_SQUARE_COLOR

    def set_board(self, board: ChessBoard) -> None:
        self.board = board
        self.update()

    def set_flipped(self, flipped: bool) -> None:
        self.show_from_white = not flipped
        self.update()

    def set_show_legal_moves(self, enabled: bool) -> None:
        self.show_legal_moves = enabled
        self.update()

    def set_theme(self, theme: str) -> None:
        if theme.lower() == 'dark':
            self.light_square_color = QColor(130, 130, 130)
            self.dark_square_color = QColor(75, 75, 75)
        else:
            self.light_square_color = LIGHT_SQUARE_COLOR
            self.dark_square_color = DARK_SQUARE_COLOR
        self.update()

    def set_last_move(self, move: chess.Move | None) -> None:
        self.last_move = move
        self.update()

    def set_premove(self, move: chess.Move | None) -> None:
        self.premove_move = move
        self.update()

    def clear_arrows(self) -> None:
        self.arrows.clear()
        self.update()

    def _display_coords(self, file_: int, rank: int) -> tuple[int, int]:
        x = file_ if self.show_from_white else 7 - file_
        y = 7 - rank if self.show_from_white else rank
        return x, y

    def _pixel_to_square(self, pos: QPointF) -> int | None:
        x = int(pos.x()) // SQUARE_SIZE
        y = int(pos.y()) // SQUARE_SIZE
        if not (0 <= x < 8 and 0 <= y < 8):
            return None
        file_ = x if self.show_from_white else 7 - x
        rank = 7 - y if self.show_from_white else y
        return chess.square(file_, rank)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for rank in range(8):
            for file_ in range(8):
                x, y = self._display_coords(file_, rank)
                rect = QRectF(x * SQUARE_SIZE, y * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
                color = self.light_square_color if (file_ + rank) % 2 == 0 else self.dark_square_color
                painter.fillRect(rect, color)

        if self.last_move:
            self._highlight_square(painter, self.last_move.from_square, QColor(246, 246, 105, 110))
            self._highlight_square(painter, self.last_move.to_square, QColor(246, 246, 105, 110))

        if self.selected_square is not None:
            self._highlight_square(painter, self.selected_square, QColor(40, 120, 220, 90))

        if self.premove_move is not None:
            self._highlight_square(painter, self.premove_move.from_square, QColor(100, 200, 255, 80))
            self._highlight_square(painter, self.premove_move.to_square, QColor(100, 200, 255, 80))

        if self.show_legal_moves and self.selected_square is not None:
            painter.setBrush(QColor(20, 20, 20, 90))
            painter.setPen(Qt.PenStyle.NoPen)
            for square in self.legal_targets:
                cx, cy = self._square_center(square)
                painter.drawEllipse(QPointF(cx, cy), 7, 7)

        self._draw_arrows(painter)

        for square, piece in self.board.piece_map().items():
            if square == self.dragging_square and self.dragging_piece is not None:
                continue
            self._draw_piece(painter, square, piece)

        if self.dragging_piece and self.drag_pos is not None:
            pix = load_piece_image(self.dragging_piece.symbol(), 'Default', SQUARE_SIZE)
            painter.drawPixmap(
                int(self.drag_pos.x() - SQUARE_SIZE / 2),
                int(self.drag_pos.y() - SQUARE_SIZE / 2),
                pix,
            )

    def _highlight_square(self, painter: QPainter, square: int, color: QColor) -> None:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        x, y = self._display_coords(file_, rank)
        painter.fillRect(QRectF(x * SQUARE_SIZE, y * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), color)

    def _square_center(self, square: int) -> tuple[float, float]:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        x, y = self._display_coords(file_, rank)
        return (x + 0.5) * SQUARE_SIZE, (y + 0.5) * SQUARE_SIZE

    def _draw_piece(self, painter: QPainter, square: int, piece: chess.Piece) -> None:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        x, y = self._display_coords(file_, rank)
        pixmap = load_piece_image(piece.symbol(), 'Default', SQUARE_SIZE)
        painter.drawPixmap(x * SQUARE_SIZE, y * SQUARE_SIZE, pixmap)

    def _draw_arrows(self, painter: QPainter) -> None:
        color_map = {
            'normal': QColor(255, 215, 0, 180),
            'shift': QColor(80, 210, 120, 180),
            'ctrl': QColor(230, 70, 70, 180),
        }
        for arrow in self.arrows:
            sx, sy = self._square_center(arrow.start)
            ex, ey = self._square_center(arrow.end)
            pen = QPen(color_map[arrow.color], 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(int(sx), int(sy), int(ex), int(ey))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        square = self._pixel_to_square(event.position())
        if square is None:
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.selected_square = square
            return

        piece = self.board.piece_at(square)
        if piece is None:
            self.selected_square = None
            self.legal_targets = []
            self.update()
            return

        if piece.color != self.board.turn:
            return

        self.selected_square = square
        self.dragging_square = square
        self.dragging_piece = piece
        self.drag_pos = event.position()
        self.legal_targets = [m.to_square for m in self.board.legal_moves if m.from_square == square]
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.dragging_piece is not None:
            self.drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        square = self._pixel_to_square(event.position())
        if event.button() == Qt.MouseButton.RightButton:
            if self.selected_square is not None and square is not None:
                if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
                    color = 'shift'
                elif QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                    color = 'ctrl'
                else:
                    color = 'normal'
                arrow = Arrow(self.selected_square, square, color)
                if arrow in self.arrows:
                    self.arrows.remove(arrow)
                else:
                    self.arrows.add(arrow)
                self.right_arrow_changed.emit()
            self.selected_square = None
            self.update()
            return

        from_square = self.dragging_square
        self.dragging_square = None
        self.dragging_piece = None
        self.drag_pos = None
        if from_square is None or square is None:
            self.update()
            return

        move = chess.Move(from_square, square)
        source_piece = self.board.piece_at(from_square)
        if source_piece and move not in self.board.legal_moves and source_piece.piece_type == chess.PAWN:
            rank = chess.square_rank(square)
            if rank in (0, 7):
                move = chess.Move(from_square, square, promotion=chess.QUEEN)

        self.legal_targets = []
        if move in self.board.legal_moves:
            self.move_dropped.emit(move.uci())
        self.update()
