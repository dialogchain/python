"""
Utility functions for the DialogChain engine.
"""

from typing import Any

def parse_uri(uri: str) -> tuple[str, str]:
    """Parse a URI into its scheme and path components.
    
    Args:
        uri: URI to parse (e.g., 'http://example.com', 'timer:5s')
        
    Returns:
        Tuple of (scheme, path)
        
    Raises:
        ValueError: If the URI format is invalid
    """
    if "://" in uri:
        # Handle standard URIs with ://
        scheme, path = uri.split("://", 1)
        return scheme, f"//{path}"  # Ensure path starts with // for standard URIs
    elif ":" in uri:
        # Handle simple URIs with just a scheme:path
        scheme, path = uri.split(":", 1)
        return scheme, path
    else:
        raise ValueError(f"Invalid URI format: {uri}")

def merge_dicts(base: dict, override: dict) -> dict:
    """Recursively merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Dictionary with values to override
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

def get_nested_value(data: dict, path: str, default=None, delimiter: str = '.') -> Any:
    """Get a value from a nested dictionary using a dot-notation path.
    
    Args:
        data: Nested dictionary
        path: Dot-separated path to the value (e.g., 'user.profile.name')
        default: Default value if the path doesn't exist
        delimiter: Path delimiter (default: '.')
        
    Returns:
        The value at the specified path or the default value
    """
    keys = path.split(delimiter)
    value = data
    
    for key in keys:
        try:
            value = value[key]
        except (KeyError, TypeError):
            return default
    
    return value

def set_nested_value(data: dict, path: str, value: Any, delimiter: str = '.') -> None:
    """Set a value in a nested dictionary using a dot-notation path.
    
    Args:
        data: Nested dictionary to update
        path: Dot-separated path to set (e.g., 'user.profile.name')
        value: Value to set
        delimiter: Path delimiter (default: '.')
    """
    keys = path.split(delimiter)
    current = data
    
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value

def deep_update(target: dict, source: dict) -> dict:
    """Recursively update a dictionary with another dictionary.
    
    Similar to dict.update() but handles nested dictionaries.
    
    Args:
        target: Dictionary to update
        source: Dictionary with updates
        
    Returns:
        Updated target dictionary
    """
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            target[key] = deep_update(target[key], value)
        else:
            target[key] = value
    return target

def format_template(template: str, context: dict) -> str:
    """Format a template string with the given context.
    
    Supports both {variable} and {{variable}} syntax.
    
    Args:
        template: Template string
        context: Dictionary with template variables
        
    Returns:
        Formatted string
    """
    try:
        # First try with single braces
        return template.format(**context)
    except (KeyError, IndexError):
        try:
            # If that fails, try with double braces
            return template.format(**{k: f'{{{k}}}' for k in context})
        except (KeyError, IndexError):
            # If that still fails, return the original template
            return template
