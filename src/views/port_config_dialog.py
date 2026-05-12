"""Port configuration dialog for detailed serial port settings."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QPushButton, QHBoxLayout, QCheckBox, QGroupBox, QDialogButtonBox,
    QLabel,
)
from PySide6.QtCore import Qt

import serial.tools.list_ports


BAUD_RATES = ["110", "300", "600", "1200", "2400", "4800", "9600",
              "14400", "19200", "38400", "56000", "57600",
              "115200", "230400", "460800", "921600"]

DATA_BITS = ["5", "6", "7", "8"]

STOP_BITS = {"1": 1, "1.5": 3, "2": 2}  # pyserial: 1=1, 2=1.5, 3=2
STOP_BITS_DISPLAY = list(STOP_BITS.keys())

PARITY = {"None": "N", "Odd": "O", "Even": "E", "Mark": "M", "Space": "S"}
PARITY_DISPLAY = list(PARITY.keys())

FLOW_CONTROL = {"None": "none", "RTS/CTS": "rts", "DTR/DSR": "dtr", "XON/XOFF": "xon"}


class PortConfigDialog(QDialog):
    """Detailed serial port settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("端口设置")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Port selection
        port_group = QGroupBox("串口")
        port_form = QFormLayout()

        self._port_combo = QComboBox()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self._port_combo.addItem(f"{p.device} - {p.description}", p.device)
        port_form.addRow("端口:", self._port_combo)

        port_group.setLayout(port_form)
        layout.addWidget(port_group)

        # Communication parameters
        comm_group = QGroupBox("通信参数")
        comm_form = QFormLayout()

        self._baud_combo = QComboBox()
        self._baud_combo.addItems(BAUD_RATES)
        self._baud_combo.setCurrentText("9600")
        comm_form.addRow("波特率:", self._baud_combo)

        self._data_bits_combo = QComboBox()
        self._data_bits_combo.addItems(DATA_BITS)
        self._data_bits_combo.setCurrentText("8")
        comm_form.addRow("数据位:", self._data_bits_combo)

        self._stop_bits_combo = QComboBox()
        self._stop_bits_combo.addItems(STOP_BITS_DISPLAY)
        self._stop_bits_combo.setCurrentText("1")
        comm_form.addRow("停止位:", self._stop_bits_combo)

        self._parity_combo = QComboBox()
        self._parity_combo.addItems(PARITY_DISPLAY)
        self._parity_combo.setCurrentText("None")
        comm_form.addRow("校验位:", self._parity_combo)

        self._flow_combo = QComboBox()
        self._flow_combo.addItems(list(FLOW_CONTROL.keys()))
        self._flow_combo.setCurrentText("None")
        comm_form.addRow("流控:", self._flow_combo)

        comm_group.setLayout(comm_form)
        layout.addWidget(comm_group)

        # Control signals
        sig_group = QGroupBox("控制信号")
        sig_layout = QHBoxLayout()

        self._dtr_cb = QCheckBox("DTR")
        self._dtr_cb.setChecked(True)
        sig_layout.addWidget(self._dtr_cb)

        self._rts_cb = QCheckBox("RTS")
        self._rts_cb.setChecked(True)
        sig_layout.addWidget(self._rts_cb)

        sig_group.setLayout(sig_layout)
        layout.addWidget(sig_group)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self) -> dict:
        """Return the configuration as a dict."""
        return {
            "port": self._port_combo.currentData(),
            "baudrate": int(self._baud_combo.currentText()),
            "bytesize": int(self._data_bits_combo.currentText()),
            "stopbits": STOP_BITS[self._stop_bits_combo.currentText()],
            "parity": PARITY[self._parity_combo.currentText()],
            "flow_control": FLOW_CONTROL[self._flow_combo.currentText()],
            "dtr": self._dtr_cb.isChecked(),
            "rts": self._rts_cb.isChecked(),
        }
