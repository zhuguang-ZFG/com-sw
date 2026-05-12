"""Modbus ASCII protocol — frame encoding, decoding, and LRC verification.

ASCII framing:
  Start: ':'
  Data: 2 hex chars per byte (uppercase)
  End: CRLF ('\\r\\n')

  [:] [SlaveID 2ch] [FunctionCode 2ch] [Data 2N ch] [LRC 2ch] [CRLF]
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from src.utils.byte_utils import lrc
from src.protocol.modbus_rtu import ModbusFrame, EXCEPTION_OFFSET


def encode_ascii_frame(slave_id: int, function_code: int, data: bytes) -> bytes:
    """Build a complete Modbus ASCII frame.

    Returns bytes in the format: :XX XX XX ... LRC\\r\\n
    """
    adu = bytes([slave_id, function_code]) + data
    lrc_val = lrc(adu)
    full = adu + bytes([lrc_val])
    hex_str = full.hex().upper()
    return (":" + hex_str + "\r\n").encode("ascii")


def decode_ascii_frame(raw: bytes) -> Optional[ModbusFrame]:
    """Decode a raw Modbus ASCII frame.

    Args:
        raw: Raw bytes received from serial port.

    Returns:
        ModbusFrame if the frame is valid, None otherwise.
    """
    # Find start marker
    start_idx = raw.find(b":")
    if start_idx < 0:
        return None

    # Find end marker (CRLF)
    end_idx = raw.find(b"\r\n", start_idx)
    if end_idx < 0:
        return None

    hex_part = raw[start_idx + 1:end_idx]

    # Hex decode
    try:
        binary = bytes.fromhex(hex_part.decode("ascii"))
    except ValueError:
        return None

    if len(binary) < 2:
        return None

    # Verify LRC (last byte)
    adu = binary[:-1]
    expected_lrc = binary[-1]
    computed_lrc = lrc(adu)

    if expected_lrc != computed_lrc:
        return None

    slave_id = adu[0]
    function_code = adu[1]
    data = adu[2:]

    is_exception = (function_code & EXCEPTION_OFFSET) != 0
    exception_code = data[0] if is_exception and len(data) >= 1 else 0

    return ModbusFrame(
        slave_id=slave_id,
        function_code=function_code,
        data=data,
        is_exception=is_exception,
        exception_code=exception_code,
        raw=raw[start_idx:end_idx + 2],
    )


def try_extract_ascii_frame(buffer: bytes) -> Tuple[Optional[ModbusFrame], bytes]:
    """Attempt to extract a complete ASCII frame from a buffer.

    Returns the first valid frame and the remaining buffer data.
    """
    # Find first colon
    start_idx = buffer.find(b":")
    if start_idx < 0:
        return None, buffer  # No start marker yet

    # Discard anything before the start marker
    if start_idx > 0:
        buffer = buffer[start_idx:]

    # Find CRLF
    end_idx = buffer.find(b"\r\n", 1)  # Start searching after ':'
    if end_idx < 0:
        return None, buffer  # Frame not yet complete

    frame_raw = buffer[:end_idx + 2]
    result = decode_ascii_frame(frame_raw)

    if result is not None:
        return result, buffer[end_idx + 2:]

    # Invalid frame — discard the colon and try again
    return None, buffer[1:]
