"""Export dialog - configure data export to file."""

import os

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    """Configure and start data export to file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Data")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._format_combo = QComboBox()
        self._format_combo.addItems(["TXT", "CSV"])
        self._format_combo.currentTextChanged.connect(self._on_format_changed)
        form.addRow("Format:", self._format_combo)

        path_layout = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Choose an export file path...")
        self._path_edit.textChanged.connect(self._update_status)
        path_layout.addWidget(self._path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        form.addRow("File:", path_layout)

        self._timestamps_cb = QCheckBox("Include timestamps")
        self._timestamps_cb.setChecked(True)
        form.addRow("", self._timestamps_cb)

        self._direction_cb = QCheckBox("Include direction")
        self._direction_cb.setChecked(True)
        form.addRow("", self._direction_cb)

        self._append_cb = QCheckBox("Append to existing file")
        self._append_cb.setChecked(True)
        form.addRow("", self._append_cb)

        layout.addLayout(form)

        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #888;")
        layout.addWidget(self._summary_label)

        self._status_label = QLabel("Choose where exported data should be saved.")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._on_format_changed(self._format_combo.currentText())

    def _on_format_changed(self, fmt: str) -> None:
        current = self._path_edit.text().strip()
        if current:
            root, ext = os.path.splitext(current)
            expected_ext = f".{fmt.lower()}"
            if ext.lower() != expected_ext:
                self._path_edit.setText(root + expected_ext)
        self._update_status()

    def _browse(self) -> None:
        fmt = self._format_combo.currentText().lower()
        default_dir = os.path.expanduser("~/Documents")
        default_path = os.path.join(default_dir, f"com-sw-export.{fmt}")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export File",
            default_path,
            f"{fmt.upper()} files (*.{fmt})",
        )
        if path:
            if not path.lower().endswith(f".{fmt}"):
                path += f".{fmt}"
            self._path_edit.setText(path)

    def _update_status(self) -> None:
        path = self._path_edit.text().strip()
        fmt = self._format_combo.currentText().lower()
        self._summary_label.setText(
            f"Will export as {fmt.upper()} with"
            f" {'timestamps' if self._timestamps_cb.isChecked() else 'no timestamps'} and"
            f" {'direction' if self._direction_cb.isChecked() else 'no direction'}"
            f" ({'append' if self._append_cb.isChecked() else 'overwrite'} mode)."
        )

        if not path:
            self._status_label.setText("Choose a file path before exporting.")
            self._status_label.setStyleSheet("color: #F44336;")
            self._buttons.button(QDialogButtonBox.Ok).setEnabled(False)
            return

        self._status_label.setText("Ready to export.")
        self._status_label.setStyleSheet("color: #888;")
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(True)

    def _on_accept(self) -> None:
        if not self._path_edit.text().strip():
            self._update_status()
            return
        self.accept()

    def get_export_config(self) -> dict:
        return {
            "file_path": self._path_edit.text().strip(),
            "format": self._format_combo.currentText().lower(),
            "include_timestamps": self._timestamps_cb.isChecked(),
            "include_direction": self._direction_cb.isChecked(),
            "append_mode": self._append_cb.isChecked(),
        }

    def set_export_config(self, config: dict) -> None:
        self._format_combo.setCurrentText(config.get("format", "txt").upper())
        self._path_edit.setText(config.get("file_path", ""))
        self._timestamps_cb.setChecked(config.get("include_timestamps", True))
        self._direction_cb.setChecked(config.get("include_direction", True))
        self._append_cb.setChecked(config.get("append_mode", True))
        self._update_status()
