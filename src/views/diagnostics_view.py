"""Diagnostics dock for lightweight runtime observability."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from src.models.runtime_metrics import RuntimeMetricsSnapshot


class DiagnosticsView(QWidget):
    """Shows runtime counters and recent diagnostics summary."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._summary_label = QLabel("Diagnostics idle.")
        self._summary_label.setStyleSheet("color: #888;")
        self._details = QPlainTextEdit()
        self._details.setReadOnly(True)
        self._details.setPlaceholderText("Runtime counters will appear here.")
        self._clear_button = QPushButton("Clear Counters")

        layout = QVBoxLayout(self)
        layout.addWidget(self._summary_label)
        layout.addWidget(self._details)
        layout.addWidget(self._clear_button)

    @property
    def clear_button(self) -> QPushButton:
        return self._clear_button

    def set_metrics(self, snapshot: RuntimeMetricsSnapshot) -> None:
        last_packet = (
            snapshot.last_packet_at.strftime("%H:%M:%S.%f")[:-3]
            if snapshot.last_packet_at
            else "-"
        )
        self._summary_label.setText(
            f"Packets {snapshot.packets_processed} | Dropped {snapshot.dropped_packets} | Batches {snapshot.batches_processed}"
        )
        self._details.setPlainText(
            "\n".join(
                [
                    f"Packets processed: {snapshot.packets_processed}",
                    f"RX bytes: {snapshot.bytes_rx}",
                    f"TX bytes: {snapshot.bytes_tx}",
                    f"Batches processed: {snapshot.batches_processed}",
                    f"Last batch size: {snapshot.last_batch_size}",
                    f"Max batch size: {snapshot.max_batch_size}",
                    f"Dropped packets: {snapshot.dropped_packets}",
                    f"Replay position: {snapshot.replay_index}/{snapshot.replay_loaded_packets}",
                    f"Replay speed: {snapshot.replay_speed:.1f}x",
                    f"Last packet at: {last_packet}",
                ]
            )
        )
