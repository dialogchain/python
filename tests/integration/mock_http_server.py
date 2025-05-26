"""
Mock HTTP server for integration testing
"""
import asyncio
import json
from aiohttp import web
from typing import Dict, Any, List, Optional
import yaml
import os

class MockHTTPServer:
    """Mock HTTP server for testing"""
    
    def __init__(self, config_path: str = None):
        """Initialize the mock server with configuration"""
        self.app = web.Application()
        self.routes = []
        self.config = {}
        
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
        
        self.setup_routes()
    
    def load_config(self, config_path: str):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def setup_routes(self):
        """Set up the mock server routes"""
        print("Setting up routes...")
        
        if 'mock_server' not in self.config:
            print("No 'mock_server' section found in config")
            return
            
        mock_config = self.config['mock_server']
        endpoints = mock_config.get('endpoints', [])
        print(f"Found {len(endpoints)} endpoints in config")
        
        async def handle_request(request):
            """Generic request handler"""
            path = request.path
            method = request.method
            print(f"\nReceived {method} request to {path}")
            
            # Find matching endpoint (case-insensitive path matching)
            for endpoint in mock_config.get('endpoints', []):
                endpoint_path = endpoint.get('path')
                endpoint_method = endpoint.get('method', 'GET').upper()
                
                print(f"Checking endpoint: {endpoint_method} {endpoint_path}")
                
                if (endpoint_path == path or 
                    (isinstance(endpoint_path, str) and endpoint_path.lower() == path.lower())) and \
                   endpoint_method == method:
                    
                    print(f"Matched endpoint: {endpoint}")
                    
                    # Get request body if present
                    request_data = {}
                    if method in ['POST', 'PUT', 'PATCH']:
                        try:
                            request_data = await request.json()
                        except:
                            request_data = {}
                            try:
                                request_data = await request.text()
                            except:
                                pass
                    
                    print(f"Request data: {request_data}")
                    
                    # Prepare response
                    response_data = endpoint.get('response', {})
                    status = response_data.get('status', 200)
                    body = response_data.get('body', {})
                    
                    print(f"Sending response - Status: {status}, Body: {body}")
                    
                    # If body is a string, return it as text/plain
                    if isinstance(body, str):
                        return web.Response(text=body, status=status)
                        
                    # Otherwise, return as JSON
                    return web.json_response(data=body, status=status)
            
            print(f"No matching endpoint found for {method} {path}")
            return web.Response(
                status=404, 
                text=f"No endpoint found for {method} {path}. Available endpoints: {[e.get('path') for e in mock_config.get('endpoints', [])]}"
            )
        
        # Register a catch-all route
        self.app.router.add_route('*', '/{path:.*}', handle_request)
        print("Added catch-all route")
    
    async def start(self, host: str = 'localhost', port: int = 8080):
        """Start the mock server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        print(f"Mock server started at http://{host}:{port}")
    
    async def stop(self):
        """Stop the mock server"""
        await self.runner.cleanup()

async def start_mock_server(config_path: str = None, host: str = 'localhost', port: int = 8080):
    """Start a mock HTTP server for testing"""
    server = MockHTTPServer(config_path)
    await server.start(host, port)
    return server

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run a mock HTTP server for testing')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--host', type=str, default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    
    args = parser.parse_args()
    
    loop = asyncio.get_event_loop()
    server = MockHTTPServer(args.config)
    
    try:
        loop.run_until_complete(server.start(args.host, args.port))
        loop.run_forever()
    except KeyboardInterrupt:
        print("Shutting down server...")
        loop.run_until_complete(server.stop())
    finally:
        loop.close()
