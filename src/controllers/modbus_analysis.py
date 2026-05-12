"""Lightweight Modbus analysis helpers for replay and monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.models.data_packet import DataPacket
from src.protocol.modbus_rtu import decode_rtu_frame


@dataclass
class ModbusAnalysisResult:
    is_modbus: bool
    is_exception: bool = False
    summary: str = ""
    slave_id: int = 0
    function_code: int = 0


@dataclass
class ModbusPairingResult:
    matched: bool
    summary: str = ""
    latency_ms: int = 0
    is_exception: bool = False


def analyze_packet(packet: DataPacket) -> ModbusAnalysisResult:
    frame = decode_rtu_frame(packet.data)
    if frame is None:
        return ModbusAnalysisResult(is_modbus=False)

    function_code = frame.function_code & 0x7F if frame.is_exception else frame.function_code
    summary = f"Modbus RTU slave={frame.slave_id} func=0x{function_code:02X}"
    if frame.is_exception:
        summary += f" exception=0x{frame.exception_code:02X}"
    return ModbusAnalysisResult(
        is_modbus=True,
        is_exception=frame.is_exception,
        summary=summary,
        slave_id=frame.slave_id,
        function_code=function_code,
    )


class ModbusPairingTracker:
    """Track the most recent Modbus TX request and pair a matching RX response."""

    def __init__(self) -> None:
        self._pending_request: Optional[tuple[DataPacket, ModbusAnalysisResult]] = None

    def reset(self) -> None:
        self._pending_request = None

    def observe(self, packet: DataPacket) -> ModbusPairingResult:
        analysis = analyze_packet(packet)
        if not analysis.is_modbus:
            return ModbusPairingResult(matched=False)

        if packet.direction.value == "TX":
            self._pending_request = (packet, analysis)
            return ModbusPairingResult(matched=False)

        if packet.direction.value == "RX" and self._pending_request is not None:
            request_packet, request_analysis = self._pending_request
            if (
                request_analysis.slave_id == analysis.slave_id
                and request_analysis.function_code == analysis.function_code
            ):
                latency_ms = int((packet.timestamp - request_packet.timestamp).total_seconds() * 1000)
                self._pending_request = None
                summary = (
                    f"Modbus pair slave={analysis.slave_id} func=0x{analysis.function_code:02X} "
                    f"latency={latency_ms}ms"
                )
                if analysis.is_exception:
                    summary += " exception"
                return ModbusPairingResult(
                    matched=True,
                    summary=summary,
                    latency_ms=latency_ms,
                    is_exception=analysis.is_exception,
                )

        return ModbusPairingResult(matched=False)
