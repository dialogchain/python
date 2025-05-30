#!/usr/bin/env python3
"""
Test the logging system.
"""
import os
import sys
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dialogchain.utils.logger import setup_logger, display_recent_logs

def main():
    """Test the logging system."""
    # Set up logger
    logger = setup_logger(__name__)
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test with extra context
    try:
        result = 1 / 0
    except Exception as e:
        logger.error("Division by zero error", exc_info=True, extra={"context": {"operation": "division"}})
    
    # Display recent logs
    print("\n=== Recent Logs ===")
    display_recent_logs(limit=10)
    
    print("\n✅ Logging test completed. Check logs.db for stored logs.")

if __name__ == "__main__":
    main()
