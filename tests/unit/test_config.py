"""Unit tests for the config module."""
import os
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
import yaml

from dialogchain.config import RouteConfig, ConfigResolver, ConfigValidator
from dialogchain.exceptions import ValidationError, ConfigurationError


def test_route_config_validation():
    """Test route configuration validation."""
    # Valid config
    valid_config = {
        "routes": [
            {
                "name": "test-route",
                "from": "rtsp://camera1",
                "to": "http://api.example.com"
            }
        ]
    }
    route_config = RouteConfig(valid_config)
    assert route_config.data == valid_config
    
    # Invalid config - missing required fields
    invalid_config = {"routes": [{"name": "invalid-route"}]}
    with pytest.raises(ValidationError) as excinfo:
        RouteConfig(invalid_config)
    assert "Missing 'from' field" in str(excinfo.value)


def test_route_config_loading():
    """Test loading route configuration from a file."""
    # This is a simplified test - in a real scenario, we'd mock the file I/O
    config_data = {
        "routes": [
            {
                "name": "test-route",
                "from": "rtsp://camera1",
                "to": "http://api.example.com"
            }
        ]
    }
    route_config = RouteConfig(config_data)
    assert route_config.data == config_data


def test_resolve_env_vars():
    """Test resolving environment variables in configuration."""
    resolver = ConfigResolver()
    
    # Test with no env vars
    assert resolver.resolve_env_vars("test") == "test"
    
    # Test with env var - using Jinja2 syntax
    with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        assert resolver.resolve_env_vars("prefix_{{ TEST_VAR }}_suffix") == "prefix_test_value_suffix"
    
    # Test with missing var - Jinja2 will leave the variable as is
    with patch.dict(os.environ, {}, clear=True):
        result = resolver.resolve_env_vars("prefix_{{ MISSING_VAR }}_suffix")
        assert result == "prefix__suffix"  # Jinja2 leaves undefined variables as empty strings


def test_check_required_env_vars():
    """Test checking for required environment variables."""
    resolver = ConfigResolver()
    
    # All vars present
    with patch.dict(os.environ, {"VAR1": "value1", "VAR2": "value2"}):
        missing = resolver.check_required_env_vars(["VAR1", "VAR2"])
        assert missing == []
    
    # Missing vars
    with patch.dict(os.environ, {}, clear=True):
        missing = resolver.check_required_env_vars(["MISSING_VAR"])
        assert missing == ["MISSING_VAR"]


def test_validate_uri():
    """Test URI validation."""
    validator = ConfigValidator()
    
    # Valid URIs
    assert validator.validate_uri("rtsp://camera1", "sources") == []
    assert validator.validate_uri("http://example.com", "destinations") == []
    
    # Invalid scheme
    errors = validator.validate_uri("invalid://test", "sources")
    assert any("Unsupported scheme 'invalid'" in e for e in errors)
    
    # Missing netloc (should be allowed for certain schemes like 'file' and 'log')
    errors = validator.validate_uri("file:///path/to/file", "sources")
    assert not errors  # Should be valid for file scheme
    
    # Missing netloc for http should be invalid
    errors = validator.validate_uri("http://", "sources")
    assert any("Missing host/netloc in URI" in e for e in errors)


def test_validate_processor():
    """Test processor configuration validation."""
    validator = ConfigValidator()
    
    # Valid processor
    valid_processor = {"type": "external", "command": "python script.py"}
    assert validator.validate_processor(valid_processor) == []
    
    # Missing type
    errors = validator.validate_processor({"name": "test"})
    assert any("Unsupported processor type 'None'" in e for e in errors)
    
    # Invalid type
    errors = validator.validate_processor({"type": "invalid"})
    assert any("Unsupported processor type 'invalid'" in e for e in errors)
    
    # Missing command for external processor
    errors = validator.validate_processor({"type": "external"})
    assert any("External processor requires 'command' field" in e for e in errors)
    
    # Test filter processor validation
    errors = validator.validate_processor({"type": "filter"})
    assert any("Filter processor requires 'condition' field" in e for e in errors)
    
    # Test transform processor validation
    errors = validator.validate_processor({"type": "transform"})
    assert any("Transform processor requires 'template' field" in e for e in errors)
