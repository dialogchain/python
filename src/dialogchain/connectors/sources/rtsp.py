"""RTSP source implementation for DialogChain."""

import asyncio
import cv2
import logging
from typing import Dict, Any, AsyncIterator
from urllib.parse import urlparse

from ..base import Source

logger = logging.getLogger(__name__)

class RTSPSource(Source):
    """RTSP video stream source."""
    
    def __init__(self, uri: str, reconnect_attempts: int = 3, frame_skip: int = 3):
        """Initialize RTSP source.
        
        Args:
            uri: RTSP stream URI (e.g., 'rtsp://username:password@ip:port/stream')
            reconnect_attempts: Number of reconnection attempts on failure
            frame_skip: Process every N-th frame (for performance)
        """
        super().__init__(uri)
        self.reconnect_attempts = reconnect_attempts
        self.frame_skip = frame_skip
        self._cap = None
        self._frame_count = 0
    
    async def _connect(self):
        """Establish RTSP connection."""
        # RTSP connection is handled in the receive method
        pass
    
    async def _disconnect(self):
        """Release RTSP resources."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
    
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Receive frames from RTSP stream.
        
        Yields:
            Dictionary containing frame data and metadata
            
        Raises:
            ConnectionError: If connection to RTSP stream fails after retries
        """
        for attempt in range(self.reconnect_attempts):
            try:
                logger.info(f"Connecting to RTSP stream: {self.uri}")
                self._cap = cv2.VideoCapture(self.uri)
                
                if not self._cap.isOpened():
                    raise ConnectionError(f"Failed to open RTSP stream: {self.uri}")
                
                logger.info("RTSP stream connected")
                
                while self.is_connected:
                    ret, frame = self._cap.read()
                    if not ret:
                        logger.warning("Failed to read frame from RTSP stream")
                        break
                    
                    self._frame_count += 1
                    if self._frame_count % self.frame_skip != 0:
                        continue
                    
                    yield {
                        'frame': frame,
                        'frame_count': self._frame_count,
                        'timestamp': asyncio.get_event_loop().time(),
                        'source': self.uri
                    }
                    
                    # Small sleep to prevent high CPU usage
                    await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"RTSP stream error (attempt {attempt + 1}/{self.reconnect_attempts}): {e}")
                if attempt == self.reconnect_attempts - 1:
                    raise ConnectionError(f"Failed to connect to RTSP stream after {self.reconnect_attempts} attempts") from e
                
                # Wait before reconnecting
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            finally:
                if self._cap is not None:
                    self._cap.release()
                    self._cap = None
                
                if attempt < self.reconnect_attempts - 1:
                    logger.info("Reconnecting to RTSP stream...")
    
    def __str__(self):
        """String representation of the source."""
        return f"RTSP Source: {self.uri}"
