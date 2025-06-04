"""
DialogChain Destinations Module

This module contains base classes and implementations for various data destinations
that can be used within the DialogChain framework.
"""

from .base import Destination
from .log import LogDestination
from .file import FileDestination
from .http import HTTPDestination
from .email import EmailDestination
from .mqtt import MQTTDestination
from .grpc import GRPCDestination

__all__ = [
    'Destination',
    'LogDestination',
    'FileDestination',
    'HTTPDestination',
    'EmailDestination',
    'MQTTDestination',
    'GRPCDestination'
]
