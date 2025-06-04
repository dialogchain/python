"""
Base Source Module

This module contains the base Source class that all data sources should inherit from.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional

class Source(ABC):
    """Base class for all data sources.
    
    All source implementations should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, **kwargs):
        """Initialize the source with any required configuration."""
        self.is_connected = False
        self.config = kwargs
    
    async def connect(self) -> None:
        """Establish connection to the data source."""
        self.is_connected = True
    
    async def disconnect(self) -> None:
        """Close connection to the data source."""
        self.is_connected = False
    
    @abstractmethod
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield messages from the source.
        
        This is an async generator that should yield messages as they become
        available from the source.
        
        Yields:
            Dict[str, Any]: A dictionary containing the message data
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
