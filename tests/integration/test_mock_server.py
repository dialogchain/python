"""
Test the mock HTTP server
"""
import pytest
import asyncio
import aiohttp
import socket
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

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
    
    # Get the port from config
    port = config['mock_server']['port']
    
    # Start the mock server
    server = MockHTTPServer()
    server.config = config  # Set the config with dynamic port
    await server.start('localhost', port)
    
    yield server
    
    # Stop the mock server
    await server.stop()

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
            assert echo_data["echo"] == test_data
        
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
        # Get data from the mock server
        async with session.get(f"http://localhost:{port}/api/data") as response:
            assert response.status == 200, f"Failed to GET /api/data: {await response.text()}"
            data = await response.json()
            
            # Create a mock message to process
            message = {
                'data': data,
                'metadata': {}
            }
            
            # Create a mock destination
            destination = HTTPDestination(f"http://localhost:{port}/api/echo")
            
            # Process the message through the route
            processed = await engine.process_route(test_config['routes'][0], message, destination)
            
            # Verify the processed data
            assert processed is not None, "No data was processed"
            assert "Processed: " in str(processed), f"Unexpected processed data: {processed}"
            
            # Verify the data was sent to the echo endpoint
            async with session.get(f"http://localhost:{port}/api/echo") as echo_response:
                assert echo_response.status == 200, f"Failed to GET /api/echo: {await echo_response.text()}"
