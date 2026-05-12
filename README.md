# COM-SW Serial Port Monitoring Tool

A lightweight serial communication debugging and monitoring tool built with Python, PySide6, and pyserial.

## Features

- Serial port enumeration and hot-plug detection
- Toolbar connection flow with saved port preferences
- Four data views:
  - `Terminal View`: ASCII / HEX send and receive with timestamps and direction
  - `Dump View`: classic hex dump with offset and ASCII sidebar
  - `Table View`: sortable structured rows for timestamp, direction, length, and data
  - `Line View`: line-oriented display with filtering
- Modbus support:
  - RTU
  - ASCII
  - TCP
- Export to `TXT` and `CSV`
- Session recording and replay via `JSONL`
- Replay playback controls with pause, stop, and speed options
- Replay-time Modbus RTU exception highlighting and quick analysis hints
- Dedicated `Modbus Analysis` dock for decoded frames and paired responses
- Persistent preferences for display and port settings
- Dark theme optimized for long sessions

## Architecture

```text
COM Port -> SerialReader(QThread) -> RingBuffer -> DataPump
  -> AppController -> Terminal / Dump / Table / Line Views
```

- MVC-style organization with Qt signal/slot wiring
- Thread-safe ring buffer with batched UI updates
- Modular views with independent formatting behavior

## Requirements

- Python 3.10+
- Windows / Linux / macOS

## Installation

```bash
git clone https://github.com/zhuguang-ZFG/com-sw.git
cd com-sw
pip install -r requirements.txt
```

## Quick Start

### Windows

Use the included launcher:

```bat
run-com-sw.cmd
```

You can also double-click `run-com-sw.cmd` in Explorer.

### Any Platform

```bash
python main.py
```

## Typical Usage

1. Select a serial port from the toolbar, or type one manually.
2. Choose a baud rate.
3. Click `Connect`.
4. Watch incoming data in all four views.
5. Use the Terminal send area for ASCII, HEX, or Modbus RTU frames.
6. Open `Port Settings`, `Preferences`, or `Export` from the UI when needed.

## Configuration

COM-SW persists settings in a JSON config file under the user profile.

Saved settings include:

- Last port and baud rate
- Port signal preferences such as `DTR` / `RTS`
- Terminal display mode and font size
- Table maximum rows
- Dump formatting preferences
- Export format and include options
- Last session recording file
- Window geometry

## Running Tests

```bash
python -m pytest tests -q
```

Examples:

```bash
python -m pytest tests/test_config_manager.py -q
python -m pytest tests/test_ring_buffer.py -q
```

## Project Structure

```text
com-sw/
├── main.py
├── run-com-sw.cmd
├── requirements.txt
├── README.md
├── src/
│   ├── app.py
│   ├── controllers/
│   ├── models/
│   ├── serial/
│   ├── utils/
│   └── views/
└── tests/
```

## Notes

- The GUI depends on `PySide6`.
- Serial access depends on `pyserial`.
- The application uses batched updates to keep the UI responsive during higher-throughput monitoring.
