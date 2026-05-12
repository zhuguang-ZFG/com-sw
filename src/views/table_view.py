"""Table view - structured column display of serial data."""

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

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

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Display:"))

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["ASCII", "HEX"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)

        self._autoscroll_cb = QCheckBox("Auto-scroll")
        self._autoscroll_cb.setChecked(True)
        self._autoscroll_cb.stateChanged.connect(self._on_autoscroll_changed)
        toolbar.addWidget(self._autoscroll_cb)

        toolbar.addStretch()

        self._row_label = QLabel("Rows: 0")
        toolbar.addWidget(self._row_label)

        toolbar.addSpacing(10)

        self._copy_btn = QPushButton("Copy Selected")
        self._copy_btn.clicked.connect(self._copy_selected)
        toolbar.addWidget(self._copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        self._status_label = QLabel("No packets yet. Incoming traffic will appear here.")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Timestamp", "Direction", "Length", "Data"])
        self._table.setFont(QFont("Consolas", 9))
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(False)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                color: #D4D4D4;
                gridline-color: #3C3C3C;
                border: 1px solid #3C3C3C;
                alternate-background-color: #252526;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #CCCCCC;
                padding: 4px;
                border: 1px solid #3C3C3C;
            }
        """)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setStretchLastSection(True)

        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.ExtendedSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setWordWrap(False)
        self._table.setSortingEnabled(True)
        self._table.itemSelectionChanged.connect(self._update_copy_button)

        layout.addWidget(self._table)
        self._update_copy_button()

    def append_packets(self, packets: List[DataPacket]) -> None:
        """Append rows to the table."""
        if not packets:
            return

        sorting_enabled = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)
        self._table.setUpdatesEnabled(False)

        current_rows = self._table.rowCount()
        self._table.setRowCount(current_rows + len(packets))

        for offset, packet in enumerate(packets):
            row = format_table_row(packet, display_mode=self._display_mode)
            table_row = current_rows + offset

            self._table.setItem(table_row, 0, QTableWidgetItem(row["timestamp"]))
            self._table.setItem(table_row, 1, QTableWidgetItem(row["direction"]))
            self._table.setItem(table_row, 2, QTableWidgetItem(row["length"]))
            self._table.setItem(table_row, 3, QTableWidgetItem(row["data"]))

        overflow_rows = self._table.rowCount() - self._max_rows
        if overflow_rows > 0:
            self._table.model().removeRows(0, overflow_rows)

        self._table.setUpdatesEnabled(True)
        self._table.setSortingEnabled(sorting_enabled)

        if self._autoscroll_cb.isChecked():
            self._table.scrollToBottom()

        self._row_label.setText(f"Rows: {self._table.rowCount()}")
        self._status_label.setText("Ready")
        self._status_label.setStyleSheet("color: #888;")
        self._update_copy_button()

    def _on_mode_changed(self, mode: str) -> None:
        self._display_mode = mode.lower()
        self._status_label.setText("Display mode changed. New incoming rows will use this format.")
        self._status_label.setStyleSheet("color: #888;")

    def _on_autoscroll_changed(self, state: int) -> None:
        self._auto_scroll = bool(state)
        self._status_label.setText("Auto-scroll enabled." if self._auto_scroll else "Auto-scroll paused.")
        self._status_label.setStyleSheet("color: #888;")

    def _update_copy_button(self) -> None:
        has_selection = bool(self._table.selectedRanges())
        self._copy_btn.setEnabled(has_selection)

    def _copy_selected(self) -> None:
        """Copy selected rows to clipboard."""
        selected = self._table.selectedRanges()
        if not selected:
            self._status_label.setText("Select one or more rows to copy.")
            self._status_label.setStyleSheet("color: #F44336;")
            return

        lines = []
        for selection in selected:
            for row in range(selection.topRow(), selection.bottomRow() + 1):
                cells = []
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    cells.append(item.text() if item else "")
                lines.append("\t".join(cells))

        QApplication.clipboard().setText("\n".join(lines))
        self._status_label.setText(f"Copied {len(lines)} row(s) to the clipboard.")
        self._status_label.setStyleSheet("color: #888;")

    def clear(self) -> None:
        self._table.setRowCount(0)
        self._row_label.setText("Rows: 0")
        self._status_label.setText("No packets yet. Incoming traffic will appear here.")
        self._status_label.setStyleSheet("color: #888;")
        self._update_copy_button()

    def apply_preferences(self, *, display_mode: str | None = None, max_rows: int | None = None,
                          font_size: int | None = None) -> None:
        if display_mode:
            self._display_mode = display_mode
            self._mode_combo.setCurrentText(display_mode.upper())
        if max_rows is not None:
            self._max_rows = max_rows
        if font_size is not None:
            self._table.setFont(QFont("Consolas", font_size))
