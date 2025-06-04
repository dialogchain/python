"""Route configuration and management for DialogChain."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Type, TypeVar
import yaml
import os

from ..exceptions import ConfigurationError
from ..connectors import Source, Destination
from ..processors import Processor, create_processor

T = TypeVar('T')

@dataclass
class RouteConfig:
    """Configuration for a single route."""
    
    name: str
    source: str
    processors: List[Dict[str, Any]] = field(default_factory=list)
    destinations: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteConfig':
        """Create RouteConfig from a dictionary."""
        return cls(
            name=data.get('name', ''),
            source=data.get('from', ''),
            processors=data.get('processors', []),
            destinations=data.get('to', []),
            config=data.get('config', {})
        )

@dataclass
class Route:
    """A processing route with source, processors, and destinations."""
    
    name: str
    source: Source
    processors: List[Processor] = field(default_factory=list)
    destinations: List[Destination] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'Route':
        """Create a Route from configuration dictionary."""
        if not isinstance(config, dict):
            raise ConfigurationError("Route config must be a dictionary")
            
        name = config.get('name')
        if not name:
            raise ConfigurationError("Route must have a 'name' field")
            
        source_uri = config.get('from')
        if not source_uri:
            raise ConfigurationError(f"Route '{name}' must have a 'from' field")
            
        # Create source
        try:
            source = Source.create(source_uri)
        except Exception as e:
            raise ConfigurationError(f"Failed to create source for route '{name}': {e}")
        
        # Create processors
        processors = []
        for proc_config in config.get('processors', []):
            try:
                processor = create_processor(proc_config)
                processors.append(processor)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create processor for route '{name}': {e}"
                ) from e
        
        # Create destinations
        destinations = []
        for dest_uri in config.get('to', []):
            try:
                dest = Destination.create(dest_uri)
                destinations.append(dest)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create destination for route '{name}': {e}"
                ) from e
        
        return cls(
            name=name,
            source=source,
            processors=processors,
            destinations=destinations,
            config=config.get('config', {})
        )
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'Route':
        """Create a Route from YAML configuration."""
        try:
            config = yaml.safe_load(yaml_str)
            if not isinstance(config, dict):
                raise ConfigurationError("YAML must contain a dictionary")
            return cls.from_config(config)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to load route from YAML: {e}") from e
    
    @classmethod
    def from_yaml_file(cls, file_path: str) -> 'Route':
        """Create a Route from a YAML file."""
        try:
            with open(file_path, 'r') as f:
                return cls.from_yaml(f.read())
        except FileNotFoundError as e:
            raise ConfigurationError(f"Configuration file not found: {file_path}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to load route from file {file_path}: {e}") from e
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert route to dictionary."""
        return {
            'name': self.name,
            'from': str(self.source),
            'processors': [p.to_dict() for p in self.processors],
            'to': [str(d) for d in self.destinations],
            'config': self.config
        }
    
    def validate(self) -> bool:
        """Validate the route configuration."""
        if not self.name:
            raise ConfigurationError("Route must have a name")
        
        if not self.source:
            raise ConfigurationError(f"Route '{self.name}' has no source")
        
        if not self.destinations:
            raise ConfigurationError(f"Route '{self.name}' has no destinations")
        
        return True
