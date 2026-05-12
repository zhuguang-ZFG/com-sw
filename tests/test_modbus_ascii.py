"""Tests for Modbus ASCII framing — LRC and encode/decode."""

import pytest
from src.protocol.modbus_ascii import (
    encode_ascii_frame, decode_ascii_frame, try_extract_ascii_frame,
)
from src.utils.byte_utils import lrc


class TestLRC:
    """LRC calculation tests."""

    def test_lrc_known_vector(self):
        # For bytes 0x01, 0x03, 0x00, 0x00, 0x00, 0x0A:
        # Sum = 0x0E, LRC = 0x100 - 0x0E = 0xF2
        data = bytes.fromhex("01 03 00 00 00 0A")
        result = lrc(data)
        assert result == 0xF2


class TestEncodeDecode:
    def test_round_trip(self):
        raw = encode_ascii_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        assert raw.startswith(b":")
        assert raw.endswith(b"\r\n")

        frame = decode_ascii_frame(raw)
        assert frame is not None
        assert frame.slave_id == 1
        assert frame.function_code == 0x03
        assert frame.data == bytes.fromhex("00 00 00 0A")

    def test_invalid_lrc(self):
        raw = b":01030000000A00\r\n"  # Wrong LRC
        frame = decode_ascii_frame(raw)
        assert frame is None

    def test_no_colon(self):
        frame = decode_ascii_frame(b"01030000000A\r\n")
        assert frame is None


class TestTryExtract:
    def test_complete(self):
        buffer = b":01030000000AF2\r\n"
        frame, remaining = try_extract_ascii_frame(buffer)
        assert frame is not None
        assert remaining == b""

    def test_incomplete(self):
        buffer = b":0103000000"  # No CRLF yet
        frame, remaining = try_extract_ascii_frame(buffer)
        assert frame is None
