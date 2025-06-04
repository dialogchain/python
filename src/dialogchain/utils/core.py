"""
Core utility functions for DialogChain.
"""
import asyncio
import importlib
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Callable, Awaitable, Union

T = TypeVar('T')
R = TypeVar('R')

def async_retry(max_retries: int = 3, delay: float = 1.0, exceptions=(Exception,)):
    """
    Retry decorator for async functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Exceptions to catch and retry on
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

def import_string(dotted_path: str) -> Type[Any]:
    """
    Import a class by its full module path.
    
    Args:
        dotted_path: Full path to the class (e.g., 'datetime.datetime')
        
    Returns:
        The imported class
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not import '{dotted_path}': {e}")

def parse_timedelta(time_str: str) -> timedelta:
    """
    Parse a time delta string (e.g., '1h2m3s') into a timedelta object.
    
    Args:
        time_str: Time string in format like '1h2m3s'
        
    Returns:
        timedelta object
    """
    if not time_str:
        return timedelta()
        
    pattern = r'(\d+h)?(\d+m)?(\d+s)?'
    match = re.fullmatch(pattern, time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}. Expected format like '1h2m3s'")
        
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def format_timedelta(delta: timedelta) -> str:
    """
    Format a timedelta object into a string like '1h2m3s'.
    
    Args:
        delta: timedelta object
        
    Returns:
        Formatted string
    """
    if not isinstance(delta, timedelta):
        raise TypeError(f"Expected timedelta, got {type(delta).__name__}")
        
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or (hours > 0 and seconds > 0):
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
        
    return "".join(parts)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    Args:
        filename: Input filename
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)
    # Remove trailing periods and spaces (Windows doesn't like them)
    filename = re.sub(r'[. ]+$', '', filename)
    # Ensure the filename is not empty
    if not filename:
        filename = 'unnamed_file'
    return filename

def deep_update(dest: Dict, src: Dict) -> Dict:
    """
    Recursively update a dictionary.
    
    Args:
        dest: Dictionary to update
        src: Dictionary with updates
        
    Returns:
        Updated dictionary
    """
    for key, value in src.items():
        if isinstance(value, dict) and key in dest and isinstance(dest[key], dict):
            dest[key] = deep_update(dest[key], value)
        else:
            dest[key] = value
    return dest

def generate_id(prefix: str = '') -> str:
    """
    Generate a unique ID with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique ID string
    """
    return f"{prefix}_{uuid.uuid4().hex}" if prefix else uuid.uuid4().hex

def format_bytes(size: int) -> str:
    """
    Format bytes to human-readable string.
    
    Args:
        size: Size in bytes
        
    Returns:
        Formatted string (e.g., '1.2 MB')
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}" if unit != 'B' else f"{size}{unit}"
        size /= 1024.0
    return f"{size:.1f}PB"

def parse_bool(value: Union[str, bool, int]) -> bool:
    """
    Parse a boolean value from various input types.
    
    Args:
        value: Input value to parse
        
    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        value = value.lower().strip()
        if value in ('true', 'yes', 'y', '1'):
            return True
        if value in ('false', 'no', 'n', '0'):
            return False
    raise ValueError(f"Cannot convert '{value}' to boolean")

class AsyncContextManager:
    """Async context manager for objects with async close method."""
    def __init__(self, obj):
        self.obj = obj

    async def __aenter__(self):
        return self.obj

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self.obj, 'aclose') and callable(self.obj.aclose):
            await self.obj.aclose()
        elif hasattr(self.obj, 'close') and callable(self.obj.close):
            if asyncio.iscoroutinefunction(self.obj.close):
                await self.obj.close()
            else:
                self.obj.close()

def async_context_manager(obj):
    """
    Create an async context manager for an object with close/cleanup methods.
    
    Args:
        obj: Object to manage
        
    Returns:
        Async context manager
    """
    return AsyncContextManager(obj)

class MetricsCollector:
    """Simple metrics collection"""
    def __init__(self):
        self.counters = {}
        self.gauges = {}
        self.histograms = {}

    def increment(self, name: str, value: int = 1) -> None:
        """Increment counter"""
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set gauge value"""
        self.gauges[name] = value

    def add_histogram(self, name: str, value: float) -> None:
        """Add histogram value"""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

    def get_metrics(self) -> Dict[str, Dict]:
        """Get all metrics"""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': {k: list(v) for k, v in self.histograms.items()}
        }
