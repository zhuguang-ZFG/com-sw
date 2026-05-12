"""Export dialog — configure data export to file."""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QPushButton, QLineEdit, QHBoxLayout, QDialogButtonBox,
    QFileDialog, QLabel,
)


class ExportDialog(QDialog):
    """Configure and start data export to file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出数据")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Format
        self._format_combo = QComboBox()
        self._format_combo.addItems(["TXT", "CSV"])
        form.addRow("格式:", self._format_combo)

        # File path
        path_layout = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("选择导出文件路径...")
        path_layout.addWidget(self._path_edit)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)
        form.addRow("文件:", path_layout)

        # Options
        self._timestamps_cb = QCheckBox("包含时间戳")
        self._timestamps_cb.setChecked(True)
        form.addRow("", self._timestamps_cb)

        self._direction_cb = QCheckBox("包含方向")
        self._direction_cb.setChecked(True)
        form.addRow("", self._direction_cb)

        self._append_cb = QCheckBox("追加模式 (不覆盖)")
        self._append_cb.setChecked(True)
        form.addRow("", self._append_cb)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        fmt = self._format_combo.currentText().lower()
        default_dir = os.path.expanduser("~/Documents")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出文件", default_dir, f"*.{fmt}"
        )
        if path:
            self._path_edit.setText(path)

    def get_export_config(self) -> dict:
        return {
            "file_path": self._path_edit.text(),
            "format": self._format_combo.currentText().lower(),
            "include_timestamps": self._timestamps_cb.isChecked(),
            "include_direction": self._direction_cb.isChecked(),
            "append_mode": self._append_cb.isChecked(),
        }
