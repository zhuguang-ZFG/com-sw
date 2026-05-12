"""Tests for formatters — display formatting utilities."""

import pytest
from datetime import datetime

from src.utils.formatters import (
    format_hex,
    format_ascii,
    format_timestamp,
    format_terminal_line,
    format_dump_line,
    format_table_row,
    format_csv_row,
    hex_to_bytes,
)
from src.models.data_packet import DataPacket, Direction


class TestFormatHex:
    def test_basic(self):
        assert format_hex(b"\x00\xFF\xAB") == "00 FF AB"

    def test_custom_separator(self):
        assert format_hex(b"\x00\xFF", sep="") == "00FF"

    def test_empty(self):
        assert format_hex(b"") == ""


class TestFormatAscii:
    def test_printable(self):
        assert format_ascii(b"Hello") == "Hello"

    def test_non_printable(self):
        assert format_ascii(b"\x00\x01\x1F\x7F") == "...."

    def test_mixed(self):
        assert format_ascii(b"A\x00B") == "A.B"


class TestFormatTimestamp:
    def test_time_only(self):
        dt = datetime(2025, 6, 20, 14, 30, 45, 123456)
        assert format_timestamp(dt, "time_only") == "14:30:45.123"

    def test_datetime(self):
        dt = datetime(2025, 6, 20, 14, 30, 45, 123456)
        result = format_timestamp(dt, "datetime")
        assert "2025-06-20" in result
        assert "14:30:45.123" in result


class TestFormatTerminalLine:
    def test_ascii_mode(self):
        packet = DataPacket(
            data=b"AT\r\n",
            direction=Direction.RX,
            timestamp=datetime(2025, 6, 20, 14, 30, 45, 0),
        )
        line = format_terminal_line(packet, display_mode="ascii")
        assert "[14:30:45.000]" in line
        assert "[RX]" in line
        assert "AT." in line

    def test_hex_mode(self):
        packet = DataPacket(
            data=b"\x01\x02",
            direction=Direction.TX,
            timestamp=datetime(2025, 6, 20, 14, 30, 45, 0),
        )
        line = format_terminal_line(packet, display_mode="hex")
        assert "01 02" in line
        assert "[TX]" in line

    def test_no_timestamp(self):
        packet = DataPacket(data=b"OK", direction=Direction.RX)
        line = format_terminal_line(packet, show_timestamp=False)
        # Direction bracket still present, but no timestamp bracket
        assert "[14:" not in line  # No timestamp
        assert "OK" in line


class TestFormatDumpLine:
    def test_full_line(self):
        data = b"Hello World\x00\x00\x00\x00\x00"
        line = format_dump_line(data, offset=0x0000)
        # Should have offset, hex, and ASCII sidebar
        assert "00000000" in line
        assert "48 65 6C 6C 6F" in line  # Hello
        assert "|Hello World.....|" in line

    def test_partial_line(self):
        data = b"AB"
        line = format_dump_line(data, offset=0x0010, bytes_per_line=16)
        assert "00000010" in line
        assert "41 42" in line  # A B
        # Remaining should be spaces, followed by ASCII sidebar
        assert "|AB" in line

    def test_eight_byte_split(self):
        """8-byte boundary should have extra space."""
        data = b"\x00" * 16
        line = format_dump_line(data, offset=0)
        # Find the double space between byte groups
        hex_part = line.split("  |")[0]
        # Bytes 0-7 and 8-15 should be separated by extra space
        assert "   " in hex_part  # At least one extra space between groups


class TestFormatTableRow:
    def test_basic(self):
        packet = DataPacket(
            data=b"Test",
            direction=Direction.RX,
            timestamp=datetime(2025, 6, 20, 14, 30, 45, 0),
        )
        row = format_table_row(packet, display_mode="ascii")
        assert row["timestamp"] == "14:30:45.000"
        assert row["direction"] == "RX"
        assert row["length"] == "4"
        assert row["data"] == "Test"


class TestFormatCsvRow:
    def test_basic(self):
        packet = DataPacket(
            data=b"Hello",
            direction=Direction.RX,
            timestamp=datetime(2025, 6, 20, 14, 30, 45, 0),
        )
        csv = format_csv_row(packet, display_mode="ascii")
        assert "2025-06-20" in csv
        assert "RX" in csv
        assert "Hello" in csv

    def test_comma_escaping(self):
        packet = DataPacket(data=b'a,b', direction=Direction.RX)
        csv = format_csv_row(packet, display_mode="ascii")
        # Comma in data should be enclosed in quotes
        assert csv.count(",") >= 2  # At least timestamp,direction,data
        assert '"a,b"' in csv or csv.endswith(',"a,b"')


class TestHexToBytes:
    def test_with_spaces(self):
        assert hex_to_bytes("00 FF AB") == b"\x00\xFF\xAB"

    def test_without_spaces(self):
        assert hex_to_bytes("00FFAB") == b"\x00\xFF\xAB"

    def test_invalid(self):
        assert hex_to_bytes("not hex") is None
        assert hex_to_bytes("G1") is None

    def test_odd_length(self):
        assert hex_to_bytes("0") is None
