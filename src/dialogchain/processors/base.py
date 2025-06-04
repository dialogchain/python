"""
Base Processor Module

This module contains the base Processor class that all processors should inherit from.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class Processor(ABC):
    """Base class for all processors.
    
    Processors transform or filter messages as they flow through the pipeline.
    All processor implementations should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, **kwargs):
        """Initialize the processor with any required configuration."""
        self.config = kwargs
    
    @abstractmethod
    async def process(self, message: Any) -> Optional[Any]:
        """Process a message.
        
        Args:
            message: The message to process
            
        Returns:
            The processed message, or None if the message should be filtered out
            
        Raises:
            Exception: If there's an error processing the message
        """
        pass
