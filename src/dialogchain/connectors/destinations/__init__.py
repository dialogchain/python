"""Destination implementations for DialogChain connectors."""

from .http import HTTPDestination
from .email import EmailDestination
from .file import FileDestination
from .log import LogDestination

__all__ = [
    'HTTPDestination',
    'EmailDestination',
    'FileDestination',
    'LogDestination',
]
