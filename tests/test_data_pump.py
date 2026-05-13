"""Tests for DataPump backlog signaling and batch emission."""

from src.controllers.data_pump import DataPump
from src.serial.ring_buffer import RingBuffer
from src.models.data_packet import DataPacket, Direction


def make_packet(data_byte: int) -> DataPacket:
    return DataPacket(data=bytes([data_byte & 0xFF]), direction=Direction.RX)


def test_data_pump_emits_backlog_before_drain() -> None:
    ring_buffer = RingBuffer(max_size=2)
    ring_buffer.append(make_packet(0))
    ring_buffer.append(make_packet(1))
    ring_buffer.append(make_packet(2))

    pump = DataPump(ring_buffer, interval_ms=50)

    backlog = []
    batches = []
    pump.backlog_detected.connect(backlog.append)
    pump.data_ready.connect(batches.append)

    pump._pump()

    assert backlog == [1]
    assert len(batches) == 1
    assert [packet.data for packet in batches[0]] == [b"\x01", b"\x02"]
