"""Serial port manager — open, close, configure, and monitor ports.

Manages the lifecycle of a serial connection and the associated
SerialReader QThread.
"""

import logging
from typing import Optional

import serial
from PySide6.QtCore import QObject, Signal

from src.models.data_packet import DataPacket, Direction
from src.models.port_config import PortConfig
from src.serial.ring_buffer import RingBuffer
from src.serial.serial_reader import SerialReader

logger = logging.getLogger(__name__)


class PortManager(QObject):
    """Manages a single open serial port and its reader thread.

    Emits signals for connection state changes and data events.
    """

    # Connection state
    connected = Signal(str)       # Port name
    disconnected = Signal(str)    # Port name
    error_occurred = Signal(str)  # Error message

    def __init__(self, ring_buffer: RingBuffer, parent=None):
        super().__init__(parent)
        self._ring_buffer = ring_buffer
        self._serial: Optional[serial.Serial] = None
        self._reader: Optional[SerialReader] = None
        self._config: Optional[PortConfig] = None
        self._is_open = False

    def open(self, config: PortConfig) -> bool:
        """Open a serial port with the given configuration.

        Returns True on success, False on failure.
        Emits connected() or error_occurred().
        """
        if self._is_open:
            self.close()

        self._config = config

        try:
            self._serial = serial.Serial(
                port=config.port,
                baudrate=config.baudrate,
                bytesize=config.bytesize,
                parity=config.parity,
                stopbits=config.stopbits,
                timeout=config.timeout,
                rtscts=(config.flow_control == "rts"),
                dsrdtr=(config.flow_control == "dtr"),
            )

            # Apply DTR/RTS if requested
            if config.dtr:
                self._serial.dtr = True
            if config.rts:
                self._serial.rts = True

            # Start the reader thread
            self._reader = SerialReader(self._serial, self._ring_buffer)
            self._reader.start()

            self._is_open = True
            logger.info(f"Port opened: {config.settings_str}")
            self.connected.emit(config.port)
            return True

        except serial.SerialException as e:
            logger.error(f"Failed to open port {config.port}: {e}")
            self.error_occurred.emit(f"无法打开 {config.port}: {e}")
            self._serial = None
            return False

    def close(self) -> None:
        """Close the serial port and stop the reader thread."""
        if self._reader is not None:
            self._reader.stop()
            self._reader.wait(timeout=2000)
            self._reader = None

        if self._serial is not None and self._serial.is_open:
            port_name = self._serial.port
            try:
                self._serial.close()
            except serial.SerialException:
                pass
            logger.info(f"Port closed: {port_name}")
            self.disconnected.emit(port_name)

        self._is_open = False
        self._serial = None

    def send(self, data: bytes) -> bool:
        """Send data through the open serial port.

        Returns True on success, False on failure.
        The sent data is also appended to the ring buffer as a TX packet.
        """
        if not self._is_open or self._serial is None:
            return False

        try:
            self._serial.write(data)
            # Add transmit data to ring buffer for display
            packet = DataPacket(data=data, direction=Direction.TX)
            self._ring_buffer.append(packet)
            return True
        except serial.SerialException as e:
            logger.error(f"Send error: {e}")
            self.error_occurred.emit(f"发送失败: {e}")
            return False

    def set_dtr(self, state: bool) -> None:
        """Set DTR control line state."""
        if self._serial and self._serial.is_open:
            self._serial.dtr = state

    def set_rts(self, state: bool) -> None:
        """Set RTS control line state."""
        if self._serial and self._serial.is_open:
            self._serial.rts = state

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def config(self) -> Optional[PortConfig]:
        return self._config
