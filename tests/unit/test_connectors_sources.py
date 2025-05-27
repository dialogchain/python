"""Unit tests for the connectors.sources module."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from dialogchain.connectors import (
    Source,
    RTSPSource,
    TimerSource,
    GRPCSource,
    FileSource
)


class TestSourceBase:
    """Test the base Source class."""
    
    def test_source_is_abstract(self):
        """Test that Source is an abstract base class."""
        with pytest.raises(TypeError):
            Source()  # Should raise TypeError as it's abstract


class TestRTSPSource:
    """Test the RTSPSource class."""
    
    @pytest.fixture
    def rtsp_source(self):
        """Create an RTSPSource instance for testing."""
        return RTSPSource("rtsp://test:554/stream")
    
    @pytest.mark.asyncio
    async def test_receive_frames(self, rtsp_source):
        """Test receiving frames from RTSP source."""
        # Mock cv2.VideoCapture
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (True, "frame1"),
            (True, "frame2"),
            (True, "frame3"),
            (False, None)  # Simulate end of stream
        ]
        
        with patch('cv2.VideoCapture', return_value=mock_cap), \
             patch('time.sleep', return_value=None):
            
            frames = []
            async for frame in rtsp_source.receive():
                frames.append(frame)
                if len(frames) >= 3:
                    break
            
            assert len(frames) == 3
            assert frames == ["frame1", "frame2", "frame3"]
    
    @pytest.mark.asyncio
    async def test_reconnect_on_failure(self, rtsp_source):
        """Test reconnection logic when frame reading fails."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.side_effect = [
            (False, None),  # First read fails
            (True, "frame1"),  # After reconnect
            (False, None)  # End of stream
        ]
        
        with patch('cv2.VideoCapture', return_value=mock_cap), \
             patch('time.sleep', return_value=None):
            
            frames = []
            async for frame in rtsp_source.receive():
                frames.append(frame)
            
            assert frames == ["frame1"]
            assert mock_cap.release.call_count == 2  # Should be released twice (once after failure, once at the end)


class TestTimerSource:
    """Test the TimerSource class."""
    
    @pytest.fixture
    def timer_source(self):
        """Create a TimerSource instance for testing."""
        return TimerSource("1s")  # 1 second interval
    
    @pytest.mark.asyncio
    async def test_timer_interval(self, timer_source):
        """Test timer generates events at the correct interval."""
        events = []
        
        # Collect 3 events with a short timeout
        async def collect_events():
            async for event in timer_source.receive():
                events.append(event)
                if len(events) >= 3:
                    break
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Make the sleep complete immediately for the test
            mock_sleep.side_effect = [None, None, None]
            await collect_events()
            
            # Should have slept 3 times (for 3 events)
            assert mock_sleep.await_count == 3
            assert len(events) == 3
    
    def test_parse_interval(self):
        """Test interval string parsing."""
        # Test seconds
        assert TimerSource("30s")._parse_interval("30s") == 30.0
        # Test minutes
        assert TimerSource("2m")._parse_interval("2m") == 120.0
        # Test hours
        assert TimerSource("1.5h")._parse_interval("1.5h") == 5400.0
        # Test invalid format
        with pytest.raises(ValueError):
            TimerSource("invalid")._parse_interval("invalid")


class TestFileSource:
    """Test the FileSource class."""
    
    @pytest.fixture
    def file_source(self, tmp_path):
        """Create a FileSource instance for testing."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        return FileSource(str(test_file))
    
    @pytest.mark.asyncio
    async def test_file_source_read(self, file_source, tmp_path):
        """Test reading from a file source."""
        test_file = tmp_path / "test.txt"
        
        # Mock file watcher to trigger a change
        mock_watcher = MagicMock()
        mock_watcher.__aiter__.return_value = [{"src_path": str(test_file)}]
        
        with patch('watchfiles.awatch', return_value=mock_watcher):
            content = None
            async for data in file_source.receive():
                content = data
                break  # Just get the first event
            
            assert content == "test content"
    
    @pytest.mark.asyncio
    async def test_file_source_nonexistent(self, tmp_path):
        """Test file source with non-existent file."""
        non_existent = tmp_path / "nonexistent.txt"
        file_source = FileSource(str(non_existent))
        
        with pytest.raises(FileNotFoundError):
            async for _ in file_source.receive():
                pass
