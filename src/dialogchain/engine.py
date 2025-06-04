"""
DialogChain Engine - Core processing engine for dialog chains
"""
import aiohttp
import asyncio
import signal
import json
import os
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Generator, AsyncGenerator
from urllib.parse import urlparse, parse_qs
from jinja2 import Template
import yaml

from .processors import (
    Processor, create_processor, FilterProcessor, TransformProcessor,
    AggregateProcessor, DebugProcessor, ExternalProcessor
)

# For backward compatibility
ProcessorType = type(Processor)
from .connectors import (
    Source, Destination, RTSPSource, FileSource, 
    HTTPDestination, FileDestination, IMAPSource, TimerSource, GRPCSource,
    EmailDestination, MQTTDestination, LogDestination, GRPCDestination
)
from dialogchain.utils.logger import setup_logger

logger = setup_logger(__name__)



def parse_uri(uri: str) -> Tuple[str, str]:
    """
    Parse a URI string into its scheme and path components.

    Args:
        uri: The URI string to parse (e.g., 'timer:5s' or 'http://example.com')

    Returns:
        A tuple of (scheme, path) where:
        - scheme is the URI scheme (e.g., 'timer', 'http')
        - path is the rest of the URI after the scheme

    Example:
        >>> parse_uri('timer:5s')
        ('timer', '5s')
        >>> parse_uri('http://example.com/path')
        ('http', '//example.com/path')
    """
    if "://" in uri:
        # Handle standard URIs with ://
        scheme, path = uri.split("://", 1)
        return scheme, f"//{path}"  # Ensure path starts with // for standard URIs
    elif ":" in uri:
        # Handle simple URIs with just a scheme:path
        scheme, path = uri.split(":", 1)
        return scheme, path
    else:
        raise ValueError(f"Invalid URI format: {uri}")


class DialogChainEngine:
    def __init__(self, config: Dict[str, Any], verbose: bool = False):
        # Initialize logger first
        self.logger = setup_logger(__name__)
        self.logger.info("🔧 Initializing DialogChainEngine")
        
        self.config = config
        self.verbose = verbose
        self.routes = config.get("routes", [])
        self.running_processes = {}
        self._is_running = False
        self._tasks = []
        
        self.logger.info(f"🔧 Loaded {len(self.routes)} routes from config")
        if self.verbose:
            self.logger.info(f"🔧 Verbose mode enabled")

        # Validate the configuration on initialization
        self.logger.info("🔧 Validating configuration...")
        errors = self.validate_config()
        if errors:
            error_msg = "Invalid configuration:\n" + "\n".join(
                f"- {error}" for error in errors
            )
            self.logger.error(f"❌ Configuration validation failed: {error_msg}")
            raise ValueError(error_msg)
            
        self.logger.info("✅ Engine initialized successfully")
            
    @property
    def is_running(self) -> bool:
        """Return whether the engine is currently running."""
        return self._is_running
        
    async def start(self):
        """Start the engine and all routes."""
        if self._is_running:
            self.log("Engine is already running")
            return

        self._is_running = True
        self.log("Starting engine...")
        
        # Clear any existing tasks
        self._tasks = []

        try:
            for route in self.routes:
                try:
                    # Create source and connect
                    from_uri = self.resolve_variables(route["from"])
                    source = self.create_source(from_uri)
                    if hasattr(source, 'connect') and callable(source.connect):
                        await source.connect()
                        # Set is_connected flag if it exists
                        if hasattr(source, 'is_connected'):
                            source.is_connected = True

                    # Create destination and connect
                    to_uri = self.resolve_variables(route["to"])
                    destination = self.create_destination(to_uri)
                    if hasattr(destination, 'connect') and callable(destination.connect):
                        await destination.connect()
                        if hasattr(destination, 'is_connected'):
                            destination.is_connected = True

                    # Create and store task
                    task = asyncio.create_task(self.run_route_config(route, source, destination))
                    self._tasks.append(task)
                    self.log(f"✅ Started route: {route.get('name', 'unnamed')}")
                    
                except Exception as e:
                    self.log(f"❌ Failed to start route {route.get('name', 'unnamed')}: {e}")
                    if self.verbose:
                        import traceback
                        self.log(traceback.format_exc())
                    continue
                
            if not self._tasks:
                self.log("⚠️  No routes were started successfully")
                self._is_running = False
            else:
                self.log(f"✅ Engine started with {len(self._tasks)} active routes")
                
        except Exception as e:
            self.log(f"❌ Error starting engine: {e}")
            if self.verbose:
                import traceback
                self.log(traceback.format_exc())
            await self.stop()
            raise
            
    async def stop(self):
        """Stop the engine and all running routes."""
        if not self._is_running:
            return
            
        self.log("Stopping DialogChain engine...")
        self._is_running = False
        
        # Cancel all running tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        self._tasks = []
    
    def run(self):
        """Run the engine until stopped."""
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Start the engine
            self.log("🚀 Starting DialogChain engine...")
            start_task = loop.create_task(self.start())
            loop.run_until_complete(start_task)
            
            # Keep the engine running until interrupted
            self.log("✅ Engine is running. Press Ctrl+C to stop...")
            
            # Set up signal handlers for graceful shutdown
            for signal_name in ('SIGINT', 'SIGTERM'):
                loop.add_signal_handler(
                    getattr(signal, signal_name),
                    lambda: asyncio.create_task(self.stop())
                )
                
            # Keep the main thread alive
            while self._is_running:
                loop.run_until_complete(asyncio.sleep(0.1))
                
        except (KeyboardInterrupt, asyncio.CancelledError):
            self.log("\n🛑 Received shutdown signal. Stopping gracefully...")
        except Exception as e:
            self.log(f"❌ Error in DialogChain engine: {e}")
            if self.verbose:
                import traceback
                self.log(traceback.format_exc())
            raise
        finally:
            # Ensure we clean up properly
            if loop.is_running():
                loop.stop()
                
            # Cancel all running tasks
            pending = asyncio.all_tasks(loop=loop)
            for task in pending:
                task.cancel()
                
            # Run loop until tasks are done
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                
            # Close the loop
            loop.close()
            self.log("✅ DialogChain engine stopped")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    def log(self, message: str):
        if self.verbose:
            print(f"🔄 {message}")

    async def run_all_routes(self):
        """Run all routes concurrently"""
        tasks = []
        for route_config in self.routes:
            try:
                # Create source and destination for this route
                from_uri = self.resolve_variables(route_config.get('from', ''))
                to_uri = self.resolve_variables(route_config.get('to', ''))
                
                if not from_uri or not to_uri:
                    self.log(f"Skipping route '{route_config.get('name', 'unnamed')}': missing 'from' or 'to' URI")
                    continue
                    
                source = self.create_source(from_uri)
                destination = self.create_destination(to_uri)
                
                # Create and start task for this route
                task = asyncio.create_task(
                    self.run_route_config(route_config, source, destination)
                )
                tasks.append(task)
                
            except Exception as e:
                self.log(f"Error setting up route '{route_config.get('name', 'unnamed')}': {e}")
                if self.verbose:
                    import traceback
                    traceback.print_exc()
                continue

        if not tasks:
            self.log("No valid routes to run")
            return
            
        self.log(f"Starting {len(tasks)} routes...")
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run_route_config(self, route: Dict[str, Any], source: Source, destination: Destination):
        """Run a specific route with the given source and destination
        
        Args:
            route: Route configuration dictionary
            source: Source connector instance
            destination: Destination connector instance
            
        This method is called by the engine's start() method for each route.
        It runs the route configuration with the provided source and destination.
        """
        route_name = route.get("name", "unnamed")
        logger.info(f"🔧 Starting route: {route_name}")
        logger.info(f"🔧 Route config: {route}")
        logger.info(f"🔧 Source type: {type(source).__name__}")
        logger.info(f"🔧 Destination type: {type(destination).__name__}")
        self.log(f"Starting route: {route_name}")
        
        if not source:
            logger.error(f"❌ No source provided for route: {route_name}")
            return
            
        if not destination:
            logger.error(f"❌ No destination provided for route: {route_name}")
            return
        
        try:
            # Connect to source if not already connected
            if hasattr(source, 'connect') and callable(source.connect) and not getattr(source, 'is_connected', False):
                await source.connect()
                if hasattr(source, 'is_connected'):
                    source.is_connected = True
            
            # Connect to destination if not already connected
            if hasattr(destination, 'connect') and callable(destination.connect) and not getattr(destination, 'is_connected', False):
                await destination.connect()
                if hasattr(destination, 'is_connected'):
                    destination.is_connected = True
                    
            # Create processors for this route
            processors = []
            for proc_config in route.get("processors", []):
                try:
                    processor = self.create_processor(proc_config)
                    processors.append(processor)
                except Exception as e:
                    self.log(f"Error creating processor in route {route_name}: {e}")
                    raise
                
            # Initialize sent_messages list if it doesn't exist
            if not hasattr(destination, 'sent_messages') or not isinstance(destination.sent_messages, list):
                destination.sent_messages = []
                
            # Process messages from source
            try:
                async for message in source.receive():
                    if not self._is_running:
                        self.log(f"🛑 Stopping route {route_name} (engine shutdown)")
                        break
                        
                    try:
                        # Process message through all processors
                        processed_message = message
                        for processor in processors:
                            try:
                                if hasattr(processor, 'process') and callable(processor.process):
                                    self.log(f"⚙️  Processing message with {type(processor).__name__}")
                                    processed_message = await processor.process(processed_message)
                                    if processed_message is None:
                                        self.log("ℹ️  Message filtered out by processor")
                                        break  # Message was filtered out
                            except Exception as e:
                                self.log(f"❌ Error in processor {type(processor).__name__} in route {route_name}: {e}")
                                if self.verbose:
                                    import traceback
                                    self.log(traceback.format_exc())
                                processed_message = None
                                break
                                
                        # Send to destination if not filtered
                        if processed_message is not None:
                            try:
                                self.log(f"📤 Sending message to destination: {type(destination).__name__}")
                                if hasattr(destination, 'send') and callable(destination.send):
                                    await destination.send(processed_message)
                                    # Store sent messages for testing/verification
                                    if hasattr(destination, 'sent_messages') and isinstance(destination.sent_messages, list):
                                        destination.sent_messages.append(processed_message)
                            except Exception as e:
                                self.log(f"❌ Error sending message to destination in route {route_name}: {e}")
                                if self.verbose:
                                    import traceback
                                    self.log(traceback.format_exc())
                    except Exception as e:
                        self.log(f"❌ Error processing message in route {route_name}: {e}")
                        if self.verbose:
                            import traceback
                            self.log(traceback.format_exc())
            except asyncio.CancelledError:
                self.log(f"🛑 Route {route_name} was cancelled")
                raise
            except Exception as e:
                self.log(f"❌ Error in message loop for route {route_name}: {e}")
                if self.verbose:
                    import traceback
                    self.log(traceback.format_exc())
                raise
                
        except asyncio.CancelledError:
            self.log(f"Route {route_name} cancelled")
            raise
        except Exception as e:
            self.log(f"Unexpected error in route {route_name}: {e}")
            if self.verbose:
                import traceback
                self.log(traceback.format_exc())
            raise
        finally:
            # Clean up resources
            if hasattr(destination, 'disconnect') and callable(destination.disconnect):
                try:
                    await destination.disconnect()
                except Exception as e:
                    self.log(f"Error disconnecting destination in route {route_name}: {e}")
                    
            if hasattr(source, 'disconnect') and callable(source.disconnect):
                try:
                    await source.disconnect()
                except Exception as e:
                    self.log(f"Error disconnecting source in route {route_name}: {e}")
                    
            self.log(f"Stopped route: {route_name}")

        if not route_config:
            raise ValueError(f"Route '{route_name}' not found")

        # Create source and destination for the route
        from_uri = self.resolve_variables(route_config["from"])
        to_uri = self.resolve_variables(route_config["to"])
        source = None
        destination = None
        
        try:
            source = self.create_source(from_uri)
            destination = self.create_destination(to_uri)
            
            # Connect to source and destination
            if hasattr(source, 'connect') and callable(source.connect):
                await source.connect()
                if hasattr(source, 'is_connected'):
                    source.is_connected = True
                    
            if hasattr(destination, 'connect') and callable(destination.connect):
                await destination.connect()
                
            await self.run_route_config(route_config, source, destination)
            
        except asyncio.CancelledError:
            self.log(f"Route {route_name} cancelled")
            raise
        except Exception as e:
            self.log(f"Error in route {route_name}: {e}")
            raise
        finally:
            # Clean up resources
            if destination and hasattr(destination, 'disconnect') and callable(destination.disconnect):
                try:
                    await destination.disconnect()
                except Exception as e:
                    self.log(f"Error disconnecting destination in route {route_name}: {e}")
                    
            if source and hasattr(source, 'disconnect') and callable(source.disconnect):
                try:
                    await source.disconnect()
                except Exception as e:
                    self.log(f"Error disconnecting source in route {route_name}: {e}")
            
            self.log(f"Stopped route: {route_name}")

    async def execute_route(self, source: Source, processors: List[Processor], destinations: List[Destination], route_name: str):
        """Execute the route pipeline"""
        async for message in source.receive():
            try:
                # Process through pipeline
                current_message = message

                for processor in processors:
                    current_message = await processor.process(current_message)
                    if current_message is None:  # Filtered out
                        break

                if current_message is not None:
                    # Send to all destinations
                    send_tasks = []
                    for destination in destinations:
                        task = asyncio.create_task(destination.send(current_message))
                        send_tasks.append(task)

                    await asyncio.gather(*send_tasks, return_exceptions=True)

            except Exception as e:
                self.log(f"❌ Error processing message in {route_name}: {e}")

    def create_source(self, uri: str) -> Source:
        """Create source connector from URI"""
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()
        
        if scheme == "rtsp":
            return RTSPSource(uri)
        elif scheme == "timer":
            return TimerSource(parsed.path)
        elif scheme == "grpc":
            return GRPCSource(uri)
        elif scheme == "file":
            return FileSource(parsed.path)
        elif scheme == "imap":
            return IMAPSource(uri)
        elif scheme == "http" or scheme == "https":
            # Create a simple HTTP source using aiohttp
            class HTTPSource(Source):
                def __init__(self, url):
                    self.url = url
                    self.session = None
                    
                async def receive(self):
                    if not self.session:
                        self.session = aiohttp.ClientSession()
                    async with self.session.get(self.url) as response:
                        data = await response.json()
                        yield data
                        
                async def __aenter__(self):
                    self.session = aiohttp.ClientSession()
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    if self.session:
                        await self.session.close()
                        
            return HTTPSource(uri)
        elif scheme == "mock":
            # For testing purposes
            from unittest.mock import AsyncMock
            mock = AsyncMock()
            mock.receive.return_value = []
            return mock
        else:
            raise ValueError(f"Unsupported source scheme: {scheme}")

    def create_processor(self, processor_config: Dict[str, Any]) -> Processor:
        """
        Create a processor instance from configuration.
        
        Args:
            processor_config: Processor configuration
            
        Returns:
            Processor instance
        """
        proc_type = processor_config.get("type")
        
        if proc_type == "filter":
            return FilterProcessor(processor_config)
        elif proc_type == "transform":
            return TransformProcessor(processor_config)
        elif proc_type == "aggregate":
            return AggregateProcessor(processor_config)
        elif proc_type == "debug":
            return DebugProcessor(processor_config)
        else:
            raise ValueError(f"Unsupported processor type: {proc_type}")
            
    def create_destination(self, uri: str) -> Destination:
        """
        Create a destination based on URI.
        
        Args:
            uri: Destination URI (e.g., 'http://api.example.com')
            
        Returns:
            Destination instance
        """
        scheme, path = parse_uri(uri)
        config = self.config.get("destinations", {}).get(uri, {})
        
        # Remove 'type' from config as it's not a valid parameter for HTTPDestination
        config = {k: v for k, v in config.items() if k != 'type'}
        
        if scheme == "http" or scheme == "https":
            return HTTPDestination(uri, **config)
        elif scheme == "file":
            return FileDestination(path, **config)
        elif scheme == "log":
            # Handle log destination (e.g., log:info, log:error)
            log_level = path.upper() if path else "INFO"
            
            # Create a simple destination that logs messages
            class LogDestination:
                def __init__(self, level):
                    self.level = level
                    self.sent_messages = []
                    
                async def send(self, message):
                    log_message = f"[Log Destination] {message}"
                    if self.level == "DEBUG":
                        self.logger.debug(log_message)
                    elif self.level == "INFO":
                        self.logger.info(log_message)
                    elif self.level == "WARNING":
                        self.logger.warning(log_message)
                    elif self.level == "ERROR":
                        self.logger.error(log_message)
                    elif self.level == "CRITICAL":
                        self.logger.critical(log_message)
                    else:
                        self.logger.info(log_message)  # Default to info
                    
                    # Store the message for testing/verification
                    self.sent_messages.append(message)
                    return True
                    
                async def connect(self):
                    pass
                    
                async def disconnect(self):
                    pass
                    
                async def __aenter__(self):
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            return LogDestination(log_level)
            
        elif scheme == "mock":
            # For testing purposes
            from unittest.mock import AsyncMock
            mock = AsyncMock()
            mock.send = AsyncMock()
            mock.sent_messages = []  # Add sent_messages list for testing
            return mock
        else:
            raise ValueError(f"Unsupported destination type: {scheme}")

    def resolve_variables(self, text: str) -> str:
        """Resolve environment variables in text using Jinja2 templates"""
        if not isinstance(text, str):
            return text

        template = Template(text)
        env_vars = dict(os.environ)

        try:
            return template.render(**env_vars)
        except Exception as e:
            self.log(f"⚠️  Variable resolution failed for '{text}': {e}")
            return text

    def dry_run(self, route_name: Optional[str] = None):
        """Show what would be executed without running"""
        routes_to_check = self.routes
        if route_name:
            routes_to_check = [r for r in self.routes if r.get("name") == route_name]
        else:
            routes_to_check = self.routes

        logger.info("🔍 DRY RUN - Configuration Analysis:")
        logger.info("=" * 50)

        for route in routes_to_check:
            name = route.get("name", "unnamed")
            print(f"\n📍 Route: {name}")
            print(f"   From: {self.resolve_variables(route['from'])}")

            if "processors" in route:
                logger.info("   Processors:")
                for i, proc in enumerate(route["processors"], 1):
                    print(f"     {i}. {proc['type']}")
                    if proc["type"] == "external":
                        print(f"        Command: {proc.get('command', 'N/A')}")

            to_config = route["to"]
            if isinstance(to_config, str):
                to_config = [to_config]

            logger.info("   To:")
            for dest in to_config:
                resolved = self.resolve_variables(dest)
                print(f"     • {resolved}")

    def validate_config(self) -> List[str]:
        """Validate the configuration."""
        errors = []
        if not isinstance(self.config, dict):
            return ["Configuration must be a dictionary"]

        if "routes" not in self.config:
            return ["Missing 'routes' in configuration"]

        for i, route in enumerate(self.config["routes"], 1):
            if not isinstance(route, dict):
                errors.append(f"Route {i}: must be a dictionary")
                continue

            route_name = route.get('name', str(i))
            if "from" not in route:
                errors.append(f"Route {route_name}: Missing 'from' field")
            if "to" not in route:
                errors.append(f"Route {route_name}: Missing 'to' field")
                
            # Validate processors
            if "processors" in route:
                for j, proc in enumerate(route["processors"], 1):
                    if not isinstance(proc, dict):
                        errors.append(f"Route {route_name}, Processor {j}: must be a dictionary")
                        continue
                        
                    proc_type = proc.get("type")
                    if not proc_type:
                        errors.append(f"Route {route_name}, Processor {j}: Missing 'type' field")
                    elif proc_type == "external" and "command" not in proc:
                        errors.append(f"Route {route_name}, Processor {j}: Missing 'command' for external processor")
        
        return errors
        
    async def process_message(self, message: Any, processors: List[Dict[str, Any]]) -> Any:
        """
        Process a message through a series of processors.
        
        Args:
            message: The message to process
            processors: List of processor configurations
            
        Returns:
            The processed message or None if the message should be filtered out
        """
        processed = message
        
        for proc in processors:
            if not processed:
                return None
                
            proc_type = proc.get("type")
            config = proc.get("config", {})
            
            if proc_type == "filter":
                # Apply filter condition
                if not self._evaluate_condition(processed, config.get("condition")):
                    return None
                    
            elif proc_type == "transform":
                # Apply transformation
                if "mapping" in config:
                    transformed = {}
                    for src, dest in config["mapping"].items():
                        if src in processed:
                            transformed[dest] = processed[src]
                    processed.update(transformed)
                    
        return processed
        
    def _evaluate_condition(self, message: Any, condition: Any) -> bool:
        """
        Evaluate a condition against a message.
        
        Args:
            message: The message to evaluate
            condition: The condition to evaluate (can be a dict with operators or a direct value)
            
        Returns:
            bool: True if the condition is met, False otherwise
        """
        if condition is None:
            return True
            
        if isinstance(condition, dict):
            for key, value in condition.items():
                if key == "$eq":
                    return message == value
                elif key == "$ne":
                    return message != value
                elif key == "$gt":
                    return message > value
                elif key == "$lt":
                    return message < value
                elif key == "$gte":
                    return message >= value
                elif key == "$lte":
                    return message <= value
                elif key == "$in":
                    return message in value
                elif key == "$nin":
                    return message not in value
                elif key == "$and" and isinstance(value, list):
                    return all(self._evaluate_condition(message, c) for c in value)
                elif key == "$or" and isinstance(value, list):
                    return any(self._evaluate_condition(message, c) for c in value)
                elif key == "$not":
                    return not self._evaluate_condition(message, value)
                else:
                    # Handle nested conditions
                    if key in message and isinstance(message[key], dict) and isinstance(value, dict):
                        return self._evaluate_condition(message[key], value)
                    return key in message and message[key] == value
                    
        return message == condition
