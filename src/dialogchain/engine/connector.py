"""
Connector management for DialogChain engine.

This module handles the creation and management of source and destination connectors.
"""

from typing import Dict, Any, Optional, Type, Union
import logging
import importlib
from urllib.parse import urlparse, parse_qs

from ..connectors import Source, Destination, ConnectorError

logger = logging.getLogger(__name__)

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
        logger.debug(f"Registered source connector: {scheme} -> {source_class.__name__}")
    
    def register_destination(self, scheme: str, dest_class: Type[Destination]) -> None:
        """Register a destination connector class.
        
        Args:
            scheme: URI scheme (e.g., 'http', 'file')
            dest_class: Destination class to register
        """
        self.destination_types[scheme] = dest_class
        logger.debug(f"Registered destination connector: {scheme} -> {dest_class.__name__}")
    
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
        elif isinstance(config, dict):
            return self._create_source_from_config(config)
        else:
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
        elif isinstance(config, dict):
            return self._create_destination_from_config(config)
        else:
            raise ValueError(f"Invalid destination config type: {type(config)}")
    
    def _create_source_from_uri(self, uri: str) -> Source:
        """Create a source connector from a URI.
        
        Args:
            uri: Source URI (e.g., 'timer:5s', 'imap://user:pass@server')
            
        Returns:
            Configured Source instance
        """
        if '://' not in uri and ':' in uri:
            # Handle URIs without slashes (e.g., 'timer:5s')
            scheme, path = uri.split(':', 1)
            uri = f"{scheme}://{path}"
        
        parsed = self._parse_uri(uri)
        scheme = parsed['scheme']
        
        if scheme not in self.source_types:
            raise ValueError(f"Unsupported source type: {scheme}")
        
        source_class = self.source_types[scheme]
        try:
            return source_class(uri, **parsed['options'])
        except Exception as e:
            raise ConnectorError(f"Failed to create source {scheme}: {e}") from e
    
    def _create_destination_from_uri(self, uri: str) -> Destination:
        """Create a destination connector from a URI.
        
        Args:
            uri: Destination URI (e.g., 'http://example.com', 'file:/path/to/file')
            
        Returns:
            Configured Destination instance
        """
        parsed = self._parse_uri(uri)
        scheme = parsed['scheme']
        
        if scheme not in self.destination_types:
            raise ValueError(f"Unsupported destination type: {scheme}")
        
        dest_class = self.destination_types[scheme]
        try:
            return dest_class(uri, **parsed['options'])
        except Exception as e:
            raise ConnectorError(f"Failed to create destination {scheme}: {e}") from e
    
    def _create_source_from_config(self, config: Dict[str, Any]) -> Source:
        """Create a source connector from a config dictionary.
        
        Args:
            config: Source configuration dictionary
            
        Returns:
            Configured Source instance
        """
        source_type = config.get('type')
        if not source_type:
            raise ValueError("Source config must include 'type'")
        
        if source_type not in self.source_types:
            # Try to dynamically import the source
            try:
                module_name, _, class_name = source_type.rpartition('.')
                if not module_name:
                    raise ValueError(f"Invalid source type format: {source_type}")
                
                module = importlib.import_module(module_name)
                source_class = getattr(module, class_name)
                self.register_source(source_type, source_class)
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Unknown source type: {source_type}") from e
        
        source_class = self.source_types[source_type]
        try:
            return source_class(**{k: v for k, v in config.items() if k != 'type'})
        except Exception as e:
            raise ConnectorError(f"Failed to create source {source_type}: {e}") from e
    
    def _create_destination_from_config(self, config: Dict[str, Any]) -> Destination:
        """Create a destination connector from a config dictionary.
        
        Args:
            config: Destination configuration dictionary
            
        Returns:
            Configured Destination instance
        """
        dest_type = config.get('type')
        if not dest_type:
            raise ValueError("Destination config must include 'type'")
        
        if dest_type not in self.destination_types:
            # Try to dynamically import the destination
            try:
                module_name, _, class_name = dest_type.rpartition('.')
                if not module_name:
                    raise ValueError(f"Invalid destination type format: {dest_type}")
                
                module = importlib.import_module(module_name)
                dest_class = getattr(module, class_name)
                self.register_destination(dest_type, dest_class)
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Unknown destination type: {dest_type}") from e
        
        dest_class = self.destination_types[dest_type]
        try:
            return dest_class(**{k: v for k, v in config.items() if k != 'type'})
        except Exception as e:
            raise ConnectorError(f"Failed to create destination {dest_type}: {e}") from e
    
    @staticmethod
    def _parse_uri(uri: str) -> Dict[str, Any]:
        """Parse a URI into its components and query parameters.
        
        Args:
            uri: URI to parse
            
        Returns:
            Dictionary with 'scheme', 'netloc', 'path', 'params', 'query', 'fragment',
            and 'options' (query parameters as a dict)
        """
        if '://' not in uri and ':' in uri:
            # Handle simple scheme:path format
            scheme, path = uri.split(':', 1)
            return {
                'scheme': scheme,
                'netloc': '',
                'path': path,
                'params': '',
                'query': '',
                'fragment': '',
                'options': {}
            }
        
        parsed = urlparse(uri)
        options = {}
        
        # Parse query parameters
        if parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            options = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        
        # Add username/password from netloc if present
        if '@' in parsed.netloc:
            auth_part, netloc = parsed.netloc.rsplit('@', 1)
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
                options['username'] = username
                options['password'] = password
        
        return {
            'scheme': parsed.scheme,
            'netloc': parsed.netloc,
            'path': parsed.path,
            'params': parsed.params,
            'query': parsed.query,
            'fragment': parsed.fragment,
            'options': options
        }

# Default connector manager instance
default_connector_manager = ConnectorManager()
