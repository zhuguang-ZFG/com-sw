"""Modbus analysis view for decoded frames and pair summaries."""

from __future__ import annotations

from typing import List

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
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

        layout.addWidget(self._table)

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
            "highlight": highlight,
        })
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

    def clear(self) -> None:
        self._entries.clear()
        self._table.setRowCount(0)
        self._count_label.setText("Entries: 0")
        self._status_label.setText("No Modbus analysis entries yet.")
        self._status_label.setStyleSheet("color: #888;")
