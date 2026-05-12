"""Configuration manager with JSON persistence and atomic writes.

Handles:
- Loading config from JSON file
- Saving config atomically (write to temp, then os.replace)
- Falling back to defaults on corruption
- Version migration support
"""

import json
import logging
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Default configuration template
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "port": {
        "last_port": "",
        "last_baudrate": 9600,
        "last_bytesize": 8,
        "last_stopbits": 1,
        "last_parity": "N",
        "last_flow_control": "none",
        "timeout": 0.1,
        "auto_reconnect": False,
        "dtr_on_connect": True,
        "rts_on_connect": True,
    },
    "display": {
        "terminal_mode": "ascii",
        "terminal_font_size": 10,
        "terminal_auto_scroll": True,
        "terminal_timestamp_format": "time_only",
        "terminal_show_direction": True,
        "terminal_show_timestamp": True,
        "table_display_mode": "ascii",
        "table_max_rows": 5000,
        "dump_bytes_per_line": 16,
        "dump_show_offset": True,
        "dump_show_ascii": True,
        "line_display_mode": "ascii",
        "line_history": 500,
    },
    "export": {
        "format": "txt",
        "include_timestamps": True,
        "include_direction": True,
        "append_mode": True,
    },
    "window": {
        "geometry": None,
        "state": None,
    },
    "ring_buffer_max_size": 10000,
    "data_pump_interval_ms": 50,
    "hotplug_poll_interval_ms": 2000,
}


class ConfigManager:
    """Manages application configuration with JSON persistence."""

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = Path.home() / ".com-sw"
        self._config_dir = Path(config_dir)
        self._config_file = self._config_dir / "config.json"
        self._config: Dict[str, Any] = {}
        self._dirty = False

    def load(self) -> Dict[str, Any]:
        """Load configuration from disk, falling back to defaults on error."""
        if not self._config_file.exists():
            logger.info("No config file found, using defaults")
            self._config = deepcopy(DEFAULT_CONFIG)
            self._ensure_dir()
            self.save()
            return self._config

        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            # Merge with defaults (fills in missing keys from newer versions)
            self._config = self._merge_defaults(loaded)
            self._migrate()
            logger.info(f"Config loaded from {self._config_file}")
            return self._config

        except (json.JSONDecodeError, PermissionError) as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            self._config = deepcopy(DEFAULT_CONFIG)
            return self._config

    def save(self) -> bool:
        """Atomically save configuration to disk.

        Returns True on success, False on failure.
        """
        self._ensure_dir()
        try:
            # Write to temp file, then atomic replace
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._config_dir), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, str(self._config_file))
                self._dirty = False
                return True
            except Exception:
                os.unlink(tmp_path)
                raise
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested config value by key path.

        Example: config.get("port", "last_baudrate") -> 9600
        """
        node = self._config
        for key in keys:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                return default
            if node is None:
                return default
        return node

    def set(self, *keys_and_value: Any) -> None:
        """Set a nested config value by key path.

        Example: config.set("port", "last_baudrate", 115200)
        """
        *keys, value = keys_and_value
        node = self._config
        for key in keys[:-1]:
            if key not in node:
                node[key] = {}
            node = node[key]
        if node.get(keys[-1]) != value:
            node[keys[-1]] = value
            self._dirty = True

    def _ensure_dir(self) -> None:
        """Create the config directory if it doesn't exist."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def _merge_defaults(self, loaded: dict) -> dict:
        """Recursively merge loaded config with defaults to fill missing keys."""
        merged = deepcopy(DEFAULT_CONFIG)
        self._deep_update(merged, loaded)
        return merged

    def _deep_update(self, target: dict, source: dict) -> None:
        """Recursively update target dict with source dict values."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def _migrate(self) -> None:
        """Handle config version migrations."""
        current = self._config.get("version", 0)
        if current < 1:
            # Add any migrations here as the config format evolves
            self._config["version"] = 1
            self._dirty = True

    @property
    def dirty(self) -> bool:
        return self._dirty
