"""Unit tests for the DialogEngine class."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from dialogchain import engine, config, exceptions
from dialogchain.connectors import BaseConnector


class MockConnector(BaseConnector):
    """Mock connector for testing."""
    
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


class TestDialogEngine:
    """Test the DialogEngine class."""
    
    @pytest.fixture
    def sample_config(self):
        """Return a sample engine configuration."""
        return {
            "version": "1.0",
            "name": "test_engine",
            "connectors": {
                "test_input": {
                    "type": "test",
                    "name": "test_input"
                },
                "test_output": {
                    "type": "test",
                    "name": "test_output"
                }
            },
            "processors": {
                "test_processor": {
                    "type": "test",
                    "input": "test_input",
                    "output": "test_output"
                }
            },
            "workflows": {
                "default": ["test_processor"]
            }
        }
    
    @pytest.fixture
    def mock_connector_factory(self):
        """Return a mock connector factory."""
        return MagicMock(side_effect=MockConnector)
    
    @pytest.fixture
    def mock_processor_factory(self):
        """Return a mock processor factory."""
        mock_processor = AsyncMock()
        mock_processor.process.return_value = {"processed": True}
        return MagicMock(return_value=mock_processor)
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, sample_config, mock_connector_factory, mock_processor_factory):
        """Test engine initialization with valid config."""
        with patch('dialogchain.connectors.create_connector', mock_connector_factory), \
             patch('dialogchain.processors.create_processor', mock_processor_factory):
            
            dialog_engine = engine.DialogEngine(sample_config)
            assert dialog_engine.name == "test_engine"
            assert len(dialog_engine.connectors) == 2
            assert len(dialog_engine.processors) == 1
            assert len(dialog_engine.workflows) == 1
    
    @pytest.mark.asyncio
    async def test_engine_start_stop(self, sample_config, mock_connector_factory, mock_processor_factory):
        """Test starting and stopping the engine."""
        with patch('dialogchain.connectors.create_connector', mock_connector_factory), \
             patch('dialogchain.processors.create_processor', mock_processor_factory):
            
            dialog_engine = engine.DialogEngine(sample_config)
            await dialog_engine.start()
            
            # Verify connectors are connected
            for connector in dialog_engine.connectors.values():
                assert connector.is_connected is True
            
            await dialog_engine.stop()
            
            # Verify connectors are disconnected
            for connector in dialog_engine.connectors.values():
                assert connector.is_connected is False
    
    @pytest.mark.asyncio
    async def test_engine_process_message(self, sample_config, mock_connector_factory, mock_processor_factory):
        """Test processing a message through the engine."""
        with patch('dialogchain.connectors.create_connector', mock_connector_factory), \
             patch('dialogchain.processors.create_processor', mock_processor_factory):
            
            dialog_engine = engine.DialogEngine(sample_config)
            await dialog_engine.start()
            
            # Get the input connector and simulate receiving a message
            input_connector = dialog_engine.connectors["test_input"]
            input_connector.received_messages = [{"text": "Hello"}]
            
            # Process a single message
            await dialog_engine.process_next_message("test_input", workflow="default")
            
            # Verify the processor was called with the message
            mock_processor = mock_processor_factory()
            mock_processor.process.assert_awaited_once_with({"text": "Hello"})
            
            # Verify the output connector received the processed message
            output_connector = dialog_engine.connectors["test_output"]
            assert len(output_connector.sent_messages) == 1
            assert output_connector.sent_messages[0][0] == {"processed": True}
            
            await dialog_engine.stop()
    
    @pytest.mark.asyncio
    async def test_engine_invalid_workflow(self, sample_config, mock_connector_factory, mock_processor_factory):
        """Test processing with an invalid workflow name."""
        with patch('dialogchain.connectors.create_connector', mock_connector_factory), \
             patch('dialogchain.processors.create_processor', mock_processor_factory):
            
            dialog_engine = engine.DialogEngine(sample_config)
            await dialog_engine.start()
            
            with pytest.raises(exceptions.ConfigurationError) as exc_info:
                await dialog_engine.process_next_message("test_input", workflow="nonexistent")
            assert "Unknown workflow" in str(exc_info.value)
            
            await dialog_engine.stop()
    
    @pytest.mark.asyncio
    async def test_engine_error_handling(self, sample_config, mock_connector_factory, mock_processor_factory):
        """Test error handling during message processing."""
        # Create a processor that raises an exception
        mock_processor = AsyncMock()
        mock_processor.process.side_effect = Exception("Test error")
        mock_processor_factory.return_value = mock_processor
        
        with patch('dialogchain.connectors.create_connector', mock_connector_factory), \
             patch('dialogchain.processors.create_processor', mock_processor_factory):
            
            dialog_engine = engine.DialogEngine(sample_config)
            await dialog_engine.start()
            
            # Get the input connector and simulate receiving a message
            input_connector = dialog_engine.connectors["test_input"]
            input_connector.received_messages = [{"text": "Hello"}]
            
            # Process a message that will cause an error
            with pytest.raises(Exception) as exc_info:
                await dialog_engine.process_next_message("test_input", workflow="default")
            assert "Test error" in str(exc_info.value)
            
            await dialog_engine.stop()
    
    @pytest.mark.asyncio
    async def test_engine_context_manager(self, sample_config, mock_connector_factory, mock_processor_factory):
        """Test using the engine as a context manager."""
        with patch('dialogchain.connectors.create_connector', mock_connector_factory), \
             patch('dialogchain.processors.create_processor', mock_processor_factory):
            
            async with engine.DialogEngine(sample_config) as dialog_engine:
                # Verify connectors are connected
                for connector in dialog_engine.connectors.values():
                    assert connector.is_connected is True
                
                # The engine should be running
                assert dialog_engine.is_running is True
            
            # After exiting the context, connectors should be disconnected
            for connector in dialog_engine.connectors.values():
                assert connector.is_connected is False
            assert dialog_engine.is_running is False
