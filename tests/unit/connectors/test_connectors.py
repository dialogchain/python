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
        })
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={'result': 'success'})
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await connector.send({'test': 'data'})
            assert result == {'result': 'success'}
    
    @pytest.mark.asyncio
    async def test_mqtt_connector(self):
        """Test the MQTT connector"""
        connector = MqttConnector({
            'broker': 'mqtt://test.mosquitto.org',
            'topic': 'test/topic'
        })
        
        with patch('asyncio_mqtt.Client') as mock_mqtt:
            mock_client = AsyncMock()
            mock_mqtt.return_value.__aenter__.return_value = mock_client
            
            await connector.send({'test': 'data'})
            mock_client.publish.assert_called_once()
