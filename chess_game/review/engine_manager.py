"""Asynchronous Stockfish analysis manager."""

from __future__ import annotations

import chess
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from chess_game.engine import StockfishEngine
from chess_game.review.models import AnalysisResult, CandidateLine


class AnalysisWorker(QObject):
    """Runs one Stockfish analysis request off the UI thread."""

    finished = pyqtSignal(int, object)
    failed = pyqtSignal(int, str)

    def __init__(self, request_id: int, stockfish_path: str, fen: str, lines: int, time_seconds: float, threads: int) -> None:
        super().__init__()
        self.request_id = request_id
        self.stockfish_path = stockfish_path
        self.fen = fen
        self.lines = lines
        self.time_seconds = time_seconds
        self.threads = threads

    def run(self) -> None:
        engine: StockfishEngine | None = None
        try:
            board = chess.Board(self.fen)
            engine = StockfishEngine(self.stockfish_path)
            raw_lines = engine.get_top_moves(board, n=self.lines, difficulty=2200, analysis_time=self.time_seconds, threads=self.threads)
            candidates = [self._candidate(board, item) for item in raw_lines if item.get('move')]
            evaluation_cp = candidates[0].score_cp if candidates else 0
            result = AnalysisResult(
                fen=self.fen,
                evaluation_cp=evaluation_cp,
                evaluation_text=self._score_text(evaluation_cp),
                best_move_uci=candidates[0].move_uci if candidates else None,
                best_move_san=candidates[0].san if candidates else '-',
                lines=candidates,
                depth=max((candidate.depth for candidate in candidates), default=0),
                engine_name='Stockfish',
                score_type='mate' if abs(evaluation_cp) >= 100000 else 'cp',
                score_value=evaluation_cp,
                request_id=self.request_id,
            )
            self.finished.emit(self.request_id, result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(self.request_id, str(exc))
        finally:
            if engine:
                engine.shutdown()

    def _candidate(self, board: chess.Board, item: dict) -> CandidateLine:
        move = chess.Move.from_uci(item['move'])
        pv_uci = tuple(item.get('line', []))
        return CandidateLine(
            move_uci=item['move'],
            san=board.san(move) if move in board.legal_moves else item['move'],
            score_cp=self._line_score_cp(item),
            score_text=self._score_text(self._line_score_cp(item)),
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


class StockfishAnalysisManager(QObject):
    """Starts analysis requests and ignores superseded results."""

    analysis_ready = pyqtSignal(object)
    analysis_failed = pyqtSignal(str)

    def __init__(self, stockfish_path: str | None) -> None:
        super().__init__()
        self.stockfish_path = stockfish_path
        self._request_id = 0
        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None
        self._threads: list[QThread] = []

    def analyze(self, fen: str, lines: int = 3, time_seconds: float = 0.5, threads: int = 2) -> None:
        self.stop()
        if not self.stockfish_path:
            self.analysis_failed.emit('Stockfish unavailable')
            return
        self._request_id += 1
        request_id = self._request_id
        self._thread = QThread(self)
        self._threads.append(self._thread)
        self._worker = AnalysisWorker(request_id, self.stockfish_path, fen, lines, time_seconds, threads)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        thread = self._thread
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(lambda thread=thread: self._on_thread_finished(thread))
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def stop(self, wait_ms: int = 25) -> None:
        self._request_id += 1
        for thread in list(self._threads):
            if thread.isRunning():
                thread.quit()
                thread.wait(wait_ms)
        self._thread = None
        self._worker = None

    def shutdown(self) -> None:
        self.stop(wait_ms=5000)

    def _on_thread_finished(self, thread: QThread) -> None:
        if thread in self._threads:
            self._threads.remove(thread)
        if self._thread is thread:
            self._thread = None
            self._worker = None

    def _on_finished(self, request_id: int, result: object) -> None:
        if request_id == self._request_id:
            self.analysis_ready.emit(result)

    def _on_failed(self, request_id: int, message: str) -> None:
        if request_id == self._request_id:
            self.analysis_failed.emit(message)
