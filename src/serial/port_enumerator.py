"""COM port enumeration with hot-plug detection.

Periodically polls for port changes and emits signals when
ports are added or removed.
"""

import logging
from typing import List

import serial.tools.list_ports
from PySide6.QtCore import QTimer, QObject, Signal

logger = logging.getLogger(__name__)


class PortEnumerator(QObject):
    """Enumerate available serial ports with hot-plug detection.

    Uses a QTimer to poll for port changes at a configurable interval.
    Emits signals on port arrival/removal.
    """

    ports_changed = Signal(list)  # Full port list
    port_added = Signal(str)       # Single port name
    port_removed = Signal(str)     # Single port name

    def __init__(self, poll_interval_ms: int = 2000, parent=None):
        super().__init__(parent)
        self._poll_interval = poll_interval_ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._known_ports: set = set()

    def start(self) -> None:
        """Begin periodic polling for port changes."""
        self._known_ports = set(self.list_ports())
        self._timer.start(self._poll_interval)
        logger.debug(f"Port enumerator started (interval={self._poll_interval}ms)")

    def stop(self) -> None:
        """Stop periodic polling."""
        self._timer.stop()
        logger.debug("Port enumerator stopped")

    def _poll(self) -> None:
        """Check for port changes and emit signals."""
        current = set(self.list_ports())
        if current != self._known_ports:
            added = current - self._known_ports
            removed = self._known_ports - current
            for port in added:
                logger.info(f"Port added: {port}")
                self.port_added.emit(port)
            for port in removed:
                logger.info(f"Port removed: {port}")
                self.port_removed.emit(port)
            self._known_ports = current
            self.ports_changed.emit(sorted(current))

    @staticmethod
    def list_ports() -> List[str]:
        """Return a list of available COM port device names."""
        ports = serial.tools.list_ports.comports()
        return sorted([p.device for p in ports])

    @staticmethod
    def get_port_info(port_name: str) -> dict:
        """Get detailed information about a specific port.

        Returns a dict with keys: device, description, hwid, manufacturer,
        product, serial_number, vid, pid.
        """
        for p in serial.tools.list_ports.comports():
            if p.device == port_name:
                return {
                    "device": p.device,
                    "description": p.description,
                    "hwid": p.hwid,
                    "manufacturer": p.manufacturer,
                    "product": p.product,
                    "serial_number": p.serial_number,
                    "vid": f"0x{p.vid:04X}" if p.vid else "",
                    "pid": f"0x{p.pid:04X}" if p.pid else "",
                }
        return {"device": port_name, "description": "", "hwid": ""}
