"""
Utility functions for DialogChain
"""
import os
import json
import logging
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Callable, Awaitable, Union
from datetime import datetime, timedelta
import importlib
from functools import wraps

T = TypeVar('T')
R = TypeVar('R')

# Retry decorator for async functions
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

# Import a class by string path
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
        raise ImportError(f'Could not import "{dotted_path}": {e}') from e


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("dialogchain")


def ensure_directory(path: str) -> Path:
    """Ensure directory exists"""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load JSON file safely"""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Error loading JSON file {filepath}: {e}")


def save_json_file(data: Dict[str, Any], filepath: str) -> None:
    """Save data to JSON file"""
    ensure_directory(os.path.dirname(filepath))
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp for logging"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_timedelta(time_str: str) -> timedelta:
    """
    Parse a time delta string (e.g., '1h2m3s') into a timedelta object.
    
    Args:
        time_str: Time string in format like '1h2m3s'
        
    Returns:
        timedelta object
    """
    pattern = r'((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?'
    match = re.fullmatch(pattern, time_str)
    if not match:
        raise ValueError(f'Invalid time format: {time_str}')
    
    parts = match.groupdict()
    time_params = {}
    for name, value in parts.items():
        if value is not None:
            time_params[name] = int(value)
    
    return timedelta(**time_params)


def format_timedelta(delta: timedelta) -> str:
    """
    Format a timedelta object into a string like '1h2m3s'.
    
    Args:
        delta: timedelta object
        
    Returns:
        Formatted string
    """
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes or (hours and seconds):
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
        
    return ''.join(parts)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    Args:
        filename: Input filename
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscore
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    # Replace multiple underscores with a single one
    filename = re.sub(r'_+', '_', filename)
    # Remove leading/trailing underscores and dots
    filename = filename.strip('_.')
    return filename or 'unnamed'


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
    return f"{prefix}{uuid.uuid4().hex}" if prefix else uuid.uuid4().hex


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
            return f"{size:.1f}{unit}" if unit != 'B' else f"{int(size)}{unit}"
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
    if not isinstance(value, str):
        raise ValueError(f"Cannot parse bool from {type(value).__name__}")
        
    value = value.strip().lower()
    if value in ('true', 't', 'yes', 'y', '1'):
        return True
    if value in ('false', 'f', 'no', 'n', '0', ''):
        return False
    raise ValueError(f"Cannot parse bool from string: {value}")


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


def parse_size_string(size_str: str) -> int:
    """Parse size string like '10MB' to bytes"""
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    size_str = size_str.upper().strip()

    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            return int(float(size_str[: -len(unit)]) * multiplier)

    return int(size_str)  # Assume bytes if no unit


def validate_url(url: str) -> bool:
    """Basic URL validation"""
    from urllib.parse import urlparse

    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


class MetricsCollector:
    """Simple metrics collection"""

    def __init__(self):
        self.counters = {}
        self.gauges = {}
        self.histograms = {}

    def increment(self, name: str, value: int = 1):
        """Increment counter"""
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float):
        """Set gauge value"""
        self.gauges[name] = value

    def add_histogram(self, name: str, value: float):
        """Add histogram value"""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            "counters": self.counters,
            "gauges": self.gauges,
            "histograms": {
                k: {
                    "count": len(v),
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                }
                for k, v in self.histograms.items()
            },
        }
