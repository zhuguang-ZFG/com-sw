"""Data pump — periodically drains the ring buffer and emits batches.

Runs on the main thread via QTimer. Drains the ring buffer at a
configurable interval, then emits the drained packets to connected views.
"""

import logging
from typing import List

from PySide6.QtCore import QObject, QTimer, Signal

from src.models.data_packet import DataPacket
from src.serial.ring_buffer import RingBuffer

logger = logging.getLogger(__name__)


class DataPump(QObject):
    """Periodic data pump that drains the ring buffer.

    Emits a signal with all pending packets every `interval_ms` milliseconds.
    """

    data_ready = Signal(list)  # List[DataPacket]

    def __init__(self, ring_buffer: RingBuffer, interval_ms: int = 50, parent=None):
        super().__init__(parent)
        self._ring_buffer = ring_buffer
        self._interval_ms = interval_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pump)
        self._is_running = False

    def start(self) -> None:
        """Start periodic pumping."""
        self._is_running = True
        self._timer.start(self._interval_ms)
        logger.debug(f"Data pump started (interval={self._interval_ms}ms)")

    def stop(self) -> None:
        """Stop periodic pumping."""
        self._timer.stop()
        self._is_running = False
        logger.debug("Data pump stopped")

    def _pump(self) -> None:
        """Drain the ring buffer and emit pending packets."""
        packets = self._ring_buffer.drain()
        if packets:
            self.data_ready.emit(packets)

    @property
    def is_running(self) -> bool:
        return self._is_running
