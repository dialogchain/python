"""Core DialogChain engine implementation."""

import asyncio
import signal
import logging
from typing import Dict, List, Any, Optional, AsyncIterator, Callable, Awaitable
from dataclasses import dataclass, field

from ..exceptions import DialogChainError, ConfigurationError
from .route import Route
from .connector import ConnectorManager
from .processor import MessageProcessor

logger = logging.getLogger(__name__)


class DialogChainEngine:
    """Main engine class for DialogChain processing."""
    
    def __init__(
        self, 
        config: Dict[str, Any], 
        verbose: bool = False,
        connector_manager: Optional[ConnectorManager] = None,
        processor_factory: Optional[Callable[[Dict[str, Any]], Awaitable[Any]]] = None
    ):
        """Initialize the DialogChain engine.
        
        Args:
            config: Engine configuration dictionary
            verbose: Enable verbose logging
            connector_manager: Optional pre-configured connector manager
            processor_factory: Optional custom processor factory function
        """
        self.config = config
        self.verbose = verbose
        self._is_running = False
        self._routes: List[Route] = []
        self._tasks: List[asyncio.Task] = []
        
        # Set up logging
        self._setup_logging()
        
        # Initialize components
        self.connector_manager = connector_manager or ConnectorManager()
        self.processor_factory = processor_factory or self._create_processor
        
        # Load and validate configuration
        self._load_config()
    
    def _setup_logging(self):
        """Configure logging based on verbosity."""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.setLevel(log_level)
    
    def _load_config(self):
        """Load and validate configuration."""
        if not isinstance(self.config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # Load routes from config
        for route_config in self.config.get('routes', []):
            try:
                route = self._create_route(route_config)
                self._routes.append(route)
                logger.info(f"Loaded route: {route.name}")
            except Exception as e:
                logger.error(f"Failed to load route: {e}", exc_info=True)
                if self.verbose:
                    raise
    
    async def _create_processor(self, config: Dict[str, Any]) -> Any:
        """Create a processor from configuration.
        
        This is a default implementation that can be overridden by providing
        a custom processor_factory to the engine constructor.
        """
        # Import here to avoid circular imports
        from ..processors import create_processor
        return create_processor(config)
    
    def _create_route(self, config: Dict[str, Any]) -> Route:
        """Create a route from configuration."""
        return Route.from_config(
            config,
            create_source=self.connector_manager.create_source,
            create_processor=self.processor_factory,
            create_destination=self.connector_manager.create_destination
        )
    
    async def start(self):
        """Start the engine and all routes."""
        if self._is_running:
            logger.warning("Engine is already running")
            return
        
        self._is_running = True
        logger.info("Starting DialogChain engine...")
        
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
        
        # Start all routes
        for route in self._routes:
            try:
                await route.start()
                self._tasks.append(asyncio.create_task(route._run_loop()))
                logger.info(f"Started route: {route.name}")
            except Exception as e:
                logger.error(f"Failed to start route {route.name}: {e}", exc_info=True)
                if self.verbose:
                    raise
                
        logger.info("DialogChain engine started successfully")
    
    async def stop(self):
        """Stop the engine and clean up resources."""
        if not self._is_running:
            return
            
        logger.info("Stopping DialogChain engine...")
        self._is_running = False
        
        # Cancel all running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Stop all routes
        stop_tasks = [route.stop() for route in self._routes]
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        self._tasks.clear()
        logger.info("DialogChain engine stopped")
    
    async def _run_route(self, route: Route):
        """Run a single route."""
        try:
            async with await route.source.connect() as source:
                async for data in source.receive():
                    if not self._is_running:
                        break
                    
                    try:
                        processed = await self._process_data(route, data)
                        if processed is not None:
                            await self._send_to_destinations(route, processed)
                    except Exception as e:
                        logger.error(f"Error processing data: {e}")
                        if self.verbose:
                            logger.exception("Processing error")
        except Exception as e:
            logger.error(f"Route '{route.name}' failed: {e}")
            if self.verbose:
                logger.exception("Route execution error")
    
    async def _process_data(self, route: Route, data: Any) -> Any:
        """Process data through the route's processors."""
        processed = data
        for processor in route.processors:
            try:
                processed = await processor.process(processed)
                if processed is None:
                    return None
            except Exception as e:
                logger.error(f"Processor {processor.__class__.__name__} failed: {e}")
                if self.verbose:
                    logger.exception("Processor error")
                return None
        return processed
    
    async def _send_to_destinations(self, route: Route, data: Any):
        """Send processed data to all destinations."""
        for destination in route.destinations:
            try:
                await destination.send(data)
            except Exception as e:
                logger.error(f"Failed to send to {destination}: {e}")
                if self.verbose:
                    logger.exception("Send error")
    
    def run(self):
        """Run the engine in the current event loop."""
        loop = asyncio.get_event_loop()
        
        try:
            # Start the engine
            loop.run_until_complete(self.start())
            
            # Run forever until interrupted
            loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down...")
        finally:
            # Cleanup
            loop.run_until_complete(self.stop())
            loop.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        
        if exc_type is not None:
            logger.error(f"Engine exited with error: {exc_val}")
            if self.verbose and exc_tb:
                import traceback
                logger.error(traceback.format_exc())
            return False
        return True
