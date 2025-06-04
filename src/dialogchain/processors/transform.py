"""
Transform Processor Module

This module implements a processor that transforms messages using templates.
"""
from typing import Any, Dict, Optional
import json
import logging
from jinja2 import Template, StrictUndefined

from .base import Processor
from dialogchain.utils.template import render_template

logger = logging.getLogger(__name__)

class TransformProcessor(Processor):
    """Processor that transforms messages using Jinja2 templates."""
    
    def __init__(self, template: str = None, template_file: str = None, **kwargs):
        """Initialize the transform processor.
        
        Args:
            template: A string template to use for transformation
            template_file: Path to a file containing the template
            **kwargs: Additional configuration options
            
        Raises:
            ValueError: If neither template nor template_file is provided
        """
        super().__init__(**kwargs)
        
        if not (template or template_file):
            raise ValueError("Either 'template' or 'template_file' must be provided")
            
        self.template_str = template
        self.template_file = template_file
        self._template = None
    
    async def process(self, message: Any) -> Optional[Any]:
        """Transform the message using the configured template.
        
        Args:
            message: The message to transform. Can be a dict, string, or any JSON-serializable object.
            
        Returns:
            The transformed message as a string, or None if transformation fails
        """
        try:
            # Load template if not already loaded
            if self._template is None:
                if self.template_file:
                    with open(self.template_file, 'r') as f:
                        self.template_str = f.read()
                self._template = Template(
                    self.template_str,
                    undefined=StrictUndefined
                )
            
            # Prepare context
            context = {}
            if isinstance(message, dict):
                context.update(message)
            elif hasattr(message, 'to_dict'):
                context.update(message.to_dict())
            else:
                context['message'] = message
            
            # Add any additional context from config
            context.update(self.config.get('context', {}))
            
            # Render template
            result = self._template.render(**context)
            
            # Try to parse as JSON if the result looks like JSON
            try:
                if (result.startswith('{') and result.endswith('}')) or \
                   (result.startswith('[') and result.endswith(']')):
                    return json.loads(result)
            except (json.JSONDecodeError, AttributeError):
                pass
                
            return result
            
        except Exception as e:
            logger.error(f"Error in TransformProcessor: {e}")
            if self.config.get('raise_errors', False):
                raise
            return None
