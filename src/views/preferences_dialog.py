"""Preferences dialog — application display and behavior settings."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QCheckBox, QGroupBox, QDialogButtonBox, QTabWidget, QWidget,
)


class PreferencesDialog(QDialog):
    """Application preferences dialog with tabbed settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("偏好设置")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # Display tab
        display_tab = QWidget()
        display_layout = QFormLayout()

        self._terminal_mode = QComboBox()
        self._terminal_mode.addItems(["ASCII", "HEX"])
        display_layout.addRow("终端显示模式:", self._terminal_mode)

        self._terminal_font_size = QSpinBox()
        self._terminal_font_size.setRange(8, 24)
        self._terminal_font_size.setValue(10)
        display_layout.addRow("字体大小:", self._terminal_font_size)

        self._dump_bytes = QSpinBox()
        self._dump_bytes.setRange(4, 64)
        self._dump_bytes.setSingleStep(4)
        self._dump_bytes.setValue(16)
        display_layout.addRow("Dump 每行字节:", self._dump_bytes)

        self._table_max_rows = QSpinBox()
        self._table_max_rows.setRange(100, 50000)
        self._table_max_rows.setSingleStep(1000)
        self._table_max_rows.setValue(5000)
        display_layout.addRow("表格最大行数:", self._table_max_rows)

        display_tab.setLayout(display_layout)
        tabs.addTab(display_tab, "显示")

        # Serial tab
        serial_tab = QWidget()
        serial_layout = QFormLayout()

        self._default_baud = QComboBox()
        self._default_baud.addItems([
            "9600", "19200", "38400", "57600", "115200", "230400", "921600"
        ])
        self._default_baud.setCurrentText("9600")
        serial_layout.addRow("默认波特率:", self._default_baud)

        self._auto_reconnect = QCheckBox("断线自动重连")
        serial_layout.addRow("", self._auto_reconnect)

        self._dtr_on_connect = QCheckBox("连接时置 DTR")
        self._dtr_on_connect.setChecked(True)
        serial_layout.addRow("", self._dtr_on_connect)

        self._rts_on_connect = QCheckBox("连接时置 RTS")
        self._rts_on_connect.setChecked(True)
        serial_layout.addRow("", self._rts_on_connect)

        serial_tab.setLayout(serial_layout)
        tabs.addTab(serial_tab, "串口")

        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
