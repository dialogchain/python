"""File source implementation for DialogChain."""

import asyncio
import os
import logging
import hashlib
from typing import Dict, Any, AsyncIterator, Optional
from pathlib import Path

from ..base import Source

logger = logging.getLogger(__name__)

class FileSource(Source):
    """File system source for watching and reading files."""
    
    def __init__(
        self, 
        uri: str, 
        watch: bool = True, 
        poll_interval: float = 1.0,
        read_mode: str = 'r',
        encoding: str = 'utf-8'
    ):
        """Initialize file source.
        
        Args:
            uri: File path or URI (e.g., 'file:///path/to/file.txt' or '/path/to/file.txt')
            watch: Whether to watch for file changes
            poll_interval: Seconds between file checks when watching
            read_mode: File open mode ('r' for text, 'rb' for binary)
            encoding: File encoding (used when read_mode is 'r')
        """
        # Handle both 'file://' URIs and direct paths
        if uri.startswith('file://'):
            from urllib.parse import unquote, urlparse
            parsed = urlparse(uri)
            filepath = unquote(parsed.path)
        else:
            filepath = uri
            
        super().__init__(f"file://{os.path.abspath(filepath)}")
        
        self.filepath = os.path.abspath(filepath)
        self.watch = watch
        self.poll_interval = poll_interval
        self.read_mode = read_mode
        self.encoding = encoding
        self._last_modified = 0
        self._last_size = 0
        self._file_hash = ""
        self._stop_event = asyncio.Event()
    
    async def _connect(self):
        """Verify file exists and is accessible."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        if not os.path.isfile(self.filepath):
            raise ValueError(f"Path is not a file: {self.filepath}")
        logger.info(f"Watching file: {self.filepath}")
    
    async def _disconnect(self):
        """No resources to release."""
        self._stop_event.set()
    
    def _get_file_metadata(self) -> Dict[str, Any]:
        """Get file metadata."""
        stat = os.stat(self.filepath)
        return {
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'path': self.filepath,
            'filename': os.path.basename(self.filepath)
        }
    
    def _calculate_file_hash(self) -> str:
        """Calculate file hash to detect changes."""
        hash_md5 = hashlib.md5()
        with open(self.filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _has_file_changed(self) -> bool:
        """Check if file has changed since last read."""
        try:
            stat = os.stat(self.filepath)
            if stat.st_mtime > self._last_modified or stat.st_size != self._last_size:
                current_hash = self._calculate_file_hash()
                if current_hash != self._file_hash:
                    self._last_modified = stat.st_mtime
                    self._last_size = stat.st_size
                    self._file_hash = current_hash
                    return True
        except Exception as e:
            logger.warning(f"Error checking file changes: {e}")
        return False
    
    async def _read_file(self) -> str:
        """Read file contents."""
        try:
            with open(self.filepath, self.read_mode, encoding=self.encoding if 'b' not in self.read_mode else None) as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error reading file {self.filepath}: {e}")
            raise
    
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield file contents, optionally watching for changes.
        
        Yields:
            Dictionary containing file data and metadata
        """
        # Initial read
        try:
            content = await self._read_file()
            metadata = self._get_file_metadata()
            
            # Update tracking
            self._last_modified = metadata['modified']
            self._last_size = metadata['size']
            self._file_hash = self._calculate_file_hash()
            
            yield {
                'type': 'file',
                'data': content,
                'metadata': metadata,
                'source': self.uri,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # If not watching, we're done
            if not self.watch:
                return
                
            # Watch for changes
            while not self._stop_event.is_set():
                try:
                    if self._has_file_changed():
                        content = await self._read_file()
                        metadata = self._get_file_metadata()
                        
                        yield {
                            'type': 'file_update',
                            'data': content,
                            'metadata': metadata,
                            'source': self.uri,
                            'timestamp': asyncio.get_event_loop().time()
                        }
                    
                    # Wait before next check
                    await asyncio.sleep(self.poll_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in file watch loop: {e}")
                    await asyncio.sleep(min(5, self.poll_interval * 2))  # Backoff on error
                    
        except Exception as e:
            logger.error(f"Error in file source: {e}")
            raise
    
    async def stop(self):
        """Stop watching the file."""
        self._stop_event.set()
    
    def __str__(self):
        """String representation of the source."""
        return f"File Source: {self.filepath}"
