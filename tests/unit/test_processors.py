"""
Tests for processors
"""
import pytest
import asyncio
import tempfile
import json
from unittest.mock import Mock, patch, mock_open
from dialogchain.processors import (
    ExternalProcessor, FilterProcessor, 
    TransformProcessor, AggregateProcessor
)

class TestExternalProcessor:
    
    def test_init(self):
        config = {
            'command': 'echo test',
            'input_format': 'json',
            'output_format': 'json'
        }
        processor = ExternalProcessor(config)
        assert processor.command == 'echo test'
        assert processor.input_format == 'json'
        assert processor.output_format == 'json'
    
    @pytest.mark.asyncio
    async def test_process_success(self):
        config = {
            'command': 'echo {"result": "success"}',
            'input_format': 'json',
            'output_format': 'json'
        }
        processor = ExternalProcessor(config)
        
        message = {'test': 'data'}
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"result": "success"}'
            
            result = await processor.process(message)
            assert result['result'] == 'success'
    
    @pytest.mark.asyncio
    async def test_process_failure(self):
        config = {
            'command': 'false',  # Command that always fails
            'timeout': 5
        }
        processor = ExternalProcessor(config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = 'Command failed'
            
            result = await processor.process({'test': 'data'})
            assert result is None

class TestFilterProcessor:
    
    def test_init(self):
        config = {'condition': '{{value}} > 10'}
        processor = FilterProcessor(config)
        assert processor.condition == '{{value}} > 10'
    
    @pytest.mark.asyncio
    async def test_filter_pass(self):
        config = {'condition': '{{value}} > 10'}
        processor = FilterProcessor(config)
        
        message = {'value': 15}
        result = await processor.process(message)
        assert result == message
    
    @pytest.mark.asyncio
    async def test_filter_block(self):
        config = {'condition': '{{value}} > 10'}
        processor = FilterProcessor(config)
        
        message = {'value': 5}
        result = await processor.process(message)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_filter_error_passthrough(self):
        config = {'condition': '{{invalid_syntax}'}
        processor = FilterProcessor(config)
        
        message = {'value': 5}
        result = await processor.process(message)
        assert result == message  # Should pass through on error

class TestTransformProcessor:
    
    def test_init(self):
        config = {'template': 'Hello {{name}}'}
        processor = TransformProcessor(config)
        assert processor.template_str == 'Hello {{name}}'
    
    @pytest.mark.asyncio
    async def test_transform_dict_message(self):
        config = {'template': 'Hello {{name}}'}
        processor = TransformProcessor(config)
        
        message = {'name': 'World'}
        result = await processor.process(message)
        assert result['message'] == 'Hello World'
        assert result['name'] == 'World'  # Original data preserved
    
    @pytest.mark.asyncio
    async def test_transform_string_message(self):
        config = {'template': 'Processed: {{message}}'}
        processor = TransformProcessor(config)
        
        message = 'test data'
        result = await processor.process(message)
        assert result['message'] == 'Processed: test data'
        assert result['original'] == 'test data'

class TestAggregateProcessor:
    
    def test_init(self):
        config = {
            'strategy': 'collect',
            'timeout': '30s',
            'max_size': 10
        }
        processor = AggregateProcessor(config)
        assert processor.strategy == 'collect'
        assert processor.max_size == 10
    
    @pytest.mark.asyncio
    async def test_aggregate_below_threshold(self):
        config = {
            'strategy': 'collect',
            'timeout': '1h',  # Long timeout
            'max_size': 10
        }
        processor = AggregateProcessor(config)
        
        # Send messages below max_size
        for i in range(5):
            result = await processor.process(f'message_{i}')
            assert result is None  # Should not flush yet
    
    @pytest.mark.asyncio
    async def test_aggregate_max_size_reached(self):
        config = {
            'strategy': 'collect',
            'timeout': '1h',
            'max_size': 3
        }
        processor = AggregateProcessor(config)
        
        # Send messages to reach max_size
        for i in range(2):
            result = await processor.process(f'message_{i}')
            assert result is None
        
        # Third message should trigger flush
        result = await processor.process('message_2')
        assert result is not None
        assert result['count'] == 3
        assert len(result['events']) == 3
    
    def test_timeout_parsing(self):
        config = {'timeout': '30s'}
        processor = AggregateProcessor(config)
        assert processor.timeout == 30
        
        config = {'timeout': '5m'}
        processor = AggregateProcessor(config)
        assert processor.timeout == 300
        
        config = {'timeout': '1h'}
        processor = AggregateProcessor(config)
        assert processor.timeout == 3600

@pytest.mark.integration
class TestProcessorIntegration:
    
    @pytest.mark.asyncio
    async def test_processor_chain(self):
        """Test chaining multiple processors"""
        
        # Create a chain: Transform -> Filter -> Transform
        transform1 = TransformProcessor({
            'template': 'Value: {{value}}'
        })
        
        filter_proc = FilterProcessor({
            'condition': '{{value}} > 5'
        })
        
        transform2 = TransformProcessor({
            'template': 'Final: {{message}}'
        })
        
        # Test message that should pass through
        message = {'value': 10}
        
        result = await transform1.process(message)
        assert 'Value: 10' in result['message']
        
        result = await filter_proc.process(result)
        assert result is not None
        
        result = await transform2.process(result)
        assert 'Final:' in result['message']
        
        # Test message that should be filtered out
        message = {'value': 3}
        
        result = await transform1.process(message)
        result = await filter_proc.process(result)
        assert result is None