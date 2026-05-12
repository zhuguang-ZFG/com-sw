"""Modbus protocol auto-detection and routing.

Given a raw byte stream from the serial port (or network),
attempts to detect whether it's RTU, ASCII, or TCP and
decode accordingly.
"""

from enum import Enum
from typing import Optional, List, Tuple

from src.protocol.modbus_rtu import (
    decode_rtu_frame, try_extract_rtu_frame, ModbusFrame,
)
from src.protocol.modbus_ascii import (
    decode_ascii_frame, try_extract_ascii_frame,
)
from src.protocol.modbus_tcp import decode_tcp_frame


class ModbusTransport(Enum):
    RTU = "rtu"
    ASCII = "ascii"
    TCP = "tcp"


class ModbusStreamDecoder:
    """Stateful decoder for a single Modbus byte stream.

    Accumulates bytes and attempts to extract complete frames
    using the configured transport mode.
    """

    def __init__(self, transport: ModbusTransport = ModbusTransport.RTU):
        self._transport = transport
        self._buffer = b""

    def feed(self, data: bytes) -> List[ModbusFrame]:
        """Feed bytes into the decoder. Returns any complete frames found."""
        self._buffer += data
        frames = []

        while True:
            if self._transport == ModbusTransport.ASCII:
                frame, remaining = try_extract_ascii_frame(self._buffer)
            elif self._transport == ModbusTransport.TCP:
                # Extract TCP frame
                frame = decode_tcp_frame(self._buffer)
                if frame is not None:
                    remaining = self._buffer[len(frame.raw):]
                else:
                    remaining = self._buffer
                    break
            else:
                frame, remaining = try_extract_rtu_frame(self._buffer)

            if frame is not None:
                frames.append(frame)
                self._buffer = remaining
            else:
                break

        # Prevent buffer from growing indefinitely
        if len(self._buffer) > 4096:
            # Discard oldest data
            self._buffer = self._buffer[-2048:]

        return frames

    def reset(self) -> None:
        """Clear the internal buffer."""
        self._buffer = b""

    @property
    def transport(self) -> ModbusTransport:
        return self._transport

    @transport.setter
    def transport(self, t: ModbusTransport) -> None:
        self._transport = t
        self._buffer = b""  # Clear buffer on transport change


class AutoDecoder:
    """Attempts to auto-detect the Modbus transport and decode frames."""

    def __init__(self):
        self._decoders = {
            ModbusTransport.RTU: ModbusStreamDecoder(ModbusTransport.RTU),
            ModbusTransport.ASCII: ModbusStreamDecoder(ModbusTransport.ASCII),
        }

    def feed(self, data: bytes) -> Tuple[Optional[ModbusTransport], List[ModbusFrame]]:
        """Feed data through all decoders. Returns the winning transport and frames.

        Simple heuristic: the first decoder to produce valid frames wins.
        """
        for transport, decoder in self._decoders.items():
            frames = decoder.feed(data)
            if frames:
                return transport, frames
        return None, []

    def reset(self) -> None:
        for decoder in self._decoders.values():
            decoder.reset()
