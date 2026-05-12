"""Status bar - connection state, counters, and lightweight guidance."""

from PySide6.QtWidgets import QLabel, QStatusBar


class StatusBar(QStatusBar):
    """Custom status bar showing connection state and data counters."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._connection_label = QLabel("Disconnected")
        self._connection_label.setStyleSheet("color: #888;")
        self.addWidget(self._connection_label, 1)

        self._port_label = QLabel("")
        self._tx_label = QLabel("TX: 0 B")
        self._rx_label = QLabel("RX: 0 B")
        self._replay_label = QLabel("")

        self.addPermanentWidget(self._port_label)
        self.addPermanentWidget(self._tx_label)
        self.addPermanentWidget(self._rx_label)
        self.addPermanentWidget(self._replay_label)

        self._rx_count = 0
        self._tx_count = 0

    def set_connected(self, port_name: str, settings_str: str) -> None:
        self._connection_label.setText(f"Connected - {settings_str}")
        self._connection_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self._port_label.setText(port_name)
        self._rx_count = 0
        self._tx_count = 0
        self._update_counters()

    def set_disconnected(self) -> None:
        self._connection_label.setText("Disconnected")
        self._connection_label.setStyleSheet("color: #888;")
        self._port_label.setText("")

    def set_error(self, message: str) -> None:
        self._connection_label.setText(message)
        self._connection_label.setStyleSheet("color: #F44336;")
        self.showMessage(message, 5000)

    def set_hint(self, message: str) -> None:
        self.showMessage(message, 4000)

    def add_rx(self, count: int) -> None:
        self._rx_count += count
        self._update_counters()

    def add_tx(self, count: int) -> None:
        self._tx_count += count
        self._update_counters()

    def reset_counters(self) -> None:
        self._rx_count = 0
        self._tx_count = 0
        self._update_counters()

    def set_replay_status(self, current: int, total: int, speed: float, playing: bool) -> None:
        if total <= 0:
            self._replay_label.setText("")
            return
        state = "Playing" if playing else "Ready"
        self._replay_label.setText(f"Replay: {current}/{total} @{speed:.1f}x {state}")

    def clear_replay_status(self) -> None:
        self._replay_label.setText("")

    def _update_counters(self) -> None:
        self._rx_label.setText(f"RX: {self._rx_count:,} B")
        self._tx_label.setText(f"TX: {self._tx_count:,} B")
