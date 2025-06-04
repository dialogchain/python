"""
Test the mock HTTP server
"""
import pytest
import asyncio
import aiohttp
import socket
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Import our test HTTPSource
from .test_https import HTTPSource
from dialogchain.engine import DialogChainEngine

# Get the directory of the current file
TEST_DIR = Path(__file__).parent
CONFIG_PATH = TEST_DIR / "test_config.yaml"


@pytest.fixture
def unused_port():
    """Find an unused port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture
def config(unused_port):
    """Load test configuration with dynamic port"""
    import yaml

    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    # Update the port in the config
    if "mock_server" in config:
        config["mock_server"]["port"] = unused_port

    # Update the port in the routes
    for route in config.get("routes", []):
        if "from" in route:
            route["from"] = route["from"].replace("8080", str(unused_port))
        if "to" in route:
            route["to"] = route["to"].replace("8080", str(unused_port))

    return config


@pytest.fixture
async def mock_server(config):
    """Fixture to start and stop the mock server"""
    from .mock_http_server import MockHTTPServer

    # Create a temporary config file with the updated port
    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        yaml.dump(config, tmp)
        tmp_path = tmp.name

    try:
        # Start the mock server with the config file
        server = MockHTTPServer(tmp_path)
        await server.start("localhost", config["mock_server"]["port"])

        yield server

        # Stop the mock server
        await server.stop()
    finally:
        # Clean up the temporary file
        import os

        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_mock_server_endpoints(mock_server, config):
    """Test the mock server endpoints"""
    port = config["mock_server"]["port"]
    base_url = f"http://localhost:{port}"

    # Test GET /api/data
    async with aiohttp.ClientSession() as session:
        # Test GET /api/data
        async with session.get(f"{base_url}/api/data") as response:
            assert (
                response.status == 200
            ), f"Failed to GET /api/data: {await response.text()}"
            data = await response.json()
            assert "data" in data, f"Response missing 'data' key: {data}"
            assert data["data"] == "test data"

        # Test POST /api/echo
        test_data = {"message": "Hello, World!"}
        async with session.post(f"{base_url}/api/echo", json=test_data) as response:
            assert (
                response.status == 200
            ), f"Failed to POST /api/echo: {await response.text()}"
            echo_data = await response.json()
            assert "echo" in echo_data, f"Response missing 'echo' key: {echo_data}"
            # The echo endpoint returns the processed data as a string
            assert isinstance(
                echo_data["echo"], str
            ), f"Expected string response, got {type(echo_data['echo'])}"
            assert (
                "Processed: " in echo_data["echo"]
            ), f"Expected 'Processed: ' in response: {echo_data}"

        # Test GET /api/events
        async with session.get(f"{base_url}/api/events") as response:
            assert (
                response.status == 200
            ), f"Failed to GET /api/events: {await response.text()}"
            events = await response.json()
            assert isinstance(events, list), f"Expected list, got {type(events)}"
            assert len(events) > 0, "Expected at least one event"
            assert "event" in events[0], f"Event missing 'event' key: {events[0]}"
            assert "value" in events[0], f"Event missing 'value' key: {events[0]}"


class MockSource:
    """Mock source that returns test data directly"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __aiter__(self):
        self._data = [
            {
                "data": {"test": "data"},
                "metadata": {"url": "mock://test", "status": 200},
            }
        ]
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._data):
            raise StopAsyncIteration
        result = self._data[self._index]
        self._index += 1
        return result

    # For backward compatibility with the engine
    def receive(self):
        """Return self as an async iterator"""
        return self


class TestDialogChainEngine(DialogChainEngine):
    """Test engine that uses our mock source"""

    def create_source(self, uri: str):
        """Always return our mock source"""
        return MockSource()


@pytest.mark.asyncio
async def test_dialogchain_with_mock_server(mock_server, config):
    """Test DialogChain with the mock server"""
    from dialogchain.connectors import HTTPDestination

    # Create a test config that uses our mock source
    test_config = {
        "routes": [
            {
                "name": "test_route",
                "from": "mock://test",
                "processors": [
                    {"type": "transform", "template": "Processed: {{ data.test }}"}
                ],
                "to": "mock://destination",
            }
        ]
    }

    # Initialize our test engine with the config
    engine = TestDialogChainEngine(test_config, verbose=True)

    # Create a mock destination to capture the output
    class MockDestination:
        def __init__(self):
            self.received_messages = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def send(self, message):
            self.received_messages.append(message)
            return [{"status": "success"}]

    # Create a mock destination
    mock_dest = MockDestination()

    # Patch the engine's create_destination method to return our mock
    original_create_dest = engine.create_destination

    def patched_create_dest(uri):
        if uri == "mock://destination":
            return mock_dest
        return original_create_dest(uri)

    engine.create_destination = patched_create_dest

    # Run the route configuration
    await engine.run_route_config(test_config["routes"][0])

    # Verify the destination received the processed message
    assert (
        len(mock_dest.received_messages) > 0
    ), "No messages were sent to the destination"
    message = mock_dest.received_messages[0]

    # The message should have the original data and metadata, plus the processed message
    assert "data" in message, f"Message missing 'data' key: {message}"
    assert "metadata" in message, f"Message missing 'metadata' key: {message}"
    assert "message" in message, f"Message missing 'message' key: {message}"

    # Check the processed message
    assert (
        message["message"] == "Processed: data"
    ), f"Unexpected processed message: {message}"

    # Check the original data is preserved
    assert message["data"] == {"test": "data"}, f"Unexpected data: {message['data']}"
    assert (
        message["metadata"]["url"] == "mock://test"
    ), f"Unexpected URL: {message['metadata']['url']}"
