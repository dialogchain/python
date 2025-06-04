"""
Processor Factory Module

This module provides a factory function to create processor instances.
"""
from typing import Any, Dict, Type, Optional, TypeVar
import logging

from .base import Processor
from .external import ExternalProcessor
from .filter import FilterProcessor
from .transform import TransformProcessor
from .aggregate import AggregateProcessor
from .debug import DebugProcessor

logger = logging.getLogger(__name__)

# Type variable for Processor subclasses
ProcessorType = TypeVar('ProcessorType', bound=Processor)

# Registry of available processor types
PROCESSOR_TYPES = {
    "external": ExternalProcessor,
    "filter": FilterProcessor,
    "transform": TransformProcessor,
    "aggregate": AggregateProcessor,
    "debug": DebugProcessor,
}

def create_processor(config: Dict[str, Any]) -> Processor:
    """Create a processor instance based on the configuration.
    
    Args:
        config: Processor configuration dictionary
        
    Returns:
        Processor: An instance of the requested processor
        
    Raises:
        ValueError: If the processor type is unknown or configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValueError("Processor configuration must be a dictionary")
    
    # Get processor type
    proc_type = config.get("type")
    if not proc_type:
        raise ValueError("Processor configuration must include a 'type' field")
    
    # Get processor class
    processor_class = PROCESSOR_TYPES.get(proc_type.lower())
    if not processor_class:
        raise ValueError(f"Unknown processor type: {proc_type}")
    
    try:
        # Create processor instance
        return processor_class(**{k: v for k, v in config.items() if k != 'type'})
    except Exception as e:
        raise ValueError(f"Failed to create {proc_type} processor: {e}") from e

def register_processor(name: str, processor_class: Type[ProcessorType]) -> None:
    """Register a new processor type.
    
    Args:
        name: Name of the processor type
        processor_class: The processor class to register
        
    Raises:
        TypeError: If processor_class is not a subclass of Processor
    """
    if not issubclass(processor_class, Processor):
        raise TypeError(f"Processor class must be a subclass of {Processor.__name__}")
    
    PROCESSOR_TYPES[name.lower()] = processor_class
    logger.debug(f"Registered processor type: {name}")

def unregister_processor(name: str) -> Optional[Type[Processor]]:
    """Unregister a processor type.
    
    Args:
        name: Name of the processor type to unregister
        
    Returns:
        The unregistered processor class, or None if not found
    """
    return PROCESSOR_TYPES.pop(name.lower(), None)
