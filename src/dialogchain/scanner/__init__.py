"""
Scanner module for DialogChain.
Provides functionality to scan for configuration files from various sources.
"""

from typing import Dict, Any, Type, List, Optional
import logging

from .base import BaseScanner, ScannerError
from .file_scanner import FileScanner
from .http_scanner import HttpScanner
from .network_scanner import NetworkScanner

# Export all scanner classes for easier importing
__all__ = [
    'BaseScanner',
    'FileScanner',
    'HttpScanner',
    'NetworkScanner',
    'ScannerError',
    'create_scanner',
    'ConfigScanner'
]

logger = logging.getLogger(__name__)

# Registry of available scanner types
SCANNER_TYPES = {
    'file': FileScanner,
    'http': HttpScanner,
    'https': HttpScanner,
    'network': NetworkScanner,
}

def create_scanner(config: Dict[str, Any]) -> BaseScanner:
    """Create a scanner instance based on configuration.
    
    Args:
        config: Scanner configuration
        
    Returns:
        Scanner instance
        
    Raises:
        ValueError: If scanner type is unknown
    """
    scanner_type = config.get('type')
    if not scanner_type:
        raise ValueError("Scanner configuration must include 'type' field")
    
    scanner_class = SCANNER_TYPES.get(scanner_type.lower())
    if not scanner_class:
        # Check if the type is a URL scheme (http, https, file, etc.)
        if '://' in scanner_type:
            scheme = scanner_type.split('://')[0].lower()
            scanner_class = SCANNER_TYPES.get(scheme)
            if scanner_class:
                # Update config to use the URL as the main parameter
                config = {'url': scanner_type, **config}
        
        if not scanner_class:
            raise ValueError(f"Unknown scanner type: {scanner_type}")
    
    # Special case for file scanner with string path
    if scanner_class == FileScanner and 'path' not in config and 'url' in config:
        config = {'path': config['url'], **{k: v for k, v in config.items() if k != 'url'}}
    
    try:
        return scanner_class.from_config(config)
    except Exception as e:
        raise ValueError(f"Failed to create {scanner_class.__name__}: {e}") from e


class ConfigScanner:
    """Manages multiple scanners and aggregates their results."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize config scanner.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.scanners = []
        
        # Create scanners from config
        for scanner_config in config.get('scanners', []):
            try:
                scanner = create_scanner(scanner_config)
                self.scanners.append(scanner)
            except Exception as e:
                logger.warning(f"Failed to create scanner: {e}")
    
    async def scan(self) -> List[str]:
        """Run all scanners and collect results.
        
        Returns:
            List of configuration file paths/URLs
            
        Raises:
            ScannerError: If scanning fails
        """
        results = []
        
        for scanner in self.scanners:
            try:
                scanner_results = await scanner.scan()
                results.extend(scanner_results)
                logger.debug(f"Scanner {scanner.__class__.__name__} found {len(scanner_results)} configs")
            except Exception as e:
                logger.error(f"Scanner {scanner.__class__.__name__} failed: {e}")
                if self.config.get('strict', False):
                    raise ScannerError(f"Scanner {scanner.__class__.__name__} failed: {e}") from e
        
        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for result in results:
            if result not in seen:
                seen.add(result)
                unique_results.append(result)
        
        logger.info(f"Found {len(unique_results)} unique configuration files")
        return unique_results
