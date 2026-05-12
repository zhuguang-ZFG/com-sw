"""Dump view - classic hex dump display with address offset and ASCII sidebar.

Similar to xxd, HxD, or WinHex display. Each line shows:
  OFFSET  HEX_BYTES  |ASCII_REPRESENTATION|
"""

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QSpinBox, QCheckBox, QPushButton,
)
from PySide6.QtGui import QFont

from src.models.data_packet import DataPacket
from src.utils.formatters import format_dump_line


class DumpView(QWidget):
    """Hexadecimal dump view with address column and ASCII sidebar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bytes_per_line = 16
        self._show_offset = True
        self._show_ascii = True
        self._merge_packets = False
        self._current_offset = 0
        self._max_lines = 5000

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Bytes/line:"))

        self._bytes_spin = QSpinBox()
        self._bytes_spin.setRange(4, 64)
        self._bytes_spin.setValue(16)
        self._bytes_spin.setSingleStep(4)
        self._bytes_spin.valueChanged.connect(self._on_bytes_changed)
        toolbar.addWidget(self._bytes_spin)

        self._offset_cb = QCheckBox("Offset")
        self._offset_cb.setChecked(True)
        toolbar.addWidget(self._offset_cb)

        self._ascii_cb = QCheckBox("ASCII")
        self._ascii_cb.setChecked(True)
        toolbar.addWidget(self._ascii_cb)

        self._merge_cb = QCheckBox("Merge packets")
        self._merge_cb.setChecked(False)
        self._merge_cb.stateChanged.connect(self._on_merge_changed)
        toolbar.addWidget(self._merge_cb)

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

        self._offset_label = QLabel("Offset: 0x00000000")
        self._offset_label.setStyleSheet("color: #888;")
        layout.addWidget(self._offset_label)

    def append_packets(self, packets: List[DataPacket]) -> None:
        """Append serial data as hex dump lines."""
        lines = []
        for packet in packets:
            data = packet.data
            if self._merge_packets:
                for i in range(0, len(data), self._bytes_per_line):
                    chunk = data[i:i + self._bytes_per_line]
                    lines.append(format_dump_line(
                        chunk,
                        offset=self._current_offset,
                        bytes_per_line=self._bytes_per_line,
                        show_offset=self._offset_cb.isChecked(),
                        show_ascii=self._ascii_cb.isChecked(),
                    ))
                    self._current_offset += len(chunk)
            else:
                for i in range(0, len(data), self._bytes_per_line):
                    chunk = data[i:i + self._bytes_per_line]
                    lines.append(format_dump_line(
                        chunk,
                        offset=i if not self._show_offset else self._current_offset + i,
                        bytes_per_line=self._bytes_per_line,
                        show_offset=self._offset_cb.isChecked(),
                        show_ascii=self._ascii_cb.isChecked(),
                    ))
                self._current_offset += len(data)

        if lines:
            self._text_display.append("\n".join(lines))
            self._offset_label.setText(f"Offset: 0x{self._current_offset:08X}")

            scrollbar = self._text_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _on_bytes_changed(self, val: int) -> None:
        self._bytes_per_line = val

    def _on_merge_changed(self, state: int) -> None:
        self._merge_packets = state == Qt.Checked.value
        if not self._merge_packets:
            self._current_offset = 0

    def clear(self) -> None:
        self._text_display.clear()
        self._current_offset = 0
        self._offset_label.setText("Offset: 0x00000000")

    def apply_preferences(self, *, bytes_per_line: int | None = None,
                          show_offset: bool | None = None, show_ascii: bool | None = None,
                          font_size: int | None = None) -> None:
        if bytes_per_line is not None:
            self._bytes_per_line = bytes_per_line
            self._bytes_spin.setValue(bytes_per_line)
        if show_offset is not None:
            self._show_offset = show_offset
            self._offset_cb.setChecked(show_offset)
        if show_ascii is not None:
            self._show_ascii = show_ascii
            self._ascii_cb.setChecked(show_ascii)
        if font_size is not None:
            self._text_display.setFont(QFont("Consolas", font_size))
