"""Data packet model — the atomic unit of data flow in the pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Direction(Enum):
    RX = "RX"
    TX = "TX"


@dataclass
class DataPacket:
    """Represents a chunk of serial data with metadata.

    This is the single data type that flows through the entire pipeline:
    SerialReader -> RingBuffer -> DataPump -> Views
    """

    data: bytes
    direction: Direction
    timestamp: datetime = field(default_factory=datetime.now)
    port_name: str = ""

    @property
    def hex_str(self) -> str:
        return self.data.hex(" ").upper()

    @property
    def length(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S.%f")[:-3]
        return f"[{ts}] {self.direction.value} {self.length}B"
