"""Modbus panel - master request builder for Modbus communication."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from src.utils.byte_utils import crc16_modbus, int_to_bytes, lrc
from src.utils.formatters import hex_to_bytes


class ModbusPanel(QWidget):
    """Modbus master request construction and send panel."""

    send_requested = Signal(int, int, bytes)

    FUNCTION_CODES = {
        "01 Read Coils": 0x01,
        "02 Read Discrete Inputs": 0x02,
        "03 Read Holding Registers": 0x03,
        "04 Read Input Registers": 0x04,
        "05 Write Single Coil": 0x05,
        "06 Write Single Register": 0x06,
        "0F Write Multiple Coils": 0x0F,
        "10 Write Multiple Registers": 0x10,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        mode_group = QGroupBox("Transport")
        mode_layout = QFormLayout()

        self._transport_combo = QComboBox()
        self._transport_combo.addItems(["RTU (Serial)", "ASCII (Serial)", "TCP"])
        self._transport_combo.currentTextChanged.connect(self._update_field_state)
        mode_layout.addRow("Mode:", self._transport_combo)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        req_group = QGroupBox("Request Builder")
        req_layout = QFormLayout()

        self._slave_spin = QSpinBox()
        self._slave_spin.setRange(0, 247)
        self._slave_spin.setValue(1)
        req_layout.addRow("Slave ID:", self._slave_spin)

        self._func_combo = QComboBox()
        self._func_combo.addItems(list(self.FUNCTION_CODES.keys()))
        self._func_combo.setCurrentText("03 Read Holding Registers")
        self._func_combo.currentTextChanged.connect(self._update_field_state)
        req_layout.addRow("Function:", self._func_combo)

        self._addr_spin = QSpinBox()
        self._addr_spin.setRange(0, 65535)
        self._addr_spin.setValue(0)
        req_layout.addRow("Start address:", self._addr_spin)

        self._quantity_spin = QSpinBox()
        self._quantity_spin.setRange(1, 125)
        self._quantity_spin.setValue(10)
        req_layout.addRow("Quantity:", self._quantity_spin)

        self._data_input = QLineEdit()
        self._data_input.setPlaceholderText("HEX payload, e.g. 00 FF")
        self._data_input.textChanged.connect(self._clear_status)
        req_layout.addRow("Data:", self._data_input)

        req_group.setLayout(req_layout)
        layout.addWidget(req_group)

        btn_layout = QHBoxLayout()
        self._send_btn = QPushButton("Send Modbus Request")
        self._send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(self._send_btn)

        self._build_btn = QPushButton("Preview Frame")
        self._build_btn.clicked.connect(self._on_preview)
        btn_layout.addWidget(self._build_btn)

        layout.addLayout(btn_layout)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setFont(QFont("Consolas", 9))
        self._preview_text.setMaximumHeight(120)
        self._preview_text.setStyleSheet("""
            QTextEdit {
                background-color: #252525;
                color: #8BC34A;
                border: 1px solid #3C3C3C;
            }
        """)
        layout.addWidget(self._preview_text)

        layout.addStretch()
        self._update_field_state()

    def _set_status(self, message: str, error: bool = False) -> None:
        self._status_label.setText(message)
        self._status_label.setStyleSheet("color: #F44336;" if error else "color: #888;")

    def _clear_status(self, *_args) -> None:
        self._set_status("Ready")

    def _update_field_state(self, *_args) -> None:
        func = self._get_func_code()
        needs_data = func in (0x05, 0x06, 0x0F, 0x10)
        self._data_input.setEnabled(needs_data)
        if needs_data:
            self._data_input.setPlaceholderText("HEX payload, e.g. 00 FF")
        else:
            self._data_input.setPlaceholderText("Not used for this function")
            self._data_input.clear()
        self._clear_status()

    def _on_send(self) -> None:
        frame = self._build_frame()
        if frame is None:
            return

        self.send_requested.emit(
            self._slave_spin.value(),
            self._get_func_code(),
            frame,
        )
        self._set_status(f"Queued {len(frame)} byte(s) for send.")

    def _on_preview(self) -> None:
        frame = self._build_frame()
        if frame is None:
            return
        self._preview_text.setText(f"Frame ({len(frame)} bytes):\n{frame.hex(' ').upper()}")
        self._set_status("Preview updated.")

    def _get_func_code(self) -> int:
        return self.FUNCTION_CODES[self._func_combo.currentText()]

    def _build_frame(self) -> bytes | None:
        slave = self._slave_spin.value()
        func = self._get_func_code()
        addr = self._addr_spin.value()
        quantity = self._quantity_spin.value()

        pdu = bytes([func])

        if func in (0x01, 0x02, 0x03, 0x04):
            pdu += int_to_bytes(addr, 2, "big")
            pdu += int_to_bytes(quantity, 2, "big")
        elif func in (0x05, 0x06):
            data_bytes = self._require_data_bytes(max_len=2)
            if data_bytes is None:
                return None
            pdu += int_to_bytes(addr, 2, "big")
            pdu += data_bytes[:2].ljust(2, b"\x00")
        elif func in (0x0F, 0x10):
            data_bytes = self._require_data_bytes()
            if data_bytes is None:
                return None
            pdu += int_to_bytes(addr, 2, "big")
            pdu += int_to_bytes(quantity, 2, "big")
            pdu += bytes([len(data_bytes)])
            pdu += data_bytes

        transport = self._transport_combo.currentText()

        if "RTU" in transport:
            adu = bytes([slave]) + pdu
            crc = crc16_modbus(adu)
            return adu + int_to_bytes(crc, 2, "little")

        if "ASCII" in transport:
            adu = bytes([slave]) + pdu
            lrc_val = lrc(adu)
            adu_with_lrc = adu + bytes([lrc_val])
            hex_encoded = adu_with_lrc.hex().upper().encode("ascii")
            return b":" + hex_encoded + b"\r\n"

        transaction_id = 1
        protocol_id = 0
        unit_id = slave
        length = len(pdu) + 1
        mbap = (
            int_to_bytes(transaction_id, 2, "big")
            + int_to_bytes(protocol_id, 2, "big")
            + int_to_bytes(length, 2, "big")
            + bytes([unit_id])
        )
        return mbap + pdu

    def _require_data_bytes(self, max_len: int | None = None) -> bytes | None:
        text = self._data_input.text().strip()
        if not text:
            self._set_status("Data is required for the selected function.", error=True)
            return None

        data_bytes = hex_to_bytes(text)
        if data_bytes is None:
            self._set_status("Invalid HEX payload. Use pairs like '00 FF'.", error=True)
            return None

        if max_len is not None and len(data_bytes) > max_len:
            self._set_status(f"Data must be at most {max_len} byte(s).", error=True)
            return None

        return data_bytes
