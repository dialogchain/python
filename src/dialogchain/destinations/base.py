"""
Base Destination Module

This module contains the base Destination class that all destinations should inherit from.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional

class Destination(ABC):
    """Base class for all data destinations.
    
    All destination implementations should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, **kwargs):
        """Initialize the destination with any required configuration."""
        self.is_connected = False
        self.config = kwargs
        self.sent_messages: List[Any] = []
    
    async def connect(self) -> None:
        """Establish connection to the destination."""
        self.is_connected = True
    
    async def disconnect(self) -> None:
        """Close connection to the destination."""
        self.is_connected = False
    
    @abstractmethod
    async def send(self, message: Any) -> None:
        """Send a message to the destination.
        
        Args:
            message: The message to send. Can be any data type that the destination supports.
            
        Raises:
            Exception: If there's an error sending the message
        """
        pass
    
    def get_sent_messages(self) -> List[Any]:
        """Get a list of all sent messages.
        
        Returns:
            List of all messages that have been sent to this destination
        """
        return self.sent_messages
    
    def clear_sent_messages(self) -> None:
        """Clear the list of sent messages."""
        self.sent_messages = []
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
