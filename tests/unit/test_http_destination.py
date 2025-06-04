"""Tests for the HTTP destination connector."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from dialogchain.connectors import HTTPDestination

class TestHTTPDestination:
    """Test HTTP destination connector."""
    
    @pytest.fixture
    def http_dest(self):
        """Create an HTTPDestination instance for testing."""
        return HTTPDestination("http://example.com/webhook")
    
    @pytest.mark.asyncio
    async def test_send_http_request(self, http_dest, capsys):
        """Test sending an HTTP request."""
        # Create a mock response for successful request
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        
        # Create a mock post method
        async def mock_post(*args, **kwargs):
            return mock_response
            
        # Create a mock session
        mock_session = AsyncMock()
        mock_session.post.side_effect = mock_post
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        # Patch the ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test with dict message
            await http_dest.send({"key": "value"})
            
            # Check output
            captured = capsys.readouterr()
            assert "🌐 HTTP sent to http://example.com/webhook" in captured.out
            
            # Verify the post was called correctly
            mock_session.post.assert_called_once_with(
                'http://example.com/webhook',
                json={"key": "value"}
            )
    
    @pytest.mark.asyncio
    async def test_send_string_message(self, http_dest, capsys):
        """Test sending a string message."""
        # Create a mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        
        # Create a mock post method
        async def mock_post(*args, **kwargs):
            return mock_response
            
        # Create a mock session
        mock_session = AsyncMock()
        mock_session.post.side_effect = mock_post
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        # Patch the ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test with string message
            await http_dest.send("test message")
            
            # Check output
            captured = capsys.readouterr()
            assert "🌐 HTTP sent to http://example.com/webhook" in captured.out
            
            # Verify the post was called correctly
            mock_session.post.assert_called_once_with(
                'http://example.com/webhook',
                json={"data": "test message"}
            )
    
    @pytest.mark.asyncio
    async def test_http_error(self, http_dest, capsys):
        """Test handling of HTTP errors."""
        # Create a mock response with error status
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        
        # Create a mock post method
        async def mock_post(*args, **kwargs):
            return mock_response
            
        # Create a mock session
        mock_session = AsyncMock()
        mock_session.post.side_effect = mock_post
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        # Patch the ClientSession
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Test with dict message
            await http_dest.send({"key": "value"})
            
            # Check error output
            captured = capsys.readouterr()
            assert "❌ HTTP error 400: Bad Request" in captured.out
