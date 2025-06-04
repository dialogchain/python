"""Integration tests for HTTP connector using mock endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import web

from dialogchain.connectors import HTTPDestination


class TestHTTPConnectorIntegration:
    """Integration tests for HTTP connector with mock endpoints."""

    @pytest.fixture
    def mock_http_server(self, unused_tcp_port: int) -> tuple[web.AppRunner, str]:
        """Create a mock HTTP server for testing.
        
        Args:
            unused_tcp_port: A free port number provided by pytest.
            
        Returns:
            A tuple containing the web server runner and its URL.
        """
        async def handle_echo(request: web.Request) -> web.Response:
            """Handle echo requests by returning the received JSON data."""
            data = await request.json()
            return web.json_response({"echo": data})
            
        app = web.Application()
        app.router.add_post("/echo", handle_echo)
        
        runner = web.AppRunner(app)
        return runner, f"http://localhost:{unused_tcp_port}"

    @pytest.mark.asyncio
    async def test_http_connector_with_mock_server(
        self, mock_http_server: tuple[web.AppRunner, str]
    ) -> None:
        """Test HTTP connector with a mock HTTP server.
        
        Args:
            mock_http_server: Fixture that provides a mock HTTP server.
        """
        runner, server_url = mock_http_server
        
        # Start the mock server
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', int(server_url.split(':')[-1]))
        await site.start()
        
        try:
            # Test the HTTP connector
            connector = HTTPDestination(f"{server_url}/echo")
            test_data = {"test": "data"}
            
            # Create a mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json.return_value = {"echo": test_data}
            
            # Create a mock request context manager
            mock_request = MagicMock()
            mock_request.__aenter__.return_value = mock_response
            mock_request.__aexit__.return_value = None
            
            # Create a mock session
            mock_session = MagicMock()
            mock_session.request.return_value = mock_request
            
            # Patch the ClientSession to return our mock session
            with patch('aiohttp.ClientSession', return_value=mock_session):
                # Send the request
                await connector.send(test_data)
                
                # Verify the request was made correctly
                mock_session.request.assert_called_once_with(
                    method='POST',
                    url=f"{server_url}/echo",
                    json=test_data,
                    data=None,
                    ssl=None
                )
                
        finally:
            # Clean up the server
            await runner.cleanup()
    
    @pytest.mark.asyncio
    async def test_http_connector_with_real_request(
        self, mock_http_server: tuple[web.AppRunner, str]
    ) -> None:
        """Test HTTP connector with a real request to mock server.
        
        Args:
            mock_http_server: Fixture that provides a mock HTTP server.
        """
        runner, server_url = mock_http_server
        
        # Start the mock server
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', int(server_url.split(':')[-1]))
        await site.start()
        
        try:
            # Test the HTTP connector with a real request
            connector = HTTPDestination(f"{server_url}/echo")
            test_data = {"message": "Hello, World!"}
            
            # This will make a real HTTP request to our mock server
            async with aiohttp.ClientSession() as session:
                with patch('aiohttp.ClientSession', return_value=session):
                    await connector.send(test_data)
                    
                    # Verify the request was made by checking the server logs
                    # or other side effects if needed
                    
        finally:
            # Clean up the server
            await runner.cleanup()
