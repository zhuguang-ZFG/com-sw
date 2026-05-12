"""Serial port reader — dedicated QThread for non-blocking reads.

Runs in a background thread, reads raw bytes from the serial port,
and appends DataPacket objects to the ring buffer.
"""

import logging
from typing import Optional

import serial
from PySide6.QtCore import QThread

from src.models.data_packet import DataPacket, Direction
from src.serial.ring_buffer import RingBuffer

logger = logging.getLogger(__name__)


class SerialReader(QThread):
    """Dedicated QThread for continuous serial port reading.

    Reads data in a loop, creating DataPacket objects for each chunk,
    and appending them to the shared RingBuffer.
    """

    # Chunk size for each read operation
    READ_CHUNK_SIZE = 4096

    def __init__(self, ser: serial.Serial, ring_buffer: RingBuffer, parent=None):
        super().__init__(parent)
        self._serial = ser
        self._ring_buffer = ring_buffer
        self._stop_flag = False

    def run(self) -> None:
        """Main thread loop: read from serial port until stopped."""
        logger.debug(f"Serial reader started for {self._serial.port}")
        error_count = 0

        while not self._stop_flag:
            try:
                if self._serial.is_open and self._serial.in_waiting > 0:
                    data = self._serial.read(self._serial.in_waiting)
                    if data:
                        packet = DataPacket(
                            data=data,
                            direction=Direction.RX,
                            port_name=self._serial.port,
                        )
                        self._ring_buffer.append(packet)
                        error_count = 0
                else:
                    # Sleep briefly when idle to prevent busy-waiting
                    self.msleep(5)
            except serial.SerialException as e:
                error_count += 1
                logger.error(f"Serial read error ({error_count}): {e}")
                if error_count >= 3:
                    # Too many consecutive errors, likely device removed
                    logger.warning("Too many read errors, stopping reader")
                    break
                self.msleep(100)
            except Exception as e:
                logger.exception(f"Unexpected error in serial reader: {e}")
                break

        logger.debug(f"Serial reader stopped for {self._serial.port}")

    def stop(self) -> None:
        """Signal the thread to stop. Does not wait for completion."""
        self._stop_flag = True
