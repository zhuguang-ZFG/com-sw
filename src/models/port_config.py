"""Serial port configuration model."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PortConfig:
    """Immutable-ish port configuration for a serial connection."""

    port: str = ""
    baudrate: int = 9600
    bytesize: int = 8
    stopbits: int = 1
    parity: str = "N"
    flow_control: str = "none"
    timeout: float = 0.1

    # Control signals
    dtr: bool = True
    rts: bool = True

    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "stopbits": self.stopbits,
            "parity": self.parity,
            "flow_control": self.flow_control,
            "timeout": self.timeout,
            "dtr": self.dtr,
            "rts": self.rts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PortConfig":
        return cls(
            port=d.get("port", ""),
            baudrate=d.get("baudrate", 9600),
            bytesize=d.get("bytesize", 8),
            stopbits=d.get("stopbits", 1),
            parity=d.get("parity", "N"),
            flow_control=d.get("flow_control", "none"),
            timeout=d.get("timeout", 0.1),
            dtr=d.get("dtr", True),
            rts=d.get("rts", True),
        )

    @property
    def settings_str(self) -> str:
        """Human-readable summary like 'COM3 9600-8-N-1'."""
        parity_map = {"N": "N", "E": "E", "O": "O", "M": "M", "S": "S"}
        p = parity_map.get(self.parity, self.parity)
        return f"{self.port} {self.baudrate}-{self.bytesize}-{p}-{self.stopbits}"

    @property
    def is_valid(self) -> bool:
        return bool(self.port) and self.baudrate > 0
