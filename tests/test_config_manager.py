"""Tests for ConfigManager — persistent JSON configuration."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.controllers.config_manager import ConfigManager, DEFAULT_CONFIG


class TestConfigManager:
    """Unit tests for ConfigManager."""

    @pytest.fixture
    def tmp_config(self):
        """Create a ConfigManager pointing to a temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ConfigManager(config_dir=Path(tmpdir))

    def test_load_defaults_when_no_file(self, tmp_config):
        config = tmp_config.load()
        assert config["version"] == 1
        assert config["port"]["last_baudrate"] == 9600
        assert config["display"]["terminal_font_size"] == 10
        assert config["display"]["table_max_rows"] == 5000

    def test_save_and_reload_preserves_values(self, tmp_config):
        tmp_config.load()
        tmp_config.set("port", "last_baudrate", 115200)
        tmp_config.set("display", "terminal_mode", "hex")
        tmp_config.save()

        # Create a new ConfigManager pointing to the same dir
        new_mgr = ConfigManager(config_dir=tmp_config._config_dir)
        new_mgr.load()
        assert new_mgr.get("port", "last_baudrate") == 115200
        assert new_mgr.get("display", "terminal_mode") == "hex"

    def test_missing_keys_fallback_to_defaults(self, tmp_config):
        """If saved config is missing a key, defaults should be used."""
        tmp_config.load()
        # Manually write a partial config
        partial = {"version": 1, "port": {"last_baudrate": 38400}}
        with open(tmp_config._config_file, "w") as f:
            json.dump(partial, f)

        new_mgr = ConfigManager(config_dir=tmp_config._config_dir)
        config = new_mgr.load()
        # The port section should have the custom baudrate
        assert config["port"]["last_baudrate"] == 38400
        # Missing keys should come from defaults
        assert config["display"]["terminal_mode"] == "ascii"
        assert config["display"]["terminal_font_size"] == 10
        assert config["display"]["table_max_rows"] == 5000

    def test_new_display_defaults_merge_into_existing_config(self, tmp_config):
        tmp_config.load()
        partial = {
            "version": 1,
            "display": {
                "terminal_mode": "hex",
            },
        }
        with open(tmp_config._config_file, "w", encoding="utf-8") as f:
            json.dump(partial, f)

        new_mgr = ConfigManager(config_dir=tmp_config._config_dir)
        config = new_mgr.load()
        assert config["display"]["terminal_mode"] == "hex"
        assert config["display"]["terminal_font_size"] == 10
        assert config["display"]["table_max_rows"] == 5000

    def test_corrupt_json_fallback(self, tmp_config):
        """Corrupt file should gracefully fall back to defaults."""
        tmp_config.load()
        tmp_config.save()
        # Write garbage to the config file
        with open(tmp_config._config_file, "w") as f:
            f.write("this is not valid json {{{")

        new_mgr = ConfigManager(config_dir=tmp_config._config_dir)
        config = new_mgr.load()
        assert config["version"] == 1

    def test_nested_get(self, tmp_config):
        tmp_config.load()
        assert tmp_config.get("port", "last_baudrate") == 9600
        assert tmp_config.get("nonexistent", "key", default=None) is None

    def test_nested_set(self, tmp_config):
        tmp_config.load()
        tmp_config.set("display", "terminal_mode", "hex")
        assert tmp_config.get("display", "terminal_mode") == "hex"
