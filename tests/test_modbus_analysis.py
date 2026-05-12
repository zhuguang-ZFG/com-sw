"""Tests for Modbus analysis helpers."""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
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


def test_modbus_analysis_view_exports_filtered_entries(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.000", "RX", 1, 0x03, None, "Frame", "normal", False)
    view.add_entry("12:00:00.100", "RX", 2, 0x04, 100, "Paired Exception", "error", True)
    view._exceptions_only_cb.setChecked(True)

    export_path = tmp_path / "analysis.csv"
    view.export_csv(str(export_path))

    content = export_path.read_text(encoding="utf-8")
    assert "timestamp,direction,slave,function,latency_ms,status,summary" in content
    assert "12:00:00.100,RX,2,0x04,100,Paired Exception,error" in content
    assert "12:00:00.000,RX,1,0x03" not in content


def test_modbus_analysis_view_shows_selected_entry_details() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.100", "RX", 1, 0x03, 25, "Paired Response", "ok", False)
    view.add_entry_details("01 03 04 00 0A 00 14", None)

    view._table.selectRow(0)
    detail = view._detail_text.toPlainText()
    assert "Direction: RX" in detail
    assert "Latency: 25 ms" in detail
    assert "Raw HEX: 01 03 04 00 0A 00 14" in detail


def test_modbus_analysis_view_search_filters_summary_and_raw_hex() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.000", "RX", 1, 0x03, None, "Frame", "holding registers", False)
    view.add_entry_details("01 03 04 00 0A 00 14", None)
    view.add_entry("12:00:00.200", "TX", 2, 0x06, None, "Frame", "write single register", False)
    view.add_entry_details("02 06 00 01 00 FF", None)

    view._search_filter.setText("holding")
    assert view._table.rowCount() == 1
    assert view._table.item(0, 6).text() == "holding registers"

    view._search_filter.setText("00 ff")
    assert view._table.rowCount() == 1
    assert view._table.item(0, 1).text() == "TX"


def test_modbus_analysis_view_sorts_numeric_columns() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.200", "RX", 10, 0x10, 200, "Frame", "later", False)
    view.add_entry("12:00:00.100", "RX", 2, 0x03, 20, "Frame", "earlier", False)

    view._table.sortItems(2, Qt.AscendingOrder)
    assert view._table.item(0, 2).text() == "2"

    view._table.sortItems(4, Qt.AscendingOrder)
    assert view._table.item(0, 4).text() == "20"


def test_modbus_analysis_view_updates_stats_for_filtered_entries() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.000", "RX", 1, 0x03, None, "Frame", "normal", False)
    view.add_entry("12:00:00.100", "RX", 1, 0x03, 100, "Paired Exception", "error", True)
    view.add_entry("12:00:00.200", "RX", 1, 0x03, 50, "Paired Response", "ok", False)

    assert "Total: 3" in view._stats_label.text()
    assert "Exceptions: 1" in view._stats_label.text()
    assert "Paired: 2" in view._stats_label.text()
    assert "Avg Latency: 75.0 ms" in view._stats_label.text()

    view._exceptions_only_cb.setChecked(True)
    assert view._stats_label.text() == "Total: 1 | Exceptions: 1 | Paired: 1 | Avg Latency: 100.0 ms"
