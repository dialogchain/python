"""
Aggregate Processor Module

This module implements a processor that aggregates multiple messages over time.
"""
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
from datetime import datetime, timedelta

from .base import Processor

logger = logging.getLogger(__name__)

class AggregateProcessor(Processor):
    """Processor that aggregates multiple messages over time."""
    
    def __init__(self, 
                 strategy: str = "collect",
                 timeout: Union[str, int] = "1m",
                 max_size: int = 100,
                 **kwargs):
        """Initialize the aggregate processor.
        
        Args:
            strategy: Aggregation strategy ('collect', 'sum', 'average', 'count')
            timeout: Time window for aggregation (e.g., '1m', '5s', '2h')
            max_size: Maximum number of messages to aggregate
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        self.strategy = strategy.lower()
        self.timeout = self._parse_timeout(timeout)
        self.max_size = max_size
        self.buffer: List[Any] = []
        self._last_flush_time = 0
        self._flush_callback: Optional[Callable[[List[Any]], Awaitable[None]]] = None
        self._flush_task: Optional[asyncio.Task] = None
    
    @property
    def last_flush(self) -> float:
        """Get the timestamp of the last flush."""
        return self._last_flush_time
    
    @last_flush.setter
    def last_flush(self, value: float):
        """Set the last flush time."""
        self._last_flush_time = value
    
    async def process(self, message: Any) -> Optional[Any]:
        """Add a message to the aggregation buffer.
        
        Args:
            message: The message to aggregate
            
        Returns:
            The aggregated result if the buffer is flushed, None otherwise
        """
        try:
            # Add message to buffer
            self.buffer.append(message)
            
            # Check if we should flush
            should_flush = False
            now = time.time()
            
            # Flush if buffer is full
            if len(self.buffer) >= self.max_size:
                logger.debug(f"Buffer full ({len(self.buffer)} >= {self.max_size}), flushing")
                should_flush = True
            
            # Flush if timeout reached
            elif self._last_flush_time > 0 and now - self._last_flush_time >= self.timeout:
                logger.debug(f"Timeout reached, flushing buffer ({len(self.buffer)} items)")
                should_flush = True
            
            # First message, schedule timeout
            elif self._last_flush_time == 0:
                self._last_flush_time = now
                self._schedule_flush()
            
            # Flush if needed
            if should_flush:
                return await self._flush()
                
            return None
            
        except Exception as e:
            logger.error(f"Error in AggregateProcessor: {e}", exc_info=True)
            return None
    
    async def _flush(self) -> Any:
        """Flush the buffer and return the aggregated result."""
        if not self.buffer:
            return None
        
        # Cancel any pending flush task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            self._flush_task = None
        
        # Get buffer contents and clear it
        buffer = self.buffer.copy()
        self.buffer.clear()
        self._last_flush_time = time.time()
        
        # Apply aggregation strategy
        result = self._apply_strategy(buffer)
        
        # Call flush callback if set
        if self._flush_callback:
            try:
                await self._flush_callback(buffer)
            except Exception as e:
                logger.error(f"Error in flush callback: {e}", exc_info=True)
        
        return result
    
    def _schedule_flush(self):
        """Schedule a flush for the timeout period."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        
        async def _flush_later():
            try:
                await asyncio.sleep(self.timeout)
                await self._flush()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in scheduled flush: {e}", exc_info=True)
        
        self._flush_task = asyncio.create_task(_flush_later())
    
    def _apply_strategy(self, buffer: List[Any]) -> Any:
        """Apply the aggregation strategy to the buffer."""
        if not buffer:
            return None
        
        if self.strategy == "collect":
            return buffer
        
        elif self.strategy == "sum":
            try:
                return sum(float(x) if isinstance(x, (int, float, str)) else 0 for x in buffer)
            except (ValueError, TypeError):
                return 0
        
        elif self.strategy == "average":
            try:
                numbers = [float(x) if isinstance(x, (int, float, str)) else 0 for x in buffer]
                return sum(numbers) / len(numbers) if numbers else 0
            except (ValueError, TypeError):
                return 0
        
        elif self.strategy == "count":
            return len(buffer)
        
        else:
            logger.warning(f"Unknown aggregation strategy: {self.strategy}")
            return buffer
    
    def _parse_timeout(self, timeout: Union[str, int]) -> float:
        """Parse a timeout string into seconds."""
        if isinstance(timeout, (int, float)):
            return float(timeout)
        
        try:
            unit = timeout[-1].lower()
            value = float(timeout[:-1])
            
            if unit == 's':
                return value
            elif unit == 'm':
                return value * 60
            elif unit == 'h':
                return value * 3600
            else:
                raise ValueError(f"Unknown time unit: {unit}")
                
        except (ValueError, IndexError, AttributeError):
            try:
                return float(timeout)
            except (ValueError, TypeError):
                logger.warning(f"Invalid timeout value: {timeout}, using default 60s")
                return 60.0
    
    def set_flush_callback(self, callback: Callable[[List[Any]], Awaitable[None]]):
        """Set a callback to be called when the buffer is flushed."""
        self._flush_callback = callback
    
    async def close(self):
        """Flush any remaining messages and clean up."""
        if self.buffer:
            await self._flush()
        
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
