"""
Tests for the main routing engine
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from dialogchain.engine import CamelRouterEngine
from dialogchain.exceptions import ConfigurationError, ValidationError

class TestCamelRouterEngine:
    
    @pytest.fixture
    def sample_config(self):
        return {
            'routes': [
                {
                    'name': 'test_route',
                    'from': 'timer://5s',
                    'processors': [
                        {
                            'type': 'transform',
                            'template': 'Hello {{message}}'
                        }
                    ],
                    'to': 'log://test.log'
                }
            ]
        }
    
    def test_engine_initialization(self, sample_config):
        engine = CamelRouterEngine(sample_config)
        assert engine.config == sample_config
        assert len(engine.routes) == 1
    
    def test_invalid_config_raises_error(self):
        invalid_config = {'invalid': 'config'}
        with pytest.raises(Exception):
            engine = CamelRouterEngine(invalid_config)
            errors = engine.validate_config()
            assert len(errors) > 0
    
    def test_route_validation(self, sample_config):
        engine = CamelRouterEngine(sample_config)
        errors = engine.validate_config()
        assert len(errors) == 0
    
    def test_variable_resolution(self, sample_config):
        engine = CamelRouterEngine(sample_config)
        
        with patch.dict('os.environ', {'TEST_VAR': 'test_value'}):
            result = engine.resolve_variables('{{TEST_VAR}}')
            assert result == 'test_value'
    
    @pytest.mark.asyncio
    async def test_single_route_execution(self, sample_config):
        engine = CamelRouterEngine(sample_config)
        
        with patch.object(engine, 'run_route_config') as mock_run:
            mock_run.return_value = None
            await engine.run_route('test_route')
            mock_run.assert_called_once()
    
    def test_dry_run_execution(self, sample_config):
        engine = CamelRouterEngine(sample_config, verbose=True)
        
        # Should not raise any exceptions
        engine.dry_run('test_route')
        engine.dry_run()  # All routes
    
    def test_source_creation(self, sample_config):
        engine = CamelRouterEngine(sample_config)
        
        # Test timer source
        source = engine.create_source('timer://5s')
        assert source is not None
        
        # Test RTSP source
        source = engine.create_source('rtsp://user:pass@host/stream')
        assert source is not None
        
        # Test invalid source
        with pytest.raises(ValueError):
            engine.create_source('invalid://source')
    
    def test_processor_creation(self, sample_config):
        engine = CamelRouterEngine(sample_config)
        
        # Test transform processor
        processor = engine.create_processor({
            'type': 'transform',
            'template': 'test'
        })
        assert processor is not None
        
        # Test filter processor
        processor = engine.create_processor({
            'type': 'filter',
            'condition': 'true'
        })
        assert processor is not None
        
        # Test invalid processor
        with pytest.raises(ValueError):
            engine.create_processor({'type': 'invalid'})
    
    def test_destination_creation(self, sample_config):
        engine = CamelRouterEngine(sample_config)
        
        # Test log destination
        dest = engine.create_destination('log://test.log')
        assert dest is not None
        
        # Test email destination
        dest = engine.create_destination('email://smtp.test.com:587?user=test&password=pass&to=test@test.com')
        assert dest is not None
        
        # Test invalid destination
        with pytest.raises(ValueError):
            engine.create_destination('invalid://dest')

@pytest.mark.asyncio
class TestAsyncRouteExecution:
    
    @pytest.fixture
    def async_config(self):
        return {
            'routes': [
                {
                    'name': 'async_test',
                    'from': 'timer://1s',
                    'processors': [
                        {
                            'type': 'external',
                            'command': 'echo test',
                            'async': True
                        }
                    ],
                    'to': 'log://async_test.log'
                }
            ]
        }
    
    async def test_async_route_execution(self, async_config):
        engine = CamelRouterEngine(async_config)
        
        # Mock the actual execution
        with patch.object(engine, 'execute_route') as mock_execute:
            mock_execute.return_value = None
            await engine.run_route('async_test')
            mock_execute.assert_called_once()