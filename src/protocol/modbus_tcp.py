"""Modbus TCP protocol — MBAP header + PDU.

TCP framing:
  [TransactionID 2B] [ProtocolID 2B: 0x0000] [Length 2B] [UnitID 1B]
  + [FunctionCode 1B] [Data N B]

Unlike RTU and ASCII, TCP does NOT use CRC/LRC — the TCP layer
provides error detection.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from src.protocol.modbus_rtu import ModbusFrame, EXCEPTION_OFFSET

MBAP_HEADER_LENGTH = 7


def encode_tcp_frame(
    transaction_id: int,
    unit_id: int,
    function_code: int,
    data: bytes,
) -> bytes:
    """Build a complete Modbus TCP frame with MBAP header.

    Args:
        transaction_id: Transaction identifier (0-65535).
        unit_id: Unit/slave identifier.
        function_code: Modbus function code.
        data: PDU data (without function code).

    Returns:
        Complete TCP frame: MBAP(7) + FunctionCode(1) + Data + No CRC
    """
    pdu = bytes([function_code]) + data
    length = len(pdu) + 1  # +1 for unit_id
    header = bytes([
        (transaction_id >> 8) & 0xFF,
        transaction_id & 0xFF,
        0x00, 0x00,  # Protocol ID (always 0)
        (length >> 8) & 0xFF,
        length & 0xFF,
        unit_id,
    ])
    return header + pdu


def decode_tcp_frame(raw: bytes) -> Optional[ModbusFrame]:
    """Decode a raw Modbus TCP frame.

    Returns ModbusFrame if valid, None otherwise.
    """
    if len(raw) < MBAP_HEADER_LENGTH + 1:
        return None

    # Parse MBAP header
    transaction_id = (raw[0] << 8) | raw[1]
    protocol_id = (raw[2] << 8) | raw[3]
    length = (raw[4] << 8) | raw[5]
    unit_id = raw[6]

    if protocol_id != 0:
        return None  # Invalid protocol ID

    expected_length = len(raw) - MBAP_HEADER_LENGTH
    if length != expected_length + 1:
        return None  # Length field mismatch

    pdu = raw[MBAP_HEADER_LENGTH:]
    if len(pdu) < 1:
        return None

    function_code = pdu[0]
    data = pdu[1:]

    is_exception = (function_code & EXCEPTION_OFFSET) != 0
    exception_code = data[0] if is_exception and len(data) >= 1 else 0

    return ModbusFrame(
        slave_id=unit_id,
        function_code=function_code,
        data=data,
        is_exception=is_exception,
        exception_code=exception_code,
        raw=raw,
    )
