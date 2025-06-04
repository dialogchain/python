"""File destination implementation for DialogChain."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, BinaryIO, TextIO

from ....exceptions import DestinationError
from ..base import Destination

logger = logging.getLogger(__name__)

class FileDestination(Destination):
    """File destination for writing data to the filesystem."""
    
    def __init__(
        self,
        uri: str,
        mode: str = 'w',
        encoding: Optional[str] = 'utf-8',
        newline: Optional[str] = None,
        append: bool = False,
        create_dirs: bool = True,
        atomic_write: bool = False,
        **kwargs
    ):
        """Initialize file destination.
        
        Args:
            uri: File path or URI (e.g., 'file:///path/to/file.txt' or '/path/to/file.txt')
            mode: File open mode ('w' for write, 'a' for append, etc.)
            encoding: File encoding (None for binary mode)
            newline: Controls universal newlines mode (see open())
            append: If True, open file in append mode (overrides 'mode' if set)
            create_dirs: If True, create parent directories if they don't exist
            atomic_write: If True, write to a temporary file first, then rename
            **kwargs: Additional arguments passed to open()
        """
        # Handle file:// URIs
        if uri.startswith('file://'):
            from urllib.parse import unquote, urlparse
            parsed = urlparse(uri)
            filepath = unquote(parsed.path)
        else:
            filepath = uri
            
        super().__init__(f"file://{os.path.abspath(filepath)}")
        
        self.filepath = os.path.abspath(filepath)
        self.mode = 'a' if append else mode
        self.encoding = encoding
        self.newline = newline
        self.create_dirs = create_dirs
        self.atomic_write = atomic_write
        self.file_kwargs = kwargs
        self._file = None
        self._lock = asyncio.Lock()
        
        # Validate mode
        if 'b' in self.mode and self.encoding is not None:
            logger.warning("Encoding is ignored in binary mode")
    
    async def _ensure_directory(self) -> None:
        """Ensure the parent directory exists."""
        if not self.create_dirs:
            return
            
        dir_path = os.path.dirname(self.filepath)
        if dir_path and not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"Created directory: {dir_path}")
            except OSError as e:
                raise DestinationError(f"Failed to create directory {dir_path}: {e}") from e
    
    async def _open_file(self):
        """Open the file if not already open."""
        if self._file is not None and not self._file.closed:
            return
            
        await self._ensure_directory()
        
        try:
            self._file = open(
                self.filepath,
                mode=self.mode,
                encoding=self.encoding,
                newline=self.newline,
                **self.file_kwargs
            )
            logger.debug(f"Opened file: {self.filepath} (mode: {self.mode})")
        except OSError as e:
            raise DestinationError(f"Failed to open file {self.filepath}: {e}") from e
    
    async def _close_file(self):
        """Close the file if open."""
        if self._file is not None and not self._file.closed:
            try:
                self._file.close()
            except Exception as e:
                logger.warning(f"Error closing file {self.filepath}: {e}")
            finally:
                self._file = None
    
    async def _connect(self):
        """Open the file if in a mode that requires it (like 'a' for append)."""
        if 'a' in self.mode or '+' in self.mode:
            await self._open_file()
    
    async def _disconnect(self):
        """Close the file if open."""
        await self._close_file()
    
    async def _write_data(self, data: Any) -> None:
        """Write data to the file."""
        try:
            if isinstance(data, (bytes, bytearray)):
                if 'b' not in self.mode:
                    raise ValueError("Cannot write bytes to text file (open with binary mode)")
                self._file.write(data)
            elif isinstance(data, str):
                if 'b' in self.mode:
                    raise ValueError("Cannot write str to binary file (open with text mode)")
                self._file.write(data)
            elif hasattr(data, 'read'):
                # File-like object
                if hasattr(data, 'seek'):
                    data.seek(0)
                chunk = data.read(8192)
                while chunk:
                    self._file.write(chunk)
                    chunk = data.read(8192)
            else:
                # Try to convert to JSON
                json.dump(data, self._file, ensure_ascii=False, indent=2)
                
            self._file.flush()
            
        except (IOError, OSError) as e:
            raise DestinationError(f"Failed to write to file {self.filepath}: {e}") from e
    
    async def send(self, data: Any, **kwargs) -> None:
        """Write data to the file.
        
        Args:
            data: Data to write (str, bytes, or JSON-serializable object)
            **kwargs: Additional arguments to pass to json.dumps() if data is not str/bytes
            
        Raises:
            DestinationError: If writing fails
        """
        async with self._lock:  # Ensure thread safety
            try:
                if self.atomic_write:
                    await self._atomic_write(data, **kwargs)
                else:
                    if self._file is None or self._file.closed:
                        await self._open_file()
                    await self._write_data(data)
                    
                logger.debug(f"Wrote data to {self.filepath}")
                
            except Exception as e:
                await self._close_file()
                raise DestinationError(f"Failed to write to file {self.filepath}: {e}") from e
    
    async def _atomic_write(self, data: Any, **kwargs) -> None:
        """Write to a temporary file first, then rename atomically."""
        import tempfile
        import shutil
        
        dirname = os.path.dirname(self.filepath)
        basename = os.path.basename(self.filepath)
        
        # Create a temporary file in the same directory for atomicity
        fd, temp_path = tempfile.mkstemp(
            prefix=f".{basename}.",
            dir=dirname,
            text='b' not in self.mode
        )
        
        try:
            with os.fdopen(fd, self.mode.replace('a', 'w'), encoding=self.encoding) as f:
                if isinstance(data, (str, bytes, bytearray)) or hasattr(data, 'read'):
                    if hasattr(data, 'read'):
                        if hasattr(data, 'seek'):
                            data.seek(0)
                        f.write(data.read())
                    else:
                        f.write(data)
                else:
                    json.dump(data, f, **kwargs)
                
                # Ensure all data is written to disk
                f.flush()
                os.fsync(f.fileno())
            
            # On Windows, we need to remove the destination first if it exists
            if os.name == 'nt' and os.path.exists(self.filepath):
                os.unlink(self.filepath)
                
            # Atomic rename
            shutil.move(temp_path, self.filepath)
            
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    
    def __str__(self):
        """String representation of the destination."""
        return f"File Destination: {self.filepath} (mode: {self.mode})"
