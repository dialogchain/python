"""Unit tests for the connectors module."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dialogchain import connectors


class TestSourceConnector:
    """Test the Source connector functionality."""

    def test_source_initialization(self):
        """Test source connector initialization."""
        class TestSource(connectors.Source):
            async def receive(self):
                yield "test"
                
        source = TestSource()
        assert isinstance(source, connectors.Source)


class TestDestinationConnector:
    """Test the Destination connector functionality."""

    def test_destination_initialization(self):
        """Test destination connector initialization."""
        class TestDestination(connectors.Destination):
            async def send(self, message):
                pass
                
        destination = TestDestination()
        assert isinstance(destination, connectors.Destination)


class TestRTSPSource:
    """Test the RTSP source connector."""
    
    @pytest.mark.asyncio
    async def test_rtsp_source_receive(self):
        """Test RTSP source receive method."""
        with patch('cv2.VideoCapture') as mock_capture:
            # Setup mock
            mock_capture.return_value.isOpened.return_value = True
            mock_capture.return_value.grab.return_value = True
            mock_capture.return_value.retrieve.return_value = (True, "frame_data")
            
            source = connectors.RTSPSource("rtsp://test")
            source.reconnect_attempts = 1  # Limit reconnect attempts for test
            
            # Test receive generator
            async for frame in source.receive():
                assert frame == {"frame": "frame_data", "metadata": {}}
                break  # Just test one iteration


class TestHTTPDestination:
    """Test the HTTP destination connector."""
    
    @pytest.mark.asyncio
    async def test_http_destination_send(self):
        """Test HTTP destination send method."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "success"}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            destination = connectors.HTTPDestination("http://test")
            await destination.send({"test": "data"})
            
            # Verify the request was made correctly
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert kwargs['json'] == {"test": "data"}
