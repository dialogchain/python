"""Unit tests for the processors module."""
import asyncio
import json
from typing import Any, AsyncIterator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import dialogchain.processors as processors
from dialogchain.processors import (
    Processor,
    ExternalProcessor,
    FilterProcessor,
    TransformProcessor,
    AggregateProcessor,
    DebugProcessor
)
from dialogchain.exceptions import ValidationError


class TestProcessor:
    """Test the base Processor class."""
    
    def test_processor_is_abstract(self):
        """Test that Processor is an abstract base class."""
        with pytest.raises(TypeError):
            Processor()  # Should raise TypeError as it's abstract
            
    def test_processor_interface(self):
        """Test the Processor interface."""
        class TestImpl(Processor):
            async def process(self, message: Any) -> Optional[Any]:
                return message
                
        impl = TestImpl()
        assert asyncio.run(impl.process("test")) == "test"
    
    @pytest.mark.asyncio
    async def test_processor_process_not_implemented(self):
        """Test that base process method raises NotImplementedError."""
        # We need to create a concrete class that doesn't implement process
        class TestImpl(Processor):
            pass
            
        with pytest.raises(TypeError):
            TestImpl()


class TestExternalProcessor:
    """Test the ExternalProcessor implementation."""
    
    @pytest.fixture
    def processor_config(self):
        """Return a sample external processor configuration."""
        return {
            "command": "cat",
            "input_format": "json",
            "output_format": "json",
            "async": False,
            "timeout": 10
        }
    
    @patch('subprocess.run')
    def test_external_processor_execution(self, mock_run, processor_config):
        """Test external processor execution."""
        # Mock subprocess run
        mock_result = MagicMock()
        mock_result.stdout = '{"result": "success"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        processor = ExternalProcessor(processor_config)
        result = asyncio.run(processor.process({"key": "value"}))
        
        assert result == {"result": "success"}
        mock_run.assert_called_once()
    
    def test_external_processor_missing_command(self):
        """Test external processor with missing command."""
        with pytest.raises(KeyError) as exc_info:
            ExternalProcessor({})
        assert "command" in str(exc_info.value)


class TestFilterProcessor:
    """Test the FilterProcessor implementation."""
    
    @pytest.fixture
    def processor_config(self):
        """Return a sample filter processor configuration."""
        return {
            "condition": "{{value}} > 10"
        }
    
    async def test_filter_processor_condition(self, processor_config):
        """Test filter processor with condition."""
        processor = FilterProcessor(processor_config)
        
        # Test passing condition
        result = await processor.process({"value": 15})
        assert result == {"value": 15}
        
        # Test failing condition
        result = await processor.process({"value": 5})
        assert result is None
    
    def test_filter_processor_missing_condition(self):
        """Test filter processor with missing condition."""
        with pytest.raises(KeyError):
            FilterProcessor({})          


class TestTransformProcessor:
    """Test the TransformProcessor implementation."""
    
    @pytest.fixture
    def processor_config(self):
        """Return a sample transform processor configuration."""
        return {
            "template": "Processed: {{message}}",
            "output_field": "result"
        }
    
    async def test_transform_processor(self, processor_config):
        """Test transform processor with template."""
        processor = TransformProcessor(processor_config)
        result = await processor.process({"message": "test"})
        # The processor should add the result to the original message
        assert result == {"message": "test", "result": "Processed: test"}
    
    def test_transform_processor_missing_template(self):
        """Test transform processor with missing template."""
        with pytest.raises(KeyError, match="'template'"):
            TransformProcessor({})


class TestAggregateProcessor:
    """Test the AggregateProcessor implementation."""
    
    @pytest.fixture
    def processor_config(self):
        """Return a sample aggregate processor configuration."""
        return {
            "strategy": "collect",
            "timeout": "1s",
            "max_size": 10
        }
    
    async def test_aggregate_processor_collect(self, processor_config):
        """Test aggregate processor with collect strategy."""
        processor = AggregateProcessor(processor_config)
        
        # First message should be buffered
        result = await processor.process({"value": 1})
        assert result is None
        
        # Second message should trigger aggregation (since max_size is 2)
        result = await processor.process({"value": 2})
        assert result is not None
        assert "events" in result
        assert len(result["events"]) == 2
        assert result["events"][0] == {"value": 1}
        assert result["events"][1] == {"value": 2}
        assert "first_timestamp" in result
        assert "last_timestamp" in result
    
    async def test_aggregate_processor_timeout(self, processor_config):
        """Test aggregate processor timeout."""
        # Create a processor with a very short timeout
        config = processor_config.copy()
        config["timeout"] = "0.1s"  # 100ms timeout
        processor = AggregateProcessor(config)
        
        # Send one message
        result = await processor.process({"value": 1})
        assert result is None
        
        # Wait for timeout plus a small buffer
        await asyncio.sleep(0.15)  # 150ms should be enough
        
        # Next process should return the buffered message
        result = await processor.process({"value": 2})
        assert result is not None
        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0] == {"value": 1}


class TestDebugProcessor:
    """Test the DebugProcessor implementation."""
    
    @pytest.fixture
    def processor_config(self):
        """Return a sample debug processor configuration."""
        return {
            "prefix": "TEST"
        }
    
    @patch('builtins.print')
    async def test_debug_processor(self, mock_print, processor_config):
        """Test debug processor logging."""
        processor = DebugProcessor(processor_config)
        result = await processor.process({"key": "value"})
        
        assert result == {"key": "value"}
        mock_print.assert_called()
        assert "TEST" in mock_print.call_args[0][0]
        assert "key" in str(mock_print.call_args[0][0])
        assert "value" in str(mock_print.call_args[0][0])


class TestProcessorFactory:
    """Test the processor factory."""
    
    def test_create_external_processor(self):
        """Test creating an external processor."""
        config = {
            "type": "external",
            "command": "echo {message}"
        }
        processor = processors.create_processor(config)
        assert isinstance(processor, processors.ExternalProcessor)
    
    def test_create_filter_processor(self):
        """Test creating a filter processor."""
        config = {
            "type": "filter",
            "condition": "message == 'test'"
        }
        processor = processors.create_processor(config)
        assert isinstance(processor, processors.FilterProcessor)
    
    def test_create_transform_processor(self):
        """Test creating a transform processor."""
        config = {
            "type": "transform",
            "template": "Processed: {message}",
            "output_field": "result"
        }
        processor = processors.create_processor(config)
        assert isinstance(processor, processors.TransformProcessor)
    
    def test_create_aggregate_processor(self):
        """Test creating an aggregate processor."""
        config = {
            "type": "aggregate",
            "strategy": "collect",
            "timeout": "1s"
        }
        processor = processors.create_processor(config)
        assert isinstance(processor, processors.AggregateProcessor)
    
    def test_create_debug_processor(self):
        """Test creating a debug processor."""
        config = {
            "type": "debug",
            "prefix": "DEBUG"
        }
        processor = processors.create_processor(config)
        assert isinstance(processor, processors.DebugProcessor)
    
    def test_create_unknown_processor(self):
        """Test creating a processor with an unknown type."""
        with pytest.raises(ValueError, match="Unknown processor type: unknown_type"):
            processors.create_processor({"type": "unknown_type"})
