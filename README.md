# COM-SW — Serial Port Monitoring Tool

A lightweight serial port communication debugging and monitoring tool, architected with a modular Python + PySide6 stack.

## Features

- **Serial Port Management**: COM port enumeration, hot-plug detection, full configuration (baud rate, parity, stop bits, flow control)
- **Four Display Views**:
  - **Terminal View**: ASCII/HEX send & receive with timestamps and direction indicators
  - **Dump View**: Classic hex dump layout with address offset and ASCII sidebar
  - **Table View**: Structured column display with sortable timestamp/direction/length/data columns
  - **Line View**: Line-by-line display with content filtering
- **Modbus Protocol**: RTU (serial), ASCII, and TCP transport with CRC16/LRC verification
- **Data Export**: TXT and CSV export with configurable include options
- **Dark Theme**: Built-in dark stylesheet for comfortable long-term use
- **Persistent Configuration**: Auto-saves window layout, port settings, and display preferences

## Architecture

```
COM Port -> SerialReader(QThread) -> RingBuffer -> DataPump(50ms timer)
  -> AppController -> TerminalView / DumpView / TableView / LineView
```

- **MVC + Signal/Slot** architecture
- **Thread-safe ring buffer** with atomic drain
- **Dedicated serial reader QThread** for non-blocking I/O
- **Modular views** — each formats data independently

## Requirements

- Python 3.10+
- Windows / Linux / macOS

## Installation

```bash
git clone https://github.com/zhuguang-ZFG/com-sw.git
cd com-sw

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
python main.py
```

1. Select a COM port from the dropdown (or type a device path on Linux)
2. Choose baud rate
3. Click "打开" to connect
4. Data appears in real-time in all four views
5. Type in the send input at the bottom of Terminal view and press Enter to send

## Project Structure

```
com-sw/
├── main.py                         # Entry point
├── requirements.txt
├── README.md
├── src/
│   ├── app.py                      # QApplication bootstrap
│   ├── serial/
│   │   ├── ring_buffer.py          # Thread-safe data buffer
│   │   ├── serial_reader.py        # QThread serial reader
│   │   ├── port_manager.py         # Port lifecycle management
│   │   └── port_enumerator.py      # COM port enumeration + hot-plug
│   ├── protocol/
│   │   ├── modbus_rtu.py           # Modbus RTU (CRC16)
│   │   ├── modbus_ascii.py         # Modbus ASCII (LRC)
│   │   ├── modbus_tcp.py           # Modbus TCP (MBAP)
│   │   └── modbus_decoder.py       # Stream decoder + auto-detect
│   ├── models/
│   │   ├── data_packet.py          # DataPacket dataclass
│   │   └── port_config.py          # PortConfig dataclass
│   ├── controllers/
│   │   ├── app_controller.py       # Central orchestrator
│   │   ├── config_manager.py       # JSON config persistence
│   │   └── data_pump.py            # QTimer-driven buffer drain
│   ├── views/
│   │   ├── main_window.py          # QMainWindow + dock layout
│   │   ├── terminal_view.py        # Terminal send/receive
│   │   ├── dump_view.py            # HEX dump display
│   │   ├── table_view.py           # Sortable table
│   │   ├── line_view.py            # Line-by-line with filter
│   │   ├── modbus_panel.py         # Modbus request builder
│   │   ├── port_config_dialog.py   # Port settings dialog
│   │   ├── preferences_dialog.py   # App preferences
│   │   ├── export_dialog.py        # Data export config
│   │   └── status_bar.py           # Connection status bar
│   ├── utils/
│   │   ├── formatters.py           # Display formatting
│   │   └── byte_utils.py           # Byte manipulation
│   └── resources/
│       └── styles/
│           └── default.qss         # Dark theme stylesheet
└── tests/
    ├── test_ring_buffer.py
    ├── test_formatters.py
    ├── test_config_manager.py
    ├── test_port_config.py
    ├── test_modbus_rtu.py
    ├── test_modbus_ascii.py
    ├── test_modbus_tcp.py
    └── test_modbus_decoder.py
```

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_modbus_rtu.py -v
```

## Development

For virtual serial port testing on Windows, install [com0com](https://sourceforge.net/projects/com0com/) or use a pair of USB-serial adapters with a null-modem cable.

## License

MIT License
