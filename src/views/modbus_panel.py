"""Modbus panel — master request builder for Modbus communication.

Allows constructing and sending Modbus RTU/ASCII/TCP requests.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QSpinBox, QLineEdit, QPushButton, QTextEdit, QLabel,
)
from PySide6.QtGui import QFont

from src.utils.byte_utils import crc16_modbus, lrc, int_to_bytes


class ModbusPanel(QWidget):
    """Modbus master request construction and send panel."""

    send_requested = Signal(int, int, bytes)  # slave_id, func_code, full_frame

    # Standard Modbus function codes
    FUNCTION_CODES = {
        "01 读取线圈": 0x01,
        "02 读取离散输入": 0x02,
        "03 读取保持寄存器": 0x03,
        "04 读取输入寄存器": 0x04,
        "05 写单个线圈": 0x05,
        "06 写单个寄存器": 0x06,
        "0F 写多个线圈": 0x0F,
        "10 写多个寄存器": 0x10,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Transport mode
        mode_group = QGroupBox("传输模式")
        mode_layout = QFormLayout()

        self._transport_combo = QComboBox()
        self._transport_combo.addItems(["RTU (串口)", "ASCII (串口)", "TCP"])
        mode_layout.addRow("模式:", self._transport_combo)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Request builder
        req_group = QGroupBox("请求构建")
        req_layout = QFormLayout()

        self._slave_spin = QSpinBox()
        self._slave_spin.setRange(0, 247)
        self._slave_spin.setValue(1)
        req_layout.addRow("从站ID:", self._slave_spin)

        self._func_combo = QComboBox()
        self._func_combo.addItems(list(self.FUNCTION_CODES.keys()))
        self._func_combo.setCurrentText("03 读取保持寄存器")
        req_layout.addRow("功能码:", self._func_combo)

        self._addr_spin = QSpinBox()
        self._addr_spin.setRange(0, 65535)
        self._addr_spin.setValue(0)
        req_layout.addRow("起始地址:", self._addr_spin)

        self._quantity_spin = QSpinBox()
        self._quantity_spin.setRange(1, 125)
        self._quantity_spin.setValue(10)
        req_layout.addRow("数量:", self._quantity_spin)

        self._data_input = QLineEdit()
        self._data_input.setPlaceholderText("写入数据 (HEX, 如: 00FF)")
        req_layout.addRow("数据:", self._data_input)

        req_group.setLayout(req_layout)
        layout.addWidget(req_group)

        # Send button
        btn_layout = QHBoxLayout()
        self._send_btn = QPushButton("发送 Modbus 请求")
        self._send_btn.clicked.connect(self._on_send)
        btn_layout.addWidget(self._send_btn)

        self._build_btn = QPushButton("预览帧")
        self._build_btn.clicked.connect(self._on_preview)
        btn_layout.addWidget(self._build_btn)

        layout.addLayout(btn_layout)

        # Preview / Response area
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

    def _on_send(self) -> None:
        """Build the frame and emit send_requested."""
        frame = self._build_frame()
        if frame:
            self.send_requested.emit(
                self._slave_spin.value(),
                self._get_func_code(),
                frame,
            )

    def _on_preview(self) -> None:
        """Preview the constructed frame."""
        frame = self._build_frame()
        if frame:
            self._preview_text.setText(f"Frame ({len(frame)} bytes):\n{frame.hex(' ').upper()}")

    def _get_func_code(self) -> int:
        """Extract function code from the combo box text."""
        fc_text = self._func_combo.currentText()[:2]
        return int(fc_text, 16)

    def _build_frame(self) -> bytes:
        """Build the complete Modbus frame based on transport mode."""
        slave = self._slave_spin.value()
        func = self._get_func_code()
        addr = self._addr_spin.value()
        quantity = self._quantity_spin.value()

        # Build PDU (Protocol Data Unit)
        pdu = bytes([func])

        # Build address/data part based on function code
        if func in (0x01, 0x02, 0x03, 0x04):  # Read functions
            pdu += int_to_bytes(addr, 2, "big")
            pdu += int_to_bytes(quantity, 2, "big")
        elif func in (0x05, 0x06):  # Write single
            pdu += int_to_bytes(addr, 2, "big")
            data_text = self._data_input.text().replace(" ", "")
            if data_text:
                try:
                    data_bytes = bytes.fromhex(data_text)
                    pdu += data_bytes[:2].ljust(2, b"\x00")
                except ValueError:
                    pass
        elif func in (0x0F, 0x10):  # Write multiple
            pdu += int_to_bytes(addr, 2, "big")
            pdu += int_to_bytes(quantity, 2, "big")
            data_text = self._data_input.text().replace(" ", "")
            if data_text:
                try:
                    data_bytes = bytes.fromhex(data_text)
                    pdu += bytes([len(data_bytes)])
                    pdu += data_bytes
                except ValueError:
                    pass

        transport = self._transport_combo.currentText()

        if "RTU" in transport:
            # ADU = slave + PDU + CRC
            adu = bytes([slave]) + pdu
            crc = crc16_modbus(adu)
            return adu + int_to_bytes(crc, 2, "little")
        elif "ASCII" in transport:
            # ADU = : + hex_encoded(slave + PDU + LRC) + CRLF
            adu = bytes([slave]) + pdu
            lrc_val = lrc(adu)
            adu_with_lrc = adu + bytes([lrc_val])
            hex_encoded = adu_with_lrc.hex().upper().encode("ascii")
            return b":" + hex_encoded + b"\r\n"
        else:
            # TCP: MBAP header (no slave in PDU, in header instead)
            # Simplified: just return as RTU for now
            adu = bytes([slave]) + pdu
            crc = crc16_modbus(adu)
            return adu + int_to_bytes(crc, 2, "little")
