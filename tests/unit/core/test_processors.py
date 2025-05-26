"""
Tests for dialog chain processors
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dialogchain.processors import (
    Processor, 
    ExternalProcessor, 
    FilterProcessor, 
    TransformProcessor,
    AggregateProcessor,
    DebugProcessor
)
from dialogchain.exceptions import ProcessorError

class TestProcessors:
    
    def test_base_processor_abstract(self):
        """Test that the base Processor class is abstract"""
        with pytest.raises(TypeError):
            Processor()
    
    @pytest.mark.asyncio
    async def test_external_processor_sync(self):
        """Test the external processor with sync command"""
        config = {
            'command': 'echo',
            'input_format': 'text',
            'output_format': 'text'
        }
        
        with patch('subprocess.run') as mock_run:
            # Mock the subprocess.run to return our expected output
            mock_result = Mock()
            mock_result.stdout = 'test message\n'
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            processor = ExternalProcessor(config)
            result = await processor.process('test message')
            
            # Verify the processor returns a dictionary with the command output
            assert isinstance(result, dict)
            assert 'output' in result
            assert 'test message' in result['output']
            
            # Verify the command was called with the expected arguments
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_filter_processor(self):
        """Test the filter processor"""
        config = {
            'condition': 'value > 10'
        }
        processor = FilterProcessor(config)
        
        # Should pass through
        result = await processor.process({'value': 15})
        assert result == {'value': 15}
        
        # Should filter out
        result = await processor.process({'value': 5})
        assert result is None
    
    @pytest.mark.asyncio
    async def test_transform_processor(self):
        """Test the transform processor"""
        config = {
            'template': '{{ message }} {{ extra }}',
            'output_field': 'transformed'
        }
        processor = TransformProcessor(config)
        
        # Test with string input
        result = await processor.process({
            'message': 'Hello',
            'extra': 'world!'
        })
        assert result == {
            'message': 'Hello',
            'extra': 'world!',
            'transformed': 'Hello world!'
        }
    
    @pytest.mark.asyncio
    async def test_debug_processor(self, capsys):
        """Test the debug processor"""
        processor = DebugProcessor({'prefix': 'TEST'})
        result = await processor.process('test message')
        
        # Should pass through the message unchanged
        assert result == 'test message'
        
        # Should print debug info
        captured = capsys.readouterr()
        assert 'TEST' in captured.out
        assert 'test message' in captured.out
