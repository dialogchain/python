"""HTTP destination implementation for DialogChain."""

import asyncio
import json
import logging
import aiohttp
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse, parse_qs

from ....exceptions import DestinationError
from ..base import Destination

logger = logging.getLogger(__name__)

class HTTPDestination(Destination):
    """HTTP/HTTPS destination for sending data to web services."""
    
    def __init__(
        self, 
        uri: str, 
        method: str = 'POST',
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize HTTP destination.
        
        Args:
            uri: Target URL (e.g., 'http://example.com/api')
            method: HTTP method (GET, POST, PUT, etc.)
            timeout: Request timeout in seconds
            headers: Custom headers to include in requests
            auth: Optional (username, password) for basic auth
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        super().__init__(uri)
        self.method = method.upper()
        self.timeout = timeout
        self.headers = headers or {'Content-Type': 'application/json'}
        self.auth = auth
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session = None
    
    async def _connect(self):
        """Create an aiohttp client session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                auth=aiohttp.BasicAuth(*self.auth) if self.auth else None,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
    
    async def _disconnect(self):
        """Close the aiohttp client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def send(self, data: Any) -> None:
        """Send data to the HTTP endpoint.
        
        Args:
            data: Data to send (will be JSON-serialized if not bytes/str)
            
        Raises:
            DestinationError: If sending fails after all retries
        """
        if not self.is_connected:
            await self.connect()
        
        # Prepare request data
        json_data = None
        data_bytes = None
        
        if isinstance(data, (str, bytes)):
            data_bytes = data if isinstance(data, bytes) else data.encode('utf-8')
        else:
            try:
                json_data = data
            except (TypeError, ValueError) as e:
                raise DestinationError(f"Failed to serialize data to JSON: {e}") from e
        
        # Try the request with retries
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self._session.request(
                    method=self.method,
                    url=self.uri,
                    json=json_data,
                    data=data_bytes,
                    ssl=None if self.verify_ssl else False
                ) as response:
                    if 200 <= response.status < 300:
                        logger.debug(f"Successfully sent data to {self.uri}")
                        return
                    
                    # Log error response
                    error_text = await response.text()
                    last_error = f"HTTP {response.status}: {error_text}"
                    logger.warning(f"HTTP request failed (attempt {attempt}/{self.max_retries}): {last_error}")
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_error = str(e)
                logger.warning(f"HTTP request error (attempt {attempt}/{self.max_retries}): {last_error}")
            
            # If we have retries left, wait before the next attempt
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay * attempt)  # Exponential backoff
        
        # If we get here, all retries failed
        raise DestinationError(f"Failed to send data to {self.uri} after {self.max_retries} attempts. Last error: {last_error}")
    
    def __str__(self):
        """String representation of the destination."""
        return f"HTTP Destination: {self.method} {self.uri}"
