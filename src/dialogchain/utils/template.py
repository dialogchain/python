"""
Template Utilities

This module provides template rendering utilities for the DialogChain framework.
"""
from typing import Any, Dict, Optional
from jinja2 import Environment, BaseLoader, StrictUndefined

def render_template(template_str: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Render a template string with the given context.
    
    Args:
        template_str: The template string to render
        context: Dictionary of variables to use in the template
        
    Returns:
        The rendered template string
        
    Raises:
        jinja2.exceptions.TemplateError: If there's an error rendering the template
    """
    if context is None:
        context = {}
        
    env = Environment(
        loader=BaseLoader(),
        undefined=StrictUndefined,
        autoescape=True
    )
    
    template = env.from_string(template_str)
    return template.render(**context)

def render_template_from_file(template_file: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Render a template from a file with the given context.
    
    Args:
        template_file: Path to the template file
        context: Dictionary of variables to use in the template
        
    Returns:
        The rendered template string
    """
    with open(template_file, 'r') as f:
        template_str = f.read()
    return render_template(template_str, context)
