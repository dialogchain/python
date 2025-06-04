"""Base classes for DialogChain connectors."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class Connector(ABC):
    """Base class for all connectors."""
    
    def __init__(self, uri: str):
        """Initialize the connector with a URI.
        
        Args:
            uri: Connection string in the format 'scheme://[user:password@]host[:port][/path][?query]'
        """
        self.uri = uri
        self.parsed_uri = urlparse(uri)
        self._is_connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if the connector is connected."""
        return self._is_connected
    
    async def connect(self):
        """Establish a connection to the resource."""
        if self._is_connected:
            return self
        
        try:
            await self._connect()
            self._is_connected = True
            logger.debug(f"Connected to {self.__class__.__name__}: {self.uri}")
            return self
        except Exception as e:
            self._is_connected = False
            logger.error(f"Failed to connect to {self.uri}: {e}")
            raise
    
    async def disconnect(self):
        """Close the connection to the resource."""
        if not self._is_connected:
            return
        
        try:
            await self._disconnect()
            logger.debug(f"Disconnected from {self.__class__.__name__}: {self.uri}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.uri}: {e}")
            raise
        finally:
            self._is_connected = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return await self.connect()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    @abstractmethod
    async def _connect(self):
        """Implementation-specific connection logic."""
        pass
    
    @abstractmethod
    async def _disconnect(self):
        """Implementation-specific disconnection logic."""
        pass


class Source(Connector):
    """Base class for all data sources."""
    
    @abstractmethod
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Async generator that yields data from the source.
        
        Yields:
            Dictionary containing the received data and metadata
        """
        pass
    
    @classmethod
    def create(cls, uri: str, **kwargs) -> 'Source':
        """Create a source instance from a URI.
        
        Args:
            uri: Source URI (e.g., 'rtsp://...', 'imap://...')
            **kwargs: Additional arguments for the source
            
        Returns:
            Source: An instance of the appropriate source class
            
        Raises:
            ValueError: If the URI scheme is not supported
        """
        from . import sources
        
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()
        
        # Map scheme to source class
        source_classes = {
            'rtsp': sources.RTSPSource,
            'imap': sources.IMAPSource,
            'file': sources.FileSource,
            'timer': sources.TimerSource,
        }
        
        if scheme not in source_classes:
            raise ValueError(f"Unsupported source scheme: {scheme}")
        
        return source_classes[scheme](uri, **kwargs)


class Destination(Connector):
    """Base class for all data destinations."""
    
    @abstractmethod
    async def send(self, data: Any) -> None:
        """Send data to the destination.
        
        Args:
            data: The data to send
            
        Raises:
            Exception: If sending fails
        """
        pass
    
    @classmethod
    def create(cls, uri: str, **kwargs) -> 'Destination':
        """Create a destination instance from a URI.
        
        Args:
            uri: Destination URI (e.g., 'http://...', 'smtp://...')
            **kwargs: Additional arguments for the destination
            
        Returns:
            Destination: An instance of the appropriate destination class
            
        Raises:
            ValueError: If the URI scheme is not supported
        """
        from . import destinations
        
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()
        
        # Map scheme to destination class
        dest_classes = {
            'http': destinations.HTTPDestination,
            'https': destinations.HTTPDestination,
            'smtp': destinations.EmailDestination,
            'file': destinations.FileDestination,
            'log': destinations.LogDestination,
        }
        
        if scheme not in dest_classes:
            raise ValueError(f"Unsupported destination scheme: {scheme}")
        
        return dest_classes[scheme](uri, **kwargs)
