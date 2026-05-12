"""Tests for timed session replay control."""

from datetime import datetime, timedelta

from src.controllers.modbus_analysis import ModbusPairingTracker, analyze_packet
from src.controllers.session_replay_controller import SessionReplayController
from src.models.data_packet import DataPacket, Direction
from src.protocol.modbus_rtu import encode_rtu_frame


def test_replay_load_and_stop() -> None:
    emitted = []
    controller = SessionReplayController(lambda packets: emitted.extend(packets))
    packets = [
        DataPacket(data=b"A", direction=Direction.RX, timestamp=datetime(2025, 1, 1, 12, 0, 0)),
        DataPacket(data=b"B", direction=Direction.TX, timestamp=datetime(2025, 1, 1, 12, 0, 0) + timedelta(milliseconds=50)),
    ]
    controller.load(packets)
    assert controller.is_loaded is True
    assert controller.total_packets == 2
    controller.stop()
    assert controller.current_index == 0
    assert controller.is_playing is False


def test_replay_speed_affects_delay() -> None:
    controller = SessionReplayController(lambda packets: None)
    controller.set_speed(2.0)
    delay = controller._compute_delay_ms(
        datetime(2025, 1, 1, 12, 0, 0),
        datetime(2025, 1, 1, 12, 0, 0) + timedelta(milliseconds=100),
    )
    assert delay == 50


def test_replay_step_advances_progress() -> None:
    emitted = []
    progress = []
    controller = SessionReplayController(lambda packets: emitted.extend(packets))
    controller.progress_changed.connect(lambda current, total, speed: progress.append((current, total, speed)))
    packets = [
        DataPacket(data=b"A", direction=Direction.RX, timestamp=datetime(2025, 1, 1, 12, 0, 0)),
        DataPacket(data=b"B", direction=Direction.TX, timestamp=datetime(2025, 1, 1, 12, 0, 0) + timedelta(milliseconds=20)),
    ]
    controller.load(packets)
    controller.step()
    assert len(emitted) == 1
    assert emitted[0].data == b"A"
    assert controller.current_index == 1
    assert progress[-1][0] == 1


def test_replay_restart_resets_and_plays() -> None:
    emitted = []
    controller = SessionReplayController(lambda packets: emitted.extend(packets))
    packets = [
        DataPacket(data=b"A", direction=Direction.RX, timestamp=datetime(2025, 1, 1, 12, 0, 0)),
    ]
    controller.load(packets)
    controller.step()
    assert controller.current_index == 1
    controller.restart()
    assert len(emitted) >= 2


def test_modbus_analysis_detects_exception_frame() -> None:
    packet = DataPacket(
        data=bytes.fromhex("01 83 02 C0 F1"),
        direction=Direction.RX,
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
    )
    analysis = analyze_packet(packet)
    assert analysis.is_modbus is True
    assert analysis.is_exception is True
    assert "exception=0x02" in analysis.summary


def test_modbus_pairing_tracker_matches_request_response() -> None:
    tracker = ModbusPairingTracker()
    tx = DataPacket(
        data=encode_rtu_frame(0x01, 0x03, bytes.fromhex("00 00 00 02")),
        direction=Direction.TX,
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
    )
    rx = DataPacket(
        data=encode_rtu_frame(0x01, 0x03, bytes.fromhex("04 00 0A 00 14")),
        direction=Direction.RX,
        timestamp=datetime(2025, 1, 1, 12, 0, 0, 250000),
    )
    first = tracker.observe(tx)
    second = tracker.observe(rx)
    assert first.matched is False
    assert second.matched is True
    assert second.latency_ms == 250
    assert "func=0x03" in second.summary
