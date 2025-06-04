"""
File system scanner for DialogChain.
Scans local file system for configuration files.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from .base import BaseScanner, ScannerError

logger = logging.getLogger(__name__)

class FileScanner(BaseScanner):
    """Scanner for local file system configurations."""
    
    def __init__(self, path: Union[str, Dict[str, Any]], pattern: str = "*.yaml", 
                 recursive: bool = True):
        """Initialize file scanner.
        
        Args:
            path: Base directory to scan (string or dict with 'path' key)
            pattern: File pattern to match (e.g., '*.yaml')
            recursive: Whether to scan subdirectories
            
        If a dictionary is provided, it should contain:
            - path: Base directory to scan (required)
            - pattern: File pattern (optional, defaults to '*.yaml')
            - recursive: Whether to scan subdirectories (optional, defaults to True)
        """
        # Handle dictionary input
        if isinstance(path, dict):
            config = path
            path = config.get('path')
            if not path:
                raise ValueError("Configuration must contain 'path' key")
            pattern = config.get('pattern', pattern)
            recursive = config.get('recursive', recursive)
        
        self.path = str(Path(path).expanduser().resolve())
        self.pattern = pattern
        self.recursive = recursive
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'FileScanner':
        """Create a file scanner from configuration.
        
        Args:
            config: Scanner configuration dictionary
            
        Returns:
            Configured FileScanner instance
        """
        return cls(**config)
    
    async def scan(self) -> List[str]:
        """Scan directory for configuration files.
        
        Returns:
            List of configuration file paths
            
        Raises:
            ScannerError: If the scan fails
        """
        try:
            if not os.path.isdir(self.path):
                raise ScannerError(f"Directory not found: {self.path}")
            
            path_obj = Path(self.path)
            pattern = self.pattern
            
            if self.recursive:
                files = [str(p) for p in path_obj.rglob(pattern)]
            else:
                files = [str(p) for p in path_obj.glob(pattern)]
            
            # Filter out directories that might match the pattern
            config_files = [f for f in files if os.path.isfile(f)]
            
            logger.info(f"Found {len(config_files)} config files in {self.path}")
            return config_files
            
        except Exception as e:
            raise ScannerError(f"Failed to scan directory {self.path}: {e}") from e
