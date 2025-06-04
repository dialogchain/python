"""
DialogChain - A flexible dialog processing framework

A powerful framework for building and managing dialog processing pipelines
with support for various sources, processors, and destinations.

Features:
- YAML-based configuration
- Support for multiple data sources and destinations
- Extensible processor architecture
- Built-in utility functions
- Asynchronous processing

Usage:
    dialogchain run -c config.yaml
    dialogchain init --template basic
    dialogchain validate -c config.yaml
"""

import logging
from typing import Dict, Any, Optional, Type, List, Union

__version__ = "0.2.0"
__author__ = "DialogChain Team"

# Import core components
from .engine import (
    DialogChainEngine,
    Route,
    RouteConfig,
    ProcessorManager,
    ProcessorConfig,
    ConnectorManager,
    default_connector_manager,
    parse_uri,
    merge_dicts,
    get_nested_value,
    set_nested_value,
    deep_update,
    format_template
)

# Import processors
from .processors import (
    Processor,
    TransformProcessor,
    FilterProcessor,
    ExternalProcessor,
    AggregateProcessor,
    DebugProcessor,
    create_processor,
)

# Import connectors
from .connectors import (
    Source,
    Destination,
    RTSPSource,
    FileSource,
    HTTPDestination,
    FileDestination,
    IMAPSource,
    TimerSource,
    EmailDestination,
    LogDestination,
)

# For backward compatibility
ProcessorType = Type[Processor]

__all__ = [
    # Core
    'DialogChainEngine',
    'Route',
    'RouteConfig',
    'ProcessorManager',
    'ProcessorConfig',
    'ConnectorManager',
    'default_connector_manager',
    'parse_uri',
    'merge_dicts',
    'get_nested_value',
    'set_nested_value',
    'deep_update',
    'format_template',
    
    # Processors
    'Processor',
    'TransformProcessor',
    'FilterProcessor',
    'ExternalProcessor',
    'AggregateProcessor',
    'DebugProcessor',
    'create_processor',
    'ProcessorType',
    
    # Connectors
    'Source',
    'Destination',
    'RTSPSource',
    'FileSource',
    'HTTPDestination',
    'FileDestination',
    'IMAPSource',
    'TimerSource',
    'EmailDestination',
    'LogDestination',
    # Exceptions
    "DialogChainError",
    "ConfigurationError",
    "ValidationError",
    "ConnectorError",
    "ProcessorError",
    "TimeoutError",
    "ScannerError",
    "ExternalProcessError",
    "SourceConnectionError",
    "DestinationError"
]
