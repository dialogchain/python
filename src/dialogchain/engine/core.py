"""
Core DialogChain Engine implementation.

This module contains the main DialogChainEngine class that orchestrates
the processing of messages through the configured routes.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
import signal

from ..processors import create_processor
from .route import Route, RouteConfig
from .processor import ProcessorManager
from .connector import ConnectorManager
from ..utils.logger import setup_logger

logger = logging.getLogger(__name__)

class DialogChainEngine:
    """Main engine class for DialogChain processing.
    
    This class manages the lifecycle of routes, processors, and connectors,
    and handles the processing of messages through the configured pipeline.
    """
    
    def __init__(self, config: Dict[str, Any], verbose: bool = False):
        """Initialize the DialogChain engine.
        
        Args:
            config: Engine configuration dictionary
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.running = False
        self.routes: List[Route] = []
        self.processor_manager = ProcessorManager()
        self.connector_manager = ConnectorManager()
        
        # Set up logging
        self.logger = setup_logger(__name__)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        
        # Initialize the engine
        self._init_engine()
    
    def _init_engine(self):
        """Initialize the engine components."""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        # Load routes from config
        self._load_routes()
    
    def _load_routes(self):
        """Load routes from configuration."""
        for route_config in self.config.get('routes', []):
            try:
                route = Route.from_config(
                    route_config,
                    self.processor_manager,
                    self.connector_manager
                )
                self.routes.append(route)
                self.logger.info(f"Loaded route: {route.name}")
            except Exception as e:
                self.logger.error(f"Failed to load route: {e}")
                if self.verbose:
                    self.logger.exception("Route load error:")
    
    async def start(self):
        """Start the engine and all routes."""
        if self.running:
            self.logger.warning("Engine is already running")
            return
            
        self.running = True
        self.logger.info("Starting DialogChain engine...")
        
        try:
            # Start all routes
            for route in self.routes:
                await route.start()
            
            # Keep the engine running
            while self.running:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.logger.info("Shutting down...")
        except Exception as e:
            self.logger.error(f"Engine error: {e}")
            if self.verbose:
                self.logger.exception("Engine error:")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the engine and all routes."""
        if not self.running:
            return
            
        self.running = False
        self.logger.info("Stopping DialogChain engine...")
        
        # Stop all routes
        for route in self.routes:
            try:
                await route.stop()
            except Exception as e:
                self.logger.error(f"Error stopping route {route.name}: {e}")
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop())
    
    @property
    def is_running(self) -> bool:
        """Check if the engine is running."""
        return self.running
    
    async def process_message(self, route_name: str, message: Any) -> Any:
        """Process a message through a specific route.
        
        Args:
            route_name: Name of the route to process the message
            message: Input message to process
            
        Returns:
            Processed output from the route
        """
        route = next((r for r in self.routes if r.name == route_name), None)
        if not route:
            raise ValueError(f"Route not found: {route_name}")
            
        return await route.process(message)
