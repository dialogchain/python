"""
Connector management for DialogChain engine.

This module handles the creation and management of source and destination connectors.
"""

from typing import Dict, Any, Optional, Type, Union, List
from urllib.parse import urlparse, parse_qs, ParseResult

from ..connectors import Source, Destination, ConnectorError

class ConnectorManager:
    """Manages the creation and lifecycle of connectors."""
    
    def __init__(
        self,
        source_types: Optional[Dict[str, Type[Source]]] = None,
        destination_types: Optional[Dict[str, Type[Destination]]] = None
    ):
        """Initialize the connector manager.
        
        Args:
            source_types: Optional dictionary of source types to source classes
            destination_types: Optional dictionary of destination types to destination classes
        """
        self.source_types = source_types or {}
        self.destination_types = destination_types or {}
        
        # Register built-in connectors
        self._register_builtin_connectors()
    
    def _register_builtin_connectors(self) -> None:
        """Register built-in source and destination connectors."""
        from ..connectors.sources import (
            RTSPSource, TimerSource, FileSource, IMAPSource
        )
        from ..connectors.destinations import (
            HTTPDestination, EmailDestination, FileDestination, LogDestination
        )
        
        # Register built-in sources
        self.register_source('rtsp', RTSPSource)
        self.register_source('timer', TimerSource)
        self.register_source('file', FileSource)
        self.register_source('imap', IMAPSource)
        
        # Register built-in destinations
        self.register_destination('http', HTTPDestination)
        self.register_destination('https', HTTPDestination)
        self.register_destination('smtp', EmailDestination)
        self.register_destination('file', FileDestination)
        self.register_destination('log', LogDestination)
    
    def register_source(self, scheme: str, source_class: Type[Source]) -> None:
        """Register a source connector class.
        
        Args:
            scheme: URI scheme (e.g., 'http', 'file')
            source_class: Source class to register
        """
        self.source_types[scheme] = source_class
    
    def register_destination(self, scheme: str, dest_class: Type[Destination]) -> None:
        """Register a destination connector class.
        
        Args:
            scheme: URI scheme (e.g., 'http', 'file')
            dest_class: Destination class to register
        """
        self.destination_types[scheme] = dest_class
    
    def create_source(self, config: Union[str, Dict[str, Any]]) -> Source:
        """Create a source connector from a URI or config dictionary.
        
        Args:
            config: Either a URI string or a config dictionary
            
        Returns:
            Configured Source instance
            
        Raises:
            ValueError: If the source type is unknown
            ConnectorError: If there's an error creating the connector
        """
        if isinstance(config, str):
            return self._create_source_from_uri(config)
        if isinstance(config, dict):
            return self._create_source_from_config(config)
        raise ValueError(f"Invalid source config type: {type(config)}")
    
    def create_destination(self, config: Union[str, Dict[str, Any]]) -> Destination:
        """Create a destination connector from a URI or config dictionary.
        
        Args:
            config: Either a URI string or a config dictionary
            
        Returns:
            Configured Destination instance
            
        Raises:
            ValueError: If the destination type is unknown
            ConnectorError: If there's an error creating the connector
        """
        if isinstance(config, str):
            return self._create_destination_from_uri(config)
        if isinstance(config, dict):
            return self._create_destination_from_config(config)
        raise ValueError(f"Invalid destination config type: {type(config)}")
    
    def _create_source_from_uri(self, uri: str) -> Source:
        """Create a source from a URI string."""
        config = self._parse_uri_to_config(uri)
        return self._create_source_from_config(config)
    
    def _create_destination_from_uri(self, uri: str) -> Destination:
        """Create a destination from a URI string."""
        config = self._parse_uri_to_config(uri)
        return self._create_destination_from_config(config)
    
    def _parse_uri_to_config(self, uri: str) -> Dict[str, Any]:
        """Parse a URI into a configuration dictionary."""
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()
        
        # Create base config
        config = {
            'uri': uri,
            'scheme': scheme,
            'path': parsed.path or ''
        }
        
        # Add query parameters
        if parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            for key, value in query_params.items():
                config[key] = value[0] if len(value) == 1 else value
        
        # Add optional components
        if parsed.netloc:
            config['netloc'] = parsed.netloc
        if parsed.params:
            config['params'] = dict(parse_qs(parsed.params))
        if parsed.fragment:
            config['fragment'] = parsed.fragment
        if parsed.username:
            config['username'] = parsed.username
        if parsed.password:
            config['password'] = parsed.password
        if parsed.hostname:
            config['hostname'] = parsed.hostname
        if parsed.port is not None:
            config['port'] = parsed.port
            
        return config
    
    def _create_source_from_config(self, config: Dict[str, Any]) -> Source:
        """Create a source from a config dictionary."""
        source_type = self._get_connector_type(config, 'source')
        try:
            return self.source_types[source_type](config)
        except Exception as e:
            raise ConnectorError(f"Failed to create source from config: {e}") from e
    
    def _create_destination_from_config(self, config: Dict[str, Any]) -> Destination:
        """Create a destination from a config dictionary."""
        dest_type = self._get_connector_type(config, 'destination')
        try:
            return self.destination_types[dest_type](config)
        except Exception as e:
            raise ConnectorError(f"Failed to create destination from config: {e}") from e
    
    def _get_connector_type(self, config: Dict[str, Any], connector_kind: str) -> str:
        """Get the connector type from config and validate it exists."""
        if not isinstance(config, dict):
            raise ValueError(f"{connector_kind.capitalize()} config must be a dictionary")
        
        connector_type = config.get('type') or config.get('scheme')
        if not connector_type:
            raise ValueError(f"{connector_kind.capitalize()} config must include 'type' or 'scheme'")
        
        if connector_type not in getattr(self, f"{connector_kind}_types"):
            raise ValueError(f"Unknown {connector_kind} type: {connector_type}")
            
        return connector_type
    
    def get_source_schemes(self) -> List[str]:
        """Get a list of registered source schemes."""
        return list(self.source_types.keys())
    
    def get_destination_schemes(self) -> List[str]:
        """Get a list of registered destination schemes."""
        return list(self.destination_types.keys())
    
    async def close(self) -> None:
        """Close all connectors and release resources."""
        # No resources to clean up in the base implementation
        pass

# Default connector manager instance
default_connector_manager = ConnectorManager()
