"""Port configuration dialog for detailed serial port settings."""

import serial.tools.list_ports
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


BAUD_RATES = [
    "110", "300", "600", "1200", "2400", "4800", "9600",
    "14400", "19200", "38400", "56000", "57600",
    "115200", "230400", "460800", "921600",
]
DATA_BITS = ["5", "6", "7", "8"]
STOP_BITS = {"1": 1, "1.5": 3, "2": 2}
STOP_BITS_DISPLAY = list(STOP_BITS.keys())
PARITY = {"None": "N", "Odd": "O", "Even": "E", "Mark": "M", "Space": "S"}
PARITY_DISPLAY = list(PARITY.keys())
FLOW_CONTROL = {"None": "none", "RTS/CTS": "rts", "DTR/DSR": "dtr", "XON/XOFF": "xon"}


class PortConfigDialog(QDialog):
    """Detailed serial port settings dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Port Settings")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)

        port_group = QGroupBox("Port")
        port_form = QFormLayout()

        self._port_combo = QComboBox()
        self._port_combo.setEditable(False)
        ports = list(serial.tools.list_ports.comports())
        if ports:
            for port in ports:
                self._port_combo.addItem(f"{port.device} - {port.description}", port.device)
        else:
            self._port_combo.addItem("No ports detected", "")
            self._port_combo.setEnabled(False)
        self._port_combo.currentIndexChanged.connect(self._update_status)
        port_form.addRow("Port:", self._port_combo)

        port_group.setLayout(port_form)
        layout.addWidget(port_group)

        comm_group = QGroupBox("Communication")
        comm_form = QFormLayout()

        self._baud_combo = QComboBox()
        self._baud_combo.addItems(BAUD_RATES)
        self._baud_combo.setCurrentText("9600")
        self._baud_combo.currentTextChanged.connect(self._update_summary)
        comm_form.addRow("Baud rate:", self._baud_combo)

        self._data_bits_combo = QComboBox()
        self._data_bits_combo.addItems(DATA_BITS)
        self._data_bits_combo.setCurrentText("8")
        self._data_bits_combo.currentTextChanged.connect(self._update_summary)
        comm_form.addRow("Data bits:", self._data_bits_combo)

        self._stop_bits_combo = QComboBox()
        self._stop_bits_combo.addItems(STOP_BITS_DISPLAY)
        self._stop_bits_combo.setCurrentText("1")
        self._stop_bits_combo.currentTextChanged.connect(self._update_summary)
        comm_form.addRow("Stop bits:", self._stop_bits_combo)

        self._parity_combo = QComboBox()
        self._parity_combo.addItems(PARITY_DISPLAY)
        self._parity_combo.setCurrentText("None")
        self._parity_combo.currentTextChanged.connect(self._update_summary)
        comm_form.addRow("Parity:", self._parity_combo)

        self._flow_combo = QComboBox()
        self._flow_combo.addItems(list(FLOW_CONTROL.keys()))
        self._flow_combo.setCurrentText("None")
        self._flow_combo.currentTextChanged.connect(self._update_summary)
        comm_form.addRow("Flow control:", self._flow_combo)

        comm_group.setLayout(comm_form)
        layout.addWidget(comm_group)

        sig_group = QGroupBox("Control Signals")
        sig_layout = QHBoxLayout()

        self._dtr_cb = QCheckBox("Assert DTR on connect")
        self._dtr_cb.setChecked(True)
        self._dtr_cb.stateChanged.connect(self._update_summary)
        sig_layout.addWidget(self._dtr_cb)

        self._rts_cb = QCheckBox("Assert RTS on connect")
        self._rts_cb.setChecked(True)
        self._rts_cb.stateChanged.connect(self._update_summary)
        sig_layout.addWidget(self._rts_cb)

        sig_group.setLayout(sig_layout)
        layout.addWidget(sig_group)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #888;")
        layout.addWidget(self._summary_label)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._update_summary()
        self._update_status()

    def _update_summary(self, *_args) -> None:
        port_name = self._port_combo.currentData() or "no port"
        self._summary_label.setText(
            f"{port_name} @ {self._baud_combo.currentText()} baud, "
            f"{self._data_bits_combo.currentText()} data bits, "
            f"{self._stop_bits_combo.currentText()} stop bit(s), "
            f"{self._parity_combo.currentText()} parity, "
            f"{self._flow_combo.currentText()} flow control."
        )

    def _update_status(self, *_args) -> None:
        has_port = bool(self._port_combo.currentData())
        if not has_port:
            self._status_label.setText("No serial port is currently available.")
            self._status_label.setStyleSheet("color: #F44336;")
            self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return

        self._status_label.setText("Ready to apply these port settings.")
        self._status_label.setStyleSheet("color: #888;")
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _on_accept(self) -> None:
        if not self._port_combo.currentData():
            self._update_status()
            return
        self.accept()

    def get_config(self) -> dict:
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

    def set_config(self, config: dict) -> None:
        port = config.get("port") or config.get("last_port", "")
        for index in range(self._port_combo.count()):
            if self._port_combo.itemData(index) == port:
                self._port_combo.setCurrentIndex(index)
                break
        self._baud_combo.setCurrentText(str(config.get("baudrate", config.get("last_baudrate", 9600))))
        self._data_bits_combo.setCurrentText(str(config.get("bytesize", config.get("last_bytesize", 8))))
        stopbits = config.get("stopbits", config.get("last_stopbits", 1))
        stopbits_display = next((k for k, v in STOP_BITS.items() if v == stopbits), "1")
        self._stop_bits_combo.setCurrentText(stopbits_display)
        parity = config.get("parity", config.get("last_parity", "N"))
        parity_display = next((k for k, v in PARITY.items() if v == parity), "None")
        self._parity_combo.setCurrentText(parity_display)
        flow = config.get("flow_control", config.get("last_flow_control", "none"))
        flow_display = next((k for k, v in FLOW_CONTROL.items() if v == flow), "None")
        self._flow_combo.setCurrentText(flow_display)
        self._dtr_cb.setChecked(config.get("dtr", config.get("dtr_on_connect", True)))
        self._rts_cb.setChecked(config.get("rts", config.get("rts_on_connect", True)))
        self._update_summary()
        self._update_status()
