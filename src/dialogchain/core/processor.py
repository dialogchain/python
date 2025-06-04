"""
Message processing for DialogChain engine.

This module handles the processing of messages through a series of processors.
"""

from typing import Any, Dict, List, Optional, Callable, Awaitable
import asyncio
import logging

from dialogchain.processors import Processor

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Handles processing of messages through a series of processors."""
    
    def __init__(self, processors: List[Processor] = None):
        """Initialize the message processor.
        
        Args:
            processors: List of processors to apply to messages
        """
        self.processors = processors or []
    
    async def process(self, message: Any) -> Any:
        """Process a message through all processors.
        
        Args:
            message: The message to process
            
        Returns:
            The processed message, or None if the message was filtered out
        """
        processed_message = message
        
        for processor in self.processors:
            try:
                processed_message = await processor.process(processed_message)
                if processed_message is None:
                    logger.debug("Message was filtered out by processor")
                    return None
            except Exception as e:
                logger.error(f"Error in processor {processor.__class__.__name__}: {e}", exc_info=True)
                raise
        
        return processed_message
    
    @classmethod
    def from_config(cls, config: Dict[str, Any], create_processor: Callable) -> 'MessageProcessor':
        """Create a message processor from a configuration.
        
        Args:
            config: Processor configuration
            create_processor: Function to create a processor from a config
            
        Returns:
            Configured MessageProcessor instance
        """
        processors = []
        
        for proc_config in config.get('processors', []):
            try:
                processor = create_processor(proc_config)
                if processor:
                    processors.append(processor)
            except Exception as e:
                logger.error(f"Error creating processor: {e}", exc_info=True)
                raise
        
        return cls(processors=processors)
