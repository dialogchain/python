"""
Camel Router - Multi-language processing engine for ML/multimedia pipelines

A simplified Apache Camel-style routing engine that can delegate tasks 
to different programming languages and external tools.

Features:
- URL-based configuration with .env support
- Multi-language external processors (Python, Go, Rust, C++, Node.js)
- Streaming video processing (RTSP, cameras)
- gRPC, HTTP, MQTT, Email connectors
- Real-time ML inference pipelines
- Easy deployment and scaling

Usage:
    dialogchain run -c routes.yaml
    dialogchain init --template camera
    dialogchain validate -c routes.yaml
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from .engine import CamelRouterEngine
from .processors import *
from .connectors import *

__all__ = [
    "CamelRouterEngine",
    "Processor",
    "ExternalProcessor",
    "FilterProcessor",
    "TransformProcessor",
    "AggregateProcessor",
    "Source",
    "Destination",
    "RTSPSource",
    "TimerSource",
    "EmailDestination",
    "HTTPDestination",
    "MQTTDestination",
    "FileDestination",
    "LogDestination",
]
