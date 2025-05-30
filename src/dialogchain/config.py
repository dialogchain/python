"""
Configuration management for Camel Router
"""
import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from .exceptions import ConfigurationError, ValidationError


class RouteConfig:
    """Route configuration management"""

    def __init__(self, config_data: Dict[str, Any]):
        self.data = config_data
        self.validate()

    def validate(self):
        """Validate route configuration"""
        errors = []

        if "routes" not in self.data:
            errors.append("Missing 'routes' section")

        for i, route in enumerate(self.data.get("routes", [])):
            route_name = route.get("name", f"route-{i}")

            if "from" not in route:
                errors.append(f"Route '{route_name}': Missing 'from' field")

            if "to" not in route:
                errors.append(f"Route '{route_name}': Missing 'to' field")

            # Validate processors
            for j, processor in enumerate(route.get("processors", [])):
                if "type" not in processor:
                    errors.append(
                        f"Route '{route_name}', Processor {j}: Missing 'type' field"
                    )

                proc_type = processor.get("type")
                if proc_type == "external" and "command" not in processor:
                    errors.append(
                        f"Route '{route_name}', Processor {j}: External processor missing 'command'"
                    )

        if errors:
            raise ValidationError(
                "Configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    @classmethod
    def from_file(cls, filepath: str) -> "RouteConfig":
        """Load configuration from YAML file"""
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
            return cls(data)
        except Exception as e:
            raise ConfigurationError(f"Error loading config file {filepath}: {e}")

    def get_routes(self) -> List[Dict[str, Any]]:
        """Get all routes"""
        return self.data.get("routes", [])

    def get_route(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific route by name"""
        for route in self.get_routes():
            if route.get("name") == name:
                return route
        return None

    def get_settings(self) -> Dict[str, Any]:
        """Get global settings"""
        return self.data.get("settings", {})

    def get_env_vars(self) -> List[str]:
        """Get required environment variables"""
        return self.data.get("env_vars", [])


class ConfigResolver:
    """Resolve configuration with environment variables"""

    @staticmethod
    def resolve_env_vars(text: str, env_override: Dict[str, str] = None) -> str:
        """Resolve environment variables in text.
        
        Supports both ${VAR} and {{VAR}} syntax, including default values with ${VAR:default}.
        """
        import re
        from jinja2 import Template

        env_vars = dict(os.environ)
        if env_override:
            env_vars.update(env_override)

        try:
            # First try Jinja2 templating with {{VAR}}
            template = Template(text)
            result = template.render(**env_vars)
            
            # If the result still contains ${VAR}, try replacing those too
            if "${" in result:
                def replace_var(match):
                    var_expr = match.group(1)
                    # Handle default values in format ${VAR:default}
                    if ':' in var_expr:
                        var_name, default = var_expr.split(':', 1)
                        return env_vars.get(var_name.strip(), default.strip())
                    # Simple variable replacement
                    return env_vars.get(var_expr, match.group(0))
                
                result = re.sub(r"\${([^}]+)}", replace_var, result)
                
            return result
        except Exception as e:
            raise ConfigurationError(f"Error resolving variables in '{text}': {e}")

    @staticmethod
    def check_required_env_vars(required_vars: List[str]) -> List[str]:
        """Check if required environment variables are set"""
        missing = []
        for var in required_vars:
            if var not in os.environ:
                missing.append(var)
        return missing


class ConfigValidator:
    """Configuration validation utilities"""

    SUPPORTED_SCHEMES = {
        "sources": ["rtsp", "timer", "file", "grpc", "mqtt"],
        "destinations": ["email", "http", "https", "mqtt", "grpc", "file", "log"],
    }

    PROCESSOR_TYPES = ["external", "filter", "transform", "aggregate", "debug"]

    @classmethod
    def validate_uri(cls, uri: str, uri_type: str) -> List[str]:
        """Validate URI format"""
        from urllib.parse import urlparse

        errors = []
        try:
            parsed = urlparse(uri)
            if not parsed.scheme:
                errors.append(f"Missing scheme in URI: {uri}")
                return errors
                
            scheme = parsed.scheme.lower()

            valid_schemes = cls.SUPPORTED_SCHEMES.get(uri_type, [])
            if scheme not in valid_schemes:
                errors.append(
                    f"Unsupported scheme '{scheme}' for {uri_type}. "
                    f"Supported schemes: {valid_schemes}"
                )

            if not parsed.netloc and scheme not in ["file", "log", "timer"]:
                errors.append(f"Missing host/netloc in URI: {uri}")

        except Exception as e:
            errors.append(f"Invalid URI format: {uri} - {e}")

        return errors

    @classmethod
    def validate_processor(cls, processor: Dict[str, Any]) -> List[str]:
        """Validate processor configuration"""
        errors = []

        proc_type = processor.get("type")
        if proc_type not in cls.PROCESSOR_TYPES:
            errors.append(
                f"Unsupported processor type '{proc_type}'. Supported: {cls.PROCESSOR_TYPES}"
            )

        if proc_type == "external":
            if "command" not in processor:
                errors.append("External processor requires 'command' field")

        if proc_type == "filter":
            if "condition" not in processor:
                errors.append("Filter processor requires 'condition' field")

        if proc_type == "transform":
            if "template" not in processor:
                errors.append("Transform processor requires 'template' field")

        return errors
