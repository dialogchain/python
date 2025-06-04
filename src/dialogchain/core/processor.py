"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please update your imports to use 'dialogchain.engine.processor' instead.
"""

import warnings

# Raise deprecation warning
warnings.warn(
    "The 'dialogchain.core.processor' module is deprecated. "
    "Please update your imports to use 'dialogchain.engine.processor' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
try:
    from ...engine.processor import ProcessorManager, ProcessorConfig
    # For backward compatibility
    MessageProcessor = ProcessorManager
except ImportError as e:
    raise ImportError(
        "Failed to import from new module location. "
        "Please update your code to use 'dialogchain.engine.processor' directly."
    ) from e
