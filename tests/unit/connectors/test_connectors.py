"""
Tests for dialog chain connectors
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import AsyncIterator
from dialogchain.connectors import Source, Destination, HTTPDestination, MQTTDestination

class TestConnectors:
    
    def test_base_source_abstract(self):
        """Test that the base Source class is abstract"""
        with pytest.raises(TypeError):
            Source()
            
    def test_base_destination_abstract(self):
        """Test that the base Destination class is abstract"""
        with pytest.raises(TypeError):
            Destination()
    
    @pytest.mark.asyncio
    async def test_http_destination(self):
        """Test the HTTP destination"""
        connector = HTTPDestination('http://example.com/test')
        assert connector.uri == 'http://example.com/test'
        
        # Test async send with mock
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await connector.send({'test': 'data'})
            mock_post.assert_called_once_with('http://example.com/test', json={'test': 'data'})
    
    @pytest.mark.asyncio
    async def test_mqtt_destination(self):
        """Test the MQTT destination"""
        connector = MQTTDestination('mqtt://broker.example.com:1883/test/topic')
        assert connector.broker == 'broker.example.com'
        assert connector.port == 1883
        assert connector.topic == 'test/topic'
        
        # Test that send method exists and can be called
        # Note: The actual MQTT implementation would need a running MQTT broker for a real test
        result = await connector.send({'test': 'data'})
        assert result is None  # The current implementation doesn't return anything
    
    @pytest.mark.asyncio
    async def test_mqtt_destination_with_auth(self):
        """Test MQTT destination with authentication"""
        connector = MQTTDestination('mqtt://user:pass@broker.example.com:1883/test/topic')
        assert connector.broker == 'broker.example.com'
        assert connector.port == 1883
        assert connector.topic == 'test/topic'
        
        # Test that send method exists and can be called
        result = await connector.send({'test': 'auth_data'})
        assert result is None  # The current implementation doesn't return anything
