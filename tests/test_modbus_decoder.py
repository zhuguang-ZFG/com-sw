"""Tests for Modbus stream decoder — accumulation and extraction."""

import pytest
from src.protocol.modbus_rtu import encode_rtu_frame
from src.protocol.modbus_ascii import encode_ascii_frame
from src.protocol.modbus_decoder import (
    ModbusStreamDecoder, AutoDecoder, ModbusTransport,
)


class TestModbusStreamDecoder:
    """Test the stateful stream decoder."""

    def test_feed_complete_rtu_frame(self):
        decoder = ModbusStreamDecoder(ModbusTransport.RTU)
        raw = encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        frames = decoder.feed(raw)
        assert len(frames) == 1
        assert frames[0].slave_id == 1
        assert frames[0].function_code == 0x03

    def test_feed_fragmented_rtu(self):
        """Data arriving in pieces should eventually produce a frame."""
        decoder = ModbusStreamDecoder(ModbusTransport.RTU)
        raw = encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))

        # Feed first 3 bytes
        frames = decoder.feed(raw[:3])
        assert len(frames) == 0  # Not enough data yet

        # Feed rest
        frames = decoder.feed(raw[3:])
        assert len(frames) == 1

    def test_ascii_feed(self):
        decoder = ModbusStreamDecoder(ModbusTransport.ASCII)
        raw = encode_ascii_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        frames = decoder.feed(raw)
        assert len(frames) == 1
        assert frames[0].function_code == 0x03

    def test_reset(self):
        decoder = ModbusStreamDecoder(ModbusTransport.RTU)
        decoder.feed(b"\x01\x03")
        decoder.reset()
        raw = encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        assert len(decoder.feed(raw)) == 1


class TestAutoDecoder:
    """Test the auto-detecting decoder."""

    def test_auto_rtu(self):
        decoder = AutoDecoder()
        raw = encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        transport, frames = decoder.feed(raw)
        assert transport == ModbusTransport.RTU
        assert len(frames) == 1

    def test_auto_ascii(self):
        decoder = AutoDecoder()
        raw = encode_ascii_frame(0x01, 0x03, bytes.fromhex("00 00 00 0A"))
        transport, frames = decoder.feed(raw)
        assert transport == ModbusTransport.ASCII
        assert len(frames) == 1
