"""Main window — QMainWindow with dock-based multi-view layout.

The main window provides:
- Menu bar (File, View, Tools, Help)
- Toolbar (connect/disconnect, port settings)
- Central tab widget for terminal/dump/table/line views
- Dockable Modbus panel
- Status bar
"""

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QMenuBar, QMenu, QToolBar, QTabWidget,
    QDockWidget, QComboBox, QPushButton, QLabel, QMessageBox,
    QWidget, QVBoxLayout, QHBoxLayout, QApplication,
)
from PySide6.QtGui import QAction, QIcon

from src.models.port_config import PortConfig
from src.views.terminal_view import TerminalView
from src.views.dump_view import DumpView
from src.views.table_view import TableView
from src.views.line_view import LineView
from src.views.modbus_panel import ModbusPanel
from src.views.status_bar import StatusBar


class MainWindow(QMainWindow):
    """Application main window with multi-view layout."""

    # Signals are connected externally by AppController

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("COM-SW 串口监控工具")
        self.resize(1200, 800)

        # Central tab widget for views
        self._tab_widget = QTabWidget()
        self._terminal_view = TerminalView()
        self._dump_view = DumpView()
        self._table_view = TableView()
        self._line_view = LineView()

        self._tab_widget.addTab(self._terminal_view, "终端")
        self._tab_widget.addTab(self._dump_view, "HEX Dump")
        self._tab_widget.addTab(self._table_view, "表格")
        self._tab_widget.addTab(self._line_view, "行模式")

        self.setCentralWidget(self._tab_widget)

        # Modbus dock (hidden by default)
        self._modbus_panel = ModbusPanel()
        self._modbus_dock = QDockWidget("Modbus", self)
        self._modbus_dock.setWidget(self._modbus_panel)
        self._modbus_dock.setVisible(False)
        self.addDockWidget(Qt.RightDockWidgetArea, self._modbus_dock)

        # Status bar
        self._status_bar = StatusBar()
        self.setStatusBar(self._status_bar)

        # Toolbar
        self._setup_toolbar()

        # Menu
        self._setup_menu()

        # Port config dialog (lazy)
        self._port_config_dialog = None
        self._export_dialog = None
        self._preferences_dialog = None

    # ---- Toolbar ------------------------------------------------------------------

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel(" 端口: "))
        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(100)
        self._port_combo.setEditable(True)
        toolbar.addWidget(self._port_combo)

        self._baud_combo = QComboBox()
        self._baud_combo.addItems([
            "9600", "19200", "38400", "57600", "115200", "230400",
            "460800", "921600", "1200", "2400", "4800",
        ])
        self._baud_combo.setCurrentText("9600")
        self._baud_combo.setMinimumWidth(80)
        toolbar.addWidget(QLabel(" "))
        toolbar.addWidget(self._baud_combo)

        self._connect_btn = QPushButton("打开")
        self._connect_btn.setMinimumWidth(60)
        self._connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; font-weight: bold;
                border: none; padding: 4px 12px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #45A049; }
        """)
        toolbar.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("关闭")
        self._disconnect_btn.setMinimumWidth(60)
        self._disconnect_btn.setEnabled(False)
        self._disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336; color: white; font-weight: bold;
                border: none; padding: 4px 12px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #E53935; }
        """)
        toolbar.addWidget(self._disconnect_btn)

        # Port config button
        self._config_btn = QPushButton("设置")
        self._config_btn.setMinimumWidth(50)
        toolbar.addWidget(self._config_btn)

    def _setup_menu(self) -> None:
        # File menu
        file_menu = self.menuBar().addMenu("文件(&F)")

        export_action = QAction("导出数据...", self)
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = self.menuBar().addMenu("视图(&V)")

        modbus_action = QAction("Modbus 面板", self)
        modbus_action.setCheckable(True)
        modbus_action.triggered.connect(
            lambda checked: self._modbus_dock.setVisible(checked)
        )
        view_menu.addAction(modbus_action)

        view_menu.addSeparator()

        clear_action = QAction("清空当前视图", self)
        clear_action.triggered.connect(self._clear_current_view)
        view_menu.addAction(clear_action)

        # Tools menu
        tools_menu = self.menuBar().addMenu("工具(&T)")

        config_action = QAction("端口设置...", self)
        config_action.triggered.connect(self._on_port_config)
        tools_menu.addAction(config_action)

        pref_action = QAction("偏好设置...", self)
        pref_action.triggered.connect(self._on_preferences)
        tools_menu.addAction(pref_action)

        # Help menu
        help_menu = self.menuBar().addMenu("帮助(&H)")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    # ---- Public API ----------------------------------------------------------------

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
            port=self._port_combo.currentText(),
            baudrate=int(self._baud_combo.currentText()),
            bytesize=8,
            stopbits=1,
            parity="N",
        )

    def update_port_list(self, ports: List[str]) -> None:
        """Update the port combo box with available ports."""
        current = self._port_combo.currentText()
        self._port_combo.clear()
        self._port_combo.addItems(ports)
        if current in ports:
            self._port_combo.setCurrentText(current)
        elif ports:
            self._port_combo.setCurrentIndex(0)

    def set_connected_ui(self, connected: bool) -> None:
        """Toggle UI elements based on connection state."""
        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._port_combo.setEnabled(not connected)
        self._baud_combo.setEnabled(not connected)

    # ---- Slots ---------------------------------------------------------------------

    def _on_port_config(self) -> None:
        from src.views.port_config_dialog import PortConfigDialog
        if self._port_config_dialog is None:
            self._port_config_dialog = PortConfigDialog(self)
        self._port_config_dialog.show()

    def _on_preferences(self) -> None:
        from src.views.preferences_dialog import PreferencesDialog
        if self._preferences_dialog is None:
            self._preferences_dialog = PreferencesDialog(self)
        self._preferences_dialog.show()

    def _on_export(self) -> None:
        from src.views.export_dialog import ExportDialog
        if self._export_dialog is None:
            self._export_dialog = ExportDialog(self)
        self._export_dialog.show()

    def _on_about(self) -> None:
        QMessageBox.about(
            self, "关于 COM-SW",
            "<h3>COM-SW 串口监控工具 v1.0</h3>"
            "<p>一个轻量级的串口通信调试和监控工具。</p>"
            "<p>支持终端/Dump/表格/行模式四种视图，"
            "以及 Modbus RTU/ASCII/TCP 协议解析。</p>"
            "<p>Python + PySide6 + pyserial + pymodbus</p>",
        )

    def _clear_current_view(self) -> None:
        current = self._tab_widget.currentWidget()
        if hasattr(current, "clear"):
            current.clear()

    def closeEvent(self, event) -> None:
        """Save window state before closing."""
        # Geometry and state will be saved by AppController
        event.accept()
