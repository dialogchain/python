"""
DialogChain Processors Module

This module contains base classes and implementations for various data processors
that can transform, filter, and aggregate messages as they flow through the DialogChain pipeline.
"""

from .base import Processor
from .transform import TransformProcessor
from .filter import FilterProcessor
from .external import ExternalProcessor
from .aggregate import AggregateProcessor
from .debug import DebugProcessor
from .factory import create_processor, register_processor, unregister_processor, PROCESSOR_TYPES

__all__ = [
    # Base class
    'Processor',
    
    # Processor implementations
    'TransformProcessor',
    'FilterProcessor',
    'ExternalProcessor',
    'AggregateProcessor',
    'DebugProcessor',
    
    # Factory functions
    'create_processor',
    'register_processor',
    'unregister_processor',
    'PROCESSOR_TYPES',
]
