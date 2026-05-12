"""Timed session replay controller for COM-SW."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, List

from PySide6.QtCore import QObject, QTimer, Signal

from src.models.data_packet import DataPacket


class SessionReplayController(QObject):
    """Replay packets with timing controls."""

    finished = Signal()
    progress_changed = Signal(int, int, float)

    def __init__(self, emit_packets: Callable[[List[DataPacket]], None], parent=None):
        super().__init__(parent)
        self._emit_packets = emit_packets
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._play_next)
        self._packets: List[DataPacket] = []
        self._index = 0
        self._speed = 1.0
        self._playing = False

    @property
    def is_loaded(self) -> bool:
        return bool(self._packets)

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def total_packets(self) -> int:
        return len(self._packets)

    @property
    def current_index(self) -> int:
        return self._index

    def load(self, packets: List[DataPacket]) -> None:
        self.stop()
        self._packets = list(packets)
        self._index = 0
        self.progress_changed.emit(self._index, len(self._packets), self._speed)

    def play(self) -> None:
        if not self._packets or self._playing:
            return
        self._playing = True
        self._play_next()

    def pause(self) -> None:
        self._playing = False
        self._timer.stop()

    def stop(self) -> None:
        self._playing = False
        self._timer.stop()
        self._index = 0
        self.progress_changed.emit(self._index, len(self._packets), self._speed)

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.1, speed)
        self.progress_changed.emit(self._index, len(self._packets), self._speed)

    def restart(self) -> None:
        self.stop()
        if self._packets:
            self.play()

    def step(self) -> None:
        if not self._packets or self._index >= len(self._packets):
            return
        self._playing = False
        self._timer.stop()
        current = self._packets[self._index]
        self._emit_packets([current])
        self._index += 1
        self.progress_changed.emit(self._index, len(self._packets), self._speed)
        if self._index >= len(self._packets):
            self.finished.emit()

    def _play_next(self) -> None:
        if not self._playing or self._index >= len(self._packets):
            if self._index >= len(self._packets):
                self._playing = False
                self.finished.emit()
            return

        current = self._packets[self._index]
        self._emit_packets([current])
        self._index += 1
        self.progress_changed.emit(self._index, len(self._packets), self._speed)

        if self._index >= len(self._packets):
            self._playing = False
            self.finished.emit()
            return

        delay_ms = self._compute_delay_ms(
            current.timestamp,
            self._packets[self._index].timestamp,
        )
        self._timer.start(delay_ms)

    def _compute_delay_ms(self, current: datetime, nxt: datetime) -> int:
        delta_ms = max(0, int((nxt - current).total_seconds() * 1000))
        return max(1, int(delta_ms / self._speed))
