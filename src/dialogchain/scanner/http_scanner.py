"""
HTTP scanner for DialogChain.
Scans HTTP/HTTPS endpoints for configuration files.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urljoin, urlparse

import aiohttp

from .base import BaseScanner, ScannerError

logger = logging.getLogger(__name__)

class HttpScanner(BaseScanner):
    """Scanner for HTTP/HTTPS configuration endpoints."""
    
    def __init__(self, url: Union[str, Dict[str, Any]], timeout: int = 30):
        """Initialize HTTP scanner.
        
        Args:
            url: Base URL to scan (string or dict with 'url' key)
            timeout: Request timeout in seconds
            
        If a dictionary is provided, it should contain:
            - url: Base URL to scan (required)
            - timeout: Request timeout in seconds (optional, defaults to 30)
            - headers: Dictionary of headers to include in the request (optional)
            - method: HTTP method (defaults to 'GET')
        """
        # Handle dictionary input
        if isinstance(url, dict):
            config = url
            url = config.get('url')
            if not url:
                raise ValueError("Configuration must contain 'url' key")
            timeout = config.get('timeout', timeout)
            self.headers = config.get('headers')
            self.method = config.get('method', 'GET')
        else:
            self.headers = None
            self.method = 'GET'
            
        self.url = url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'HttpScanner':
        """Create an HTTP scanner from configuration.
        
        Args:
            config: Scanner configuration dictionary
            
        Returns:
            Configured HttpScanner instance
        """
        return cls(**config)
    
    async def scan(self) -> List[str]:
        """Scan HTTP endpoint for configurations.
        
        Returns:
            List of configuration URLs
            
        Raises:
            ScannerError: If the scan fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        raise ScannerError(
                            f"HTTP {response.status} when accessing {self.url}"
                        )
                    
                    # Try to parse response as JSON
                    try:
                        data = await response.json()
                        if isinstance(data, list) and all(isinstance(x, str) for x in data):
                            return data
                        elif isinstance(data, dict) and 'configs' in data and \
                                isinstance(data['configs'], list) and \
                                all(isinstance(x, str) for x in data['configs']):
                            return data['configs']
                        else:
                            # If we can't parse as a list of URLs, return the original URL
                            return [self.url]
                    except ValueError:
                        # If not JSON, return the original URL
                        return [self.url]
                        
        except aiohttp.ClientError as e:
            raise ScannerError(f"Failed to access {self.url}: {e}") from e
        except asyncio.TimeoutError as e:
            raise ScannerError(f"Timeout while accessing {self.url}") from e
