"""Tests for session recording and replay helpers."""

from datetime import datetime
from pathlib import Path

from src.controllers.session_recorder import (
    SessionRecorder,
    load_session,
    packet_to_record,
    record_to_packet,
)
from src.models.data_packet import DataPacket, Direction


def test_packet_record_roundtrip() -> None:
    packet = DataPacket(
        data=b"\x01\x03\x02\x00\x64",
        direction=Direction.RX,
        timestamp=datetime(2025, 8, 14, 10, 21, 33, 123000),
        port_name="COM3",
    )
    restored = record_to_packet(packet_to_record(packet))
    assert restored.data == packet.data
    assert restored.direction == packet.direction
    assert restored.timestamp == packet.timestamp
    assert restored.port_name == packet.port_name


def test_session_recorder_write_and_load(tmp_path: Path) -> None:
    recorder = SessionRecorder()
    session_path = tmp_path / "session.jsonl"
    recorder.start(str(session_path))
    recorder.record_packets([
        DataPacket(data=b"ABC", direction=Direction.TX, timestamp=datetime(2025, 1, 1, 12, 0, 0)),
        DataPacket(data=b"\x01\x02", direction=Direction.RX, timestamp=datetime(2025, 1, 1, 12, 0, 1)),
    ])
    recorder.stop()

    packets = load_session(str(session_path))
    assert len(packets) == 2
    assert packets[0].data == b"ABC"
    assert packets[0].direction == Direction.TX
    assert packets[1].data == b"\x01\x02"
    assert packets[1].direction == Direction.RX
