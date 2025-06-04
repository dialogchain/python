"""
Processor management for DialogChain engine.

This module handles the creation and management of data processors.
"""

from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Callable
import logging
import importlib
from dataclasses import dataclass, field

from ..processors import Processor, create_processor

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class ProcessorConfig:
    """Configuration for a processor."""
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'ProcessorConfig':
        """Create a ProcessorConfig from a dictionary."""
        return cls(
            type=config['type'],
            config=config.get('config', {})
        )

class ProcessorManager:
    """Manages the creation and lifecycle of processors."""
    
    def __init__(self, processors: Optional[Dict[str, Type[Processor]]] = None):
        """Initialize the processor manager.
        
        Args:
            processors: Optional dictionary of processor types to processor classes
        """
        self.processors = processors or {}
    
    def register_processor(self, processor_type: str, processor_class: Type[Processor]) -> None:
        """Register a processor class.
        
        Args:
            processor_type: Type identifier for the processor
            processor_class: Processor class to register
        """
        self.processors[processor_type] = processor_class
    
    def create_processor(self, config: Dict[str, Any]) -> Processor:
        """Create a processor from a configuration dictionary.
        
        Args:
            config: Processor configuration
            
        Returns:
            Configured Processor instance
            
        Raises:
            ValueError: If the processor type is unknown
        """
        processor_config = ProcessorConfig.from_dict(config)
        processor_type = processor_config.type
        
        if processor_type not in self.processors:
            # Try to dynamically import the processor
            try:
                module_name, _, class_name = processor_type.rpartition('.')
                if not module_name:
                    raise ValueError(f"Invalid processor type format: {processor_type}")
                
                module = importlib.import_module(module_name)
                processor_class = getattr(module, class_name)
                self.register_processor(processor_type, processor_class)
            except (ImportError, AttributeError) as e:
                raise ValueError(f"Unknown processor type: {processor_type}") from e
        
        # Create and initialize the processor
        processor_class = self.processors[processor_type]
        return processor_class(**processor_config.config)
    
    def get_processor(self, processor_type: str) -> Optional[Type[Processor]]:
        """Get a processor class by type.
        
        Args:
            processor_type: Type identifier for the processor
            
        Returns:
            Processor class if found, None otherwise
        """
        return self.processors.get(processor_type)
    
    def list_processors(self) -> List[str]:
        """List all registered processor types.
        
        Returns:
            List of processor type strings
        """
        return list(self.processors.keys())


# Default processor manager instance
default_processor_manager = ProcessorManager()

# Register built-in processors
from ..processors import (
    TransformProcessor, FilterProcessor, ExternalProcessor,
    AggregateProcessor, DebugProcessor
)

default_processor_manager.register_processor('transform', TransformProcessor)
default_processor_manager.register_processor('filter', FilterProcessor)
default_processor_manager.register_processor('external', ExternalProcessor)
default_processor_manager.register_processor('aggregate', AggregateProcessor)
default_processor_manager.register_processor('debug', DebugProcessor)
