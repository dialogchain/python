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

# Get the directory of the current file
TEST_DIR = Path(__file__).parent
CONFIG_PATH = TEST_DIR / "test_config.yaml"

@pytest.fixture
def unused_port():
    """Find an unused port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

@pytest.fixture
def config(unused_port):
    """Load test configuration with dynamic port"""
    import yaml
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update the port in the config
    if 'mock_server' in config:
        config['mock_server']['port'] = unused_port
    
    # Update the port in the routes
    for route in config.get('routes', []):
        if 'from' in route:
            route['from'] = route['from'].replace('8080', str(unused_port))
        if 'to' in route:
            route['to'] = route['to'].replace('8080', str(unused_port))
    
    return config

@pytest.fixture
async def mock_server(config):
    """Fixture to start and stop the mock server"""
    from .mock_http_server import MockHTTPServer
    
    # Create a temporary config file with the updated port
    import tempfile
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp:
        yaml.dump(config, tmp)
        tmp_path = tmp.name
    
    try:
        # Start the mock server with the config file
        server = MockHTTPServer(tmp_path)
        await server.start('localhost', config['mock_server']['port'])
        
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
    port = config['mock_server']['port']
    base_url = f"http://localhost:{port}"
    
    # Test GET /api/data
    async with aiohttp.ClientSession() as session:
        # Test GET /api/data
        async with session.get(f"{base_url}/api/data") as response:
            assert response.status == 200, f"Failed to GET /api/data: {await response.text()}"
            data = await response.json()
            assert "data" in data, f"Response missing 'data' key: {data}"
            assert data["data"] == "test data"
        
        # Test POST /api/echo
        test_data = {"message": "Hello, World!"}
        async with session.post(
            f"{base_url}/api/echo",
            json=test_data
        ) as response:
            assert response.status == 200, f"Failed to POST /api/echo: {await response.text()}"
            echo_data = await response.json()
            assert "echo" in echo_data, f"Response missing 'echo' key: {echo_data}"
            # The echo endpoint returns the processed data as a string
            assert isinstance(echo_data["echo"], str), f"Expected string response, got {type(echo_data['echo'])}"
            assert "Processed: " in echo_data["echo"], f"Expected 'Processed: ' in response: {echo_data['echo']}"
        
        # Test GET /api/events
        async with session.get(f"{base_url}/api/events") as response:
            assert response.status == 200, f"Failed to GET /api/events: {await response.text()}"
            events = await response.json()
            assert isinstance(events, list), f"Expected list, got {type(events)}"
            assert len(events) > 0, "Expected at least one event"
            assert "event" in events[0], f"Event missing 'event' key: {events[0]}"
            assert "value" in events[0], f"Event missing 'value' key: {events[0]}"

@pytest.mark.asyncio
async def test_dialogchain_with_mock_server(mock_server, config):
    """Test DialogChain with the mock server"""
    from dialogchain.engine import CamelRouterEngine
    from dialogchain.connectors import HTTPDestination
    
    # Get the port from config
    port = config['mock_server']['port']
    
    # Create a test config that uses our mock server
    test_config = {
        "routes": [
            {
                "name": "test_http_route",
                "from": f"http://localhost:{port}/api/data",
                "processors": [
                    {
                        "type": "transform",
                        "template": "Processed: {{ data }}"
                    }
                ],
                "to": f"http://localhost:{port}/api/echo"
            }
        ]
    }
    
    # Initialize the engine with test config
    engine = CamelRouterEngine(test_config, verbose=True)
    
    # Test the route processing
    async with aiohttp.ClientSession() as session:
        # Get data from the mock server to verify it's working
        async with session.get(f"http://localhost:{port}/api/data") as response:
            assert response.status == 200, f"Failed to GET /api/data: {await response.text()}"
            data = await response.json()
            assert "data" in data, f"Unexpected response format: {data}"
        
        # Run the route configuration
        await engine.run_route_config(test_config['routes'][0])
        
        # Verify the data was processed and sent to the echo endpoint
        # We'll check the mock server's echo endpoint to see the processed data
        async with session.get(f"http://localhost:{port}/api/echo") as echo_response:
            assert echo_response.status == 200, f"Failed to GET /api/echo: {await echo_response.text()}"
            echo_data = await echo_response.json()
            assert "echo" in echo_data, f"Unexpected response format from echo: {echo_data}"
            assert "Processed: " in str(echo_data["echo"]), f"Expected 'Processed: ' in response: {echo_data}"
