"""AppController — the central orchestrator.

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

        # Wire everything
        self._wire_signals()

        # Initial port scan
        self._port_enumerator.start()
        ports = PortEnumerator.list_ports()
        self.main_window.update_port_list(ports)

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
            QMessageBox.warning(self.main_window, "提示", "请选择串口")
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

        # Save last port
        self._config.set("port", "last_port", port_name)
        self._config.set("port", "last_baudrate", config.baudrate if config else 9600)

    def _on_port_disconnected(self, port_name: str) -> None:
        """Port closed."""
        self._is_connected = False
        self.main_window.status_bar.set_disconnected()
        self.main_window.set_connected_ui(False)

    def _on_port_error(self, message: str) -> None:
        """Port error occurred."""
        self.main_window.status_bar.set_error(message)

    # ---- Data Flow ----------------------------------------------------------------

    def _on_data_received(self, packets: List[DataPacket]) -> None:
        """Data pumped from the ring buffer — route to all views."""
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

    # ---- Export -------------------------------------------------------------------

    def _on_modbus_send(self, slave_id: int, func_code: int, data: bytes) -> None:
        """Handle Modbus master request from the Modbus panel."""
        if not self._is_connected:
            QMessageBox.warning(self.main_window, "提示", "请先连接串口")
            return
        # The Modbus panel formats the full frame
        self._port_manager.send(data)

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
