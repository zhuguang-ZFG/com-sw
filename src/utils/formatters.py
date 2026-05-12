"""Formatting utilities for serial data display.

Provides consistent formatting across all views:
- Terminal: HEX/ASCII with timestamps
- Dump: Address-offset + HEX + ASCII sidebar
- Table: CSV-style rows
- Line: Plain text lines
"""

from datetime import datetime
from typing import List, Optional

from src.models.data_packet import DataPacket


def format_hex(data: bytes, sep: str = " ") -> str:
    """Format bytes as uppercase hex string. e.g., '00 FF AB'."""
    if sep:
        return data.hex(sep).upper()
    return data.hex().upper()


def format_ascii(data: bytes) -> str:
    """Convert bytes to readable ASCII, replacing non-printables with '.'."""
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def format_timestamp(dt: datetime, mode: str = "time_only") -> str:
    """Format a datetime for display.

    Args:
        dt: The datetime to format.
        mode: 'time_only', 'datetime', or 'delta'
    """
    if mode == "time_only":
        return dt.strftime("%H:%M:%S.%f")[:-3]
    elif mode == "datetime":
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif mode == "delta":
        return dt.strftime("%H:%M:%S")
    return dt.strftime("%H:%M:%S.%f")[:-3]


def format_terminal_line(
    packet: DataPacket,
    display_mode: str = "ascii",
    show_timestamp: bool = True,
    show_direction: bool = True,
) -> str:
    """Format a single DataPacket for terminal view display.

    Args:
        packet: The data packet to format.
        display_mode: 'ascii' or 'hex'.
        show_timestamp: Prefix with timestamp.
        show_direction: Prefix with RX/TX direction.

    Returns:
        A single formatted line string.
    """
    parts = []

    if show_timestamp:
        parts.append(f"[{format_timestamp(packet.timestamp)}]")

    if show_direction:
        parts.append(f"[{packet.direction.value}]")

    if display_mode == "hex":
        parts.append(format_hex(packet.data))
    else:
        parts.append(format_ascii(packet.data))

    return " ".join(parts)


def format_dump_line(
    data: bytes,
    offset: int,
    bytes_per_line: int = 16,
    show_offset: bool = True,
    show_ascii: bool = True,
) -> str:
    """Format a single line of a hex dump (like xxd or HxD).

    Args:
        data: Up to bytes_per_line bytes.
        offset: The file/stream offset for this line.
        bytes_per_line: Number of hex bytes per line.
        show_offset: Include the address offset column.
        show_ascii: Include the ASCII sidebar.

    Returns:
        Formatted dump line, e.g.:
        '00000000  48 65 6C 6C 6F 20 57 6F 72 6C 64 00 00 00 00 00  |Hello World.....|'
    """
    parts = []

    if show_offset:
        parts.append(f"{offset:08X}  ")

    # Hex column
    hex_parts = []
    for i in range(bytes_per_line):
        if i < len(data):
            hex_parts.append(f"{data[i]:02X}")
        else:
            hex_parts.append("  ")
        if i == 7:  # Extra space between 8-byte groups
            hex_parts.append(" ")
    parts.append(" ".join(hex_parts))

    if show_ascii:
        ascii_str = format_ascii(data)
        padding = " " * (bytes_per_line - len(data))
        parts.append(f"  |{ascii_str}{padding}|")

    return "".join(parts)


def format_table_row(
    packet: DataPacket,
    display_mode: str = "ascii",
) -> dict:
    """Convert a DataPacket to a dict suitable for table view columns.

    Returns a dict with keys: timestamp, direction, length, data.
    """
    return {
        "timestamp": format_timestamp(packet.timestamp, mode="time_only"),
        "direction": packet.direction.value,
        "length": str(packet.length),
        "data": format_hex(packet.data) if display_mode == "hex" else format_ascii(packet.data),
    }


def format_csv_row(packet: DataPacket, display_mode: str = "ascii") -> str:
    """Format a single DataPacket as a CSV line for export.

    Columns: timestamp, direction, data
    """
    ts = format_timestamp(packet.timestamp, mode="datetime")
    direction = packet.direction.value
    data_str = format_hex(packet.data) if display_mode == "hex" else format_ascii(packet.data)
    # Escape commas and quotes in data
    data_str = data_str.replace('"', '""')
    return f'{ts},{direction},"{data_str}"'


def hex_to_bytes(hex_str: str) -> Optional[bytes]:
    """Convert a hex string (e.g., '00 FF AB' or '00FFAB') to bytes.

    Returns None if the string is not valid hex.
    """
    try:
        cleaned = hex_str.replace(" ", "").replace("\n", "").replace("\r", "")
        if len(cleaned) % 2 != 0:
            return None
        return bytes.fromhex(cleaned)
    except ValueError:
        return None
