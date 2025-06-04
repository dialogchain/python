"""Timer source implementation for DialogChain."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, AsyncIterator, Union

from ..base import Source

logger = logging.getLogger(__name__)

class TimerSource(Source):
    """Timer source that generates events at regular intervals."""
    
    def __init__(
        self, 
        interval: Union[str, float], 
        immediate: bool = True,
        max_ticks: Optional[int] = None
    ):
        """Initialize timer source.
        
        Args:
            interval: Time between ticks in seconds or as a string (e.g., '1s', '5m', '1h')
            immediate: If True, emit first tick immediately
            max_ticks: Maximum number of ticks before stopping (None for infinite)
        """
        super().__init__(f"timer://{interval}")
        self.interval = self._parse_interval(interval)
        self.immediate = immediate
        self.max_ticks = max_ticks
        self._tick_count = 0
        self._stop_event = asyncio.Event()
    
    def _parse_interval(self, interval: Union[str, float]) -> float:
        """Parse interval from string or number."""
        if isinstance(interval, (int, float)):
            return float(interval)
            
        if not isinstance(interval, str):
            raise ValueError("Interval must be a number or string")
            
        interval = interval.lower().strip()
        
        # Parse string interval (e.g., '1s', '5m', '2h')
        if interval.endswith('s'):
            return float(interval[:-1])
        elif interval.endswith('m'):
            return float(interval[:-1]) * 60
        elif interval.endswith('h'):
            return float(interval[:-1]) * 3600
        elif interval.endswith('d'):
            return float(interval[:-1]) * 86400
        else:
            # Try to parse as float
            try:
                return float(interval)
            except ValueError as e:
                raise ValueError(
                    f"Invalid interval format: {interval}. "
                    "Use a number or a string with suffix (s, m, h, d)"
                ) from e
    
    async def _connect(self):
        """No connection needed for timer."""
        pass
    
    async def _disconnect(self):
        """Stop the timer."""
        self._stop_event.set()
    
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Generate timer events at regular intervals.
        
        Yields:
            Dictionary containing timer event data
        """
        self._tick_count = 0
        
        # First tick immediately if requested
        if self.immediate:
            yield self._create_tick_event()
            self._tick_count += 1
            
            if self.max_ticks is not None and self._tick_count >= self.max_ticks:
                return
        
        # Subsequent ticks at regular intervals
        while not self._stop_event.is_set():
            try:
                # Wait for the interval (or until stop is requested)
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), 
                        timeout=self.interval
                    )
                    # If we get here, stop was requested
                    break
                except asyncio.TimeoutError:
                    # Normal case - interval elapsed
                    pass
                
                # Generate tick
                yield self._create_tick_event()
                self._tick_count += 1
                
                # Check if we've reached max ticks
                if self.max_ticks is not None and self._tick_count >= self.max_ticks:
                    logger.info(f"Reached max ticks ({self.max_ticks}), stopping timer")
                    break
                    
            except asyncio.CancelledError:
                logger.debug("Timer was cancelled")
                break
            except Exception as e:
                logger.error(f"Error in timer: {e}")
                await asyncio.sleep(min(5, self.interval))  # Backoff on error
    
    def _create_tick_event(self) -> Dict[str, Any]:
        """Create a timer tick event."""
        now = datetime.utcnow()
        return {
            'type': 'timer_tick',
            'tick_count': self._tick_count + 1,
            'interval': self.interval,
            'timestamp': now.isoformat(),
            'utc_timestamp': now.timestamp(),
            'source': self.uri
        }
    
    async def stop(self):
        """Stop the timer."""
        self._stop_event.set()
    
    def __str__(self):
        """String representation of the source."""
        return f"Timer Source (every {self.interval}s)"
