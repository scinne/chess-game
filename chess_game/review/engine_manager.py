"""Asynchronous persistent Stockfish analysis manager."""

from __future__ import annotations

import logging
import time

import chess
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from chess_game.engine import StockfishEngine
from chess_game.review.models import AnalysisResult, CandidateLine

LOGGER = logging.getLogger(__name__)


class AnalysisWorker(QObject):
    """Owns one Stockfish process and runs analysis off the UI thread."""

    finished = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)

    def __init__(self, stockfish_path: str) -> None:
        super().__init__()
        self.stockfish_path = stockfish_path
        self.engine: StockfishEngine | None = None

    @pyqtSlot()
    def start_engine(self) -> None:
        start = time.perf_counter()
        try:
            self.engine = StockfishEngine(self.stockfish_path)
            LOGGER.info('Stockfish startup completed in %.1f ms', (time.perf_counter() - start) * 1000)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception('Stockfish startup failed after %.1f ms', (time.perf_counter() - start) * 1000)
            self.failed.emit(-1, str(exc))

    @pyqtSlot(int, str, int, float, int)
    def analyze(self, request_id: int, fen: str, lines: int, time_seconds: float, threads: int) -> None:
        request_start = time.perf_counter()
        try:
            board = chess.Board(fen)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(request_id, f'Invalid FEN: {exc}')
            return

        if self.engine is None:
            self.start_engine()
            if self.engine is None:
                self.failed.emit(request_id, 'Stockfish unavailable')
                return

        try:
            raw_lines = self.engine.get_top_moves(
                board,
                n=lines,
                difficulty=2200,
                analysis_time=time_seconds,
                threads=threads,
            )
            candidates = [self._candidate(board, item) for item in raw_lines if item.get('move')]
            evaluation_cp = candidates[0].score_cp if candidates else 0
            first_raw = raw_lines[0] if raw_lines else {}
            score_type = 'mate' if first_raw.get('type') == 'mate' else 'cp'
            score_value = int(first_raw.get('score') or evaluation_cp)
            result = AnalysisResult(
                fen=fen,
                evaluation_cp=evaluation_cp,
                evaluation_text=self._item_score_text(first_raw) if first_raw else self._score_text(evaluation_cp),
                best_move_uci=candidates[0].move_uci if candidates else None,
                best_move_san=candidates[0].san if candidates else '-',
                lines=candidates,
                depth=max((candidate.depth for candidate in candidates), default=0),
                engine_name='Stockfish',
                score_type=score_type,
                score_value=score_value,
                request_id=request_id,
            )
            LOGGER.info(
                'Analysis request %s completed in %.1f ms for FEN %s',
                request_id,
                (time.perf_counter() - request_start) * 1000,
                fen,
            )
            self.finished.emit(request_id, result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(request_id, str(exc))

    @pyqtSlot()
    def shutdown(self) -> None:
        if self.engine:
            self.engine.shutdown()
            self.engine = None

    def _candidate(self, board: chess.Board, item: dict) -> CandidateLine:
        move = chess.Move.from_uci(item['move'])
        pv_uci = tuple(item.get('line', []))
        return CandidateLine(
            move_uci=item['move'],
            san=board.san(move) if move in board.legal_moves else item['move'],
            score_cp=self._line_score_cp(item),
            score_text=self._item_score_text(item),
            pv_uci=pv_uci,
            pv_san=tuple(self._pv_san(board, pv_uci)),
            depth=int(item.get('depth') or 0),
            multipv=int(item.get('multipv') or 1),
        )

    def _pv_san(self, board: chess.Board, line: tuple[str, ...]) -> list[str]:
        temp = board.copy(stack=False)
        san = []
        for uci in line[:8]:
            move = chess.Move.from_uci(uci)
            if move not in temp.legal_moves:
                break
            san.append(temp.san(move))
            temp.push(move)
        return san

    def _line_score_cp(self, item: dict) -> int:
        if item.get('type') == 'mate':
            mate = int(item.get('score') or 0)
            return 100000 if mate > 0 else -100000
        return int(item.get('score') or 0)

    def _score_text(self, cp: int) -> str:
        if abs(cp) >= 100000:
            return 'M'
        return f'{cp / 100:+.2f}'

    def _item_score_text(self, item: dict) -> str:
        if item.get('type') == 'mate':
            mate = int(item.get('score') or 0)
            sign = '+' if mate > 0 else '-'
            return f'{sign}M{abs(mate)}'
        value = max(-990, min(990, int(item.get('score') or 0)))
        return f'{value / 100:+.1f}'


class StockfishAnalysisManager(QObject):
    """Starts persistent async analysis requests and ignores superseded results."""

    analysis_ready = pyqtSignal(object)
    analysis_failed = pyqtSignal(str)
    _request_analysis = pyqtSignal(int, str, int, float, int)
    _shutdown_worker = pyqtSignal()

    def __init__(self, stockfish_path: str | None) -> None:
        super().__init__()
        self.stockfish_path = stockfish_path
        self._request_id = 0
        self._worker: AnalysisWorker | None = None
        self._thread: QThread | None = None
        self._current_fen: str | None = None
        self._cache: dict[tuple[str, int], AnalysisResult] = {}
        self._last_emit = 0.0
        if self.stockfish_path:
            self._start_worker()

    def analyze(self, fen: str, lines: int = 3, time_seconds: float = 0.5, threads: int = 2) -> None:
        if not self.stockfish_path:
            self.analysis_failed.emit('Stockfish unavailable')
            return
        try:
            fen = chess.Board(fen).fen()
        except Exception as exc:  # noqa: BLE001
            self.analysis_failed.emit(f'Invalid FEN: {exc}')
            return
        self._current_fen = fen
        self._request_id += 1
        cache_key = (fen, max(1, lines))
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.request_id = self._request_id
            self._emit_ready(cached)
            return
        if self._thread is None or self._worker is None:
            self._start_worker()
        self._request_analysis.emit(self._request_id, fen, max(1, lines), max(0.05, time_seconds), max(1, threads))

    def stop(self, wait_ms: int = 25) -> None:
        self._request_id += 1
        self._current_fen = None

    def shutdown(self) -> None:
        self.stop()
        if self._worker:
            self._shutdown_worker.emit()
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
        self._thread = None
        self._worker = None

    def _start_worker(self) -> None:
        if not self.stockfish_path:
            return
        self._thread = QThread(self)
        self._worker = AnalysisWorker(self.stockfish_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start_engine)
        self._request_analysis.connect(self._worker.analyze)
        self._shutdown_worker.connect(self._worker.shutdown)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._thread.finished.connect(self._worker.shutdown)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.start()

    def _on_finished(self, request_id: int, result: object) -> None:
        if not isinstance(result, AnalysisResult):
            return
        self._cache[(result.fen, len(result.lines))] = result
        if request_id == self._request_id and result.fen == self._current_fen:
            self._emit_ready(result)

    def clear_cache(self) -> None:
        self._cache.clear()

    def _on_failed(self, request_id: int, message: str) -> None:
        if request_id in {-1, self._request_id}:
            self.analysis_failed.emit(message)

    def _emit_ready(self, result: AnalysisResult) -> None:
        now = time.perf_counter()
        if now - self._last_emit < 0.05:
            return
        self._last_emit = now
        self.analysis_ready.emit(result)
