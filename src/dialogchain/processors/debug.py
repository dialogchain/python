"""
Debug Processor Module

This module implements a simple debug processor for logging messages.
"""
import logging
from typing import Any, Optional

from .base import Processor

logger = logging.getLogger(__name__)

class DebugProcessor(Processor):
    """Simple processor that logs messages for debugging purposes."""
    
    def __init__(self, prefix: str = "DEBUG", **kwargs):
        """Initialize the debug processor.
        
        Args:
            prefix: Prefix to use in log messages
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        self.prefix = prefix
    
    async def process(self, message: Any) -> Any:
        """Log the message and pass it through.
        
        Args:
            message: The message to log
            
        Returns:
            The original message
        """
        try:
            logger.info(f"{self.prefix}: {message}")
            return message
        except Exception as e:
            logger.error(f"Error in DebugProcessor: {e}", exc_info=True)
            return message
