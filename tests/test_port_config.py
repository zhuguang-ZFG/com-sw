"""Tests for PortConfig model."""

import pytest

from src.models.port_config import PortConfig


class TestPortConfig:
    def test_default(self):
        cfg = PortConfig()
        assert cfg.baudrate == 9600
        assert cfg.bytesize == 8
        assert cfg.parity == "N"
        assert cfg.is_valid is False  # No port specified

    def test_valid_with_port(self):
        cfg = PortConfig(port="COM3")
        assert cfg.is_valid is True

    def test_settings_str(self):
        cfg = PortConfig(port="COM3", baudrate=115200, bytesize=8, stopbits=1, parity="N")
        assert cfg.settings_str == "COM3 115200-8-N-1"

    def test_roundtrip_dict(self):
        cfg = PortConfig(port="COM7", baudrate=921600, parity="E", flow_control="rts")
        d = cfg.to_dict()
        restored = PortConfig.from_dict(d)
        assert restored.port == "COM7"
        assert restored.baudrate == 921600
        assert restored.parity == "E"
        assert restored.flow_control == "rts"
