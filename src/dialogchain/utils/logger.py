"""
Standardized logging with SQLite storage support for DialogChain.

This module provides a robust logging solution with the following features:
- SQLite-based log storage for persistence and querying
- Configurable log levels and formats
- Thread-safe logging
- Structured log data with timestamps and metadata
- Support for both file and database logging

Example usage:
    >>> from dialogchain.utils.logger import setup_logger, get_logs
    >>> logger = setup_logger(__name__, log_level='DEBUG')
    >>> logger.info('This is an info message', extra={'key': 'value'})
    >>> logs = get_logs(limit=10)
"""
import logging
import sqlite3
import json
import os
import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from logging.handlers import RotatingFileHandler

# Default configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_DB_PATH = 'logs/dialogchain.db'
DEFAULT_LOG_FILE = 'logs/dialogchain.log'
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

# Thread lock for SQLite operations
db_lock = threading.Lock()

# Create a module-level logger that doesn't trigger setup
_logger = logging.getLogger(__name__)
_logger.setLevel(DEFAULT_LOG_LEVEL)

# Prevent duplicate handlers
if not _logger.handlers:
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(DEFAULT_DB_PATH) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(DEFAULT_LOG_FILE) or '.', exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    _logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            DEFAULT_LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s", "data": %(extra)s}',
            datefmt='%Y-%m-%dT%H:%M:%S%z'
        )
        file_handler.setFormatter(file_formatter)
        _logger.addHandler(file_handler)
    except Exception as e:
        _logger.error(f"Failed to initialize file handler: {e}", exc_info=True)


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that stores logs in SQLite database."""
    
    def __init__(self, db_path: str = 'logs.db'):
        super().__init__()
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Ensure the database and logs table exist."""
        try:
            # Ensure the directory exists
            db_dir = os.path.dirname(os.path.abspath(self.db_path))
            if db_dir:  # Only try to create directory if path is not empty
                os.makedirs(db_dir, exist_ok=True)
            
            # Connect to the database and create table if it doesn't exist
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        level TEXT NOT NULL,
                        module TEXT NOT NULL,
                        function TEXT NOT NULL,
                        message TEXT NOT NULL,
                        extra TEXT
                    )
                """)
                conn.commit()
                _logger.debug(f"Database initialized at: {os.path.abspath(self.db_path)}")
        except Exception as e:
            _logger.error(f"Failed to initialize database: {e}", exc_info=True)
            # Re-raise the exception to prevent silent failures
            raise
    
    def emit(self, record):
        """Save the log record to the database."""
        try:
            extra = json.dumps(getattr(record, 'extra', {}), default=str)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO logs (timestamp, level, module, function, message, extra)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.fromtimestamp(record.created).isoformat(),
                        record.levelname,
                        record.module,
                        record.funcName,
                        record.getMessage(),
                        extra
                    )
                )
                conn.commit()
        except Exception as e:
            _logger.error(f"Failed to write log to database: {e}", exc_info=True)

def setup_logger(name: str, log_level: int = logging.INFO, db_path: str = 'logs/dialogchain.db') -> logging.Logger:
    """
    Set up a logger with both console and database handlers.
    
    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (default: INFO)
        db_path: Path to SQLite database file (relative to project root)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    # Skip if already configured
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Database handler
    try:
        # Convert to absolute path if relative
        if not os.path.isabs(db_path):
            # Get project root (assuming this file is in src/dialogchain/utils/)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            db_path = os.path.join(project_root, db_path)
        
        # Ensure the directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Only try to create directory if path is not empty
            os.makedirs(db_dir, exist_ok=True)
        
        db_handler = DatabaseLogHandler(db_path)
        db_handler.setLevel(log_level)
        db_handler.setFormatter(formatter)
        logger.addHandler(db_handler)
        _logger.info(f"Database logging initialized at: {os.path.abspath(db_path)}")
    except Exception as e:
        _logger.error(f"Failed to initialize database logging: {e}", exc_info=True)
    
    return logger

def _resolve_db_path(db_path: str) -> str:
    """Resolve the database path to an absolute path."""
    if os.path.isabs(db_path):
        return db_path
    # Get project root (assuming this file is in src/dialogchain/utils/)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(project_root, db_path)

def get_logs(limit: int = 100, level: Optional[str] = None, module: Optional[str] = None,
            db_path: str = 'logs/dialogchain.db') -> List[Dict[str, Any]]:
    """
    Retrieve logs from the database.
    
    Args:
        limit: Maximum number of logs to retrieve
        level: Filter by log level (e.g., 'INFO', 'ERROR')
        module: Filter by module name
        db_path: Path to SQLite database file (relative to project root)
        
    Returns:
        List of log entries as dictionaries
    """
    try:
        # Resolve to absolute path
        abs_db_path = _resolve_db_path(db_path)
        
        # Ensure database exists
        if not os.path.exists(abs_db_path):
            _logger.warning(f"Database file not found: {abs_db_path}")
            return []
            
        query = "SELECT * FROM logs"
        params = []
        
        conditions = []
        if level:
            conditions.append("level = ?")
            params.append(level.upper())
        if module:
            conditions.append("module = ?")
            params.append(module)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(abs_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        _logger.error(f"Error retrieving logs from {db_path}: {e}", exc_info=True)
        return []

def display_recent_logs(limit: int = 20, db_path: str = 'logs/dialogchain.db') -> None:
    """
    Display recent logs in a formatted way.
    
    Args:
        limit: Maximum number of logs to display
        db_path: Path to SQLite database file (relative to project root)
    """
    # Resolve to absolute path for display
    abs_db_path = _resolve_db_path(db_path)
    print(f"\n=== Loading logs from: {abs_db_path} ===")
    
    logs = get_logs(limit=limit, db_path=db_path)
    if not logs:
        print("No logs found in the database.")
        return
    
    print(f"\n=== Recent Logs (showing {len(logs)} of {limit} max) ===")
    for log in logs:
        try:
            extra = json.loads(log['extra'] or '{}')
            extra_str = f" | {json.dumps(extra, ensure_ascii=False, separators=(',', ':'))}" if extra else ""
            print(f"{log['timestamp']} - {log['level']:8} - {log['module']}.{log['function']} - {log['message']}{extra_str}")
        except Exception as e:
            print(f"Error displaying log entry: {e}")
    print("=" * 70)

# Module-level logger instance
logger = setup_logger(__name__)

if __name__ == "__main__":
    # Example usage
    logger.info("Logger initialized", extra={"test": True})
