import asyncio
import json
import os
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from jinja2 import Template
import yaml
from .processors import *
from .connectors import *
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
        parsed = urlparse(uri)
        return parsed.scheme, uri.split("://", 1)[1]
    elif ":" in uri:
        # Handle simple URIs with just a scheme:path
        scheme, path = uri.split(":", 1)
        return scheme, path
    else:
        raise ValueError(f"Invalid URI format: {uri}")


class CamelRouterEngine:
    def __init__(self, config: Dict[str, Any], verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.routes = config.get("routes", [])
        self.running_processes = {}

        # Validate the configuration on initialization
        errors = self.validate_config()
        if errors:
            error_msg = "Invalid configuration:\n" + "\n".join(
                f"- {error}" for error in errors
            )
            raise ValueError(error_msg)

    def log(self, message: str):
        if self.verbose:
            print(f"🔄 {message}")

    async def run_all_routes(self):
        """Run all routes concurrently"""
        tasks = []
        for route_config in self.routes:
            task = asyncio.create_task(self.run_route_config(route_config))
            tasks.append(task)

        self.log(f"Starting {len(tasks)} routes...")
        await asyncio.gather(*tasks, return_exceptions=True)

    async def run_route(self, route_name: str):
        """Run specific route by name"""
        route_config = None
        for route in self.routes:
            if route.get("name") == route_name:
                route_config = route
                break

        if not route_config:
            raise ValueError(f"Route '{route_name}' not found")

        await self.run_route_config(route_config)

    async def run_route_config(self, route_config: Dict[str, Any]):
        """Run single route configuration"""
        route_name = route_config.get("name", "unnamed")
        self.log(f"Starting route: {route_name}")

        try:
            # Parse source
            from_uri = self.resolve_variables(route_config["from"])
            source = self.create_source(from_uri)

            # Parse processors
            processors = []
            for proc_config in route_config.get("processors", []):
                processor = self.create_processor(proc_config)
                processors.append(processor)

            # Parse destinations
            to_config = route_config["to"]
            if isinstance(to_config, str):
                to_config = [to_config]

            destinations = []
            for dest_uri in to_config:
                dest_uri = self.resolve_variables(dest_uri)
                destination = self.create_destination(dest_uri)
                destinations.append(destination)

            # Run the route
            await self.execute_route(source, processors, destinations, route_name)

        except Exception as e:
            self.log(f"❌ Error in route {route_name}: {e}")
            raise

    async def execute_route(self, source, processors, destinations, route_name):
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

    def create_source(self, uri: str):
        """Create source connector from URI"""
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()

        if scheme == "rtsp":
            return RTSPSource(uri)
        elif scheme == "timer":
            # For timer URIs, the interval can be in either the netloc or path
            # e.g., timer:5s, timer://5s, or timer:/5s
            interval = parsed.netloc or parsed.path.lstrip("/")
            if not interval:
                raise ValueError(f"No interval specified in timer URI: {uri}")
            return TimerSource(interval)
        elif scheme == "grpc":
            return GRPCSource(uri)
        elif scheme == "file":
            return FileSource(parsed.path)
        else:
            raise ValueError(f"Unsupported source scheme: {scheme}")

    def create_processor(self, config: Dict[str, Any]):
        """Create processor from configuration"""
        proc_type = config["type"]

        if proc_type == "external":
            return ExternalProcessor(config)
        elif proc_type == "filter":
            return FilterProcessor(config)
        elif proc_type == "transform":
            return TransformProcessor(config)
        elif proc_type == "aggregate":
            return AggregateProcessor(config)
        else:
            raise ValueError(f"Unsupported processor type: {proc_type}")

    def create_destination(self, uri: str):
        """Create destination connector from URI"""
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()

        if scheme == "email":
            return EmailDestination(uri)
        elif scheme == "http" or scheme == "https":
            return HTTPDestination(uri)
        elif scheme == "mqtt":
            return MQTTDestination(uri)
        elif scheme == "grpc":
            return GRPCDestination(uri)
        elif scheme == "file":
            return FileDestination(uri)
        elif scheme == "log":
            return LogDestination(uri)
        else:
            raise ValueError(f"Unsupported destination scheme: {scheme}")

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
        """Validate configuration and return list of errors"""
        errors = []

        if "routes" not in self.config:
            errors.append("Missing 'routes' section")
            return errors

        for i, route in enumerate(self.routes):
            route_prefix = f"Route {i + 1}"
            name = route.get("name", f"unnamed-{i}")
            route_prefix += f" ({name})"

            if "from" not in route:
                errors.append(f"{route_prefix}: Missing 'from' field")

            if "to" not in route:
                errors.append(f"{route_prefix}: Missing 'to' field")

            # Validate processors
            if "processors" in route:
                for j, proc in enumerate(route.get("processors", [])):
                    if "type" not in proc:
                        errors.append(
                            f"{route_prefix}, Processor {j + 1}: Missing 'type' field"
                        )

                    proc_type = proc.get("type")
                    if proc_type == "external" and "command" not in proc:
                        errors.append(
                            f"{route_prefix}, Processor {j + 1}: External processor missing 'command'"
                        )

        return errors
