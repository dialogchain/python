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
        scanner = MagicMock()
        scanner.scan.return_value = ["config1.yaml", "config2.yaml"]
        return scanner
    
    @pytest.fixture
    def mock_http_scanner(self):
        """Create a mock HTTP scanner."""
        scanner = MagicMock()
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
            
            mock_file_scanner.scan.assert_awaited_once()
            mock_http_scanner.scan.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_scan_with_error(self, sample_config, mock_file_scanner):
        """Test error handling during scanning."""
        # Configure one scanner to raise an exception
        mock_file_scanner.scan.side_effect = Exception("Scan failed")
        
        with patch('dialogchain.scanner.create_scanner', return_value=mock_file_scanner):
            config_scanner = scanner.ConfigScanner({"scanners": [{"type": "file"}]})
            
            with pytest.raises(exceptions.ScannerError) as exc_info:
                await config_scanner.scan()
            assert "Scan failed" in str(exc_info.value)


class TestFileScanner:
    """Test the FileScanner class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            os.makedirs(os.path.join(temp_dir, "subdir"))
            
            # Create YAML files
            with open(os.path.join(temp_dir, "config1.yaml"), "w") as f:
                f.write("key1: value1")
            
            with open(os.path.join(temp_dir, "config2.yaml"), "w") as f:
                f.write("key2: value2")
            
            # Create a file that doesn't match the pattern
            with open(os.path.join(temp_dir, "notes.txt"), "w") as f:
                f.write("Some notes")
            
            # Create a file in subdirectory
            os.makedirs(os.path.join(temp_dir, "subdir"))
            with open(os.path.join(temp_dir, "subdir", "config3.yaml"), "w") as f:
                f.write("key3: value3")
            
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_file_scanner_scan(self, temp_dir):
        """Test file scanning with pattern matching."""
        config = {
            "type": "file",
            "path": temp_dir,
            "pattern": "*.yaml",
            "recursive": False
        }
        
        file_scanner = scanner.FileScanner(config)
        results = await file_scanner.scan()
        
        # Should find 2 YAML files in the root directory
        assert len(results) == 2
        assert any("config1.yaml" in str(p) for p in results)
        assert any("config2.yaml" in str(p) for p in results)
        assert not any("config3.yaml" in str(p) for p in results)  # Not in root dir
    
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
        
        # Should find all 3 YAML files including subdirectories
        assert len(results) == 3
        assert any("config1.yaml" in str(p) for p in results)
        assert any("config2.yaml" in str(p) for p in results)
        assert any("config3.yaml" in str(p) for p in results)
    
    @pytest.mark.asyncio
    async def test_file_scanner_nonexistent_path(self):
        """Test file scanning with a non-existent path."""
        config = {
            "type": "file",
            "path": "/nonexistent/path",
            "pattern": "*.yaml"
        }
        
        file_scanner = scanner.FileScanner(config)
        
        with pytest.raises(exceptions.ScannerError) as exc_info:
            await file_scanner.scan()
        assert "does not exist" in str(exc_info.value)


class TestHttpScanner:
    """Test the HttpScanner class."""
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = MagicMock()
        response.status = 200
        response.json.return_value = {
            "configs": [
                {"name": "config1", "url": "http://example.com/config1.yaml"},
                {"name": "config2", "url": "http://example.com/config2.yaml"}
            ]
        }
        return response
    
    @pytest.fixture
    def mock_session(self, mock_response):
        """Create a mock aiohttp client session."""
        session = MagicMock()
        session.get.return_value.__aenter__.return_value = mock_response
        return session
    
    @pytest.mark.asyncio
    async def test_http_scanner_scan(self, mock_session):
        """Test HTTP scanning with a mock session."""
        config = {
            "type": "http",
            "url": "http://example.com/api/configs",
            "method": "GET",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 30
        }
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            http_scanner = scanner.HttpScanner(config)
            results = await http_scanner.scan()
            
            assert len(results) == 2
            assert "http://example.com/config1.yaml" in results
            assert "http://example.com/config2.yaml" in results
            
            # Verify the request was made correctly
            mock_session.get.assert_called_once_with(
                "http://example.com/api/configs",
                headers={"Authorization": "Bearer token"},
                timeout=30
            )
    
    @pytest.mark.asyncio
    async def test_http_scanner_error_handling(self):
        """Test error handling in HTTP scanner."""
        config = {
            "type": "http",
            "url": "http://example.com/api/configs"
        }
        
        # Mock a failed request
        async def mock_get(*args, **kwargs):
            raise Exception("Connection failed")
        
        mock_session = MagicMock()
        mock_session.get.side_effect = mock_get
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            http_scanner = scanner.HttpScanner(config)
            
            with pytest.raises(exceptions.ScannerError) as exc_info:
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
