"""Unit tests for the config module."""
import os
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from dialogchain.config import (
    RouteConfig,
    ConfigResolver,
    ConfigValidator,
    ValidationError
)


class TestRouteConfig:
    """Test the RouteConfig class."""
    
    @pytest.fixture
    def sample_config(self):
        """Return a sample route configuration."""
        return {
            "routes": [
                {
                    "name": "test_route",
                    "from": "rtsp://camera1",
                    "to": "http://api.example.com/webhook",
                    "processors": [
                        {
                            "type": "filter",
                            "config": {"min_confidence": 0.5}
                        }
                    ]
                }
            ]
        }
    
    def test_route_config_validation(self, sample_config):
        """Test route configuration validation."""
        # Test valid config
        config = RouteConfig(sample_config)
        assert isinstance(config.data, dict)
        assert "routes" in config.data
        
        # Test missing required fields
        invalid_config = {"routes": [{"name": "invalid"}]}
        with pytest.raises(ValidationError) as exc_info:
            RouteConfig(invalid_config)
        assert "Missing 'from' field" in str(exc_info.value)
    
    def test_route_config_loading(self, sample_config, tmp_path):
        """Test loading route config from a YAML file."""
        # Create a temporary YAML file
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(sample_config))
        
        # Load the config from file
        with open(config_file) as f:
            loaded_config = yaml.safe_load(f)
        
        config = RouteConfig(loaded_config)
        assert len(config.data["routes"]) == 1
        assert config.data["routes"][0]["name"] == "test_route"


class TestConfigResolver:
    """Test the ConfigResolver class."""
    
    def test_resolve_env_vars(self):
        """Test environment variable resolution."""
        resolver = ConfigResolver()
        env_vars = {
            "DB_HOST": "localhost",
            "DB_PORT": "5432"
        }
        
        # Test with direct variable
        result = resolver.resolve_env_vars(
            "postgresql://${DB_HOST}:${DB_PORT}/mydb",
            env_vars
        )
        assert result == "postgresql://localhost:5432/mydb"
        
        # Test with default value
        result = resolver.resolve_env_vars(
            "postgresql://${DB_HOST:127.0.0.1}:${DB_PORT:5432}/mydb",
            {}
        )
        assert result == "postgresql://127.0.0.1:5432/mydb"
    
    def test_check_required_env_vars(self):
        """Test required environment variable validation."""
        resolver = ConfigResolver()
        
        # Test with all required vars present
        env_vars = {
            "REQUIRED_VAR_1": "value1",
            "REQUIRED_VAR_2": "value2"
        }
        resolver.check_required_env_vars(["REQUIRED_VAR_1", "REQUIRED_VAR_2"], env_vars)
        
        # Test with missing required var
        with pytest.raises(ValueError) as exc_info:
            resolver.check_required_env_vars(
                ["REQUIRED_VAR_1", "MISSING_VAR"],
                env_vars
            )
        assert "Missing required environment variable: MISSING_VAR" in str(exc_info.value)


class TestConfigValidator:
    """Test the ConfigValidator class."""
    
    def test_validate_uri(self):
        """Test URI validation."""
        # Test valid RTSP URI
        assert ConfigValidator.validate_uri("rtsp://camera1:554/stream", "sources") is None
        
        # Test invalid scheme
        with pytest.raises(ValueError) as exc_info:
            ConfigValidator.validate_uri("invalid://test", "sources")
        assert "Unsupported scheme 'invalid' for source" in str(exc_info.value)
        
        # Test invalid destination
        with pytest.raises(ValueError) as exc_info:
            ConfigValidator.validate_uri("rtsp://test", "destinations")
        assert "Unsupported scheme 'rtsp' for destination" in str(exc_info.value)
    
    def test_validate_processor(self):
        """Test processor configuration validation."""
        # Test valid processor
        valid_processor = {
            "type": "filter",
            "config": {"min_confidence": 0.5}
        }
        assert ConfigValidator.validate_processor(valid_processor) is None
        
        # Test missing type
        with pytest.raises(ValueError) as exc_info:
            ConfigValidator.validate_processor({"config": {}})
        assert "Processor config missing 'type' field" in str(exc_info.value)
        
        # Test invalid type
        with pytest.raises(ValueError) as exc_info:
            ConfigValidator.validate_processor({"type": "invalid"})
        assert "Unsupported processor type: invalid" in str(exc_info.value)
        
        # Test missing config
        with pytest.raises(ValueError) as exc_info:
            ConfigValidator.validate_processor({"type": "filter"})
        assert "Processor config missing 'config' field" in str(exc_info.value)


def test_config_loading_from_file(tmp_path):
    """Test loading configuration from a file."""
    # Create a temporary config file
    config_data = {
        "routes": [
            {
                "name": "test_route",
                "from": "rtsp://camera1",
                "to": "http://api.example.com/webhook",
                "processors": [{"type": "filter"}]
            }
        ]
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data))
    
    # Test loading the config
    with open(config_file) as f:
        loaded_config = yaml.safe_load(f)
    
    config = RouteConfig(loaded_config)
    assert len(config.data["routes"]) == 1
    assert config.data["routes"][0]["name"] == "test_route"
