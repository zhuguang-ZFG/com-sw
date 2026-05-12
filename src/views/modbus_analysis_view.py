"""Modbus analysis view for decoded frames and pair summaries."""

from __future__ import annotations

from typing import List

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
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
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        self._count_label = QLabel("Entries: 0")
        toolbar.addWidget(self._count_label)
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
        row = self._table.rowCount()
        self._table.insertRow(row)
        items: List[QTableWidgetItem] = [
            QTableWidgetItem(timestamp),
            QTableWidgetItem(direction),
            QTableWidgetItem(str(slave)),
            QTableWidgetItem(f"0x{function:02X}"),
            QTableWidgetItem("" if latency_ms is None else str(latency_ms)),
            QTableWidgetItem(status),
            QTableWidgetItem(summary),
        ]
        if highlight:
            for item in items:
                item.setBackground(QColor("#4A1F1F"))
                item.setForeground(QColor("#FFB3B3"))
        for column, item in enumerate(items):
            self._table.setItem(row, column, item)
        self._count_label.setText(f"Entries: {self._table.rowCount()}")
        self._status_label.setText("Ready")
        self._table.scrollToBottom()

    def clear(self) -> None:
        self._table.setRowCount(0)
        self._count_label.setText("Entries: 0")
        self._status_label.setText("No Modbus analysis entries yet.")
        self._status_label.setStyleSheet("color: #888;")
