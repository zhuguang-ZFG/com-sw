"""Terminal view — the primary serial data display with send capability.

Supports HEX and ASCII display modes, auto-scroll, timestamp display,
and data sending with CR/LF/CRLF line endings.
"""

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QCheckBox, QSplitter,
)
from PySide6.QtGui import QFont, QTextCursor

from src.models.data_packet import DataPacket
from src.utils.formatters import format_terminal_line, hex_to_bytes
from src.utils.byte_utils import crc16_modbus


class TerminalView(QWidget):
    """Terminal view for serial data display and sending.

    Displays incoming/outgoing data with timestamps and direction indicators.
    Supports HEX and ASCII display modes, and allows sending data.
    """

    send_requested = Signal(bytes)  # Emitted when user wants to send data
    modbus_send_requested = Signal(int, int, bytes)  # slave_id, func_code, data

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = "ascii"
        self._show_timestamp = True
        self._show_direction = True
        self._auto_scroll = True
        self._max_display_lines = 10000
        self._line_count = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Display area ===
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

        # === Toolbar ===
        toolbar = QHBoxLayout()

        # Display mode selector
        toolbar.addWidget(QLabel("显示:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["ASCII", "HEX"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)

        toolbar.addSpacing(10)

        # Checkboxes
        self._timestamp_cb = QCheckBox("时间戳")
        self._timestamp_cb.setChecked(True)
        self._timestamp_cb.stateChanged.connect(self._on_timestamp_changed)
        toolbar.addWidget(self._timestamp_cb)

        self._direction_cb = QCheckBox("方向")
        self._direction_cb.setChecked(True)
        self._direction_cb.stateChanged.connect(self._on_direction_changed)
        toolbar.addWidget(self._direction_cb)

        self._autoscroll_cb = QCheckBox("自动滚动")
        self._autoscroll_cb.setChecked(True)
        toolbar.addWidget(self._autoscroll_cb)

        toolbar.addSpacing(10)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._text_display.clear)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # === Send area ===
        send_layout = QHBoxLayout()

        # Send mode
        self._send_mode_combo = QComboBox()
        self._send_mode_combo.addItems(["ASCII", "HEX", "Modbus RTU"])
        send_layout.addWidget(self._send_mode_combo)

        # Line ending
        self._line_ending_combo = QComboBox()
        self._line_ending_combo.addItems(["无", "\\r\\n", "\\n", "\\r"])
        send_layout.addWidget(QLabel("换行:"))
        send_layout.addWidget(self._line_ending_combo)

        # Send input
        self._send_input = QLineEdit()
        self._send_input.setPlaceholderText("输入要发送的数据...")
        self._send_input.returnPressed.connect(self._on_send)
        send_layout.addWidget(self._send_input)

        self._send_btn = QPushButton("发送")
        self._send_btn.clicked.connect(self._on_send)
        send_layout.addWidget(self._send_btn)

        layout.addLayout(send_layout)

    def append_packets(self, packets: List[DataPacket]) -> None:
        """Append a batch of DataPackets to the display."""
        lines = []
        total_bytes = 0

        for packet in packets:
            line = format_terminal_line(
                packet,
                display_mode=self._display_mode,
                show_timestamp=self._show_timestamp,
                show_direction=self._show_direction,
            )
            lines.append(line)
            total_bytes += packet.length

        if lines:
            self._text_display.append("\n".join(lines))

            # Trim old lines if over limit
            self._line_count += len(lines)
            if self._line_count > self._max_display_lines:
                cursor = self._text_display.textCursor()
                cursor.movePosition(QTextCursor.Start)
                cursor.movePosition(
                    QTextCursor.Down, QTextCursor.KeepAnchor,
                    self._line_count - self._max_display_lines,
                )
                cursor.removeSelectedText()
                self._line_count = self._max_display_lines

            # Auto-scroll to bottom
            if self._autoscroll_cb.isChecked():
                scrollbar = self._text_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

    def _on_send(self) -> None:
        """Handle send button or Enter key."""
        text = self._send_input.text()
        if not text:
            return

        send_mode = self._send_mode_combo.currentText()
        line_ending = self._line_ending_combo.currentText()

        try:
            if send_mode == "HEX":
                data = hex_to_bytes(text)
                if data is None:
                    return
            elif send_mode == "Modbus RTU":
                data = hex_to_bytes(text)
                if data is None:
                    return
                # Auto-append CRC16
                crc = crc16_modbus(data)
                data = data + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
            else:
                data = text.encode("utf-8")

            # Append line ending
            le_map = {"无": b"", "\\r\\n": b"\r\n", "\\n": b"\n", "\\r": b"\r"}
            data = data + le_map.get(line_ending, b"")

            self.send_requested.emit(data)
            self._send_input.clear()
        except Exception:
            pass

    def _on_mode_changed(self, mode: str) -> None:
        self._display_mode = mode.lower()

    def _on_timestamp_changed(self, state: int) -> None:
        self._show_timestamp = state == Qt.Checked.value

    def _on_direction_changed(self, state: int) -> None:
        self._show_direction = state == Qt.Checked.value

    def clear(self) -> None:
        self._text_display.clear()
        self._line_count = 0

    @property
    def display_mode(self) -> str:
        return self._display_mode
