#!/usr/bin/env python3
"""
Initialize logging and display recent logs.
"""
import os
import sys
from pathlib import Path
from dialogchain.utils.logger import setup_logger, display_recent_logs

# Set up logger for this script
logger = setup_logger(__name__)

def main():
    """Initialize logging and display recent logs."""
    try:
        # Log a test message
        logger.info("Logging system initialized")
        
        # Display recent logs
        print("\n" + "="*50)
        print("DIALOGCHAIN LOGGING SYSTEM")
        print("="*50)
        
        display_recent_logs(limit=10)
        
        print("\nLogs are being saved to: logs.db")
        print("Use `python -m dialogchain.utils.logger` to view logs\n")
        
    except Exception as e:
        logger.error(f"Failed to initialize logging: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
