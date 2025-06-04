"""Log destination implementation for DialogChain."""

import logging
import json
from typing import Any, Dict, Optional, Union

from ....exceptions import DestinationError
from ..base import Destination

logger = logging.getLogger(__name__)

class LogDestination(Destination):
    """Log destination for writing messages to a logger."""
    
    def __init__(
        self,
        name: Optional[str] = None,
        level: Union[int, str] = logging.INFO,
        format: Optional[str] = None,
        **kwargs
    ):
        """Initialize log destination.
        
        Args:
            name: Logger name (default: 'dialogchain.destinations.log')
            level: Logging level (default: INFO)
            format: Log message format string
            **kwargs: Additional arguments for logger configuration
        """
        super().__init__(f"log://{name or 'default'}")
        
        self.logger_name = name or 'dialogchain.destinations.log'
        self.logger = logging.getLogger(self.logger_name)
        
        # Set log level
        if isinstance(level, str):
            level = level.upper()
        self.level = logging.getLevelName(level) if isinstance(level, str) else level
        
        # Set format if provided
        self.format = format or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Configure logger
        self._configure_logger(**kwargs)
    
    def _configure_logger(self, **kwargs):
        """Configure the logger with the specified settings."""
        # Clear existing handlers to avoid duplicate logs
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
        
        # Create console handler by default
        if not kwargs.get('disable_console', False):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.level)
            
            formatter = logging.Formatter(self.format)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
        
        # Set log level
        self.logger.setLevel(self.level)
        
        # Disable propagation to root logger by default
        self.logger.propagate = kwargs.get('propagate', False)
    
    async def _connect(self):
        """No connection needed for logging."""
        pass
    
    async def _disconnect(self):
        """No disconnection needed for logging."""
        pass
    
    async def send(
        self, 
        message: Any, 
        level: Optional[Union[int, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log a message.
        
        Args:
            message: Message to log (can be any type, will be converted to string)
            level: Log level override (default: use instance level)
            extra: Additional fields to include in the log record
            **kwargs: Additional fields to include in the log record
        """
        try:
            # Determine log level
            log_level = self.level
            if level is not None:
                if isinstance(level, str):
                    level = level.upper()
                log_level = logging.getLevelName(level) if isinstance(level, str) else level
            
            # Convert message to string if needed
            if not isinstance(message, str):
                if hasattr(message, '__dict__'):
                    message = str(message.__dict__)
                else:
                    try:
                        message = json.dumps(message, default=str, ensure_ascii=False)
                    except (TypeError, ValueError):
                        message = str(message)
            
            # Merge extra and kwargs
            log_extra = {}
            if extra:
                log_extra.update(extra)
            log_extra.update(kwargs)
            
            # Log the message
            self.logger.log(log_level, message, extra=log_extra)
            
        except Exception as e:
            # Fallback to basic logging if there's an error with the custom logger
            try:
                self.logger.log(
                    logging.ERROR,
                    f"Error in LogDestination: {e}\nOriginal message: {message}",
                    exc_info=True
                )
            except Exception:
                # Last resort
                print(f"[ERROR] LogDestination failed to log message: {e}")
    
    def __str__(self):
        """String representation of the destination."""
        level_name = logging.getLevelName(self.level)
        return f"Log Destination: {self.logger_name} (level: {level_name})"
