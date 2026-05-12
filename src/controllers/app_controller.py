"""AppController 鈥?the central orchestrator.

Wires together all components:
- PortManager + SerialReader + RingBuffer + DataPump
- ConfigManager
- MainWindow + all views
- Export
- Modbus controller
"""

import logging
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog

from src.controllers.config_manager import ConfigManager
from src.controllers.data_pump import DataPump
from src.controllers.modbus_analysis import ModbusPairingTracker, analyze_packet
from src.controllers.session_replay_controller import SessionReplayController
from src.controllers.session_recorder import SessionRecorder, load_session
from src.models.data_packet import DataPacket
from src.models.port_config import PortConfig
from src.serial.ring_buffer import RingBuffer
from src.serial.port_manager import PortManager
from src.serial.port_enumerator import PortEnumerator
from src.views.main_window import MainWindow
from src.utils.formatters import format_terminal_line, hex_to_bytes, format_csv_row

logger = logging.getLogger(__name__)


class AppController(QObject):
    """Central application controller.

    Owns all model objects and wires signals/slots between them.
    """

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config_manager

        # Model layer
        ring_buf_size = self._config.get("ring_buffer_max_size", default=10000)
        self._ring_buffer = RingBuffer(max_size=ring_buf_size)

        # Serial layer
        self._port_manager = PortManager(self._ring_buffer)
        self._port_enumerator = PortEnumerator(
            poll_interval_ms=self._config.get("hotplug_poll_interval_ms", default=2000)
        )

        # Data pump
        pump_interval = self._config.get("data_pump_interval_ms", default=50)
        self._data_pump = DataPump(self._ring_buffer, interval_ms=pump_interval)

        # UI
        self.main_window = MainWindow()

        # State
        self._is_connected = False
        self._export_file = None
        self._export_format = "txt"
        self._session_recorder = SessionRecorder()
        self._replay_controller = SessionReplayController(self._on_data_received, self)
        self._modbus_pairing = ModbusPairingTracker()

        # Wire everything
        self._wire_signals()

        # Initial port scan
        self._port_enumerator.start()
        ports = PortEnumerator.list_ports()
        self.main_window.update_port_list(ports)
        self._apply_config_to_ui()

        # Restore window geometry
        self._restore_window_state()

    def _wire_signals(self) -> None:
        """Connect all signals and slots."""

        # === Serial layer ===
        self._port_manager.connected.connect(self._on_port_connected)
        self._port_manager.disconnected.connect(self._on_port_disconnected)
        self._port_manager.error_occurred.connect(self._on_port_error)

        # Hot-plug detection
        self._port_enumerator.ports_changed.connect(
            self.main_window.update_port_list
        )

        # === Data pump -> Views ===
        self._data_pump.data_ready.connect(self._on_data_received)

        # === UI controls ===
        self.main_window.connect_button.clicked.connect(self._on_connect_clicked)
        self.main_window.disconnect_button.clicked.connect(self._on_disconnect_clicked)
        self.main_window.config_button.clicked.connect(
            lambda: self.main_window._on_port_config()
        )
        self.main_window.port_config_requested.connect(self._open_port_config_dialog)
        self.main_window.preferences_requested.connect(self._open_preferences_dialog)
        self.main_window.export_requested.connect(self._open_export_dialog)
        self.main_window.start_recording_requested.connect(self._start_recording)
        self.main_window.stop_recording_requested.connect(self._stop_recording)
        self.main_window.replay_requested.connect(self._replay_session)
        self.main_window.replay_play_requested.connect(self._play_replay)
        self.main_window.replay_pause_requested.connect(self._pause_replay)
        self.main_window.replay_stop_requested.connect(self._stop_replay)
        self.main_window.replay_restart_requested.connect(self._restart_replay)
        self.main_window.replay_step_requested.connect(self._step_replay)
        self.main_window.replay_speed_requested.connect(self._set_replay_speed)
        self._replay_controller.finished.connect(self._on_replay_finished)
        self._replay_controller.progress_changed.connect(self._on_replay_progress_changed)

        # Terminal view send
        self.main_window.terminal_view.send_requested.connect(
            self._port_manager.send
        )

        # Modbus panel send
        self.main_window.modbus_panel.send_requested.connect(
            self._on_modbus_send
        )

        # === Window close ===
        self.main_window.destroyed.connect(self._on_shutdown)

    # ---- Connection Management ----------------------------------------------------

    def _on_connect_clicked(self) -> None:
        """User clicked Connect."""
        config = self.main_window.get_selected_port_config()
        if not config.port:
            QMessageBox.warning(self.main_window, "Port Required", "Select a serial port or type a device path before connecting.")
            return

        # Apply preferences from config
        config.baudrate = int(self.main_window.baud_combo.currentText())
        config.bytesize = self._config.get("port", "last_bytesize", default=8)
        config.stopbits = self._config.get("port", "last_stopbits", default=1)
        config.parity = self._config.get("port", "last_parity", default="N")
        config.flow_control = self._config.get("port", "last_flow_control", default="none")
        config.dtr = self._config.get("port", "dtr_on_connect", default=True)
        config.rts = self._config.get("port", "rts_on_connect", default=True)

        if self._port_manager.open(config):
            self._data_pump.start()

    def _on_disconnect_clicked(self) -> None:
        """User clicked Disconnect."""
        self._data_pump.stop()
        self._port_manager.close()

    def _on_port_connected(self, port_name: str) -> None:
        """Port successfully opened."""
        self._is_connected = True
        config = self._port_manager.config
        if config:
            self.main_window.status_bar.set_connected(port_name, config.settings_str)
        self.main_window.set_connected_ui(True)
        self.main_window.status_bar.set_hint(f"Connected to {port_name}.")

        # Save last port
        self._config.set("port", "last_port", port_name)
        self._config.set("port", "last_baudrate", config.baudrate if config else 9600)

    def _on_port_disconnected(self, port_name: str) -> None:
        """Port closed."""
        self._is_connected = False
        self.main_window.status_bar.set_disconnected()
        self.main_window.set_connected_ui(False)
        self.main_window.status_bar.set_hint(f"Disconnected from {port_name}.")

    def _on_port_error(self, message: str) -> None:
        """Port error occurred."""
        self.main_window.status_bar.set_error(message)

    # ---- Data Flow ----------------------------------------------------------------

    def _on_data_received(self, packets: List[DataPacket]) -> None:
        """Data pumped from the ring buffer 鈥?route to all views."""
        if not packets:
            return

        # Route to each view
        self.main_window.terminal_view.append_packets(packets)
        self.main_window.dump_view.append_packets(packets)
        self.main_window.table_view.append_packets(packets)
        self.main_window.line_view.append_packets(packets)

        # Update counters
        for p in packets:
            if p.direction.value == "RX":
                self.main_window.status_bar.add_rx(p.length)
            else:
                self.main_window.status_bar.add_tx(p.length)

        # Export if active
        if self._export_file:
            self._write_export(packets)
        if self._session_recorder.is_recording:
            self._session_recorder.record_packets(packets)
        self._update_modbus_hint(packets)

    # ---- Export -------------------------------------------------------------------

    def _on_modbus_send(self, slave_id: int, func_code: int, data: bytes) -> None:
        """Handle Modbus master request from the Modbus panel."""
        if not self._is_connected:
            QMessageBox.warning(self.main_window, "Not Connected", "Connect to a serial port before sending a Modbus frame.")
            return
        # The Modbus panel formats the full frame
        self._port_manager.send(data)

    def _open_port_config_dialog(self) -> None:
        from src.views.port_config_dialog import PortConfigDialog

        dialog = PortConfigDialog(self.main_window)
        dialog.set_config(self._config.get("port", default={}))
        if dialog.exec():
            config = dialog.get_config()
            self._config.set("port", "last_port", config["port"])
            self._config.set("port", "last_baudrate", config["baudrate"])
            self._config.set("port", "last_bytesize", config["bytesize"])
            self._config.set("port", "last_stopbits", config["stopbits"])
            self._config.set("port", "last_parity", config["parity"])
            self._config.set("port", "last_flow_control", config["flow_control"])
            self._config.set("port", "dtr_on_connect", config["dtr"])
            self._config.set("port", "rts_on_connect", config["rts"])
            self._config.save()
            self.main_window.port_combo.setEditText(config["port"])
            self.main_window.baud_combo.setCurrentText(str(config["baudrate"]))
            self.main_window.status_bar.set_hint("Port settings saved.")

    def _open_preferences_dialog(self) -> None:
        from src.views.preferences_dialog import PreferencesDialog

        dialog = PreferencesDialog(self.main_window)
        dialog.set_preferences(self._config.load())
        if dialog.exec():
            prefs = dialog.get_preferences()
            for key, value in prefs["display"].items():
                self._config.set("display", key, value)
            for key, value in prefs["port"].items():
                self._config.set("port", key, value)
            self._config.save()
            self._apply_config_to_ui()
            self.main_window.status_bar.set_hint("Preferences saved.")

    def _open_export_dialog(self) -> None:
        from src.views.export_dialog import ExportDialog

        dialog = ExportDialog(self.main_window)
        export_config = self._config.get("export", default={})
        export_config = {**export_config, "file_path": self._export_file or ""}
        dialog.set_export_config(export_config)
        if dialog.exec():
            export = dialog.get_export_config()
            self._config.set("export", "format", export["format"])
            self._config.set("export", "include_timestamps", export["include_timestamps"])
            self._config.set("export", "include_direction", export["include_direction"])
            self._config.set("export", "append_mode", export["append_mode"])
            self._config.save()
            self.start_export(export["file_path"], export["format"])
            self.main_window.status_bar.set_hint(f"Exporting to {export['file_path']}")

    def _start_recording(self) -> None:
        suggested = self._config.get("recording", "last_session_file", default="")
        if not suggested:
            suggested = str(Path.home() / "Documents" / "com-sw-session.jsonl")
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Start Session Recording",
            suggested,
            "JSON Lines (*.jsonl)",
        )
        if not file_path:
            return
        self._session_recorder.start(file_path)
        self._config.set("recording", "last_session_file", file_path)
        self._config.save()
        self.main_window.status_bar.set_hint(f"Recording session to {file_path}")

    def _stop_recording(self) -> None:
        if not self._session_recorder.is_recording:
            self.main_window.status_bar.set_hint("No active session recording.")
            return
        file_path = self._session_recorder.file_path
        self._session_recorder.stop()
        self.main_window.status_bar.set_hint(f"Recording saved to {file_path}")

    def _replay_session(self) -> None:
        suggested = self._config.get("recording", "last_session_file", default="")
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Replay Session",
            suggested,
            "JSON Lines (*.jsonl)",
        )
        if not file_path:
            return
        packets = load_session(file_path)
        self._prepare_replay_view()
        self._replay_controller.load(packets)
        self._config.set("recording", "last_session_file", file_path)
        self._config.save()
        self.main_window.status_bar.set_hint(f"Loaded {len(packets)} packet(s) from {file_path}. Use Play Replay to start.")

    def _play_replay(self) -> None:
        if not self._replay_controller.is_loaded:
            self.main_window.status_bar.set_hint("No replay session loaded.")
            return
        self.main_window.status_bar.set_hint(
            f"Replay started at {self._replay_controller.speed:.1f}x speed."
        )
        self._replay_controller.play()

    def _pause_replay(self) -> None:
        if not self._replay_controller.is_playing:
            self.main_window.status_bar.set_hint("Replay is not currently playing.")
            return
        self._replay_controller.pause()
        self.main_window.status_bar.set_hint("Replay paused.")

    def _stop_replay(self) -> None:
        if not self._replay_controller.is_loaded:
            self.main_window.status_bar.set_hint("No replay session loaded.")
            return
        self._replay_controller.stop()
        self._prepare_replay_view()
        self.main_window.status_bar.set_hint("Replay stopped and reset.")

    def _restart_replay(self) -> None:
        if not self._replay_controller.is_loaded:
            self.main_window.status_bar.set_hint("No replay session loaded.")
            return
        self._prepare_replay_view()
        self._replay_controller.restart()
        self.main_window.status_bar.set_hint("Replay restarted.")

    def _step_replay(self) -> None:
        if not self._replay_controller.is_loaded:
            self.main_window.status_bar.set_hint("No replay session loaded.")
            return
        self._replay_controller.step()
        self.main_window.status_bar.set_hint("Replay stepped by one packet.")

    def _set_replay_speed(self, speed: float) -> None:
        self._replay_controller.set_speed(speed)
        self._config.set("recording", "replay_speed", speed)
        self._config.save()
        self.main_window.status_bar.set_hint(f"Replay speed set to {speed:.1f}x.")

    def _on_replay_finished(self) -> None:
        self.main_window.status_bar.set_hint("Replay finished.")

    def _on_replay_progress_changed(self, current: int, total: int, speed: float) -> None:
        self.main_window.status_bar.set_replay_status(
            current,
            total,
            speed,
            self._replay_controller.is_playing,
        )

    def _prepare_replay_view(self) -> None:
        self.main_window.terminal_view.clear()
        self.main_window.dump_view.clear()
        self.main_window.table_view.clear()
        self.main_window.line_view.clear()
        self.main_window.status_bar.reset_counters()
        self.main_window.status_bar.clear_replay_status()
        self._modbus_pairing.reset()

    def _update_modbus_hint(self, packets: List[DataPacket]) -> None:
        for packet in reversed(packets):
            pairing = self._modbus_pairing.observe(packet)
            if pairing.matched:
                if pairing.is_exception:
                    self.main_window.status_bar.set_hint(f"Modbus response exception: {pairing.summary}")
                else:
                    self.main_window.status_bar.set_hint(pairing.summary)
                return
            analysis = analyze_packet(packet)
            if not analysis.is_modbus:
                continue
            if analysis.is_exception:
                self.main_window.status_bar.set_hint(f"Modbus exception detected: {analysis.summary}")
            elif self._replay_controller.is_loaded:
                self.main_window.status_bar.set_hint(analysis.summary)
            return

    def _apply_config_to_ui(self) -> None:
        self._replay_controller.set_speed(
            float(self._config.get("recording", "replay_speed", default=1.0))
        )
        self.main_window.baud_combo.setCurrentText(str(self._config.get("port", "last_baudrate", default=9600)))
        last_port = self._config.get("port", "last_port", default="")
        if last_port:
            self.main_window.port_combo.setEditText(last_port)
        self.main_window.terminal_view.apply_preferences(
            display_mode=self._config.get("display", "terminal_mode", default="ascii"),
            auto_scroll=self._config.get("display", "terminal_auto_scroll", default=True),
            show_timestamp=self._config.get("display", "terminal_show_timestamp", default=True),
            show_direction=self._config.get("display", "terminal_show_direction", default=True),
            font_size=self._config.get("display", "terminal_font_size", default=10),
        )
        self.main_window.table_view.apply_preferences(
            display_mode=self._config.get("display", "table_display_mode", default="ascii"),
            max_rows=self._config.get("display", "table_max_rows", default=5000),
            font_size=self._config.get("display", "terminal_font_size", default=10),
        )
        self.main_window.line_view.apply_preferences(
            display_mode=self._config.get("display", "line_display_mode", default="ascii"),
            max_lines=self._config.get("display", "line_history", default=500),
            font_size=self._config.get("display", "terminal_font_size", default=10),
        )
        self.main_window.dump_view.apply_preferences(
            bytes_per_line=self._config.get("display", "dump_bytes_per_line", default=16),
            show_offset=self._config.get("display", "dump_show_offset", default=True),
            show_ascii=self._config.get("display", "dump_show_ascii", default=True),
            font_size=self._config.get("display", "terminal_font_size", default=10),
        )

    # ---- Export -------------------------------------------------------------------

    def start_export(self, file_path: str, fmt: str = "txt") -> None:
        """Begin exporting data to a file."""
        self._export_file = file_path
        self._export_format = fmt
        mode = self._config.get("export", "append_mode", default=True)
        if mode:
            # Add header for new files
            try:
                if Path(file_path).stat().st_size == 0:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("# COM-SW Export\n")
            except FileNotFoundError:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("# COM-SW Export\n")

    def stop_export(self) -> None:
        """Stop exporting data."""
        self._export_file = None

    @property
    def is_exporting(self) -> bool:
        return self._export_file is not None

    def _write_export(self, packets: List[DataPacket]) -> None:
        """Write packets to the export file."""
        if not self._export_file:
            return
        try:
            with open(self._export_file, "a", encoding="utf-8") as f:
                for p in packets:
                    if self._export_format == "csv":
                        f.write(format_csv_row(p, "ascii") + "\n")
                    else:
                        line = format_terminal_line(
                            p,
                            display_mode="ascii",
                            show_timestamp=self._config.get("export", "include_timestamps", default=True),
                            show_direction=self._config.get("export", "include_direction", default=True),
                        )
                        f.write(line + "\n")
        except Exception as e:
            logger.error(f"Export write error: {e}")

    # ---- Shutdown -----------------------------------------------------------------

    def _on_shutdown(self) -> None:
        """Clean up all resources on application shutdown."""
        self._data_pump.stop()
        self._port_enumerator.stop()
        if self._is_connected:
            self._port_manager.close()
        self._config.set("window", "geometry",
                         bytes(self.main_window.saveGeometry()).hex())
        self._config.save()

    def _restore_window_state(self) -> None:
        """Restore window geometry from config."""
        geom_hex = self._config.get("window", "geometry")
        if geom_hex:
            try:
                geom = bytes.fromhex(geom_hex)
                self.main_window.restoreGeometry(geom)
            except Exception:
                pass

