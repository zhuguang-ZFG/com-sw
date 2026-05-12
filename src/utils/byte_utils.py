"""Byte manipulation utilities."""


def int_to_bytes(value: int, length: int, byteorder: str = "big") -> bytes:
    """Convert an integer to a fixed-length bytes object."""
    return value.to_bytes(length, byteorder)


def bytes_to_int(data: bytes, byteorder: str = "big") -> int:
    """Convert bytes to an integer."""
    return int.from_bytes(data, byteorder)


def split_bytes(data: bytes, chunk_size: int) -> list:
    """Split bytes into fixed-size chunks."""
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


def xor_checksum(data: bytes) -> int:
    """Compute XOR checksum of bytes."""
    result = 0
    for b in data:
        result ^= b
    return result


def crc16_modbus(data: bytes) -> int:
    """Compute Modbus CRC16 (polynomial 0xA001, init 0xFFFF).

    This is the standard CRC used in Modbus RTU mode.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def lrc(data: bytes) -> int:
    """Compute LRC (Longitudinal Redundancy Check) for Modbus ASCII mode.

    LRC is the 8-bit two's complement of the sum of all bytes.
    """
    total = sum(data) & 0xFF
    return (-total) & 0xFF
