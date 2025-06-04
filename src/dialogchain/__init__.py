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

__version__ = "0.2.0"
__author__ = "DialogChain Team"

# Core components
from .core.engine import DialogChainEngine

# Processors
from .processors import (
    Processor, 
    TransformProcessor,
    FilterProcessor,
    EnrichProcessor,
    ValidateProcessor
)

# Sources
from .sources import (
    Source,
    TimerSource,
    FileSource,
    IMAPSource,
    RTSPSource,
    GRPCSource
)

# Destinations
from .destinations import (
    Destination,
    LogDestination,
    FileDestination,
    HTTPDestination,
    EmailDestination,
    MQTTDestination,
    GRPCDestination
)

# Utils and exceptions
from . import utils
from .exceptions import *

__all__ = [
    # Core components
    "DialogChainEngine",
    
    # Processors
    "Processor",
    "TransformProcessor",
    "FilterProcessor",
    "EnrichProcessor",
    "ValidateProcessor",
    
    # Sources
    "Source",
    "TimerSource",
    "FileSource",
    "IMAPSource",
    "RTSPSource",
    "GRPCSource",
    
    # Destinations
    "Destination",
    "LogDestination",
    "FileDestination",
    "HTTPDestination",
    "EmailDestination",
    "MQTTDestination",
    "GRPCDestination",
    
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
