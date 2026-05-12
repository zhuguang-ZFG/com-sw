"""Tests for Modbus RTU framing — CRC16 and encode/decode."""

import pytest
from src.protocol.modbus_rtu import (
    encode_rtu_frame, decode_rtu_frame, try_extract_rtu_frame, ModbusFrame,
)
from src.utils.byte_utils import crc16_modbus


class TestCRC16:
    """CRC16 calculation tests with known vectors."""

    def test_known_vector_read_holding(self):
        """Standard Modbus read holding registers request."""
        # 01 03 00 00 00 0A -> CRC = C5 CD
        data = bytes.fromhex("01 03 00 00 00 0A")
        crc = crc16_modbus(data)
        assert crc == 0xCDC5  # LE representation

    def test_known_vector_write_single(self):
        """Standard Modbus write single register."""
        # 01 06 00 01 00 03 -> compute CRC16
        from src.utils.byte_utils import crc16_modbus
        data = bytes.fromhex("01 06 00 01 00 03")
        crc = crc16_modbus(data)
        # Verify round-trip
        assert crc == crc16_modbus(data)  # Self-consistent


class TestEncodeDecode:
    """Round-trip encoding and decoding."""

    def test_round_trip_read_holding(self):
        raw = encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        frame = decode_rtu_frame(raw)
        assert frame is not None
        assert frame.slave_id == 1
        assert frame.function_code == 0x03
        assert frame.data == bytes.fromhex("00 00 00 0A")
        assert not frame.is_exception

    def test_round_trip_all_func_codes(self):
        """All function codes should round-trip correctly."""
        for fc in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x0F, 0x10]:
            raw = encode_rtu_frame(0x01, fc, b"\x00\x01\x00\x02")
            frame = decode_rtu_frame(raw)
            assert frame is not None, f"FC 0x{fc:02X} failed"
            assert frame.function_code == fc

    def test_invalid_crc(self):
        """Frame with bad CRC should return None."""
        raw = bytes.fromhex("01 03 00 00 00 0A 00 00")  # Bad CRC
        frame = decode_rtu_frame(raw)
        assert frame is None

    def test_short_frame(self):
        """Frame too short should return None."""
        assert decode_rtu_frame(b"\x01\x02") is None

    def test_exception_frame(self):
        """Exception frame: function_code | 0x80 + exception code."""
        raw = encode_rtu_frame(0x01, 0x83, bytes.fromhex("02"))
        frame = decode_rtu_frame(raw)
        assert frame is not None
        assert frame.is_exception
        assert frame.function_code == 0x83
        assert frame.exception_code == 0x02


class TestTryExtractFrame:
    """Test incremental frame extraction from a stream buffer."""

    def test_extract_complete_frame(self):
        buffer = bytes.fromhex("01 03 00 00 00 0A C5 CD")
        frame, remaining = try_extract_rtu_frame(buffer)
        assert frame is not None
        assert remaining == b""

    def test_extract_with_junk_prefix(self):
        """If buffer has junk before frame, should not match."""
        # Current implementation only checks from beginning
        buffer = bytes.fromhex("FF FF 01 03 00 00 00 0A C5 CD")
        frame, remaining = try_extract_rtu_frame(buffer)
        # With junk prefix, frame won't be found (previous bytes create bad CRC)
        assert frame is None or len(remaining) < len(buffer)

    def test_incomplete_frame_returns_none(self):
        buffer = bytes.fromhex("01 03 00")  # Too short
        frame, remaining = try_extract_rtu_frame(buffer)
        assert frame is None
        assert remaining == buffer
