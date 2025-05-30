"""Unit tests for the scanner module."""
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest
import yaml

from dialogchain import scanner, exceptions


class TestConfigScanner:
    """Test the ConfigScanner class."""
    
    @pytest.fixture
    def sample_config(self):
        """Return a sample configuration for testing."""
        return {
            "version": "1.0",
            "name": "test_scanner",
            "scanners": [
                {
                    "type": "file",
                    "path": "/path/to/configs",
                    "pattern": "*.yaml",
                    "recursive": True
                },
                {
                    "type": "http",
                    "url": "http://example.com/api/configs",
                    "interval": 300
                }
            ]
        }
    
    @pytest.fixture
    def mock_file_scanner(self):
        """Create a mock file scanner."""
        scanner = AsyncMock()
        scanner.scan.return_value = ["config1.yaml", "config2.yaml"]
        return scanner
    
    @pytest.fixture
    def mock_http_scanner(self):
        """Create a mock HTTP scanner."""
        scanner = AsyncMock()
        scanner.scan.return_value = ["http://example.com/config1.yaml"]
        return scanner
    
    def test_scanner_initialization(self, sample_config):
        """Test scanner initialization with config."""
        with patch('dialogchain.scanner.create_scanner') as mock_create_scanner:
            mock_create_scanner.side_effect = ["file_scanner", "http_scanner"]
            
            config_scanner = scanner.ConfigScanner(sample_config)
            
            assert config_scanner.config == sample_config
            assert len(config_scanner.scanners) == 2
            assert mock_create_scanner.call_count == 2
    
    @pytest.mark.asyncio
    async def test_scan(self, sample_config, mock_file_scanner, mock_http_scanner):
        """Test scanning for configuration files."""
        with patch('dialogchain.scanner.create_scanner') as mock_create_scanner:
            mock_create_scanner.side_effect = [mock_file_scanner, mock_http_scanner]
            
            config_scanner = scanner.ConfigScanner(sample_config)
            results = await config_scanner.scan()
            
            assert len(results) == 3  # 2 from file scanner, 1 from http scanner
            assert "config1.yaml" in results
            assert "config2.yaml" in results
            assert "http://example.com/config1.yaml" in results
            
            # Ensure scan was called as a coroutine
            mock_file_scanner.scan.assert_awaited_once()
            mock_http_scanner.scan.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_scan_with_error(self, sample_config):
        """Test error handling during scanning."""
        # Create a mock scanner that will raise an exception
        mock_scanner = AsyncMock()
        mock_scanner.scan.side_effect = Exception("Scan failed")
        
        with patch('dialogchain.scanner.create_scanner', return_value=mock_scanner):
            config_scanner = scanner.ConfigScanner({"scanners": [{"type": "file"}]})
            
            # We expect a ScannerError to be raised
            with pytest.raises(exceptions.ScannerError) as exc_info:
                await config_scanner.scan()
            
            # Check that the error message contains our error
            error_msg = str(exc_info.value)
            assert "Scanner failed: Scan failed" == error_msg, \
                f"Unexpected error message, got: {error_msg}"
            # Verify the mock was called
            mock_scanner.scan.assert_awaited_once()


class TestFileScanner:
    """Test the FileScanner class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create some test files
            (tmp_path / "config1.yaml").touch()
            (tmp_path / "config2.yaml").touch()
            (tmp_path / "other.txt").touch()
            
            # Create a subdirectory
            subdir = tmp_path / "subdir"
            subdir.mkdir(exist_ok=True)
            (subdir / "config3.yaml").touch()
            
            yield str(tmp_path)
    
    @pytest.mark.asyncio
    async def test_file_scanner_scan(self, temp_dir):
        """Test file scanning with pattern matching."""
        config = {
            "type": "file",
            "path": temp_dir,
            "pattern": "*.yaml",
            "recursive": False  # Explicitly set to non-recursive
        }
        
        file_scanner = scanner.FileScanner(config)
        results = await file_scanner.scan()
        
        # Get just the filenames from the results
        result_filenames = [Path(p).name for p in results]
        
        # Should only find the YAML files in the root directory
        assert len(results) == 2, f"Expected 2 files, got {len(results)}: {result_filenames}"
        assert "config1.yaml" in result_filenames
        assert "config2.yaml" in result_filenames
        assert "config3.yaml" not in result_filenames  # Should not be included in non-recursive scan
    
    @pytest.mark.asyncio
    async def test_file_scanner_scan_recursive(self, temp_dir):
        """Test recursive file scanning."""
        config = {
            "type": "file",
            "path": temp_dir,
            "pattern": "*.yaml",
            "recursive": True
        }
        
        file_scanner = scanner.FileScanner(config)
        results = await file_scanner.scan()
        
        # Convert all paths to strings for comparison
        result_paths = [str(Path(p).name) for p in results]
        
        assert len(results) == 3
        assert "config1.yaml" in result_paths
        assert "config2.yaml" in result_paths
        assert "config3.yaml" in result_paths
    
    @pytest.mark.asyncio
    async def test_file_scanner_nonexistent_path(self, tmp_path):
        """Test file scanning with a non-existent path."""
        # Create a path that doesn't exist
        non_existent_path = str(tmp_path / "nonexistent" / "path")
        
        config = {
            "type": "file",
            "path": non_existent_path,
            "pattern": "*.yaml"
        }
        
        file_scanner = scanner.FileScanner(config)
        
        # We expect a ScannerError to be raised
        with pytest.raises(exceptions.ScannerError) as exc_info:
            await file_scanner.scan()
        
        # Check the exact error message
        expected_error = f"Path does not exist: {non_existent_path}"
        actual_error = str(exc_info.value)
        assert actual_error == expected_error, \
            f"Expected error: '{expected_error}', got: '{actual_error}'"


class TestHttpScanner:
    """Test the HttpScanner class."""
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        # Create a mock response with the expected data structure
        response_data = {
            "configs": [
                {"name": "config1", "url": "http://example.com/config1.yaml"},
                {"name": "config2", "url": "http://example.com/config2.yaml"}
            ]
        }
        
        # Create an AsyncMock for the response
        response = AsyncMock()
        response.status = 200
        
        # Make json() return the response data directly
        response.json = AsyncMock(return_value=response_data)
        
        # For async context manager support
        response.__aenter__.return_value = response
        return response
    
    @pytest.fixture
    def mock_session(self, mock_response):
        """Create a mock aiohttp client session."""
        session = AsyncMock()
        # Make get() return the mock response
        session.get.return_value = mock_response
        return session
    
    @pytest.mark.asyncio
    async def test_http_scanner_scan(self, mock_session, mock_response):
        """Test HTTP scanning with a mock session."""
        config = {
            "type": "http",
            "url": "http://example.com/api/configs",
            "method": "GET",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 30
        }
        
        # Configure the mock response
        mock_response.json.return_value = {
            "configs": [
                {"name": "config1", "url": "http://example.com/config1.yaml"},
                {"name": "config2", "url": "http://example.com/config2.yaml"}
            ]
        }
        
        # Create the scanner and set the test session
        http_scanner = scanner.HttpScanner(config)
        http_scanner._test_session = mock_session
        
        # Run the scan
        results = await http_scanner.scan()
        
        # Verify the results
        assert len(results) == 2
        assert "http://example.com/config1.yaml" in results
        assert "http://example.com/config2.yaml" in results
        
        # Verify the request was made correctly
        from aiohttp import ClientTimeout
        
        # Get the actual call arguments
        args, kwargs = mock_session.get.call_args
        
        # Verify the URL and headers
        assert args[0] == "http://example.com/api/configs"
        assert kwargs['headers'] == {"Authorization": "Bearer token"}
        
        # Verify the timeout is a ClientTimeout with the correct total
        assert isinstance(kwargs['timeout'], ClientTimeout)
        assert kwargs['timeout'].total == 30
        
        # Ensure the mock response was used
        mock_response.json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_http_scanner_error_handling(self):
        """Test error handling in HTTP scanner."""
        config = {
            "type": "http",
            "url": "http://example.com/api/configs"
        }
        
        # Create a mock session that raises an exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Connection failed")
        
        # Create the scanner and set the test session
        http_scanner = scanner.HttpScanner(config)
        http_scanner._test_session = mock_session
        
        # Verify the exception is raised and contains the error message
        with pytest.raises(scanner.ScannerError) as exc_info:
            await http_scanner.scan()
        assert "Connection failed" in str(exc_info.value)


class TestScannerFactory:
    """Test the scanner factory functions."""
    
    def test_create_file_scanner(self):
        """Test creating a file scanner."""
        config = {
            "type": "file",
            "path": "/test/path",
            "pattern": "*.yaml"
        }
        scanner_obj = scanner.create_scanner(config)
        assert isinstance(scanner_obj, scanner.FileScanner)
        assert scanner_obj.path == Path("/test/path")
    
    def test_create_http_scanner(self):
        """Test creating an HTTP scanner."""
        config = {
            "type": "http",
            "url": "http://example.com/api"
        }
        scanner_obj = scanner.create_scanner(config)
        assert isinstance(scanner_obj, scanner.HttpScanner)
        assert scanner_obj.url == "http://example.com/api"
    
    def test_create_unknown_scanner(self):
        """Test creating a scanner with an unknown type."""
        config = {
            "type": "unknown",
            "path": "/test"
        }
        with pytest.raises(ValueError) as exc_info:
            scanner.create_scanner(config)
        assert "Unknown scanner type" in str(exc_info.value)
