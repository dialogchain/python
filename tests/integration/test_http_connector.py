"""Integration tests for HTTP connector using mock endpoints."""

from unittest.mock import MagicMock, patch

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
    async def test_http_connector_with_mock_server(self, mock_http_server: tuple[web.AppRunner, str]) -> None:
        """Test HTTP connector with a mock HTTP server"""
        runner, server_url = mock_http_server

        # Start the mock server
        await runner.setup()
        site = web.TCPSite(runner, "localhost", int(server_url.split(":")[-1]))
        await site.start()

        try:
            # Test the HTTP connector
            connector = HTTPDestination(f"{server_url}/echo")
            test_data = {"test": "data"}

            # Mock the session to capture the request
            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = MagicMock()
                mock_response.__aenter__.return_value.status = 200
                mock_response.__aenter__.return_value.json.return_value = {
                    "echo": test_data
                }
                mock_post.return_value = mock_response

                await connector.send(test_data)

                # Verify the request was made correctly
                mock_post.assert_called_once_with(f"{server_url}/echo", json=test_data)

        finally:
            # Clean up the server
            await runner.cleanup()

    @pytest.mark.asyncio
    async def test_http_connector_with_real_request(self, mock_http_server):
        """Test HTTP connector with a real request to mock server"""
        runner, server_url = mock_http_server

        # Start the mock server
        await runner.setup()
        site = web.TCPSite(runner, "localhost", int(server_url.split(":")[-1]))
        await site.start()

        try:
            # Test the HTTP connector with a real request
            connector = HTTPDestination(f"{server_url}/echo")
            test_data = {"message": "Hello, World!"}

            # This will make a real HTTP request to our mock server
            async with aiohttp.ClientSession() as session:
                with patch("aiohttp.ClientSession", return_value=session):
                    await connector.send(test_data)

                    # Verify the request was made by checking the server logs
                    # or other side effects if needed

        finally:
            # Clean up the server
            await runner.cleanup()
