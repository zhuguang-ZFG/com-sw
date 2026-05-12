"""Line view — filtered line-by-line serial data display.

Displays each received data packet as a single line.
Supports content filtering (show only lines containing a substring).
"""

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QCheckBox, QComboBox,
)
from PySide6.QtGui import QFont, QTextCursor

from src.models.data_packet import DataPacket
from src.utils.formatters import format_terminal_line


class LineView(QWidget):
    """Line-by-line view with content filtering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = "ascii"
        self._filter_text = ""
        self._show_timestamp = True
        self._max_lines = 5000
        self._line_count = 0
        self._filtered_count = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("显示:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["ASCII", "HEX"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)

        toolbar.addSpacing(10)

        toolbar.addWidget(QLabel("过滤:"))
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("输入关键词过滤...")
        self._filter_input.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._filter_input)

        self._filter_label = QLabel("")
        toolbar.addWidget(self._filter_label)

        toolbar.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # Display area
        self._text_display = QTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setFont(QFont("Consolas", 10))
        self._text_display.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
            }
        """)
        layout.addWidget(self._text_display)

    def append_packets(self, packets: List[DataPacket]) -> None:
        """Append lines to the display, applying any active filter."""
        lines = []
        filtered = 0

        for packet in packets:
            line = format_terminal_line(
                packet,
                display_mode=self._display_mode,
                show_timestamp=self._show_timestamp,
                show_direction=True,
            )

            if self._filter_text:
                if self._filter_text not in line:
                    filtered += 1
                    continue

            lines.append(line)

        if lines:
            self._text_display.append("\n".join(lines))
            self._line_count += len(lines)
            self._filtered_count += filtered

            # Trim
            if self._line_count > self._max_lines:
                cursor = self._text_display.textCursor()
                cursor.movePosition(QTextCursor.Start)
                cursor.movePosition(
                    QTextCursor.Down, QTextCursor.KeepAnchor,
                    self._line_count - self._max_lines,
                )
                cursor.removeSelectedText()
                self._line_count = self._max_lines

            # Auto-scroll
            scrollbar = self._text_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        self._update_filter_label()

    def _on_mode_changed(self, mode: str) -> None:
        self._display_mode = mode.lower()

    def _on_filter_changed(self, text: str) -> None:
        self._filter_text = text
        self._update_filter_label()

    def _update_filter_label(self) -> None:
        if self._filter_text:
            self._filter_label.setText(
                f"(已过滤: {self._filtered_count})"
            )
        else:
            self._filter_label.setText("")

    def clear(self) -> None:
        self._text_display.clear()
        self._line_count = 0
        self._filtered_count = 0
