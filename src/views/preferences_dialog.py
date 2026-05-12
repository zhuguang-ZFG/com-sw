"""Preferences dialog - application display and behavior settings."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class PreferencesDialog(QDialog):
    """Application preferences dialog with tabbed settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        display_tab = QWidget()
        display_layout = QFormLayout()

        self._terminal_mode = QComboBox()
        self._terminal_mode.addItems(["ASCII", "HEX"])
        self._terminal_mode.currentTextChanged.connect(self._update_summary)
        display_layout.addRow("Terminal mode:", self._terminal_mode)

        self._terminal_font_size = QSpinBox()
        self._terminal_font_size.setRange(8, 24)
        self._terminal_font_size.setValue(10)
        self._terminal_font_size.valueChanged.connect(self._update_summary)
        display_layout.addRow("Font size:", self._terminal_font_size)

        self._dump_bytes = QSpinBox()
        self._dump_bytes.setRange(4, 64)
        self._dump_bytes.setSingleStep(4)
        self._dump_bytes.setValue(16)
        self._dump_bytes.valueChanged.connect(self._update_summary)
        display_layout.addRow("Dump bytes per line:", self._dump_bytes)

        self._table_max_rows = QSpinBox()
        self._table_max_rows.setRange(100, 50000)
        self._table_max_rows.setSingleStep(1000)
        self._table_max_rows.setValue(5000)
        self._table_max_rows.valueChanged.connect(self._update_summary)
        display_layout.addRow("Table max rows:", self._table_max_rows)

        display_tab.setLayout(display_layout)
        tabs.addTab(display_tab, "Display")

        serial_tab = QWidget()
        serial_layout = QFormLayout()

        self._default_baud = QComboBox()
        self._default_baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "921600"])
        self._default_baud.setCurrentText("9600")
        self._default_baud.currentTextChanged.connect(self._update_summary)
        serial_layout.addRow("Default baud:", self._default_baud)

        self._auto_reconnect = QCheckBox("Auto reconnect after disconnect")
        self._auto_reconnect.stateChanged.connect(self._update_summary)
        serial_layout.addRow("", self._auto_reconnect)

        self._dtr_on_connect = QCheckBox("Assert DTR on connect")
        self._dtr_on_connect.setChecked(True)
        self._dtr_on_connect.stateChanged.connect(self._update_summary)
        serial_layout.addRow("", self._dtr_on_connect)

        self._rts_on_connect = QCheckBox("Assert RTS on connect")
        self._rts_on_connect.setChecked(True)
        self._rts_on_connect.stateChanged.connect(self._update_summary)
        serial_layout.addRow("", self._rts_on_connect)

        serial_tab.setLayout(serial_layout)
        tabs.addTab(serial_tab, "Serial")

        layout.addWidget(tabs)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #888;")
        layout.addWidget(self._summary_label)

        self._status_label = QLabel("Changes apply when the app starts using these settings.")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_summary()

    def _update_summary(self, *_args) -> None:
        self._summary_label.setText(
            f"Terminal: {self._terminal_mode.currentText()}, {self._terminal_font_size.value()} pt. "
            f"Dump: {self._dump_bytes.value()} bytes/line. "
            f"Table: {self._table_max_rows.value()} max rows. "
            f"Default baud: {self._default_baud.currentText()}."
        )

    def get_preferences(self) -> dict:
        return {
            "display": {
                "terminal_mode": self._terminal_mode.currentText().lower(),
                "terminal_font_size": self._terminal_font_size.value(),
                "dump_bytes_per_line": self._dump_bytes.value(),
                "table_max_rows": self._table_max_rows.value(),
            },
            "port": {
                "default_baudrate": int(self._default_baud.currentText()),
                "auto_reconnect": self._auto_reconnect.isChecked(),
                "dtr_on_connect": self._dtr_on_connect.isChecked(),
                "rts_on_connect": self._rts_on_connect.isChecked(),
            },
        }

    def set_preferences(self, config: dict) -> None:
        display = config.get("display", {})
        port = config.get("port", {})
        self._terminal_mode.setCurrentText(display.get("terminal_mode", "ascii").upper())
        self._terminal_font_size.setValue(display.get("terminal_font_size", 10))
        self._dump_bytes.setValue(display.get("dump_bytes_per_line", 16))
        self._table_max_rows.setValue(display.get("table_max_rows", 5000))
        self._default_baud.setCurrentText(str(port.get("default_baudrate", port.get("last_baudrate", 9600))))
        self._auto_reconnect.setChecked(port.get("auto_reconnect", False))
        self._dtr_on_connect.setChecked(port.get("dtr_on_connect", True))
        self._rts_on_connect.setChecked(port.get("rts_on_connect", True))
        self._update_summary()
