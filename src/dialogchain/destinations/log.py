"""
Log Destination Module

This module implements a destination that logs messages to the console and/or file.
"""
import logging
import re
from typing import Any, Dict, Optional

from dialogchain.utils.logger import setup_logger
from .base import Destination

class LogDestination(Destination):
    """Destination that logs messages to the console and/or file."""
    
    def __init__(self, log_level: str = "INFO", **kwargs):
        """Initialize the log destination.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        self.log_level = self._parse_log_level(log_level)
        self.logger = setup_logger(__name__)
        self.logger.setLevel(self.log_level)
    
    async def send(self, message: Any) -> None:
        """Log the message at the configured log level.
        
        Args:
            message: The message to log. Can be any type that can be converted to a string.
        """
        try:
            # Convert message to string if it's not already
            if not isinstance(message, str):
                if hasattr(message, 'to_dict'):
                    message = str(message.to_dict())
                else:
                    message = str(message)
            
            # Log at the appropriate level
            if self.log_level <= logging.DEBUG:
                self.logger.debug("📝 %s", message)
            elif self.log_level <= logging.INFO:
                self.logger.info("ℹ️ %s", message)
            elif self.log_level <= logging.WARNING:
                self.logger.warning("⚠️ %s", message)
            elif self.log_level <= logging.ERROR:
                self.logger.error("❌ %s", message)
            else:  # CRITICAL
                self.logger.critical("🚨 %s", message)
                
            # Store the sent message
            self.sent_messages.append(message)
            
        except Exception as e:
            self.logger.error(f"Error logging message: {e}")
            raise
    
    def _parse_log_level(self, level_str: str) -> int:
        """Parse log level string to logging level constant.
        
        Args:
            level_str: Log level string (case-insensitive)
            
        Returns:
            int: Logging level constant
            
        Raises:
            ValueError: If level_str is not a valid log level
        """
        level_str = level_str.upper()
        
        # Remove any non-alphabetic characters (e.g., from 'log:info' -> 'INFO')
        level_str = re.sub(r'[^A-Z]', '', level_str)
        
        if not level_str:  # Default to INFO if empty after cleaning
            return logging.INFO
            
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        # Try to get the log level, default to INFO if not found
        return level_map.get(level_str, logging.INFO)
