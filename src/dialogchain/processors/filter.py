"""
Filter Processor Module

This module implements a processor that filters messages based on conditions.
"""
import logging
from typing import Any, Dict, Optional, Union

from .base import Processor

logger = logging.getLogger(__name__)

class FilterProcessor(Processor):
    """Processor that filters messages based on conditions."""
    
    def __init__(self, min_confidence: float = None, condition: str = None, **kwargs):
        """Initialize the filter processor.
        
        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0)
            condition: A condition string to evaluate
            **kwargs: Additional configuration options
            
        Raises:
            ValueError: If neither min_confidence nor condition is provided
        """
        super().__init__(**kwargs)
        
        if min_confidence is None and condition is None:
            raise ValueError("Either 'min_confidence' or 'condition' must be provided")
            
        self.min_confidence = min_confidence
        self.condition = condition
    
    async def process(self, message: Any) -> Optional[Any]:
        """Filter the message based on the configured conditions.
        
        Args:
            message: The message to filter
            
        Returns:
            The message if it passes the filter, None otherwise
        """
        try:
            # Check min_confidence if set
            if self.min_confidence is not None:
                if not self._check_confidence(message, self.min_confidence):
                    return None
            
            # Check condition if set
            if self.condition is not None:
                if not self._evaluate_condition(self.condition, message):
                    return None
            
            return message
            
        except Exception as e:
            logger.error(f"Error in FilterProcessor: {e}", exc_info=True)
            return None
    
    def _check_confidence(self, message: Any, min_confidence: float) -> bool:
        """Check if the message has the minimum required confidence.
        
        Args:
            message: The message to check
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            bool: True if the message meets the confidence threshold
        """
        if not isinstance(message, dict):
            return False
            
        confidence = message.get('confidence')
        if confidence is None:
            return False
            
        try:
            return float(confidence) >= min_confidence
        except (TypeError, ValueError):
            return False
    
    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate a condition string against a context.
        
        Args:
            condition: The condition string to evaluate
            context: Dictionary of variables to use in the condition
            
        Returns:
            bool: The result of the condition evaluation
            
        Raises:
            ValueError: If the condition is invalid
        """
        if not condition.strip():
            return True
            
        try:
            # Create a safe dictionary with only the context values
            safe_dict = {}
            for key, value in context.items():
                # Only include simple types that are safe to evaluate
                if isinstance(value, (int, float, str, bool, type(None))):
                    safe_dict[key] = value
            
            # Evaluate the condition
            return bool(eval(condition, {"__builtins__": {}}, safe_dict))
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
