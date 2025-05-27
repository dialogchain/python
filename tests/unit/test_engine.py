"""Unit tests for the CamelRouterEngine class."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from dialogchain.engine import CamelRouterEngine, parse_uri
from dialogchain.connectors import Source, Destination, RTSPSource, HTTPDestination
from dialogchain.config import RouteConfig, ValidationError


class MockSource(Source):
    """Mock source for testing."""
    
    def __init__(self):
        self.messages = []
        self.is_connected = False
    
    async def connect(self):
        self.is_connected = True
    
    async def disconnect(self):
        self.is_connected = False
    
    async def receive(self):
        while self.messages:
            yield self.messages.pop(0)


class MockDestination(Destination):
    """Mock destination for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.is_connected = False
    
    async def connect(self):
        self.is_connected = True
    
    async def disconnect(self):
        self.is_connected = False
    
    async def send(self, message):
        self.sent_messages.append(message)


class TestCamelRouterEngine:
    """Test the CamelRouterEngine class."""
    
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
            ],
            "sources": {
                "rtsp://camera1": {
                    "type": "rtsp"
                }
            },
            "destinations": {
                "http://api.example.com/webhook": {
                    "type": "http"
                }
            }
        }
    
    @pytest.fixture
    def mock_source(self):
        """Create a mock source for testing."""
        return MockSource()
    
    @pytest.fixture
    def mock_destination(self):
        """Create a mock destination for testing."""
        return MockDestination()
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, sample_config):
        """Test engine initialization with valid config."""
        engine = CamelRouterEngine(sample_config)
        assert engine.config == sample_config
        assert len(engine.routes) == 1
        assert engine.routes[0]["name"] == "test_route"
    
    @pytest.mark.asyncio
    async def test_parse_uri(self):
        """Test the parse_uri function."""
        # Test with standard URI
        scheme, path = parse_uri("http://example.com/path")
        assert scheme == "http"
        assert path == "//example.com/path"
        
        # Test with simple scheme:path format
        scheme, path = parse_uri("timer:5s")
        assert scheme == "timer"
        assert path == "5s"
        
        # Test with invalid URI
        with pytest.raises(ValueError):
            parse_uri("invalid_uri")
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self, sample_config, mock_source, mock_destination):
        """Test starting and stopping the engine."""
        with patch('dialogchain.connectors.RTSPSource', return_value=mock_source), \
             patch('dialogchain.connectors.HTTPDestination', return_value=mock_destination):
            
            engine = CamelRouterEngine(sample_config)
            await engine.start()
            
            # Verify source and destination are connected
            assert mock_source.is_connected is True
            assert mock_destination.is_connected is True
            
            await engine.stop()
            
            # Verify source and destination are disconnected
            assert mock_source.is_connected is False
            assert mock_destination.is_connected is False
    
    @pytest.mark.asyncio
    async def test_engine_process_message(self, sample_config, mock_source, mock_destination):
        """Test processing a message through the engine."""
        test_message = {"frame": "test_frame", "confidence": 0.7}
        mock_source.messages = [test_message]
        
        with patch('dialogchain.connectors.RTSPSource', return_value=mock_source), \
             patch('dialogchain.connectors.HTTPDestination', return_value=mock_destination):
            
            engine = CamelRouterEngine(sample_config)
            await engine.start()
            
            # Process messages for a short duration
            process_task = asyncio.create_task(engine.run())
            await asyncio.sleep(0.1)  # Allow some time for processing
            process_task.cancel()
            
            # Verify the message was processed and sent to destination
            assert len(mock_destination.sent_messages) > 0
            assert mock_destination.sent_messages[0] == test_message
            
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_engine_invalid_config(self):
        """Test engine initialization with invalid config."""
        invalid_config = {"routes": [{"name": "invalid"}]}  # Missing required fields
        
        with pytest.raises(ValidationError):
            CamelRouterEngine(invalid_config)
    
    @pytest.mark.asyncio
    async def test_engine_context_manager(self, sample_config, mock_source, mock_destination):
        """Test using the engine as a context manager."""
        with patch('dialogchain.connectors.RTSPSource', return_value=mock_source), \
             patch('dialogchain.connectors.HTTPDestination', return_value=mock_destination):
            
            async with CamelRouterEngine(sample_config) as engine:
                # Verify engine is running
                assert engine.is_running is True
                assert mock_source.is_connected is True
                assert mock_destination.is_connected is True
            
            # Verify engine is stopped after context
            assert engine.is_running is False
            assert mock_source.is_connected is False
            assert mock_destination.is_connected is False
