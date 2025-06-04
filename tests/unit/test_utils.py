"""Unit tests for the utils module."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dialogchain import utils

# Re-export the event_loop fixture from conftest
pytest_plugins = ['tests.conftest']



def test_import_string():
    """Test importing a class by string path."""
    # Test importing built-in class
    datetime_cls = utils.import_string("datetime.datetime")
    assert datetime_cls == datetime

    # Test importing with invalid path
    with pytest.raises(ImportError):
        utils.import_string("nonexistent.module")


def test_parse_timedelta():
    """Test parsing time delta from string."""
    # Test seconds
    assert utils.parse_timedelta("30s") == timedelta(seconds=30)

    # Test minutes and seconds
    assert utils.parse_timedelta("2m30s") == timedelta(minutes=2, seconds=30)

    # Test hours, minutes, seconds
    assert utils.parse_timedelta("1h2m3s") == timedelta(hours=1, minutes=2, seconds=3)

    # Test invalid format
    with pytest.raises(ValueError):
        utils.parse_timedelta("invalid")


def test_format_timedelta():
    """Test formatting timedelta as string."""
    assert utils.format_timedelta(timedelta(seconds=30)) == "30s"
    assert utils.format_timedelta(timedelta(minutes=2, seconds=30)) == "2m30s"
    assert utils.format_timedelta(timedelta(hours=1, minutes=2, seconds=3)) == "1h2m3s"


@pytest.mark.asyncio
async def test_async_retry_success():
    """Test successful async retry."""
    mock_func = AsyncMock(return_value="success")

    @utils.async_retry(max_retries=3, delay=0.1)
    async def test_func():
        return await mock_func()

    result = await test_func()
    assert result == "success"
    mock_func.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_retry_failure():
    """Test async retry with failures."""
    mock_func = AsyncMock(side_effect=Exception("Failed"))

    @utils.async_retry(max_retries=2, delay=0.1)
    async def test_func():
        return await mock_func()

    with pytest.raises(Exception, match="Failed"):
        await test_func()

    assert mock_func.await_count == 2  # Initial attempt + 1 retry


def test_sanitize_filename():
    """Test sanitizing filenames."""
    assert utils.sanitize_filename("test/file:name.txt") == "test_file_name.txt"
    assert utils.sanitize_filename("../malicious\0file") == ".._malicious_file"
    assert utils.sanitize_filename("normal-name_123") == "normal-name_123"


def test_deep_update():
    """Test deep update of dictionaries."""
    dest = {"a": 1, "b": {"x": 1, "y": 2}}
    src = {"b": {"y": 3, "z": 4}, "c": 5}
    expected = {"a": 1, "b": {"x": 1, "y": 3, "z": 4}, "c": 5}

    result = utils.deep_update(dest, src)
    assert result == expected
    assert dest == expected  # Original dict should be modified


def test_generate_id():
    """Test generating unique IDs."""
    id1 = utils.generate_id()
    id2 = utils.generate_id()

    assert isinstance(id1, str)
    assert len(id1) == 32  # Default length for hex digest
    assert id1 != id2


def test_format_bytes():
    """Test formatting bytes to human-readable string."""
    assert utils.format_bytes(1023) == "1023B"
    assert utils.format_bytes(1024) == "1.0KB"
    assert utils.format_bytes(1024 * 1024) == "1.0MB"
    assert utils.format_bytes(1024 * 1024 * 1024) == "1.0GB"


def test_parse_bool():
    """Test parsing boolean values from various inputs."""
    assert utils.parse_bool("true") is True
    assert utils.parse_bool("True") is True
    assert utils.parse_bool("1") is True
    assert utils.parse_bool(1) is True
    assert utils.parse_bool(True) is True

    assert utils.parse_bool("false") is False
    assert utils.parse_bool("False") is False
    assert utils.parse_bool("0") is False
    assert utils.parse_bool(0) is False
    assert utils.parse_bool(False) is False

    with pytest.raises(ValueError):
        utils.parse_bool("invalid")


@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager utility."""
    mock_obj = MagicMock()
    mock_obj.aclose = AsyncMock()

    async with utils.async_context_manager(mock_obj) as obj:
        assert obj == mock_obj

    mock_obj.aclose.assert_awaited_once()
