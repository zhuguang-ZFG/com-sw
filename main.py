"""Entry point for the Serial Port Monitor application."""

import sys
from pathlib import Path

# Ensure the project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    from src.app import SerialMonitorApp

    app = SerialMonitorApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
