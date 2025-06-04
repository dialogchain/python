"""
Route management for DialogChain engine.

This module handles the configuration and execution of routes in the DialogChain engine.
"""

from typing import Dict, List, Any, Optional, AsyncIterator
import asyncio
import logging

from dialogchain.connectors import Source, Destination
from dialogchain.processors import Processor

logger = logging.getLogger(__name__)


class Route:
    """Represents a route in the DialogChain engine."""
    
    def __init__(
        self,
        name: str,
        source: Source,
        processors: List[Processor],
        destinations: List[Destination],
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize a route.
        
        Args:
            name: Name of the route
            source: Source connector
            processors: List of processors to apply to messages
            destinations: List of destination connectors
            config: Additional route configuration
        """
        self.name = name
        self.source = source
        self.processors = processors or []
        self.destinations = destinations or []
        self.config = config or {}
        self._is_running = False
        self._task = None
    
    async def start(self):
        """Start the route."""
        if self._is_running:
            logger.warning(f"Route {self.name} is already running")
            return
            
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Started route: {self.name}")
    
    async def stop(self):
        """Stop the route."""
        if not self._is_running:
            return
            
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Stopped route: {self.name}")
    
    async def _run_loop(self):
        """Main loop for processing messages from the source."""
        try:
            async for message in self.source.receive():
                if not self._is_running:
                    break
                    
                try:
                    # Process the message through all processors
                    processed_message = message
                    for processor in self.processors:
                        processed_message = await processor.process(processed_message)
                        if processed_message is None:
                            logger.debug(f"Message filtered out by processor in route {self.name}")
                            break
                    
                    if processed_message is not None:
                        # Send to all destinations
                        for destination in self.destinations:
                            try:
                                await destination.send(processed_message)
                            except Exception as e:
                                logger.error(f"Error sending to destination in route {self.name}: {e}", exc_info=True)
                
                except Exception as e:
                    logger.error(f"Error processing message in route {self.name}: {e}", exc_info=True)
                    
        except asyncio.CancelledError:
            logger.info(f"Route {self.name} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Route {self.name} encountered an error: {e}", exc_info=True)
            raise
    
    @classmethod
    def from_config(
        cls, 
        config: Dict[str, Any], 
        create_source, 
        create_processor, 
        create_destination
    ) -> 'Route':
        """Create a route from a configuration dictionary.
        
        Args:
            config: Route configuration
            create_source: Function to create a source from a URI
            create_processor: Function to create a processor from a config
            create_destination: Function to create a destination from a URI
            
        Returns:
            Configured Route instance
        """
        name = config.get('name', 'unnamed')
        
        # Create source
        source_uri = config.get('from')
        if not source_uri:
            raise ValueError(f"Route {name} is missing 'from' URI")
        source = create_source(source_uri)
        
        # Create processors
        processors = []
        for proc_config in config.get('processors', []):
            try:
                processor = create_processor(proc_config)
                if processor:
                    processors.append(processor)
            except Exception as e:
                logger.error(f"Error creating processor in route {name}: {e}", exc_info=True)
                raise
        
        # Create destinations
        destinations = []
        to_uris = config.get('to', [])
        if isinstance(to_uris, str):
            to_uris = [to_uris]
            
        for dest_uri in to_uris:
            try:
                destination = create_destination(dest_uri)
                if destination:
                    destinations.append(destination)
            except Exception as e:
                logger.error(f"Error creating destination in route {name}: {e}", exc_info=True)
                raise
        
        if not destinations:
            logger.warning(f"Route {name} has no valid destinations")
        
        return cls(
            name=name,
            source=source,
            processors=processors,
            destinations=destinations,
            config=config
        )
