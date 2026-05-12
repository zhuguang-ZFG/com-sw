"""Tests for Modbus TCP framing — MBAP header."""

import pytest
from src.protocol.modbus_tcp import encode_tcp_frame, decode_tcp_frame


class TestEncodeDecode:
    def test_round_trip(self):
        raw = encode_tcp_frame(0x0001, 0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        # 7 MBAP + 1 FC + 4 data = 12 bytes
        assert len(raw) == 12

        frame = decode_tcp_frame(raw)
        assert frame is not None
        assert frame.slave_id == 1
        assert frame.function_code == 0x03
        assert frame.data == bytes.fromhex("00 00 00 0A")
        assert not frame.is_exception

    def test_mbap_header(self):
        raw = encode_tcp_frame(0x0001, 0x01, 0x03, b"")
        # Transaction ID: 00 01
        assert raw[0] == 0x00
        assert raw[1] == 0x01
        # Protocol ID: 00 00
        assert raw[2] == 0x00
        assert raw[3] == 0x00
        # Length: 00 02 (1 for unit_id + 1 for function_code)
        assert raw[4] == 0x00
        assert raw[5] == 0x02
        # Unit ID
        assert raw[6] == 0x01

    def test_short_frame(self):
        assert decode_tcp_frame(b"\x00\x01\x00") is None

    def test_bad_protocol_id(self):
        # Construct a frame with non-zero protocol ID
        bad = bytes([0x00, 0x01, 0x00, 0x01, 0x00, 0x02, 0x01, 0x03])
        frame = decode_tcp_frame(bad)
        assert frame is None
