"""
Tests for the main routing engine
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from dialogchain.engine import DialogChainEngine
from dialogchain.exceptions import ConfigurationError, ValidationError

class TestDialogChainEngine:
    
    @pytest.fixture
    def sample_config(self):
        return {
            'routes': [
                {
                    'name': 'test_route',
                    'from': 'timer://5s',
                    'processors': [
                        {
                            'type': 'log',
                            'message': 'Processing message'
                        }
                    ]
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self, sample_config):
        """Test that the engine initializes with a valid config"""
        engine = DialogChainEngine(sample_config)
        assert engine is not None
        assert len(engine.routes) == 1
        assert engine.routes[0].name == 'test_route'
