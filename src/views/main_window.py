"""Main window - QMainWindow with multi-view serial monitoring layout."""

from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QToolBar,
)

from src.models.port_config import PortConfig
from src.views.dump_view import DumpView
from src.views.diagnostics_view import DiagnosticsView
from src.views.line_view import LineView
from src.views.modbus_analysis_view import ModbusAnalysisView
from src.views.modbus_panel import ModbusPanel
from src.views.status_bar import StatusBar
from src.views.table_view import TableView
from src.views.terminal_view import TerminalView


class MainWindow(QMainWindow):
    """Application main window with multi-view layout."""

    port_config_requested = Signal()
    preferences_requested = Signal()
    export_requested = Signal()
    start_recording_requested = Signal()
    stop_recording_requested = Signal()
    replay_requested = Signal()
    replay_play_requested = Signal()
    replay_pause_requested = Signal()
    replay_stop_requested = Signal()
    replay_restart_requested = Signal()
    replay_step_requested = Signal()
    replay_speed_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("COM-SW Serial Monitor")
        self.resize(1200, 800)

        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)
        self._terminal_view = TerminalView()
        self._dump_view = DumpView()
        self._table_view = TableView()
        self._line_view = LineView()

        self._tab_widget.addTab(self._terminal_view, "Terminal")
        self._tab_widget.addTab(self._dump_view, "Hex Dump")
        self._tab_widget.addTab(self._table_view, "Table")
        self._tab_widget.addTab(self._line_view, "Lines")
        self.setCentralWidget(self._tab_widget)

        self._modbus_panel = ModbusPanel()
        self._modbus_dock = QDockWidget("Modbus", self)
        self._modbus_dock.setObjectName("modbus_dock")
        self._modbus_dock.setWidget(self._modbus_panel)
        self._modbus_dock.setVisible(False)
        self.addDockWidget(Qt.RightDockWidgetArea, self._modbus_dock)

        self._modbus_analysis_view = ModbusAnalysisView()
        self._modbus_analysis_dock = QDockWidget("Modbus Analysis", self)
        self._modbus_analysis_dock.setObjectName("modbus_analysis_dock")
        self._modbus_analysis_dock.setWidget(self._modbus_analysis_view)
        self._modbus_analysis_dock.setVisible(False)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._modbus_analysis_dock)

        self._diagnostics_view = DiagnosticsView()
        self._diagnostics_dock = QDockWidget("Diagnostics", self)
        self._diagnostics_dock.setObjectName("diagnostics_dock")
        self._diagnostics_dock.setWidget(self._diagnostics_view)
        self._diagnostics_dock.setVisible(False)
        self.addDockWidget(Qt.BottomDockWidgetArea, self._diagnostics_dock)

        self._status_bar = StatusBar()
        self.setStatusBar(self._status_bar)

        self._setup_toolbar()
        self._setup_menu()

        self._port_config_dialog = None
        self._export_dialog = None
        self._preferences_dialog = None

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        port_label = QLabel("Port:")
        toolbar.addWidget(port_label)

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(180)
        self._port_combo.setEditable(True)
        self._port_combo.setInsertPolicy(QComboBox.NoInsert)
        self._port_combo.setToolTip("Select a serial port or type a device path manually.")
        self._port_combo.lineEdit().setPlaceholderText("COM3 or /dev/ttyUSB0")
        toolbar.addWidget(self._port_combo)

        baud_label = QLabel("Baud:")
        toolbar.addWidget(baud_label)

        self._baud_combo = QComboBox()
        self._baud_combo.addItems([
            "9600", "19200", "38400", "57600", "115200", "230400",
            "460800", "921600", "1200", "2400", "4800",
        ])
        self._baud_combo.setCurrentText("9600")
        self._baud_combo.setMinimumWidth(90)
        self._baud_combo.setToolTip("Serial baud rate.")
        toolbar.addWidget(self._baud_combo)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setMinimumWidth(80)
        self._connect_btn.setToolTip("Open the selected serial port.")
        self._connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; font-weight: bold;
                border: none; padding: 4px 12px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #45A049; }
            QPushButton:disabled { background-color: #5f7f60; color: #d7d7d7; }
        """)
        toolbar.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setMinimumWidth(90)
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.setToolTip("Close the active serial port.")
        self._disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336; color: white; font-weight: bold;
                border: none; padding: 4px 12px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #E53935; }
            QPushButton:disabled { background-color: #8a6866; color: #d7d7d7; }
        """)
        toolbar.addWidget(self._disconnect_btn)

        self._config_btn = QPushButton("Port Settings")
        self._config_btn.setMinimumWidth(100)
        self._config_btn.setToolTip("Open advanced serial port settings.")
        toolbar.addWidget(self._config_btn)

    def _setup_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File(&F)")

        export_action = QAction("Export Data...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        start_record_action = QAction("Start Recording...", self)
        start_record_action.setShortcut(QKeySequence("Ctrl+R"))
        start_record_action.triggered.connect(self._on_start_recording)
        file_menu.addAction(start_record_action)

        stop_record_action = QAction("Stop Recording", self)
        stop_record_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        stop_record_action.triggered.connect(self._on_stop_recording)
        file_menu.addAction(stop_record_action)

        replay_action = QAction("Replay Session...", self)
        replay_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        replay_action.triggered.connect(self._on_replay)
        file_menu.addAction(replay_action)

        file_menu.addSeparator()

        replay_play_action = QAction("Play Replay", self)
        replay_play_action.triggered.connect(self._on_replay_play)
        file_menu.addAction(replay_play_action)

        replay_pause_action = QAction("Pause Replay", self)
        replay_pause_action.triggered.connect(self._on_replay_pause)
        file_menu.addAction(replay_pause_action)

        replay_stop_action = QAction("Stop Replay", self)
        replay_stop_action.triggered.connect(self._on_replay_stop)
        file_menu.addAction(replay_stop_action)

        replay_restart_action = QAction("Restart Replay", self)
        replay_restart_action.triggered.connect(self._on_replay_restart)
        file_menu.addAction(replay_restart_action)

        replay_step_action = QAction("Step Replay", self)
        replay_step_action.triggered.connect(self._on_replay_step)
        file_menu.addAction(replay_step_action)

        replay_speed_menu = file_menu.addMenu("Replay Speed")
        for label, speed in (("0.5x", 0.5), ("1x", 1.0), ("2x", 2.0), ("4x", 4.0)):
            speed_action = QAction(label, self)
            speed_action.triggered.connect(lambda checked=False, s=speed: self.replay_speed_requested.emit(s))
            replay_speed_menu.addAction(speed_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit(&X)", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("View(&V)")

        self._modbus_action = QAction("Modbus Panel", self)
        self._modbus_action.setCheckable(True)
        self._modbus_action.triggered.connect(
            lambda checked: self._modbus_dock.setVisible(checked)
        )
        view_menu.addAction(self._modbus_action)
        self._modbus_dock.visibilityChanged.connect(self._modbus_action.setChecked)

        self._modbus_analysis_action = QAction("Modbus Analysis", self)
        self._modbus_analysis_action.setCheckable(True)
        self._modbus_analysis_action.triggered.connect(
            lambda checked: self._modbus_analysis_dock.setVisible(checked)
        )
        view_menu.addAction(self._modbus_analysis_action)
        self._modbus_analysis_dock.visibilityChanged.connect(
            self._modbus_analysis_action.setChecked
        )

        self._diagnostics_action = QAction("Diagnostics", self)
        self._diagnostics_action.setCheckable(True)
        self._diagnostics_action.triggered.connect(
            lambda checked: self._diagnostics_dock.setVisible(checked)
        )
        view_menu.addAction(self._diagnostics_action)
        self._diagnostics_dock.visibilityChanged.connect(
            self._diagnostics_action.setChecked
        )

        view_menu.addSeparator()

        clear_action = QAction("Clear Current View", self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self._clear_current_view)
        view_menu.addAction(clear_action)

        tools_menu = self.menuBar().addMenu("Tools(&T)")

        config_action = QAction("Port Settings...", self)
        config_action.triggered.connect(self._on_port_config)
        tools_menu.addAction(config_action)

        pref_action = QAction("Preferences...", self)
        pref_action.triggered.connect(self._on_preferences)
        tools_menu.addAction(pref_action)

        help_menu = self.menuBar().addMenu("Help(&H)")

        about_action = QAction("About", self)
        about_action.setShortcut(QKeySequence.HelpContents)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    @property
    def terminal_view(self) -> TerminalView:
        return self._terminal_view

    @property
    def dump_view(self) -> DumpView:
        return self._dump_view

    @property
    def table_view(self) -> TableView:
        return self._table_view

    @property
    def line_view(self) -> LineView:
        return self._line_view

    @property
    def modbus_panel(self) -> ModbusPanel:
        return self._modbus_panel

    @property
    def modbus_analysis_view(self) -> ModbusAnalysisView:
        return self._modbus_analysis_view

    @property
    def diagnostics_view(self) -> DiagnosticsView:
        return self._diagnostics_view

    @property
    def status_bar(self) -> StatusBar:
        return self._status_bar

    @property
    def connect_button(self) -> QPushButton:
        return self._connect_btn

    @property
    def disconnect_button(self) -> QPushButton:
        return self._disconnect_btn

    @property
    def port_combo(self) -> QComboBox:
        return self._port_combo

    @property
    def baud_combo(self) -> QComboBox:
        return self._baud_combo

    @property
    def config_button(self) -> QPushButton:
        return self._config_btn

    def get_selected_port_config(self) -> PortConfig:
        """Build a PortConfig from the toolbar UI selections."""
        return PortConfig(
            port=self._port_combo.currentText().strip(),
            baudrate=int(self._baud_combo.currentText()),
            bytesize=8,
            stopbits=1,
            parity="N",
        )

    def update_port_list(self, ports: List[str]) -> None:
        """Update the port combo box with available ports."""
        current = self._port_combo.currentText().strip()
        self._port_combo.clear()
        self._port_combo.addItems(ports)

        if current in ports:
            self._port_combo.setCurrentText(current)
        elif current:
            self._port_combo.setEditText(current)
        elif ports:
            self._port_combo.setCurrentIndex(0)

        if ports:
            self._status_bar.set_hint(f"Detected {len(ports)} port(s).")
        else:
            self._status_bar.set_hint("No ports detected. You can still type a device path manually.")

    def set_connected_ui(self, connected: bool) -> None:
        """Toggle UI elements based on connection state."""
        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._port_combo.setEnabled(not connected)
        self._baud_combo.setEnabled(not connected)
        self._config_btn.setEnabled(not connected)

    def _on_port_config(self) -> None:
        self.port_config_requested.emit()

    def _on_preferences(self) -> None:
        self.preferences_requested.emit()

    def _on_export(self) -> None:
        self.export_requested.emit()

    def _on_start_recording(self) -> None:
        self.start_recording_requested.emit()

    def _on_stop_recording(self) -> None:
        self.stop_recording_requested.emit()

    def _on_replay(self) -> None:
        self.replay_requested.emit()

    def _on_replay_play(self) -> None:
        self.replay_play_requested.emit()

    def _on_replay_pause(self) -> None:
        self.replay_pause_requested.emit()

    def _on_replay_stop(self) -> None:
        self.replay_stop_requested.emit()

    def _on_replay_restart(self) -> None:
        self.replay_restart_requested.emit()

    def _on_replay_step(self) -> None:
        self.replay_step_requested.emit()

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "About COM-SW",
            "<h3>COM-SW Serial Monitor v1.0</h3>"
            "<p>A lightweight serial communication debugging and monitoring tool.</p>"
            "<p>Includes terminal, hex dump, table, and line-oriented views, with Modbus RTU/ASCII/TCP support.</p>"
            "<p>Built with Python, PySide6, and pyserial.</p>",
        )

    def _clear_current_view(self) -> None:
        current = self._tab_widget.currentWidget()
        if hasattr(current, "clear"):
            current.clear()
            self._status_bar.set_hint("Current view cleared.")

    def closeEvent(self, event) -> None:
        event.accept()
