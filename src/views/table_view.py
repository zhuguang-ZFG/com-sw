"""Table view — structured column display of serial data.

Each row shows: timestamp, direction, length, data.
Columns are sortable. Rows can be selected and copied.
"""

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QCheckBox, QComboBox, QApplication,
)
from PySide6.QtGui import QFont

from src.models.data_packet import DataPacket
from src.utils.formatters import format_table_row


class TableView(QWidget):
    """Sortable table view for serial data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = "ascii"
        self._max_rows = 5000
        self._auto_scroll = True

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("显示模式:"))

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["ASCII", "HEX"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)

        self._autoscroll_cb = QCheckBox("自动滚动")
        self._autoscroll_cb.setChecked(True)
        toolbar.addWidget(self._autoscroll_cb)

        toolbar.addStretch()

        self._row_label = QLabel("行数: 0")
        toolbar.addWidget(self._row_label)

        toolbar.addSpacing(10)

        copy_btn = QPushButton("复制选中行")
        copy_btn.clicked.connect(self._copy_selected)
        toolbar.addWidget(copy_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["时间", "方向", "长度", "数据"])
        self._table.setFont(QFont("Consolas", 9))
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                color: #D4D4D4;
                gridline-color: #3C3C3C;
                border: 1px solid #3C3C3C;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #CCCCCC;
                padding: 4px;
                border: 1px solid #3C3C3C;
            }
        """)

        # Column sizing
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self._table)

    def append_packets(self, packets: List[DataPacket]) -> None:
        """Append rows to the table."""
        self._table.setUpdatesEnabled(False)

        for packet in packets:
            row = format_table_row(packet, display_mode=self._display_mode)
            table_row = self._table.rowCount()
            self._table.insertRow(table_row)

            self._table.setItem(table_row, 0, QTableWidgetItem(row["timestamp"]))
            self._table.setItem(table_row, 1, QTableWidgetItem(row["direction"]))
            self._table.setItem(table_row, 2, QTableWidgetItem(row["length"]))
            self._table.setItem(table_row, 3, QTableWidgetItem(row["data"]))

        # Trim old rows
        while self._table.rowCount() > self._max_rows:
            self._table.removeRow(0)

        self._table.setUpdatesEnabled(True)

        # Auto-scroll
        if self._autoscroll_cb.isChecked():
            self._table.scrollToBottom()

        self._row_label.setText(f"行数: {self._table.rowCount()}")

    def _on_mode_changed(self, mode: str) -> None:
        self._display_mode = mode.lower()

    def _copy_selected(self) -> None:
        """Copy selected rows to clipboard."""
        selected = self._table.selectedRanges()
        if not selected:
            return
        lines = []
        for r in selected:
            for row in range(r.topRow(), r.bottomRow() + 1):
                cells = []
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    cells.append(item.text() if item else "")
                lines.append("\t".join(cells))
        QApplication.clipboard().setText("\n".join(lines))

    def clear(self) -> None:
        self._table.setRowCount(0)
        self._row_label.setText("行数: 0")
