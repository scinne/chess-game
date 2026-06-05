"""Chessboard rendering and interaction widget."""

from __future__ import annotations

import math
from dataclasses import dataclass

import chess
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QApplication, QSizePolicy, QWidget

from chess_game.board import ChessBoard
from chess_game.utils.constants import (
    BOARD_SIZE,
    DARK_SQUARE_COLOR,
    LIGHT_SQUARE_COLOR,
    SQUARE_SIZE,
)
from chess_game.utils.helpers import load_piece_image
from chess_game.review.overlays import MOVE_QUALITY_BADGES, MOVE_QUALITY_COLORS, BoardOverlayState


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
        self.setMinimumSize(560, 560)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.selected_square: int | None = None
        self.dragging_square: int | None = None
        self.dragging_piece: chess.Piece | None = None
        self.drag_pos: QPointF | None = None
        self.legal_targets: list[int] = []
        self.show_legal_moves = True
        self.show_from_white = True
        self.premove_color: chess.Color | None = None
        self.last_move: chess.Move | None = None
        self.premove_move: chess.Move | None = None
        self.hint_move: chess.Move | None = None
        self.hint_mode: str | None = None
        self.review_overlay = BoardOverlayState()
        self.show_board_overlays = True
        self.show_move_quality_icons = True
        self.show_coordinates = True
        self.arrows: set[Arrow] = set()
        self.highlighted_squares: set[int] = set()
        self.light_square_color = LIGHT_SQUARE_COLOR
        self.dark_square_color = DARK_SQUARE_COLOR

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(BOARD_SIZE * SQUARE_SIZE, BOARD_SIZE * SQUARE_SIZE)

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return width

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def _board_rect(self) -> QRectF:
        size = min(self.width(), self.height())
        x = (self.width() - size) / 2
        y = (self.height() - size) / 2
        return QRectF(x, y, size, size)

    def _square_size(self) -> float:
        return self._board_rect().width() / BOARD_SIZE

    def set_board(self, board: ChessBoard) -> None:
        self.board = board
        self.update()

    def set_flipped(self, flipped: bool) -> None:
        self.show_from_white = not flipped
        self.update()

    def set_show_legal_moves(self, enabled: bool) -> None:
        self.show_legal_moves = enabled
        self.update()

    def set_show_coordinates(self, enabled: bool) -> None:
        self.show_coordinates = enabled
        self.update()

    def set_show_board_overlays(self, enabled: bool) -> None:
        self.show_board_overlays = enabled
        self.update()

    def set_show_move_quality_icons(self, enabled: bool) -> None:
        self.show_move_quality_icons = enabled
        self.update()

    def set_review_overlay(self, overlay: BoardOverlayState | None) -> None:
        self.review_overlay = overlay or BoardOverlayState()
        self.update()

    def set_theme(self, theme: str) -> None:
        if theme.lower() == 'dark':
            self.light_square_color = QColor(178, 190, 181)
            self.dark_square_color = QColor(70, 88, 94)
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

    def set_premove_color(self, color: chess.Color | None) -> None:
        self.premove_color = color
        if color is None and self.dragging_piece is not None and self.dragging_piece.color != self.board.turn:
            self.dragging_square = None
            self.dragging_piece = None
            self.drag_pos = None
            self.selected_square = None
            self.legal_targets = []
        self.update()

    def clear_arrows(self) -> None:
        self.arrows.clear()
        self.update()

    def clear_marks(self) -> None:
        self.arrows.clear()
        self.highlighted_squares.clear()
        self.hint_move = None
        self.hint_mode = None
        self.review_overlay = BoardOverlayState()
        self.update()

    def set_hint_move(self, move: chess.Move | None, mode: str | None) -> None:
        self.hint_move = move
        self.hint_mode = mode
        self.update()

    def _display_coords(self, file_: int, rank: int) -> tuple[int, int]:
        x = file_ if self.show_from_white else 7 - file_
        y = 7 - rank if self.show_from_white else rank
        return x, y

    def _pixel_to_square(self, pos: QPointF) -> int | None:
        board_rect = self._board_rect()
        if not board_rect.contains(pos):
            return None
        square_size = self._square_size()
        x = int((pos.x() - board_rect.x()) // square_size)
        y = int((pos.y() - board_rect.y()) // square_size)
        if not (0 <= x < 8 and 0 <= y < 8):
            return None
        file_ = x if self.show_from_white else 7 - x
        rank = 7 - y if self.show_from_white else y
        return chess.square(file_, rank)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        board_rect = self._board_rect()
        square_size = self._square_size()

        for rank in range(8):
            for file_ in range(8):
                x, y = self._display_coords(file_, rank)
                rect = QRectF(
                    board_rect.x() + x * square_size,
                    board_rect.y() + y * square_size,
                    square_size,
                    square_size,
                )
                color = self.dark_square_color if (file_ + rank) % 2 == 0 else self.light_square_color
                painter.fillRect(rect, color)
                if self.show_coordinates:
                    self._draw_notation(painter, rect, file_, rank, color == self.dark_square_color)

        if self.last_move:
            self._highlight_square(painter, self.last_move.from_square, QColor(246, 246, 105, 110))
            self._highlight_square(painter, self.last_move.to_square, QColor(246, 246, 105, 110))

        for square in self.highlighted_squares:
            self._highlight_square(painter, square, QColor(255, 220, 74, 120))

        if self.hint_move is not None and self.hint_mode == 'square':
            self._highlight_square(painter, self.hint_move.from_square, QColor(126, 196, 86, 150))

        if self.selected_square is not None:
            self._highlight_square(painter, self.selected_square, QColor(40, 120, 220, 90))

        if self.premove_move is not None:
            self._highlight_square(painter, self.premove_move.from_square, QColor(100, 200, 255, 80))
            self._highlight_square(painter, self.premove_move.to_square, QColor(100, 200, 255, 80))

        if self.show_legal_moves and self.selected_square is not None:
            painter.setBrush(QColor(20, 20, 20, 90))
            painter.setPen(Qt.PenStyle.NoPen)
            radius = max(5.0, square_size * 0.1)
            for square in self.legal_targets:
                cx, cy = self._square_center(square)
                painter.drawEllipse(QPointF(cx, cy), radius, radius)

        self._draw_arrows(painter)
        self._draw_hint_arrow(painter)
        self._draw_review_best_move(painter)

        for square, piece in self.board.piece_map().items():
            if square == self.dragging_square and self.dragging_piece is not None:
                continue
            self._draw_piece(painter, square, piece)

        if self.dragging_piece and self.drag_pos is not None:
            piece_size = int(square_size * 0.92)
            pix = load_piece_image(self.dragging_piece.symbol(), 'Default', piece_size)
            painter.drawPixmap(
                int(self.drag_pos.x() - piece_size / 2),
                int(self.drag_pos.y() - piece_size / 2),
                pix,
            )

        self._draw_review_badge(painter)

    def _highlight_square(self, painter: QPainter, square: int, color: QColor) -> None:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        x, y = self._display_coords(file_, rank)
        board_rect = self._board_rect()
        square_size = self._square_size()
        painter.fillRect(
            QRectF(
                board_rect.x() + x * square_size,
                board_rect.y() + y * square_size,
                square_size,
                square_size,
            ),
            color,
        )

    def _square_center(self, square: int) -> tuple[float, float]:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        x, y = self._display_coords(file_, rank)
        board_rect = self._board_rect()
        square_size = self._square_size()
        return board_rect.x() + (x + 0.5) * square_size, board_rect.y() + (y + 0.5) * square_size

    def _draw_piece(self, painter: QPainter, square: int, piece: chess.Piece) -> None:
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        x, y = self._display_coords(file_, rank)
        board_rect = self._board_rect()
        square_size = self._square_size()
        piece_size = int(square_size * 0.92)
        offset = (square_size - piece_size) / 2
        pixmap = load_piece_image(piece.symbol(), 'Default', piece_size)
        painter.drawPixmap(
            int(board_rect.x() + x * square_size + offset),
            int(board_rect.y() + y * square_size + offset),
            pixmap,
        )

    def _draw_notation(self, painter: QPainter, rect: QRectF, file_: int, rank: int, is_dark: bool) -> None:
        x, y = self._display_coords(file_, rank)
        text_color = QColor(246, 238, 225, 210) if is_dark else QColor(73, 89, 72, 210)
        font = QFont('Segoe UI')
        font.setPixelSize(max(10, int(rect.width() * 0.16)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(text_color)

        margin = max(4, int(rect.width() * 0.06))
        if x == 0:
            painter.drawText(rect.adjusted(margin, margin, -margin, -margin), Qt.AlignmentFlag.AlignTop, str(rank + 1))
        if y == 7:
            painter.drawText(
                rect.adjusted(margin, margin, -margin, -margin),
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                chess.FILE_NAMES[file_],
            )

    def _draw_arrows(self, painter: QPainter) -> None:
        color_map = {
            'normal': QColor(255, 215, 0, 180),
            'shift': QColor(80, 210, 120, 180),
            'ctrl': QColor(230, 70, 70, 180),
        }
        for arrow in self.arrows:
            sx, sy = self._square_center(arrow.start)
            ex, ey = self._square_center(arrow.end)
            dx = ex - sx
            dy = ey - sy
            length = math.hypot(dx, dy)
            if length < 1:
                continue

            unit_x = dx / length
            unit_y = dy / length
            square_size = self._square_size()
            line_width = max(5, int(square_size * 0.105))
            head_length = square_size * 0.32
            head_width = square_size * 0.26
            shaft_end_x = ex - unit_x * head_length * 0.62
            shaft_end_y = ey - unit_y * head_length * 0.62
            pen = QPen(
                color_map[arrow.color],
                line_width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
            painter.setPen(pen)
            painter.drawLine(QPointF(sx, sy), QPointF(shaft_end_x, shaft_end_y))

            perp_x = -unit_y
            perp_y = unit_x
            head = QPolygonF(
                [
                    QPointF(ex, ey),
                    QPointF(ex - unit_x * head_length + perp_x * head_width / 2, ey - unit_y * head_length + perp_y * head_width / 2),
                    QPointF(ex - unit_x * head_length - perp_x * head_width / 2, ey - unit_y * head_length - perp_y * head_width / 2),
                ]
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color_map[arrow.color])
            painter.drawPolygon(head)

    def _draw_hint_arrow(self, painter: QPainter) -> None:
        if self.hint_move is None or self.hint_mode != 'arrow':
            return
        self._draw_arrow_between(
            painter,
            self.hint_move.from_square,
            self.hint_move.to_square,
            QColor(126, 196, 86, 205),
        )

    def _draw_review_best_move(self, painter: QPainter) -> None:
        if not self.show_board_overlays or self.review_overlay.best_move is None:
            return
        self._draw_arrow_between(
            painter,
            self.review_overlay.best_move.from_square,
            self.review_overlay.best_move.to_square,
            QColor(80, 150, 210, 175),
        )

    def _draw_review_badge(self, painter: QPainter) -> None:
        if not self.show_board_overlays or not self.show_move_quality_icons:
            return
        square = self.review_overlay.badge_square
        label = self.review_overlay.badge_label
        text = MOVE_QUALITY_BADGES.get(label, '')
        if square is None or not text:
            return
        file_ = chess.square_file(square)
        rank = chess.square_rank(square)
        x, y = self._display_coords(file_, rank)
        board_rect = self._board_rect()
        square_size = self._square_size()
        badge_size = max(22.0, square_size * 0.28)
        rect = QRectF(
            board_rect.x() + (x + 1) * square_size - badge_size - square_size * 0.05,
            board_rect.y() + y * square_size + square_size * 0.05,
            badge_size,
            badge_size,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(MOVE_QUALITY_COLORS.get(label, '#7a886f')))
        painter.drawEllipse(rect)
        font = QFont('Segoe UI')
        font.setBold(True)
        font.setPixelSize(max(8, int(badge_size * (0.33 if len(text) > 1 else 0.55))))
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_arrow_between(self, painter: QPainter, start: int, end: int, color: QColor) -> None:
        sx, sy = self._square_center(start)
        ex, ey = self._square_center(end)
        dx = ex - sx
        dy = ey - sy
        length = math.hypot(dx, dy)
        if length < 1:
            return

        unit_x = dx / length
        unit_y = dy / length
        square_size = self._square_size()
        line_width = max(5, int(square_size * 0.105))
        head_length = square_size * 0.32
        head_width = square_size * 0.26
        shaft_end_x = ex - unit_x * head_length * 0.62
        shaft_end_y = ey - unit_y * head_length * 0.62

        painter.setPen(QPen(color, line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(sx, sy), QPointF(shaft_end_x, shaft_end_y))

        perp_x = -unit_y
        perp_y = unit_x
        head = QPolygonF(
            [
                QPointF(ex, ey),
                QPointF(ex - unit_x * head_length + perp_x * head_width / 2, ey - unit_y * head_length + perp_y * head_width / 2),
                QPointF(ex - unit_x * head_length - perp_x * head_width / 2, ey - unit_y * head_length - perp_y * head_width / 2),
            ]
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(head)

    def _is_premove_piece(self, piece: chess.Piece) -> bool:
        return self.premove_color is not None and piece.color == self.premove_color and piece.color != self.board.turn

    def _targets_for_piece(self, square: int, piece: chess.Piece) -> list[int]:
        if self._is_premove_piece(piece):
            temp_board = self.board.copy(stack=False)
            temp_board.turn = piece.color
            return [move.to_square for move in temp_board.pseudo_legal_moves if move.from_square == square]
        return [move.to_square for move in self.board.legal_moves if move.from_square == square]

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

        if piece.color != self.board.turn and not self._is_premove_piece(piece):
            return

        self.selected_square = square
        self.dragging_square = square
        self.dragging_piece = piece
        self.drag_pos = event.position()
        self.legal_targets = self._targets_for_piece(square, piece)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.dragging_piece is not None:
            self.drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        square = self._pixel_to_square(event.position())
        if event.button() == Qt.MouseButton.RightButton:
            if self.selected_square is not None and square is not None:
                if self.selected_square == square:
                    if square in self.highlighted_squares:
                        self.highlighted_squares.remove(square)
                    else:
                        self.highlighted_squares.add(square)
                    self.selected_square = None
                    self.update()
                    return
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
        is_premove = source_piece is not None and self._is_premove_piece(source_piece)
        if source_piece and source_piece.piece_type == chess.PAWN:
            rank = chess.square_rank(square)
            if rank in (0, 7):
                move = chess.Move(from_square, square, promotion=chess.QUEEN)

        self.legal_targets = []
        if is_premove:
            temp_board = self.board.copy(stack=False)
            temp_board.turn = source_piece.color
            if move in temp_board.pseudo_legal_moves:
                self.move_dropped.emit(move.uci())
        elif move in self.board.legal_moves:
            self.move_dropped.emit(move.uci())
        self.update()
