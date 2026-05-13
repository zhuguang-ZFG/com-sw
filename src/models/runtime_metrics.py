"""Runtime diagnostics metrics for serial monitoring sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from src.models.data_packet import DataPacket


@dataclass
class RuntimeMetricsSnapshot:
    elapsed_seconds: float
    packets_processed: int
    bytes_rx: int
    bytes_tx: int
    bytes_total: int
    packets_per_second: float
    bytes_per_second: float
    batches_processed: int
    last_batch_size: int
    max_batch_size: int
    dropped_packets: int
    replay_loaded_packets: int
    replay_index: int
    replay_speed: float
    last_packet_at: datetime | None
    recent_errors: list[str]
    recent_events: list[str]


class RuntimeMetrics:
    """Collects lightweight runtime counters for diagnostics UI."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._started_at = datetime.now()
        self._packets_processed = 0
        self._bytes_rx = 0
        self._bytes_tx = 0
        self._batches_processed = 0
        self._last_batch_size = 0
        self._max_batch_size = 0
        self._dropped_packets = 0
        self._replay_loaded_packets = 0
        self._replay_index = 0
        self._replay_speed = 1.0
        self._last_packet_at: datetime | None = None
        self._recent_errors: list[str] = []
        self._recent_events: list[str] = []

    def record_packets(self, packets: Iterable[DataPacket]) -> None:
        packet_list = list(packets)
        if not packet_list:
            return
        self._batches_processed += 1
        self._last_batch_size = len(packet_list)
        self._max_batch_size = max(self._max_batch_size, len(packet_list))
        self._packets_processed += len(packet_list)
        self._last_packet_at = packet_list[-1].timestamp
        for packet in packet_list:
            if packet.direction.value == "RX":
                self._bytes_rx += packet.length
            else:
                self._bytes_tx += packet.length

    def record_dropped_packets(self, dropped_packets: int) -> None:
        if dropped_packets > 0:
            self._dropped_packets += dropped_packets

    def set_replay_state(self, current: int, total: int, speed: float) -> None:
        self._replay_index = current
        self._replay_loaded_packets = total
        self._replay_speed = speed

    def record_error(self, message: str, when: datetime | None = None) -> None:
        timestamp = (when or datetime.now()).strftime("%H:%M:%S")
        self._recent_errors.append(f"[{timestamp}] {message}")
        self._recent_errors = self._recent_errors[-5:]

    def record_event(self, message: str, when: datetime | None = None) -> None:
        timestamp = (when or datetime.now()).strftime("%H:%M:%S")
        self._recent_events.append(f"[{timestamp}] {message}")
        self._recent_events = self._recent_events[-12:]

    def snapshot(self, now: datetime | None = None) -> RuntimeMetricsSnapshot:
        snapshot_time = now or datetime.now()
        elapsed_seconds = max((snapshot_time - self._started_at).total_seconds(), 0.001)
        bytes_total = self._bytes_rx + self._bytes_tx
        return RuntimeMetricsSnapshot(
            elapsed_seconds=elapsed_seconds,
            packets_processed=self._packets_processed,
            bytes_rx=self._bytes_rx,
            bytes_tx=self._bytes_tx,
            bytes_total=bytes_total,
            packets_per_second=self._packets_processed / elapsed_seconds,
            bytes_per_second=bytes_total / elapsed_seconds,
            batches_processed=self._batches_processed,
            last_batch_size=self._last_batch_size,
            max_batch_size=self._max_batch_size,
            dropped_packets=self._dropped_packets,
            replay_loaded_packets=self._replay_loaded_packets,
            replay_index=self._replay_index,
            replay_speed=self._replay_speed,
            last_packet_at=self._last_packet_at,
            recent_errors=list(self._recent_errors),
            recent_events=list(self._recent_events),
        )
