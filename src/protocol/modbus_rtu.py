"""Modbus RTU protocol — frame encoding, decoding, and CRC16 verification.

RTU framing:
  [SlaveID 1B] [FunctionCode 1B] [Data N B] [CRC16 2B (LE)]

Frame boundaries are detected by 3.5-char time gap in a real RTU network.
In our implementation, we rely on the CRC16 to validate complete frames.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from src.utils.byte_utils import crc16_modbus

# Minimum Modbus RTU frame: Slave(1) + Function(1) + CRC(2) = 4 bytes
MIN_RTU_FRAME_LENGTH = 4

# Modbus exception function code offset
EXCEPTION_OFFSET = 0x80


@dataclass
class ModbusFrame:
    """Decoded Modbus frame."""
    slave_id: int
    function_code: int
    data: bytes          # PDU data (without slave ID and CRC)
    is_exception: bool = False
    exception_code: int = 0
    raw: bytes = b""      # Original raw frame

    @property
    def is_valid(self) -> bool:
        return self.function_code > 0

    @property
    def function_name(self) -> str:
        """Human-readable function name."""
        func_map = {
            0x01: "Read Coils",
            0x02: "Read Discrete Inputs",
            0x03: "Read Holding Registers",
            0x04: "Read Input Registers",
            0x05: "Write Single Coil",
            0x06: "Write Single Register",
            0x0F: "Write Multiple Coils",
            0x10: "Write Multiple Registers",
            0x17: "Read/Write Multiple Registers",
        }
        code = self.function_code & 0x7F
        return func_map.get(code, f"Function {self.function_code:02X}")


def encode_rtu_frame(slave_id: int, function_code: int, data: bytes) -> bytes:
    """Build a complete Modbus RTU frame.

    Args:
        slave_id: Slave address (0-247).
        function_code: Modbus function code.
        data: PDU data (without slave ID).

    Returns:
        Complete RTU frame: slave_id + function_code + data + CRC16_LE.
    """
    adr = bytes([slave_id]) + bytes([function_code]) + data
    crc = crc16_modbus(adr)
    return adr + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def decode_rtu_frame(raw: bytes) -> Optional[ModbusFrame]:
    """Decode a raw byte sequence into a ModbusFrame, verifying CRC.

    Args:
        raw: Raw bytes received from serial port.

    Returns:
        ModbusFrame if the CRC is valid, None otherwise.
    """
    if len(raw) < MIN_RTU_FRAME_LENGTH:
        return None

    # Verify CRC
    adu = raw[:-2]
    expected_crc = raw[-2] | (raw[-1] << 8)  # LE
    computed_crc = crc16_modbus(adu)

    if expected_crc != computed_crc:
        return None  # CRC mismatch

    slave_id = adu[0]
    function_code = adu[1]
    data = adu[2:]

    # Check for exception
    is_exception = (function_code & EXCEPTION_OFFSET) != 0
    exception_code = data[0] if is_exception and len(data) >= 1 else 0

    return ModbusFrame(
        slave_id=slave_id,
        function_code=function_code,
        data=data,
        is_exception=is_exception,
        exception_code=exception_code,
        raw=raw,
    )


def try_extract_rtu_frame(buffer: bytes) -> Tuple[Optional[ModbusFrame], bytes]:
    """Attempt to extract a complete RTU frame from a buffer.

    Tries each possible frame length (from MIN upwards) and checks CRC.
    Returns the first valid frame and the remaining buffer data.

    Args:
        buffer: Accumulated received bytes.

    Returns:
        Tuple of (ModbusFrame or None, remaining_bytes).
    """
    blen = len(buffer)
    if blen < MIN_RTU_FRAME_LENGTH:
        return None, buffer

    # Try to find a valid frame starting from the beginning
    # CRC is 2 bytes, so minimum data is 0 bytes (slave + func = 2B + CRC = 4B)
    for frame_end in range(MIN_RTU_FRAME_LENGTH, blen + 1):
        frame_candidate = buffer[:frame_end]
        result = decode_rtu_frame(frame_candidate)
        if result is not None:
            return result, buffer[frame_end:]

    # No valid CRC found
    if blen > 256:  # Max Modbus RTU frame is 256 bytes
        return None, buffer[1:]  # Discard first byte and retry
    return None, buffer
