"""Tests for Modbus analysis helpers."""

from datetime import datetime

from src.controllers.modbus_analysis import (
    ModbusPairingTracker,
    analyze_packet,
    packet_to_display_entry,
)
from src.models.data_packet import DataPacket, Direction
from src.protocol.modbus_rtu import encode_rtu_frame


def test_packet_to_display_entry_uses_analysis_values() -> None:
    packet = DataPacket(
        data=encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 02")),
        direction=Direction.TX,
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
    )
    analysis = analyze_packet(packet)
    entry = packet_to_display_entry(packet, analysis)
    assert entry.direction == "TX"
    assert entry.slave_id == 1
    assert entry.function_code == 0x03
    assert entry.status == "Frame"


def test_modbus_pairing_tracker_exception_response() -> None:
    tracker = ModbusPairingTracker()
    tx = DataPacket(
        data=encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 02")),
        direction=Direction.TX,
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
    )
    rx = DataPacket(
        data=bytes.fromhex("01 83 02 C0 F1"),
        direction=Direction.RX,
        timestamp=datetime(2025, 1, 1, 12, 0, 0, 100000),
    )
    tracker.observe(tx)
    result = tracker.observe(rx)
    assert result.matched is True
    assert result.is_exception is True
    assert result.latency_ms == 100
