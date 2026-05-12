"""Tests for Modbus analysis helpers."""

from datetime import datetime

from PySide6.QtWidgets import QApplication

from src.controllers.modbus_analysis import (
    ModbusPairingTracker,
    analyze_packet,
    packet_to_display_entry,
)
from src.models.data_packet import DataPacket, Direction
from src.protocol.modbus_rtu import encode_rtu_frame
from src.views.modbus_analysis_view import ModbusAnalysisView


def test_modbus_analysis_view_filters_entries() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.000", "RX", 1, 0x03, None, "Frame", "normal", False)
    view.add_entry("12:00:00.100", "RX", 1, 0x03, 100, "Paired Exception", "error", True)
    assert view._table.rowCount() == 2

    view._exceptions_only_cb.setChecked(True)
    assert view._table.rowCount() == 1

    view._exceptions_only_cb.setChecked(False)
    view._paired_only_cb.setChecked(True)
    assert view._table.rowCount() == 1

    view._paired_only_cb.setChecked(False)
    view._slave_filter.setText("1")
    view._function_filter.setText("03")
    assert view._table.rowCount() == 2


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
