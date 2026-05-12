"""Application bootstrap — QApplication setup and single-instance enforcement."""

import sys
from pathlib import Path

from PySide6.QtCore import QSharedMemory, QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

from src.controllers.config_manager import ConfigManager


class SerialMonitorApp:
    """Main application class handling lifecycle."""

    APP_NAME = "com-sw"
    ORG_NAME = "com-sw"

    def __init__(self, argv: list):
        self._argv = argv

    def run(self) -> int:
        """Initialize and run the application. Returns exit code."""
        # Single instance enforcement
        shared_mem = QSharedMemory("com-sw-serial-monitor-instance")
        if not shared_mem.create(1) and shared_mem.error() == QSharedMemory.AlreadyExists:
            # Another instance is already running
            print("Another instance of com-sw is already running. Exiting.")
            return 0

        # Create QApplication
        app = QApplication(self._argv)
        app.setApplicationName(self.APP_NAME)
        app.setOrganizationName(self.ORG_NAME)
        app.setApplicationVersion("1.0.0")

        # Load configuration
        config_manager = ConfigManager()
        config_manager.load()

        # Apply stylesheet
        self._apply_stylesheet(app)

        # Build and show main window
        from src.controllers.app_controller import AppController

        controller = AppController(config_manager)
        controller.main_window.show()

        return app.exec()

    def _apply_stylesheet(self, app: QApplication) -> None:
        """Load and apply the Qt stylesheet if available."""
        style_path = Path(__file__).parent / "resources" / "styles" / "default.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
