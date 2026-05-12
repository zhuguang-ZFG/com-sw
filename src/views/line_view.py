"""Line view - filtered line-by-line serial data display."""

from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QComboBox,
)
from PySide6.QtGui import QFont

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
        self._filtered_count = 0

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

        toolbar.addSpacing(10)

        toolbar.addWidget(QLabel("Filter:"))
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Type text to filter visible lines...")
        self._filter_input.textChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self._filter_input)

        self._filter_label = QLabel("")
        toolbar.addWidget(self._filter_label)

        toolbar.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        self._text_display = QTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setFont(QFont("Consolas", 10))
        self._text_display.document().setMaximumBlockCount(self._max_lines)
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

            if self._filter_text and self._filter_text not in line:
                filtered += 1
                continue

            lines.append(line)

        self._filtered_count += filtered

        if lines:
            self._text_display.append("\n".join(lines))
            scrollbar = self._text_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        self._update_filter_label()

    def _on_mode_changed(self, mode: str) -> None:
        self._display_mode = mode.lower()

    def _on_filter_changed(self, text: str) -> None:
        self._filter_text = text
        self._filtered_count = 0
        self._update_filter_label()

    def _update_filter_label(self) -> None:
        if self._filter_text:
            self._filter_label.setText(f"Filtered: {self._filtered_count}")
        else:
            self._filter_label.setText("")

    def clear(self) -> None:
        self._text_display.clear()
        self._filtered_count = 0
        self._update_filter_label()

    def apply_preferences(self, *, display_mode: str | None = None, max_lines: int | None = None,
                          font_size: int | None = None) -> None:
        if display_mode:
            self._display_mode = display_mode
            self._mode_combo.setCurrentText(display_mode.upper())
        if max_lines is not None:
            self._max_lines = max_lines
            self._text_display.document().setMaximumBlockCount(max_lines)
        if font_size is not None:
            self._text_display.setFont(QFont("Consolas", font_size))
