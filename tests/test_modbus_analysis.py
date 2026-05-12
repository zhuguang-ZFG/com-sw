"""Tests for Modbus analysis helpers."""

from datetime import datetime
import json
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
    view.add_entry_details("02 84 02", 0x02)
    view._exceptions_only_cb.setChecked(True)

    export_path = tmp_path / "analysis.csv"
    view.export_csv(str(export_path))

    content = export_path.read_text(encoding="utf-8")
    assert "timestamp,direction,slave,function,latency_ms,status,summary,exception_code,raw_hex" in content
    assert "12:00:00.100,RX,2,0x04,100,Paired Exception,error,0x02,02 84 02" in content
    assert "12:00:00.000,RX,1,0x03" not in content


def test_modbus_analysis_view_exports_filtered_entries_to_json(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.000", "RX", 1, 0x03, None, "Frame", "normal", False)
    view.add_entry_details("01 03 00 00", None)
    view.add_entry("12:00:00.100", "RX", 2, 0x04, 100, "Paired Exception", "error", True)
    view.add_entry_details("02 84 02", 0x02)
    view._exceptions_only_cb.setChecked(True)

    export_path = tmp_path / "analysis.json"
    view.export_json(str(export_path))

    content = json.loads(export_path.read_text(encoding="utf-8"))
    assert len(content) == 1
    assert content[0]["timestamp"] == "12:00:00.100"
    assert content[0]["function"] == "0x04"
    assert content[0]["exception_code"] == "0x02"
    assert content[0]["raw_hex"] == "02 84 02"
    assert content[0]["highlight"] is True


def test_modbus_analysis_view_copies_selected_entry_as_json() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.100", "RX", 2, 0x04, 100, "Paired Exception", "error", True)
    view.add_entry_details("02 84 02", 0x02)

    view._table.selectRow(0)
    assert view.copy_selected_json() is True

    payload = json.loads(app.clipboard().text())
    assert payload["timestamp"] == "12:00:00.100"
    assert payload["function"] == "0x04"
    assert payload["exception_code"] == "0x02"
    assert payload["raw_hex"] == "02 84 02"
    assert payload["highlight"] is True


def test_modbus_analysis_view_copy_selected_json_without_selection() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    app.clipboard().setText("")

    assert view.copy_selected_json() is False
    assert app.clipboard().text() == ""


def test_modbus_analysis_view_copies_filtered_entries_as_json() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.add_entry("12:00:00.000", "RX", 1, 0x03, None, "Frame", "normal", False)
    view.add_entry_details("01 03 00 00", None)
    view.add_entry("12:00:00.100", "RX", 2, 0x04, 100, "Paired Exception", "error", True)
    view.add_entry_details("02 84 02", 0x02)
    view._exceptions_only_cb.setChecked(True)

    payload = json.loads(view._filtered_json_text())
    assert len(payload) == 1
    assert payload[0]["timestamp"] == "12:00:00.100"
    assert payload[0]["function"] == "0x04"
    assert payload[0]["exception_code"] == "0x02"
    assert payload[0]["raw_hex"] == "02 84 02"
    assert payload[0]["highlight"] is True

    assert view.copy_filtered_json() is True


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
    assert "Min Latency: 50 ms" in view._stats_label.text()
    assert "Max Latency: 100 ms" in view._stats_label.text()
    assert "Avg Latency: 75.0 ms" in view._stats_label.text()

    view._exceptions_only_cb.setChecked(True)
    assert view._stats_label.text() == (
        "Total: 1 | Exceptions: 1 | Paired: 1 | Min Latency: 100 ms | "
        "Max Latency: 100 ms | Avg Latency: 100.0 ms"
    )


def test_modbus_analysis_view_restores_filter_state() -> None:
    app = QApplication.instance() or QApplication([])
    view = ModbusAnalysisView()
    view.set_filter_state(
        {
            "exceptions_only": True,
            "paired_only": True,
            "slave_filter": "2",
            "function_filter": "04",
            "search_filter": "error",
        }
    )

    assert view.get_filter_state() == {
        "exceptions_only": True,
        "paired_only": True,
        "slave_filter": "2",
        "function_filter": "04",
        "search_filter": "error",
    }
