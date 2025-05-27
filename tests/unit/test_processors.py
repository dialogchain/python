"""Unit tests for the processors module."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dialogchain import processors, exceptions
from dialogchain.connectors import BaseConnector


class MockConnector(BaseConnector):
    """Mock connector for testing processors."""
    
    def __init__(self, config):
        super().__init__(config)
        self.sent_messages = []
        self.received_messages = []
    
    async def connect(self):
        self.is_connected = True
    
    async def disconnect(self):
        self.is_connected = False
    
    async def send(self, message, **kwargs):
        self.sent_messages.append((message, kwargs))
        return {"status": "ok"}
    
    async def receive(self, **kwargs):
        if self.received_messages:
            return self.received_messages.pop(0)
        return None


class TestBaseProcessor:
    """Test the base processor functionality."""
    
    def test_processor_initialization(self):
        """Test processor initialization with config."""
        config = {
            "name": "test_processor",
            "type": "test",
            "input": "test_input",
            "output": "test_output"
        }
        
        processor = processors.BaseProcessor(config)
        assert processor.name == "test_processor"
        assert processor.input_connector == "test_input"
        assert processor.output_connector == "test_output"
    
    @pytest.mark.asyncio
    async def test_processor_process_not_implemented(self):
        """Test that base process method raises NotImplementedError."""
        processor = processors.BaseProcessor({"name": "test"})
        with pytest.raises(NotImplementedError):
            await processor.process({"test": "data"})


class TestTextProcessor:
    """Test the TextProcessor implementation."""
    
    @pytest.fixture
    def processor_config(self):
        """Return a sample text processor configuration."""
        return {
            "name": "text_processor",
            "type": "text",
            "input": "test_input",
            "output": "test_output",
            "template": "Processed: {text}",
            "filters": ["trim", "lower"],
            "validation": {
                "required": ["text"],
                "types": {"text": "string"}
            }
        }
    
    @pytest.mark.asyncio
    async def test_text_processor_initialization(self, processor_config):
        """Test text processor initialization."""
        processor = processors.TextProcessor(processor_config)
        assert processor.name == "text_processor"
        assert processor.template == "Processed: {text}"
        assert "trim" in processor.filters
        assert "lower" in processor.filters
    
    @pytest.mark.asyncio
    async def test_text_processor_process(self, processor_config):
        """Test text processing with template and filters."""
        processor = processors.TextProcessor(processor_config)
        
        # Test with valid input
        result = await processor.process({"text": "  TEST  "})
        assert result == {"text": "processed: test"}  # lower filter is applied
        
        # Test with template
        processor.template = "Result: {text}"
        result = await processor.process({"text": "test"})
        assert result == {"text": "Result: test"}
    
    @pytest.mark.asyncio
    async def test_text_processor_validation(self, processor_config):
        """Test input validation in text processor."""
        processor = processors.TextProcessor(processor_config)
        
        # Test missing required field
        with pytest.raises(exceptions.ValidationError) as exc_info:
            await processor.process({"wrong_field": "test"})
        assert "Missing required field" in str(exc_info.value)
        
        # Test invalid type
        with pytest.raises(exceptions.ValidationError) as exc_info:
            await processor.process({"text": 123})
        assert "must be of type" in str(exc_info.value)


class TestHttpProcessor:
    """Test the HttpProcessor implementation."""
    
    @pytest.fixture
    def processor_config(self):
        """Return a sample HTTP processor configuration."""
        return {
            "name": "http_processor",
            "type": "http",
            "input": "test_input",
            "output": "test_output",
            "url": "http://example.com/api/process",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 1
        }
    
    @pytest.fixture
    def mock_http_connector(self):
        """Create a mock HTTP connector."""
        connector = MockConnector({"name": "http_connector"})
        connector.request = AsyncMock(return_value={"status": "success", "result": "processed"})
        return connector
    
    @pytest.mark.asyncio
    async def test_http_processor_initialization(self, processor_config):
        """Test HTTP processor initialization."""
        processor = processors.HttpProcessor(processor_config)
        assert processor.name == "http_processor"
        assert processor.url == "http://example.com/api/process"
        assert processor.method == "POST"
        assert processor.timeout == 30
    
    @pytest.mark.asyncio
    async def test_http_processor_process(self, processor_config, mock_http_connector):
        """Test HTTP request processing."""
        processor = processors.HttpProcessor(processor_config)
        
        # Mock the connector factory to return our mock connector
        with patch('dialogchain.connectors.create_connector', return_value=mock_http_connector):
            # Test successful request
            result = await processor.process({"text": "test"})
            assert result == {"status": "success", "result": "processed"}
            
            # Verify the HTTP request was made correctly
            mock_http_connector.request.assert_called_once_with(
                "POST",
                "http://example.com/api/process",
                json={"text": "test"},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
    
    @pytest.mark.asyncio
    async def test_http_processor_retry(self, processor_config, mock_http_connector):
        """Test HTTP processor retry logic."""
        # Configure the mock to fail twice before succeeding
        mock_http_connector.request.side_effect = [
            Exception("Connection error"),
            Exception("Timeout"),
            {"status": "success", "result": "processed"}
        ]
        
        processor = processors.HttpProcessor(processor_config)
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep, \
             patch('dialogchain.connectors.create_connector', return_value=mock_http_connector):
            
            result = await processor.process({"text": "test"})
            assert result == {"status": "success", "result": "processed"}
            
            # Verify retry logic
            assert mock_http_connector.request.call_count == 3
            assert mock_sleep.await_count == 2  # Should sleep between retries


class TestProcessorFactory:
    """Test the processor factory."""
    
    def test_create_text_processor(self):
        """Test creating a text processor."""
        config = {
            "name": "test_text",
            "type": "text",
            "template": "Test: {text}"
        }
        processor = processors.create_processor(config)
        assert isinstance(processor, processors.TextProcessor)
        assert processor.name == "test_text"
    
    def test_create_http_processor(self):
        """Test creating an HTTP processor."""
        config = {
            "name": "test_http",
            "type": "http",
            "url": "http://example.com"
        }
        processor = processors.create_processor(config)
        assert isinstance(processor, processors.HttpProcessor)
        assert processor.name == "test_http"
    
    def test_create_unknown_processor(self):
        """Test creating a processor with an unknown type."""
        config = {
            "name": "test_unknown",
            "type": "unknown_type"
        }
        with pytest.raises(ValueError) as exc_info:
            processors.create_processor(config)
        assert "Unknown processor type" in str(exc_info.value)
