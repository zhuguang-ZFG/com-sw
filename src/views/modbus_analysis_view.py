"""Modbus analysis view for decoded frames and pair summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QLineEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class NumericTableWidgetItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by numeric value."""

    def __init__(self, text: str, numeric_value: int) -> None:
        super().__init__(text)
        self._numeric_value = numeric_value

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, NumericTableWidgetItem):
            return self._numeric_value < other._numeric_value
        return super().__lt__(other)


class ModbusAnalysisView(QWidget):
    """Tabular Modbus analysis results."""

    focus_packet_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[dict] = []
        self._restoring_filters = False
        self._status_filter_value = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self._count_label = QLabel("Entries: 0")
        toolbar.addWidget(self._count_label)
        self._exceptions_only_cb = QCheckBox("Exceptions Only")
        self._exceptions_only_cb.toggled.connect(self._apply_filters)
        toolbar.addWidget(self._exceptions_only_cb)

        self._paired_only_cb = QCheckBox("Paired Only")
        self._paired_only_cb.toggled.connect(self._apply_filters)
        toolbar.addWidget(self._paired_only_cb)

        toolbar.addWidget(QLabel("Slave:"))
        self._slave_filter = QLineEdit()
        self._slave_filter.setPlaceholderText("e.g. 1")
        self._slave_filter.setMaximumWidth(60)
        self._slave_filter.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self._slave_filter)

        toolbar.addWidget(QLabel("Func:"))
        self._function_filter = QLineEdit()
        self._function_filter.setPlaceholderText("e.g. 03")
        self._function_filter.setMaximumWidth(60)
        self._function_filter.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self._function_filter)

        toolbar.addWidget(QLabel("Search:"))
        self._search_filter = QLineEdit()
        self._search_filter.setPlaceholderText("summary / status / raw hex")
        self._search_filter.setMaximumWidth(220)
        self._search_filter.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self._search_filter)

        toolbar.addWidget(QLabel("Status:"))
        self._status_filter_group = QButtonGroup(self)
        self._status_filter_group.setExclusive(True)
        self._status_filter_buttons: dict[str, QPushButton] = {}
        for label, value in [
            ("All", ""),
            ("Frame", "Frame"),
            ("Response", "Paired Response"),
            ("Exception", "Paired Exception"),
        ]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, status_value=value: self._set_status_filter(status_value))
            toolbar.addWidget(button)
            self._status_filter_group.addButton(button)
            self._status_filter_buttons[value] = button
        self._status_filter_buttons[""].setChecked(True)

        toolbar.addStretch()

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        export_json_btn = QPushButton("Export JSON")
        export_json_btn.clicked.connect(self._export_json)
        toolbar.addWidget(export_json_btn)

        copy_json_btn = QPushButton("Copy JSON")
        copy_json_btn.clicked.connect(self._copy_selected_json)
        toolbar.addWidget(copy_json_btn)

        copy_filtered_json_btn = QPushButton("Copy Filtered JSON")
        copy_filtered_json_btn.clicked.connect(self._copy_filtered_json)
        toolbar.addWidget(copy_filtered_json_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)
        layout.addLayout(toolbar)

        self._status_label = QLabel("No Modbus analysis entries yet.")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        self._stats_label = QLabel(
            "Total: 0 | Exceptions: 0 | Paired: 0 | Min Latency: n/a | Max Latency: n/a | Avg Latency: n/a"
        )
        self._stats_label.setStyleSheet("color: #888;")
        layout.addWidget(self._stats_label)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Timestamp",
            "Direction",
            "Slave",
            "Function",
            "Latency (ms)",
            "Status",
            "Summary",
        ])
        self._table.setFont(QFont("Consolas", 9))
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setWordWrap(False)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        self._table.itemSelectionChanged.connect(self._update_detail_panel)
        self._table.cellDoubleClicked.connect(self._on_row_double_clicked)

        layout.addWidget(self._table)

        self._detail_label = QLabel("Select an analysis row to inspect raw frame details.")
        self._detail_label.setStyleSheet("color: #888;")
        layout.addWidget(self._detail_label)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setMaximumHeight(140)
        self._detail_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self._detail_text)

    def add_entry(
        self,
        timestamp: str,
        direction: str,
        slave: int,
        function: int,
        latency_ms: int | None,
        status: str,
        summary: str,
        highlight: bool = False,
        frame_index: int | None = None,
    ) -> None:
        self._entries.append({
            "timestamp": timestamp,
            "direction": direction,
            "slave": slave,
            "function": function,
            "latency_ms": latency_ms,
            "status": status,
            "summary": summary,
            "raw_hex": "",
            "exception_code": None,
            "highlight": highlight,
            "frame_index": frame_index,
        })
        self._apply_filters()

    def add_entry_details(self, raw_hex: str, exception_code: int | None) -> None:
        if not self._entries:
            return
        self._entries[-1]["raw_hex"] = raw_hex
        self._entries[-1]["exception_code"] = exception_code
        self._apply_filters()

    def get_filter_state(self) -> dict:
        return {
            "exceptions_only": self._exceptions_only_cb.isChecked(),
            "paired_only": self._paired_only_cb.isChecked(),
            "slave_filter": self._slave_filter.text(),
            "function_filter": self._function_filter.text(),
            "search_filter": self._search_filter.text(),
            "status_filter": self._status_filter_value,
        }

    def set_filter_state(self, state: dict) -> None:
        self._restoring_filters = True
        try:
            self._exceptions_only_cb.setChecked(bool(state.get("exceptions_only", False)))
            self._paired_only_cb.setChecked(bool(state.get("paired_only", False)))
            self._slave_filter.setText(str(state.get("slave_filter", "")))
            self._function_filter.setText(str(state.get("function_filter", "")))
            self._search_filter.setText(str(state.get("search_filter", "")))
            self._set_status_filter(str(state.get("status_filter", "")), apply_filters=False)
        finally:
            self._restoring_filters = False
        self._apply_filters()

    def _set_status_filter(self, status_value: str, *, apply_filters: bool = True) -> None:
        self._status_filter_value = status_value
        button = self._status_filter_buttons.get(status_value, self._status_filter_buttons[""])
        button.setChecked(True)
        if apply_filters and not self._restoring_filters:
            self._apply_filters()

    def _apply_filters(self) -> None:
        filtered_entries = self.get_filtered_entries()

        self._table.setRowCount(0)
        for entry in filtered_entries:
            self._append_table_row(entry)

        self._count_label.setText(f"Entries: {len(filtered_entries)}")
        self._status_label.setText("Ready" if filtered_entries else "No matching Modbus analysis entries.")
        self._update_stats(filtered_entries)
        self._update_detail_panel()

    def _update_stats(self, entries: List[dict]) -> None:
        total = len(entries)
        exceptions = sum(1 for entry in entries if entry["highlight"])
        paired = sum(1 for entry in entries if "Paired" in entry["status"])
        latencies = [entry["latency_ms"] for entry in entries if entry["latency_ms"] is not None]
        min_latency = f"{min(latencies)} ms" if latencies else "n/a"
        max_latency = f"{max(latencies)} ms" if latencies else "n/a"
        avg_latency = f"{sum(latencies) / len(latencies):.1f} ms" if latencies else "n/a"
        self._stats_label.setText(
            f"Total: {total} | Exceptions: {exceptions} | Paired: {paired} | "
            f"Min Latency: {min_latency} | Max Latency: {max_latency} | Avg Latency: {avg_latency}"
        )

    def get_filtered_entries(self) -> List[dict]:
        exception_only = self._exceptions_only_cb.isChecked()
        paired_only = self._paired_only_cb.isChecked()
        slave_filter = self._slave_filter.text().strip()
        function_filter = self._function_filter.text().strip().lower().removeprefix("0x")
        search_filter = self._search_filter.text().strip().lower()
        status_filter = self._status_filter_value

        filtered_entries = []
        for entry in self._entries:
            if exception_only and not entry["highlight"]:
                continue
            if paired_only and "Paired" not in entry["status"]:
                continue
            if slave_filter and str(entry["slave"]) != slave_filter:
                continue
            if function_filter and f"{entry['function']:02x}" != function_filter:
                continue
            if status_filter and entry["status"] != status_filter:
                continue
            if search_filter:
                haystack = " ".join([
                    entry["timestamp"],
                    entry["direction"],
                    str(entry["slave"]),
                    f"0x{entry['function']:02X}",
                    "" if entry["latency_ms"] is None else str(entry["latency_ms"]),
                    entry["status"],
                    entry["summary"],
                    entry.get("raw_hex", ""),
                ]).lower()
                if search_filter not in haystack:
                    continue
            filtered_entries.append(entry)
        return filtered_entries

    def export_csv(self, file_path: str) -> None:
        entries = self.get_filtered_entries()
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "timestamp",
                "direction",
                "slave",
                "function",
                "latency_ms",
                "status",
                "summary",
                "exception_code",
                "raw_hex",
            ])
            for entry in entries:
                writer.writerow([
                    entry["timestamp"],
                    entry["direction"],
                    entry["slave"],
                    f"0x{entry['function']:02X}",
                    "" if entry["latency_ms"] is None else entry["latency_ms"],
                    entry["status"],
                    entry["summary"],
                    "" if entry.get("exception_code") is None else f"0x{entry['exception_code']:02X}",
                    entry.get("raw_hex", ""),
                ])

    def export_json(self, file_path: str) -> None:
        entries = self.get_filtered_entries()
        payload = self._serialize_entries(entries)

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    def _serialize_entry(self, entry: dict) -> dict:
        return {
            "timestamp": entry["timestamp"],
            "direction": entry["direction"],
            "slave": entry["slave"],
            "function": f"0x{entry['function']:02X}",
            "latency_ms": entry["latency_ms"],
            "status": entry["status"],
            "summary": entry["summary"],
            "exception_code": None if entry.get("exception_code") is None else f"0x{entry['exception_code']:02X}",
            "raw_hex": entry.get("raw_hex", ""),
            "highlight": entry["highlight"],
        }

    def _serialize_entries(self, entries: List[dict]) -> List[dict]:
        return [self._serialize_entry(entry) for entry in entries]

    def _filtered_json_text(self) -> str:
        return json.dumps(
            self._serialize_entries(self.get_filtered_entries()),
            indent=2,
            ensure_ascii=False,
        )

    def copy_selected_json(self) -> bool:
        row = self._table.currentRow()
        if row < 0:
            return False
        filtered_entries = self.get_filtered_entries()
        if row >= len(filtered_entries):
            return False
        payload = self._serialize_entry(filtered_entries[row])
        clipboard = QApplication.clipboard()
        clipboard.setText(json.dumps(payload, indent=2, ensure_ascii=False))
        return True

    def copy_filtered_json(self) -> bool:
        clipboard = QApplication.clipboard()
        clipboard.setText(self._filtered_json_text())
        return True

    def _export_csv(self) -> None:
        default_path = str(Path.home() / "Documents" / "com-sw-modbus-analysis.csv")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Modbus Analysis",
            default_path,
            "CSV files (*.csv)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"
        self.export_csv(file_path)
        self._status_label.setText(f"Exported analysis to {file_path}")
        self._status_label.setStyleSheet("color: #888;")

    def _export_json(self) -> None:
        default_path = str(Path.home() / "Documents" / "com-sw-modbus-analysis.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Modbus Analysis",
            default_path,
            "JSON files (*.json)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path += ".json"
        self.export_json(file_path)
        self._status_label.setText(f"Exported analysis to {file_path}")
        self._status_label.setStyleSheet("color: #888;")

    def _copy_selected_json(self) -> None:
        if self.copy_selected_json():
            self._status_label.setText("Copied selected analysis as JSON")
            self._status_label.setStyleSheet("color: #888;")
            return
        self._status_label.setText("No analysis row selected to copy")
        self._status_label.setStyleSheet("color: #888;")

    def _copy_filtered_json(self) -> None:
        self.copy_filtered_json()
        self._status_label.setText("Copied filtered analysis as JSON")
        self._status_label.setStyleSheet("color: #888;")

    def _on_row_double_clicked(self, row: int, _column: int) -> None:
        filtered_entries = self.get_filtered_entries()
        if row < 0 or row >= len(filtered_entries):
            return
        frame_index = filtered_entries[row].get("frame_index")
        if frame_index is None:
            self._status_label.setText("No linked frame available for this analysis row")
            self._status_label.setStyleSheet("color: #888;")
            return
        self.focus_packet_requested.emit(frame_index)
        self._status_label.setText(f"Focused linked frame #{frame_index}")
        self._status_label.setStyleSheet("color: #888;")

    def _append_table_row(self, entry: dict) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        items: List[QTableWidgetItem] = [
            QTableWidgetItem(entry["timestamp"]),
            QTableWidgetItem(entry["direction"]),
            NumericTableWidgetItem(str(entry["slave"]), entry["slave"]),
            NumericTableWidgetItem(f"0x{entry['function']:02X}", entry["function"]),
            NumericTableWidgetItem(
                "" if entry["latency_ms"] is None else str(entry["latency_ms"]),
                -1 if entry["latency_ms"] is None else entry["latency_ms"],
            ),
            QTableWidgetItem(entry["status"]),
            QTableWidgetItem(entry["summary"]),
        ]
        if entry["highlight"]:
            for item in items:
                item.setBackground(QColor("#4A1F1F"))
                item.setForeground(QColor("#FFB3B3"))
        for column, item in enumerate(items):
            self._table.setItem(row, column, item)
        self._table.scrollToBottom()

    def _update_detail_panel(self) -> None:
        current_row = self._table.currentRow()
        if current_row < 0 or current_row >= self._table.rowCount():
            self._detail_label.setText("Select an analysis row to inspect raw frame details.")
            self._detail_text.clear()
            return

        timestamp = self._table.item(current_row, 0).text()
        direction = self._table.item(current_row, 1).text()
        slave = self._table.item(current_row, 2).text()
        function = self._table.item(current_row, 3).text()
        latency = self._table.item(current_row, 4).text()
        status = self._table.item(current_row, 5).text()
        summary = self._table.item(current_row, 6).text()

        matched_entry = None
        for entry in self.get_filtered_entries():
            if (
                entry["timestamp"] == timestamp
                and entry["direction"] == direction
                and str(entry["slave"]) == slave
                and f"0x{entry['function']:02X}" == function
                and entry["status"] == status
                and entry["summary"] == summary
            ):
                matched_entry = entry
                break

        detail_lines = [
            f"Timestamp: {timestamp}",
            f"Direction: {direction}",
            f"Slave: {slave}",
            f"Function: {function}",
            f"Status: {status}",
            f"Latency: {latency or 'n/a'} ms",
            f"Summary: {summary}",
        ]
        if matched_entry is not None:
            if matched_entry.get("exception_code") is not None:
                detail_lines.append(f"Exception Code: 0x{matched_entry['exception_code']:02X}")
            detail_lines.append(f"Raw HEX: {matched_entry.get('raw_hex', '') or 'n/a'}")

        self._detail_label.setText("Selected Modbus analysis entry")
        self._detail_text.setPlainText("\n".join(detail_lines))

    def clear(self) -> None:
        self._entries.clear()
        self._table.setRowCount(0)
        self._count_label.setText("Entries: 0")
        self._status_label.setText("No Modbus analysis entries yet.")
        self._status_label.setStyleSheet("color: #888;")
        self._stats_label.setText(
            "Total: 0 | Exceptions: 0 | Paired: 0 | Min Latency: n/a | Max Latency: n/a | Avg Latency: n/a"
        )
        self._detail_label.setText("Select an analysis row to inspect raw frame details.")
        self._detail_text.clear()
        self._search_filter.clear()
        self._set_status_filter("", apply_filters=False)
