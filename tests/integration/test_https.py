"""
Test HTTP source connector for DialogChain
"""
import aiohttp
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from dialogchain.connectors import HTTPDestination

class HTTPSource:
    """HTTP source connector for DialogChain"""
    
    def __init__(self, url: str):
        self.url = url
        self.session = None
        self._data_received = False
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _fetch_data(self):
        """Fetch data from the HTTP endpoint"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        async with self.session.get(self.url) as response:
            if response.status == 200:
                data = await response.json()
                return {'data': data, 'metadata': {'url': self.url, 'status': response.status}}
            else:
                return {'error': f"HTTP {response.status}", 'metadata': {'url': self.url, 'status': response.status}}
    
    async def receive(self):
        """Return an async iterator that yields messages"""
        class HTTPSourceIterator:
            def __init__(self, source):
                self.source = source
                self._data_received = False
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self._data_received:
                    raise StopAsyncIteration
                self._data_received = True
                return await self.source._fetch_data()
        
        return HTTPSourceIterator(self)

# Patch the engine to use our test HTTPSource
@pytest.fixture(autouse=True)
def patch_engine():
    with patch('dialogchain.engine.HTTPSource', new=HTTPSource):
        yield
