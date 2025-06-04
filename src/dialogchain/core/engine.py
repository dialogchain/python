"""Core DialogChain engine implementation."""

import asyncio
import signal
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
import logging

from ..exceptions import DialogChainError, ConfigurationError
from .routes import Route, RouteConfig
from .tasks import TaskManager
from ..connectors import Source, Destination
from ..processors import Processor

logger = logging.getLogger(__name__)

@dataclass
class DialogChainEngine:
    """Main engine class for DialogChain processing."""
    
    config: Dict[str, Any]
    routes: List[Route] = field(default_factory=list)
    tasks: List[asyncio.Task] = field(default_factory=list)
    _is_running: bool = False
    verbose: bool = False
    
    def __post_init__(self):
        """Initialize the engine with configuration."""
        self.task_manager = TaskManager()
        self._setup_logging()
        self._load_config()
    
    def _setup_logging(self):
        """Configure logging based on verbosity."""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_config(self):
        """Load and validate configuration."""
        if not isinstance(self.config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # Load routes from config
        for route_config in self.config.get('routes', []):
            try:
                route = Route.from_config(route_config)
                self.routes.append(route)
                logger.info(f"Loaded route: {route.name}")
            except Exception as e:
                logger.error(f"Failed to load route: {e}")
                if self.verbose:
                    logger.exception("Route loading error")
    
    async def start(self):
        """Start the engine and all routes."""
        if self._is_running:
            logger.warning("Engine is already running")
            return
        
        self._is_running = True
        logger.info("Starting DialogChain engine...")
        
        try:
            for route in self.routes:
                task = asyncio.create_task(self._run_route(route))
                self.tasks.append(task)
            
            logger.info("Engine started successfully")
        except Exception as e:
            logger.error(f"Failed to start engine: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the engine and clean up resources."""
        if not self._is_running:
            return
            
        logger.info("Stopping DialogChain engine...")
        self._is_running = False
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
        logger.info("Engine stopped")
    
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
