"""
DialogChain Engine Package

This package contains the core engine components for DialogChain,
split into modular components for better maintainability.
"""

from .core import DialogChainEngine
from .route import Route, RouteConfig
from .processor import ProcessorManager, ProcessorConfig
from .connector import ConnectorManager, default_connector_manager
from .utils import parse_uri, merge_dicts, get_nested_value, set_nested_value, deep_update, format_template

__all__ = [
    'DialogChainEngine',
    'Route',
    'RouteConfig',
    'ProcessorManager',
    'ProcessorConfig',
    'ConnectorManager',
    'default_connector_manager',
    'parse_uri',
    'merge_dicts',
    'get_nested_value',
    'set_nested_value',
    'deep_update',
    'format_template',
]
