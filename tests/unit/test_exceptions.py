"""Unit tests for the exceptions module."""
import pytest

from dialogchain import exceptions


def test_dialogchain_exception():
    """Test base DialogChainException."""
    with pytest.raises(exceptions.DialogChainException) as exc_info:
        raise exceptions.DialogChainException("Test error")

    assert "Test error" in str(exc_info.value)
    assert exc_info.value.return_code == 1


def test_configuration_error():
    """Test ConfigurationError."""
    with pytest.raises(exceptions.ConfigurationError) as exc_info:
        raise exceptions.ConfigurationError("Invalid config")

    assert "Invalid config" in str(exc_info.value)
    assert exc_info.value.return_code == 2


def test_validation_error():
    """Test ValidationError."""
    with pytest.raises(exceptions.ValidationError) as exc_info:
        raise exceptions.ValidationError("Validation failed", field="test_field")

    assert "Validation failed" in str(exc_info.value)
    assert exc_info.value.field == "test_field"
    assert exc_info.value.return_code == 3


def test_connector_error():
    """Test ConnectorError."""
    with pytest.raises(exceptions.ConnectorError) as exc_info:
        raise exceptions.ConnectorError("Connection failed", status_code=500)

    assert "Connection failed" in str(exc_info.value)
    assert exc_info.value.status_code == 500
    assert exc_info.value.return_code == 4


def test_processor_error():
    """Test ProcessorError."""
    with pytest.raises(exceptions.ProcessorError) as exc_info:
        raise exceptions.ProcessorError(
            "Processing failed", processor_name="test_processor"
        )

    assert "Processing failed" in str(exc_info.value)
    assert exc_info.value.processor_name == "test_processor"
    assert exc_info.value.return_code == 5


def test_timeout_error():
    """Test TimeoutError."""
    with pytest.raises(exceptions.TimeoutError) as exc_info:
        raise exceptions.TimeoutError("Operation timed out", timeout=30)

    assert "Operation timed out" in str(exc_info.value)
    assert exc_info.value.timeout == 30
    assert exc_info.value.return_code == 6
