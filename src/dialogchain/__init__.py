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

__version__ = "0.1.0"
__author__ = "DialogChain Team"

# Core components
from .engine import DialogChainEngine
from .processors import *
from .connectors import *
from .exceptions import *

# Import and expose utility functions
from . import utils

__all__ = [
    # Core components
    "DialogChainEngine",
    
    # Processors
    "Processor",
    "ExternalProcessor",
    "FilterProcessor",
    "TransformProcessor",
    "AggregateProcessor",
    "DebugProcessor",
    
    # Sources
    "Source",
    "RTSPSource",
    "TimerSource",
    "FileSource",
    "HTTPSource",
    "IMAPSource",
    "MQTTSource",
    
    # Destinations
    "Destination",
    "EmailDestination",
    "HTTPDestination",
    "MQTTDestination",
    "FileDestination",
    "LogDestination",
    
    # Utils
    "utils",
    
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
