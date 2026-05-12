"""Thread-safe ring buffer for serial data.

The ring buffer is the central data structure in the pipeline.
SerialReader (QThread) appends raw bytes, DataPump (main thread timer)
atomically drains all pending data.
"""

import threading
from collections import deque
from typing import List, Optional

from src.models.data_packet import DataPacket


class RingBuffer:
    """Thread-safe bounded ring buffer using deque + Lock.

    Design:
    - append() is called from the serial reader thread
    - drain() is called from the main thread's data pump timer
    - The lock is held only for the duration of the swap, not for iteration
    - Bounded size prevents memory exhaustion under high throughput
    """

    def __init__(self, max_size: int = 10000):
        self._max_size = max_size
        self._buffer: deque[DataPacket] = deque()
        self._lock = threading.Lock()
        self._overflow_count = 0

    def append(self, packet: DataPacket) -> None:
        """Add a packet to the buffer. Thread-safe. Blocks minimally."""
        with self._lock:
            self._buffer.append(packet)
            if len(self._buffer) > self._max_size:
                self._overflow_count += 1
                self._buffer.popleft()  # Drop oldest

    def drain(self) -> List[DataPacket]:
        """Atomically extract all pending packets. Returns empty list if none."""
        with self._lock:
            if not self._buffer:
                return []
            drained = list(self._buffer)
            self._buffer.clear()
            self._overflow_count = 0
            return drained

    def peek(self) -> List[DataPacket]:
        """View all packets without removing them."""
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        """Discard all buffered data."""
        with self._lock:
            self._buffer.clear()
            self._overflow_count = 0

    @property
    def length(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def overflow_count(self) -> int:
        with self._lock:
            return self._overflow_count
