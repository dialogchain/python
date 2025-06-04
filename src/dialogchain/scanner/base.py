"""
Base scanner module for DialogChain.
Provides the base scanner class and exceptions.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Any, Dict, AsyncGenerator, Optional

logger = logging.getLogger(__name__)

class ScannerError(Exception):
    """Base exception for scanner related errors."""
    pass

class BaseScanner(ABC):
    """Base class for all scanners."""
    
    @abstractmethod
    async def scan(self) -> List[str]:
        """Scan for configuration files.
        
        Returns:
            List of configuration file paths or URLs
        """
        raise NotImplementedError("Subclasses must implement scan()")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'BaseScanner':
        """Create a scanner instance from configuration.
        
        Args:
            config: Scanner configuration dictionary
            
        Returns:
            Configured scanner instance
            
        Raises:
            ValueError: If configuration is invalid
        """
        raise NotImplementedError("Subclasses must implement from_config()")
