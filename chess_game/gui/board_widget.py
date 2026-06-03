from __future__ import annotations

from dataclasses import dataclass

import chess
from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QInputDialog, QWidget

from chess_game.utils.constants import (
    BOARD_SIZE,
    DARK_SQUARE,
    LAST_MOVE_HIGHLIGHT,
    LEGAL_MOVE_DOT,
    LIGHT_SQUARE,
    PIECE_UNICODE,
    SELECTION_HIGHLIGHT,
)


@dataclass(frozen=True)
class Arrow:
    start: chess.Square
    end: chess.Square


class BoardWidget(QWidget):
    move_played = pyqtSignal(chess.Move)

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(BOARD_SIZE, BOARD_SIZE)
        self.board = chess.Board()
        self.flipped = False
        self.show_legal_moves = True
        self.selected_square: chess.Square | None = None
        self.arrows: set[Arrow] = set()
        self._drag_start: chess.Square | None = None
        self._arrow_start: chess.Square | None = None
        self._last_move: chess.Move | None = None
        self._light_square = LIGHT_SQUARE
        self._dark_square = DARK_SQUARE
        self._piece_theme = "Unicode"
        self._piece_color = Qt.GlobalColor.black

    def set_board(self, board: chess.Board) -> None:
        self.board = board.copy(stack=True)
        self._last_move = self.board.peek() if self.board.move_stack else None
        self.update()

    def flip(self) -> None:
        self.flipped = not self.flipped
        self.update()

    def set_board_theme(self, theme: str) -> None:
        themes = {
            "Classic": (LIGHT_SQUARE, DARK_SQUARE),
            "Blue": ("#DEE3E6", "#8CA2AD"),
            "Green": ("#E6F0D6", "#6C8C45"),
            "Gray": ("#E3E3E3", "#9A9A9A"),
        }
        self._light_square, self._dark_square = themes.get(theme, themes["Classic"])
        self.update()

    def set_piece_theme(self, theme: str) -> None:
        self._piece_theme = theme
        self._piece_color = {
            "Unicode": Qt.GlobalColor.black,
            "Classic": Qt.GlobalColor.darkBlue,
        }.get(theme, Qt.GlobalColor.black)
        self.update()

    def _promotion_piece(self) -> chess.PieceType:
        options = ["Queen", "Rook", "Bishop", "Knight"]
        choice, ok = QInputDialog.getItem(self, "Pawn Promotion", "Promote to:", options, 0, False)
        if not ok:
            return chess.QUEEN
        return {
            "Queen": chess.QUEEN,
            "Rook": chess.ROOK,
            "Bishop": chess.BISHOP,
            "Knight": chess.KNIGHT,
        }[choice]

    def _square_size(self) -> int:
        return self.width() // 8

    def _to_square(self, point: QPoint) -> chess.Square | None:
        size = self._square_size()
        file_ = point.x() // size
        rank_vis = 7 - (point.y() // size)
        if not (0 <= file_ < 8 and 0 <= rank_vis < 8):
            return None
        if self.flipped:
            file_ = 7 - file_
            rank_vis = 7 - rank_vis
        return chess.square(file_, rank_vis)

    def _to_point(self, square: chess.Square) -> tuple[int, int]:
        size = self._square_size()
        file_ = chess.square_file(square)
        rank_ = chess.square_rank(square)
        if self.flipped:
            file_ = 7 - file_
            rank_ = 7 - rank_
        x = file_ * size
        y = (7 - rank_) * size
        return x, y

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        square = self._to_square(event.position().toPoint())
        if square is None:
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._arrow_start = square
            return

        piece = self.board.piece_at(square)
        if self.selected_square is not None:
            selected_piece = self.board.piece_at(self.selected_square)
            if selected_piece is not None:
                move = chess.Move(self.selected_square, square)
                if selected_piece.piece_type == chess.PAWN and chess.square_rank(square) in {0, 7}:
                    move = chess.Move(self.selected_square, square, promotion=self._promotion_piece())
                if move in self.board.legal_moves:
                    self.move_played.emit(move)
                    self.selected_square = None
                    return

        if piece and piece.color == self.board.turn:
            self.selected_square = square
            self._drag_start = square
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        end_square = self._to_square(event.position().toPoint())
        if event.button() == Qt.MouseButton.RightButton and self._arrow_start is not None and end_square is not None:
            arrow = Arrow(self._arrow_start, end_square)
            if arrow in self.arrows:
                self.arrows.remove(arrow)
            else:
                self.arrows.add(arrow)
            self._arrow_start = None
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        size = self._square_size()

        for rank in range(8):
            for file_ in range(8):
                color = QColor(self._light_square if (file_ + rank) % 2 == 0 else self._dark_square)
                painter.fillRect(file_ * size, rank * size, size, size, color)

        if self._last_move:
            for sq in [self._last_move.from_square, self._last_move.to_square]:
                x, y = self._to_point(sq)
                painter.fillRect(x, y, size, size, QColor(LAST_MOVE_HIGHLIGHT))

        if self.selected_square is not None:
            x, y = self._to_point(self.selected_square)
            painter.fillRect(x, y, size, size, QColor(SELECTION_HIGHLIGHT))

        if self.show_legal_moves and self.selected_square is not None:
            painter.setBrush(QColor(LEGAL_MOVE_DOT))
            painter.setPen(Qt.PenStyle.NoPen)
            for move in self.board.legal_moves:
                if move.from_square != self.selected_square:
                    continue
                x, y = self._to_point(move.to_square)
                painter.drawEllipse(x + size // 3, y + size // 3, size // 3, size // 3)

        font = painter.font()
        font.setPointSize(int(size * 0.45))
        painter.setFont(font)

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece is None:
                continue
            x, y = self._to_point(square)
            painter.setPen(self._piece_color)
            painter.drawText(x, y, size, size, Qt.AlignmentFlag.AlignCenter, PIECE_UNICODE[piece.symbol()])

        pen = QPen(QColor("#228BE6"), 6)
        painter.setPen(pen)
        for arrow in self.arrows:
            x1, y1 = self._to_point(arrow.start)
            x2, y2 = self._to_point(arrow.end)
            painter.drawLine(x1 + size // 2, y1 + size // 2, x2 + size // 2, y2 + size // 2)
        super().paintEvent(event)
