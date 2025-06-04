"""
Connector management for DialogChain engine.

This module handles the creation and management of source and destination connectors.
"""

from typing import Dict, Any, Optional, Type, List, Union
import importlib
import logging

from dialogchain.connectors import Source, Destination
from dialogchain.connectors.sources import (
    RTSPSource, TimerSource, FileSource, IMAPSource, GRPCSource
)
from dialogchain.connectors.destinations import (
    HTTPDestination, EmailDestination, FileDestination as FileDest,
    LogDestination, MQTTDestination, GRPCDestination
)

logger = logging.getLogger(__name__)


class ConnectorManager:
    """Manages the creation and lifecycle of connectors."""
    
    # Default source mappings
    DEFAULT_SOURCES = {
        'rtsp': RTSPSource,
        'timer': TimerSource,
        'file': FileSource,
        'imap': IMAPSource,
        'grpc': GRPCSource,
    }
    
    # Default destination mappings
    DEFAULT_DESTINATIONS = {
        'http': HTTPDestination,
        'https': HTTPDestination,
        'smtp': EmailDestination,
        'file': FileDest,
        'log': LogDestination,
        'mqtt': MQTTDestination,
        'grpc': GRPCDestination,
    }
    
    def __init__(
        self,
        source_types: Optional[Dict[str, Type[Source]]] = None,
        destination_types: Optional[Dict[str, Type[Destination]]] = None
    ):
        """Initialize the connector manager.
        
        Args:
            source_types: Additional or override source types
            destination_types: Additional or override destination types
        """
        self.source_types = {**self.DEFAULT_SOURCES, **(source_types or {})}
        self.destination_types = {**self.DEFAULT_DESTINATIONS, **(destination_types or {})}
    
    def create_source(self, uri: str) -> Source:
        """Create a source connector from a URI.
        
        Args:
            uri: Source URI (e.g., 'timer:5s', 'imap://user:pass@server')
            
        Returns:
            Configured Source instance
            
        Raises:
            ValueError: If the URI scheme is not recognized
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
        return source_class(uri)
    
    def create_destination(self, uri: str) -> Destination:
        """Create a destination connector from a URI.
        
        Args:
            uri: Destination URI (e.g., 'http://example.com', 'log:info')
            
        Returns:
            Configured Destination instance
            
        Raises:
            ValueError: If the URI scheme is not recognized
        """
        if '://' not in uri and ':' in uri:
            # Handle URIs without slashes (e.g., 'log:info')
            scheme, path = uri.split(':', 1)
            uri = f"{scheme}://{path}"
        
        parsed = self._parse_uri(uri)
        scheme = parsed['scheme']
        
        if scheme not in self.destination_types:
            raise ValueError(f"Unsupported destination type: {scheme}")
        
        dest_class = self.destination_types[scheme]
        return dest_class(uri)
    
    def _parse_uri(self, uri: str) -> Dict[str, str]:
        """Parse a URI into its components.
        
        Args:
            uri: The URI to parse
            
        Returns:
            Dictionary with parsed URI components (scheme, netloc, path, etc.)
        """
        if '://' not in uri and ':' in uri:
            # Handle URIs without slashes (e.g., 'timer:5s')
            scheme, path = uri.split(':', 1)
            return {
                'scheme': scheme,
                'netloc': '',
                'path': path,
                'full': uri
            }
        
        # Use urllib.parse for standard URIs
        from urllib.parse import urlparse
        parsed = urlparse(uri)
        
        return {
            'scheme': parsed.scheme,
            'netloc': parsed.netloc,
            'path': parsed.path.lstrip('/'),
            'params': parsed.params,
            'query': parsed.query,
            'fragment': parsed.fragment,
            'full': uri
        }
