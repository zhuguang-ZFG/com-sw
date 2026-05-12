"""Status bar — connection status, TX/RX counters, DTR/RTS indicators."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QHBoxLayout


class StatusBar(QStatusBar):
    """Custom status bar showing connection state and data counters."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Connection state label (left side)
        self._connection_label = QLabel("未连接")
        self._connection_label.setStyleSheet("color: #888;")
        self.addWidget(self._connection_label)

        # Permanent widgets (right side)
        self._rx_label = QLabel("RX: 0")
        self._tx_label = QLabel("TX: 0")
        self._port_label = QLabel("")

        self.addPermanentWidget(self._port_label)
        self.addPermanentWidget(self._tx_label)
        self.addPermanentWidget(self._rx_label)

        self._rx_count = 0
        self._tx_count = 0

    def set_connected(self, port_name: str, settings_str: str) -> None:
        """Update status bar to show connected state."""
        self._connection_label.setText(f"已连接: {settings_str}")
        self._connection_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self._port_label.setText(port_name)
        self._rx_count = 0
        self._tx_count = 0
        self._update_counters()

    def set_disconnected(self) -> None:
        """Update status bar to show disconnected state."""
        self._connection_label.setText("未连接")
        self._connection_label.setStyleSheet("color: #888;")
        self._port_label.setText("")

    def set_error(self, message: str) -> None:
        """Show a temporary error message."""
        self._connection_label.setText(message)
        self._connection_label.setStyleSheet("color: #F44336;")
        self.showMessage(message, 5000)

    def add_rx(self, count: int) -> None:
        """Increment RX byte counter."""
        self._rx_count += count
        self._update_counters()

    def add_tx(self, count: int) -> None:
        """Increment TX byte counter."""
        self._tx_count += count
        self._update_counters()

    def _update_counters(self) -> None:
        self._rx_label.setText(f"RX: {self._rx_count}")
        self._tx_label.setText(f"TX: {self._tx_count}")
