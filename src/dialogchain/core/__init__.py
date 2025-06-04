"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please update your imports to use the new module locations:

- dialogchain.engine (for DialogChainEngine, Route, RouteConfig)
- dialogchain.engine.processor (for TaskManager)
"""

import warnings

# Import from new locations with deprecation warnings
warnings.warn(
    "The 'dialogchain.core' module is deprecated. "
    "Please update your imports to use 'dialogchain.engine' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
try:
    from ..engine import DialogChainEngine, Route, RouteConfig
    from ..engine.processor import ProcessorManager as TaskManager
except ImportError as e:
    raise ImportError(
        "Failed to import from new module locations. "
        "Please update your code to use 'dialogchain.engine' directly."
    ) from e

__all__ = [
    'DialogChainEngine',
    'Route',
    'RouteConfig',
    'TaskManager'
]
