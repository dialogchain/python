"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please update your imports to use 'dialogchain.engine.route' instead.
"""

import warnings

# Raise deprecation warning
warnings.warn(
    "The 'dialogchain.core.route' module is deprecated. "
    "Please update your imports to use 'dialogchain.engine.route' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
try:
    from ...engine.route import Route, RouteConfig
except ImportError as e:
    raise ImportError(
        "Failed to import from new module location. "
        "Please update your code to use 'dialogchain.engine.route' directly."
    ) from e
