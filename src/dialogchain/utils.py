"""
Utility functions for Camel Router
"""
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime


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
