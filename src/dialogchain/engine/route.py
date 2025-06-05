"""
Route management for DialogChain engine.

This module handles the creation and management of processing routes.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..processors import Processor, create_processor
from ..connectors import Source, Destination
from .connector import ConnectorManager

logger = logging.getLogger(__name__)

@dataclass
class RouteConfig:
    """Configuration for a processing route."""
    name: str
    source_config: Dict[str, Any]
    processors: List[Dict[str, Any]]
    destination_config: Dict[str, Any]
    enabled: bool = True
    error_handlers: List[Dict[str, Any]] = field(default_factory=list)
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'RouteConfig':
        """Create a RouteConfig from a dictionary."""
        return cls(
            name=config['name'],
            source_config=config.get('from', {}),
            processors=config.get('processors', []),
            destination_config=config.get('to', {}),
            enabled=config.get('enabled', True),
            error_handlers=config.get('error_handlers', []),
            retry_attempts=config.get('retry_attempts', 3),
            retry_delay=config.get('retry_delay', 1.0),
            timeout=config.get('timeout')
        )

class Route:
    """A processing route that connects a source to a destination through processors."""
    
    def __init__(
        self,
        name: str,
        source: Source,
        processors: List[Processor],
        destination: Destination,
        error_handlers: Optional[List[Dict[str, Any]]] = None,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        verbose: bool = False
    ):
        """Initialize a route.
        
        Args:
            name: Route name
            source: Source connector
            processors: List of processors to apply
            destination: Destination connector
            error_handlers: List of error handlers
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
            timeout: Operation timeout in seconds
            verbose: Enable verbose logging
        """
        self.name = name
        self.source = source
        self.processors = processors or []
        self.destination = destination
        self.error_handlers = error_handlers or []
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.verbose = verbose
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def log(self, message: str, level: str = 'info'):
        """Log a message with the route name as context."""
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(f"[Route {self.name}] {message}")
        
        if self.verbose and level.lower() == 'error':
            import traceback
            self.log(traceback.format_exc(), 'debug')
    
    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        processor_manager: 'ProcessorManager',
        connector_manager: ConnectorManager
    ) -> 'Route':
        """Create a route from a configuration dictionary.
        
        Args:
            config: Route configuration
            processor_manager: Processor manager instance
            connector_manager: Connector manager instance
            
        Returns:
            Configured Route instance
        """
        route_config = RouteConfig.from_dict(config)
        
        # Create source connector
        source = connector_manager.create_source(route_config.source_config)
        
        # Create processors
        processors = [
            processor_manager.create_processor(proc_config)
            for proc_config in route_config.processors
        ]
        
        # Create destination connector
        destination = connector_manager.create_destination(route_config.destination_config)
        
        return cls(
            name=route_config.name,
            source=source,
            processors=processors,
            destination=destination,
            error_handlers=route_config.error_handlers,
            retry_attempts=route_config.retry_attempts,
            retry_delay=route_config.retry_delay,
            timeout=route_config.timeout
        )
    
    async def start(self):
        """Start the route."""
        if self._running:
            self.log("Route is already running", 'warning')
            return

        self._running = True
        self.log("Starting route")

        # Start the processing loop in a background task
        self._task = asyncio.create_task(self._run_loop())
        
    async def stop(self):
        """Stop the route."""
        if not self._running:
            return
            
        self._running = False
        self.log("Stopping route")
        
        # Cancel the background task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                self.log("Processing cancelled")
                
        # Disconnect from source and destination
        try:
            if hasattr(self.source, 'disconnect'):
                await self.source.disconnect()
        except Exception as e:
            self.log(f"Error disconnecting source: {e}", 'error')
            
        try:
            if hasattr(self.destination, 'disconnect'):
                await self.destination.disconnect()
        except Exception as e:
            self.log(f"Error disconnecting destination: {e}", 'error')                       
    
    async def _run_loop(self):
        """Main processing loop for the route."""
        try:
            async with self.source as source:
                while self._running:
                    try:
                        # Get data from source
                        data = await self._safe_receive(source)
                        if data is None:
                            continue
                        
                        # Process the data
                        result = await self.process(data)
                        
                        # Send to destination
                        if result is not None:
                            await self._safe_send(self.destination, result)
                            
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error(f"Error in route {self.name}: {e}")
                        await self._handle_error(e)
        except asyncio.CancelledError:
            logger.info(f"Route {self.name} processing cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in route {self.name}: {e}")
            raise
    
    async def process(self, data: Any) -> Any:
        """Process data through the route's processors.
        
        Args:
            data: The data to process
            
        Returns:
            The processed data or None if processing should stop
        """
        result = data
        
        for processor in self.processors:
            try:
                if self.verbose:
                    self.log(f"Processing with {processor.__class__.__name__}", 'debug')
                    
                result = await processor.process(result)
                
                if result is None:
                    self.log("Processor returned None, stopping processing", 'debug')
                    return None
                    
            except Exception as e:
                self.log(f"Error in processor {processor.__class__.__name__}: {e}", 'error')
                raise
                
        return result
        
    async def _send_to_destination(self, message: Any):
        """Send a message to the destination.
        
        Args:
            message: The message to send
            
        Raises:
            Exception: If sending fails and error handling doesn't suppress it
        """
        try:
            if hasattr(self.destination, 'send'):
                if self.verbose:
                    self.log(f"Sending to destination: {message}", 'debug')
                await self.destination.send(message)
                if self.verbose:
                    self.log("Successfully sent to destination", 'debug')
        except Exception as e:
            self.log(f"Error sending to destination: {e}", 'error')
            raise
            
    async def _handle_error(self, error: Exception, message: Any = None) -> bool:
        """Handle an error that occurred during processing.
        
        Args:
            error: The exception that was raised
            message: Optional message being processed when the error occurred
            
        Returns:
            bool: True if the error was handled successfully, False otherwise
        """
        self.log(f"Handling error: {error}", 'error')
        handled = False
        
        # Execute error handlers
        for handler in self.error_handlers:
            try:
                handler_type = handler.get('type', 'log')
                
                if handler_type == 'log':
                    # Log the error
                    log_message = handler.get('message', 'Error in route {route_name}: {error}')
                    log_message = log_message.format(
                        route_name=self.name,
                        error=str(error),
                        message=message
                    )
                    self.log(log_message, 'error')
                    handled = True
                    
                elif handler_type == 'retry':
                    # Handle retry logic
                    max_attempts = handler.get('max_attempts', 3)
                    delay = handler.get('delay', 1.0)
                    
                    for attempt in range(max_attempts):
                        try:
                            self.log(f"Retry attempt {attempt + 1}/{max_attempts}", 'warning')
                            if message is not None:
                                result = await self.process(message)
                                if result is not None:
                                    await self._send_to_destination(result)
                                    return True
                            await asyncio.sleep(delay)
                        except Exception as retry_error:
                            self.log(f"Retry {attempt + 1} failed: {retry_error}", 'warning')
                            await asyncio.sleep(delay)
                    
                    self.log(f"Max retries ({max_attempts}) exceeded", 'error')
                    
                elif handler_type == 'fallback':
                    # Handle fallback destination
                    fallback_dest = handler.get('destination')
                    if fallback_dest:
                        self.log(f"Using fallback destination: {fallback_dest}", 'warning')
                        # In a real implementation, we would send to the fallback destination
                        handled = True
                
            except Exception as handler_error:
                self.log(f"Error in {handler_type} error handler: {handler_error}", 'error')
        
        return handled
    
    async def _safe_receive(self, source: Source) -> Any:
        """Safely receive data from a source with retries.
        
        Args:
            source: The source to receive data from
            
        Returns:
            The received data, or None if all retries are exhausted
            
        Raises:
            asyncio.TimeoutError: If the operation times out after all retries
            Exception: If an error occurs after all retries
        """
        for attempt in range(self.retry_attempts + 1):
            try:
                return await asyncio.wait_for(
                    source.receive(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                if attempt == self.retry_attempts:
                    self.log("Timeout receiving from source", 'error')
                    raise
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                self.log(f"Error receiving from source: {e}", 'error')
                if attempt == self.retry_attempts:
                    raise
                await asyncio.sleep(self.retry_delay)
        return None
    
    async def _safe_send(self, destination: Destination, data: Any) -> None:
        """Safely send data to a destination with retries.
        
        Args:
            destination: The destination to send data to
            data: The data to send
            
        Raises:
            asyncio.TimeoutError: If the operation times out after all retries
            Exception: If an error occurs after all retries
        """
        for attempt in range(self.retry_attempts + 1):
            try:
                await asyncio.wait_for(
                    destination.send(data),
                    timeout=self.timeout
                )
                return
            except asyncio.TimeoutError:
                if attempt == self.retry_attempts:
                    self.log("Timeout sending to destination", 'error')
                    raise
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                self.log(f"Error sending to destination: {e}", 'error')
                if attempt == self.retry_attempts:
                    raise
                await asyncio.sleep(self.retry_delay)
