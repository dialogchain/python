"""
Timer Source Module

This module implements a timer-based source that generates events at regular intervals.
"""
import asyncio
from datetime import datetime
from typing import Any, AsyncIterator, Dict

from .base import Source
from dialogchain.utils.logger import setup_logger

class TimerSource(Source):
    """Timer-based source that generates events at regular intervals."""
    
    def __init__(self, interval: str, **kwargs):
        """Initialize the timer source.
        
        Args:
            interval: String representing the interval (e.g., '5s', '1m', '1h')
        """
        super().__init__(**kwargs)
        self.interval = self._parse_interval(interval)
        self.logger = setup_logger(__name__)
    
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield timer events at the specified interval.
        
        Yields:
            Dictionary with timer event data:
            {
                'type': 'timer_event',
                'timestamp': ISO format timestamp,
                'interval': interval in seconds
            }
        """
        self.logger.info(f"⏱️ Timer source started with interval: {self.interval}s")
        
        try:
            while True:
                event = {
                    'type': 'timer_event',
                    'timestamp': datetime.now().isoformat(),
                    'interval': self.interval
                }
                self.logger.debug(f"⏱️ Timer event: {event}")
                yield event
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            self.logger.info("⏱️ Timer source cancelled")
            raise
        except Exception as e:
            self.logger.error(f"⏱️ Timer source error: {e}")
            raise
    
    def _parse_interval(self, interval_str: str) -> float:
        """Parse interval string to seconds.
        
        Args:
            interval_str: String in format '1s' (seconds), '1m' (minutes), or '1h' (hours)
            
        Returns:
            float: Interval in seconds
            
        Raises:
            ValueError: If interval_str is empty or invalid
        """
        if not interval_str or not isinstance(interval_str, str):
            raise ValueError(
                f"Invalid interval: '{interval_str}'. Must be a non-empty string."
            )

        try:
            if interval_str.endswith("s"):
                return float(interval_str[:-1])
            elif interval_str.endswith("m"):
                return float(interval_str[:-1]) * 60
            elif interval_str.endswith("h"):
                return float(interval_str[:-1]) * 3600
            else:
                return float(interval_str)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid interval format: '{interval_str}'. Expected format: '1s', '1m', or '1h'."
            ) from e
