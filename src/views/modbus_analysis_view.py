"""Modbus analysis view for decoded frames and pair summaries."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
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


class ModbusAnalysisView(QWidget):
    """Tabular Modbus analysis results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: List[dict] = []
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

        toolbar.addStretch()

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)
        layout.addLayout(toolbar)

        self._status_label = QLabel("No Modbus analysis entries yet.")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

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
        })
        self._apply_filters()

    def add_entry_details(self, raw_hex: str, exception_code: int | None) -> None:
        if not self._entries:
            return
        self._entries[-1]["raw_hex"] = raw_hex
        self._entries[-1]["exception_code"] = exception_code
        self._apply_filters()

    def _apply_filters(self) -> None:
        exception_only = self._exceptions_only_cb.isChecked()
        paired_only = self._paired_only_cb.isChecked()
        slave_filter = self._slave_filter.text().strip()
        function_filter = self._function_filter.text().strip().lower().removeprefix("0x")

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
            filtered_entries.append(entry)

        self._table.setRowCount(0)
        for entry in filtered_entries:
            self._append_table_row(entry)

        self._count_label.setText(f"Entries: {len(filtered_entries)}")
        self._status_label.setText("Ready" if filtered_entries else "No matching Modbus analysis entries.")
        self._update_detail_panel()

    def get_filtered_entries(self) -> List[dict]:
        exception_only = self._exceptions_only_cb.isChecked()
        paired_only = self._paired_only_cb.isChecked()
        slave_filter = self._slave_filter.text().strip()
        function_filter = self._function_filter.text().strip().lower().removeprefix("0x")

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
            filtered_entries.append(entry)
        return filtered_entries

    def export_csv(self, file_path: str) -> None:
        entries = self.get_filtered_entries()
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp", "direction", "slave", "function", "latency_ms", "status", "summary"])
            for entry in entries:
                writer.writerow([
                    entry["timestamp"],
                    entry["direction"],
                    entry["slave"],
                    f"0x{entry['function']:02X}",
                    "" if entry["latency_ms"] is None else entry["latency_ms"],
                    entry["status"],
                    entry["summary"],
                ])

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

    def _append_table_row(self, entry: dict) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        items: List[QTableWidgetItem] = [
            QTableWidgetItem(entry["timestamp"]),
            QTableWidgetItem(entry["direction"]),
            QTableWidgetItem(str(entry["slave"])),
            QTableWidgetItem(f"0x{entry['function']:02X}"),
            QTableWidgetItem("" if entry["latency_ms"] is None else str(entry["latency_ms"])),
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
        self._detail_label.setText("Select an analysis row to inspect raw frame details.")
        self._detail_text.clear()
