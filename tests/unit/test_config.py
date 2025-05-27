"""Unit tests for the config module."""
import os
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
import yaml

from dialogchain import config


def test_load_config_from_file(tmp_path):
    """Test loading configuration from a file."""
    # Create a sample config file
    config_data = {"version": "1.0", "name": "test_config", "settings": {"debug": True}}
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    # Test loading the config
    loaded = config.load_config(str(config_path))
    assert loaded == config_data


def test_load_config_from_dict():
    """Test loading configuration from a dictionary."""
    config_data = {"version": "1.0", "name": "test_config"}
    assert config.load_config(config_data) == config_data


def test_load_config_invalid():
    """Test loading invalid configuration."""
    with pytest.raises(ValueError):
        config.load_config(123)  # type: ignore


@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data="invalid: yaml")
def test_load_config_invalid_yaml(mock_file, mock_exists):
    """Test loading invalid YAML from file."""
    with pytest.raises(yaml.YAMLError):
        config.load_config("dummy_path.yaml")


def test_get_config_value(sample_config):
    """Test getting a value from configuration."""
    value = config.get_config_value(sample_config, ["connectors", "http", "timeout"])
    assert value == 30


def test_get_config_value_default(sample_config):
    """Test getting a default value from configuration."""
    value = config.get_config_value(sample_config, ["nonexistent", "key"], default=42)
    assert value == 42


def test_get_config_value_required(sample_config):
    """Test getting a required value that doesn't exist."""
    with pytest.raises(KeyError):
        config.get_config_value(sample_config, ["nonexistent", "key"], required=True)


def test_validate_config_valid(sample_config):
    """Test validating a valid configuration."""
    assert config.validate_config(sample_config) is None


def test_validate_config_invalid():
    """Test validating an invalid configuration."""
    with pytest.raises(ValueError):
        config.validate_config({"invalid": "config"})


@patch.dict(os.environ, {"DIALOGCHAIN_DEBUG": "true"})
def test_get_env_bool():
    """Test getting a boolean value from environment."""
    assert config.get_env_bool("DIALOGCHAIN_DEBUG") is True
    assert config.get_env_bool("NON_EXISTENT", False) is False


def test_get_env_int():
    """Test getting an integer value from environment."""
    with patch.dict(os.environ, {"DIALOGCHAIN_TIMEOUT": "30"}):
        assert config.get_env_int("DIALOGCHAIN_TIMEOUT", 10) == 30
        assert config.get_env_int("NON_EXISTENT", 42) == 42


def test_merge_configs():
    """Test merging two configurations."""
    base = {"a": 1, "b": {"x": 1, "y": 2}}
    override = {"b": {"y": 3, "z": 4}, "c": 5}
    expected = {"a": 1, "b": {"x": 1, "y": 3, "z": 4}, "c": 5}
    assert config.merge_configs(base, override) == expected
