"""Tests for runtime diagnostics metrics."""

from datetime import datetime

from src.models.data_packet import DataPacket, Direction
from src.models.runtime_metrics import RuntimeMetrics


def make_packet(data: bytes, direction: Direction) -> DataPacket:
    return DataPacket(data=data, direction=direction, timestamp=datetime(2025, 1, 1, 12, 0, 0))


def test_runtime_metrics_accumulate_packets_and_bytes() -> None:
    metrics = RuntimeMetrics()
    metrics.record_packets(
        [
            make_packet(b"AB", Direction.RX),
            make_packet(b"XYZ", Direction.TX),
        ]
    )

    snapshot = metrics.snapshot(now=datetime(2025, 1, 1, 12, 0, 1))
    assert snapshot.elapsed_seconds >= 0.001
    assert snapshot.packets_processed == 2
    assert snapshot.bytes_rx == 2
    assert snapshot.bytes_tx == 3
    assert snapshot.bytes_total == 5
    assert snapshot.batches_processed == 1
    assert snapshot.last_batch_size == 2
    assert snapshot.max_batch_size == 2
    assert snapshot.packets_per_second > 0
    assert snapshot.bytes_per_second > 0


def test_runtime_metrics_track_drops_and_replay_state() -> None:
    metrics = RuntimeMetrics()
    metrics.record_dropped_packets(3)
    metrics.set_replay_state(current=4, total=10, speed=2.0)
    metrics.record_error("Send failed", when=datetime(2025, 1, 1, 12, 0, 3))

    snapshot = metrics.snapshot()
    assert snapshot.dropped_packets == 3
    assert snapshot.replay_index == 4
    assert snapshot.replay_loaded_packets == 10
    assert snapshot.replay_speed == 2.0
    assert snapshot.recent_errors[-1].endswith("Send failed")


def test_runtime_metrics_reset_clears_counters() -> None:
    metrics = RuntimeMetrics()
    metrics.record_packets([make_packet(b"A", Direction.RX)])
    metrics.record_dropped_packets(2)
    metrics.reset()

    snapshot = metrics.snapshot()
    assert snapshot.packets_processed == 0
    assert snapshot.dropped_packets == 0
    assert snapshot.last_packet_at is None
    assert snapshot.recent_errors == []
