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
        
        # Test with direct variable using Jinja2 syntax
        result = resolver.resolve_env_vars(
            "postgresql://{{DB_HOST}}:{{DB_PORT}}/mydb",
            env_vars
        )
        assert result == "postgresql://localhost:5432/mydb"
        
        # Test with direct variable using ${} syntax
        result = resolver.resolve_env_vars(
            "postgresql://${DB_HOST}:${DB_PORT}/mydb",
            env_vars
        )
        assert result == "postgresql://localhost:5432/mydb"
    
    def test_check_required_env_vars(self):
        """Test required environment variable validation."""
        resolver = ConfigResolver()
        
        # Set up environment variables
        os.environ["REQUIRED_VAR_1"] = "value1"
        os.environ["REQUIRED_VAR_2"] = "value2"
        
        try:
            # Test with all required vars present
            missing = resolver.check_required_env_vars(["REQUIRED_VAR_1", "REQUIRED_VAR_2"])
            assert missing == [], "Expected no missing variables"
            
            # Test with missing required var
            missing = resolver.check_required_env_vars(["REQUIRED_VAR_1", "MISSING_VAR"])
            assert missing == ["MISSING_VAR"], "Expected MISSING_VAR to be missing"
        finally:
            # Clean up
            os.environ.pop("REQUIRED_VAR_1", None)
            os.environ.pop("REQUIRED_VAR_2", None)


class TestConfigValidator:
    """Test the ConfigValidator class."""
    
    def test_validate_uri(self):
        """Test URI validation."""
        # Test valid RTSP URI
        errors = ConfigValidator.validate_uri("rtsp://camera1:554/stream", "sources")
        assert not errors, f"Expected no errors, got: {errors}"
        
        # Test invalid scheme
        errors = ConfigValidator.validate_uri("invalid://test", "sources")
        assert any("Unsupported scheme 'invalid' for sources" in e for e in errors), \
            f"Expected unsupported scheme error, got: {errors}"
        
        # Test invalid destination
        errors = ConfigValidator.validate_uri("rtsp://test", "destinations")
        assert any("Unsupported scheme 'rtsp' for destinations" in e for e in errors), \
            f"Expected unsupported scheme error for destination, got: {errors}"
    
    def test_validate_processor(self):
        """Test processor configuration validation."""
        # Test valid processor
        valid_processor = {
            "type": "filter",
            "condition": "some_condition"
        }
        errors = ConfigValidator.validate_processor(valid_processor)
        assert not errors, f"Expected no errors, got: {errors}"
        
        # Test missing type
        errors = ConfigValidator.validate_processor({"config": {}})
        assert any("Unsupported processor type 'None'" in e for e in errors), \
            f"Expected missing type error, got: {errors}"
        
        # Test invalid type
        errors = ConfigValidator.validate_processor({"type": "invalid"})
        assert any("Unsupported processor type 'invalid'" in e for e in errors), \
            f"Expected unsupported type error, got: {errors}"
        
        # Test missing required fields for filter type
        errors = ConfigValidator.validate_processor({"type": "filter"})
        assert any("Filter processor requires 'condition' field" in e for e in errors), \
            f"Expected missing condition error, got: {errors}"
            
        # Test external processor validation
        errors = ConfigValidator.validate_processor({"type": "external"})
        assert any("External processor requires 'command' field" in e for e in errors), \
            f"Expected missing command error, got: {errors}"


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
