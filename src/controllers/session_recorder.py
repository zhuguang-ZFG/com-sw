"""Session recording and replay helpers for COM-SW."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from src.models.data_packet import DataPacket, Direction


class SessionRecorder:
    """Append serial packets to a JSONL session file."""

    def __init__(self) -> None:
        self._file_path: Path | None = None

    @property
    def is_recording(self) -> bool:
        return self._file_path is not None

    @property
    def file_path(self) -> str | None:
        return str(self._file_path) if self._file_path else None

    def start(self, file_path: str) -> None:
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def stop(self) -> None:
        self._file_path = None

    def record_packets(self, packets: Iterable[DataPacket]) -> None:
        if not self._file_path:
            return
        with self._file_path.open("a", encoding="utf-8") as handle:
            for packet in packets:
                handle.write(json.dumps(packet_to_record(packet), ensure_ascii=False) + "\n")


def packet_to_record(packet: DataPacket) -> dict:
    return {
        "timestamp": packet.timestamp.isoformat(timespec="milliseconds"),
        "direction": packet.direction.value,
        "data_hex": packet.hex_str,
        "length": packet.length,
        "port_name": packet.port_name,
    }


def record_to_packet(record: dict) -> DataPacket:
    return DataPacket(
        data=bytes.fromhex(record["data_hex"]),
        direction=Direction(record["direction"]),
        timestamp=datetime.fromisoformat(record["timestamp"]),
        port_name=record.get("port_name", ""),
    )


def load_session(file_path: str) -> List[DataPacket]:
    packets: List[DataPacket] = []
    with Path(file_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            packets.append(record_to_packet(json.loads(line)))
    return packets
