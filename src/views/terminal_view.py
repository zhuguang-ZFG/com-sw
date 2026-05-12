"""Terminal view - the primary serial data display with send capability."""

from typing import List

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QCheckBox,
)
from PySide6.QtGui import QFont

from src.models.data_packet import DataPacket
from src.utils.formatters import format_terminal_line, hex_to_bytes
from src.utils.byte_utils import crc16_modbus


class TerminalView(QWidget):
    """Terminal view for serial data display and sending."""

    send_requested = Signal(bytes)
    modbus_send_requested = Signal(int, int, bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = "ascii"
        self._show_timestamp = True
        self._show_direction = True
        self._auto_scroll = True
        self._max_display_lines = 10000

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_display = QTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setFont(QFont("Consolas", 10))
        self._text_display.document().setMaximumBlockCount(self._max_display_lines)
        self._text_display.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
            }
        """)
        layout.addWidget(self._text_display)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Display:"))

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["ASCII", "HEX"])
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        toolbar.addWidget(self._mode_combo)

        toolbar.addSpacing(10)

        self._timestamp_cb = QCheckBox("Timestamp")
        self._timestamp_cb.setChecked(True)
        self._timestamp_cb.stateChanged.connect(self._on_timestamp_changed)
        toolbar.addWidget(self._timestamp_cb)

        self._direction_cb = QCheckBox("Direction")
        self._direction_cb.setChecked(True)
        self._direction_cb.stateChanged.connect(self._on_direction_changed)
        toolbar.addWidget(self._direction_cb)

        self._autoscroll_cb = QCheckBox("Auto-scroll")
        self._autoscroll_cb.setChecked(True)
        self._autoscroll_cb.stateChanged.connect(self._on_autoscroll_changed)
        toolbar.addWidget(self._autoscroll_cb)

        toolbar.addSpacing(10)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        send_layout = QHBoxLayout()

        self._send_mode_combo = QComboBox()
        self._send_mode_combo.addItems(["ASCII", "HEX", "Modbus RTU"])
        self._send_mode_combo.currentTextChanged.connect(self._on_send_mode_changed)
        send_layout.addWidget(self._send_mode_combo)

        self._line_ending_combo = QComboBox()
        self._line_ending_combo.addItems(["None", "\\r\\n", "\\n", "\\r"])
        send_layout.addWidget(QLabel("Line ending:"))
        send_layout.addWidget(self._line_ending_combo)

        self._send_input = QLineEdit()
        self._send_input.setPlaceholderText("Type data to send...")
        self._send_input.returnPressed.connect(self._on_send)
        send_layout.addWidget(self._send_input)

        self._send_btn = QPushButton("Send")
        self._send_btn.clicked.connect(self._on_send)
        send_layout.addWidget(self._send_btn)

        layout.addLayout(send_layout)

        self._send_status = QLabel("Ready")
        self._send_status.setStyleSheet("color: #888;")
        layout.addWidget(self._send_status)

        self._on_send_mode_changed(self._send_mode_combo.currentText())

    def append_packets(self, packets: List[DataPacket]) -> None:
        lines = []
        for packet in packets:
            lines.append(format_terminal_line(
                packet,
                display_mode=self._display_mode,
                show_timestamp=self._show_timestamp,
                show_direction=self._show_direction,
            ))

        if lines:
            self._text_display.append("\n".join(lines))
            if self._autoscroll_cb.isChecked():
                scrollbar = self._text_display.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

    def _on_mode_changed(self, mode: str) -> None:
        self._display_mode = mode.lower()

    def _on_timestamp_changed(self, state: int) -> None:
        self._show_timestamp = bool(state)

    def _on_direction_changed(self, state: int) -> None:
        self._show_direction = bool(state)

    def _on_autoscroll_changed(self, state: int) -> None:
        self._auto_scroll = bool(state)

    def _on_send_mode_changed(self, mode: str) -> None:
        is_modbus = mode == "Modbus RTU"
        self._line_ending_combo.setEnabled(not is_modbus)
        if mode == "HEX":
            self._send_input.setPlaceholderText("Enter hex bytes, e.g. 01 03 00 00 00 02")
        elif is_modbus:
            self._send_input.setPlaceholderText("Enter a full Modbus RTU frame in HEX")
        else:
            self._send_input.setPlaceholderText("Type data to send...")
        self._set_send_status("Ready", error=False)

    def _set_send_status(self, message: str, error: bool = False) -> None:
        self._send_status.setText(message)
        self._send_status.setStyleSheet(
            "color: #F44336;" if error else "color: #888;"
        )

    def _on_send(self) -> None:
        text = self._send_input.text().strip()
        if not text:
            self._set_send_status("Nothing to send.", error=True)
            return

        mode = self._send_mode_combo.currentText()
        payload: bytes | None = None

        if mode == "ASCII":
            le_map = {"None": b"", "\\r\\n": b"\r\n", "\\n": b"\n", "\\r": b"\r"}
            payload = text.encode("utf-8") + le_map[self._line_ending_combo.currentText()]
        else:
            payload = hex_to_bytes(text)
            if payload is None:
                self._set_send_status("Invalid HEX input. Use pairs like '01 03 00 00'.", error=True)
                return

            if mode == "Modbus RTU" and len(payload) >= 4:
                body = payload[:-2]
                expected_crc = int.from_bytes(payload[-2:], "little")
                actual_crc = crc16_modbus(body)
                if actual_crc != expected_crc:
                    self._set_send_status(
                        f"CRC mismatch: expected {expected_crc:04X}, computed {actual_crc:04X}.",
                        error=True,
                    )
                    return

        self.send_requested.emit(payload)
        self._set_send_status(f"Sent {len(payload)} byte(s).", error=False)
        self._send_input.clear()

    def clear(self) -> None:
        self._text_display.clear()
        self._set_send_status("Cleared terminal output.", error=False)

    @property
    def display_mode(self) -> str:
        return self._display_mode

    def apply_preferences(self, *, display_mode: str | None = None, auto_scroll: bool | None = None,
                          show_timestamp: bool | None = None, show_direction: bool | None = None,
                          font_size: int | None = None) -> None:
        if display_mode:
            self._display_mode = display_mode
            self._mode_combo.setCurrentText(display_mode.upper())
        if font_size is not None:
            self._text_display.setFont(QFont("Consolas", font_size))
        if auto_scroll is not None:
            self._auto_scroll = auto_scroll
            self._autoscroll_cb.setChecked(auto_scroll)
        if show_timestamp is not None:
            self._show_timestamp = show_timestamp
            self._timestamp_cb.setChecked(show_timestamp)
        if show_direction is not None:
            self._show_direction = show_direction
            self._direction_cb.setChecked(show_direction)
