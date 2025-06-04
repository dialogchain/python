"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please update your imports to use 'dialogchain.engine.connector' instead.
"""

import warnings

# Raise deprecation warning
warnings.warn(
    "The 'dialogchain.core.connector' module is deprecated. "
    "Please update your imports to use 'dialogchain.engine.connector' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
try:
    from ...engine.connector import ConnectorManager, default_connector_manager
except ImportError as e:
    raise ImportError(
        "Failed to import from new module location. "
        "Please update your code to use 'dialogchain.engine.connector' directly."
    ) from e
