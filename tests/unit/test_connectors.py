"""Unit tests for the connectors module."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp
import pytest_asyncio

from dialogchain import connectors
from dialogchain.config import Config


class TestBaseConnector:
    """Test the base connector functionality."""

    def test_init(self):
        """Test connector initialization."""
        config = {"name": "test_connector", "type": "test", "timeout": 30}
        connector = connectors.BaseConnector(config)
        assert connector.name == "test_connector"
        assert connector.timeout == 30
        assert connector.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connect and disconnect methods."""
        connector = connectors.BaseConnector({"name": "test"})
        await connector.connect()
        assert connector.is_connected is True
        await connector.disconnect()
        assert connector.is_connected is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test connector as a context manager."""
        connector = connectors.BaseConnector({"name": "test"})
        async with connector:
            assert connector.is_connected is True
        assert connector.is_connected is False


class TestHttpConnector:
    """Test the HTTP connector implementation."""

    @pytest.fixture
    def connector_config(self):
        """Return a sample HTTP connector config."""
        return {
            "name": "http_test",
            "type": "http",
            "base_url": "http://example.com/api",
            "timeout": 10,
            "headers": {"X-Test": "test"},
            "auth": {"username": "user", "password": "pass"},
        }

    @pytest.fixture
    def mock_response(self):
        """Create a mock aiohttp response."""
        response = AsyncMock(spec=aiohttp.ClientResponse)
        response.status = 200
        response.json.return_value = {"status": "ok"}
        response.text.return_value = '{"status": "ok"}'
        response.__aenter__.return_value = response
        return response

    @pytest.fixture
    def mock_session(self, mock_response):
        """Create a mock aiohttp client session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.request.return_value = mock_response
        session.__aenter__.return_value = session
        return session

    @pytest.mark.asyncio
    async def test_http_connector_init(self, connector_config):
        """Test HTTP connector initialization."""
        connector = connectors.HttpConnector(connector_config)
        assert connector.base_url == "http://example.com/api"
        assert connector.timeout == 10
        assert connector.headers == {"X-Test": "test"}
        assert connector.auth == aiohttp.BasicAuth("user", "pass")

    @pytest.mark.asyncio
    async def test_http_connector_connect(self, connector_config, mock_session):
        """Test HTTP connector connection."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            connector = connectors.HttpConnector(connector_config)
            await connector.connect()
            assert connector.is_connected is True
            assert connector.session is not None

    @pytest.mark.asyncio
    async def test_http_connector_request(self, connector_config, mock_session, mock_response):
        """Test HTTP connector request method."""
        with patch('aiohttp.ClientSession', return_value=mock_session):
            connector = connectors.HttpConnector(connector_config)
            await connector.connect()
            
            # Test GET request
            response = await connector.request("GET", "/test")
            assert response == {"status": "ok"}
            mock_session.request.assert_called_once_with(
                "GET",
                "http://example.com/api/test",
                headers={"X-Test": "test"},
                auth=aiohttp.BasicAuth("user", "pass"),
                timeout=10,
                json=None,
                data=None,
                params=None
            )
            
            # Reset mock for next test
            mock_session.request.reset_mock()
            
            # Test POST with data
            await connector.request(
                "POST",
                "/test",
                json={"key": "value"},
                headers={"X-Custom": "header"},
                params={"q": "test"}
            )
            mock_session.request.assert_called_once_with(
                "POST",
                "http://example.com/api/test",
                headers={"X-Test": "test", "X-Custom": "header"},
                auth=aiohttp.BasicAuth("user", "pass"),
                timeout=10,
                json={"key": "value"},
                data=None,
                params={"q": "test"}
            )

    @pytest.mark.asyncio
    async def test_http_connector_http_errors(self, connector_config, mock_session, mock_response):
        """Test HTTP connector error handling."""
        # Test 404 error
        mock_response.status = 404
        mock_response.text.return_value = '{"error": "Not found"}'
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            connector = connectors.HttpConnector(connector_config)
            await connector.connect()
            
            with pytest.raises(connectors.ConnectorError) as exc_info:
                await connector.request("GET", "/nonexistent")
            assert "404" in str(exc_info.value)


class TestMqttConnector:
    """Test the MQTT connector implementation."""

    @pytest.fixture
    def connector_config(self):
        """Return a sample MQTT connector config."""
        return {
            "name": "mqtt_test",
            "type": "mqtt",
            "host": "test.mosquitto.org",
            "port": 1883,
            "client_id": "test_client",
            "clean_session": True,
            "topics": ["test/topic"],
        }

    @pytest.fixture
    def mock_mqtt_client(self):
        """Create a mock MQTT client."""
        client = AsyncMock()
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.subscribe = AsyncMock()
        client.unsubscribe = AsyncMock()
        client.publish = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_mqtt_connector_init(self, connector_config):
        """Test MQTT connector initialization."""
        with patch('asyncio_mqtt.Client') as mock_client:
            connector = connectors.MqttConnector(connector_config)
            assert connector.host == "test.mosquitto.org"
            assert connector.port == 1883
            assert connector.client_id == "test_client"

    @pytest.mark.asyncio
    async def test_mqtt_connector_connect_disconnect(self, connector_config, mock_mqtt_client):
        """Test MQTT connector connection and disconnection."""
        with patch('asyncio_mqtt.Client', return_value=mock_mqtt_client):
            connector = connectors.MqttConnector(connector_config)
            
            # Test connect
            await connector.connect()
            assert connector.is_connected is True
            mock_mqtt_client.connect.assert_awaited_once()
            
            # Test subscribe on connect
            mock_mqtt_client.subscribe.assert_awaited_once_with("test/topic")
            
            # Test disconnect
            await connector.disconnect()
            assert connector.is_connected is False
            mock_mqtt_client.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mqtt_connector_publish(self, connector_config, mock_mqtt_client):
        """Test MQTT connector publish method."""
        with patch('asyncio_mqtt.Client', return_value=mock_mqtt_client):
            connector = connectors.MqttConnector(connector_config)
            await connector.connect()
            
            # Test publish
            await connector.publish("test/topic", {"key": "value"}, qos=1)
            mock_mqtt_client.publish.assert_awaited_once()
            
            # Get the actual call arguments
            args, kwargs = mock_mqtt_client.publish.call_args
            assert args[0] == "test/topic"
            assert json.loads(args[1]) == {"key": "value"}
            assert kwargs["qos"] == 1


class TestConnectorFactory:
    """Test the connector factory."""

    def test_create_connector_http(self):
        """Test creating an HTTP connector."""
        config = {"name": "http_test", "type": "http", "base_url": "http://example.com"}
        connector = connectors.create_connector(config)
        assert isinstance(connector, connectors.HttpConnector)
        assert connector.name == "http_test"
        assert connector.base_url == "http://example.com"

    def test_create_connector_mqtt(self):
        """Test creating an MQTT connector."""
        config = {"name": "mqtt_test", "type": "mqtt", "host": "test.mosquitto.org"}
        connector = connectors.create_connector(config)
        assert isinstance(connector, connectors.MqttConnector)
        assert connector.name == "mqtt_test"
        assert connector.host == "test.mosquitto.org"

    def test_create_connector_invalid_type(self):
        """Test creating a connector with an invalid type."""
        config = {"name": "invalid", "type": "invalid_type"}
        with pytest.raises(ValueError) as exc_info:
            connectors.create_connector(config)
        assert "Unknown connector type" in str(exc_info.value)
