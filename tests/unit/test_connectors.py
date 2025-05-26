"""
Tests for connectors (sources and destinations)
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, mock_open
from dialogchain.connectors import (
    TimerSource, FileSource, EmailDestination, 
    HTTPDestination, LogDestination
)

class TestTimerSource:
    
    def test_init(self):
        source = TimerSource('30s')
        assert source.interval == 30
        
        source = TimerSource('5m')
        assert source.interval == 300
        
        source = TimerSource('1h')
        assert source.interval == 3600
    
    @pytest.mark.asyncio
    async def test_timer_events(self):
        source = TimerSource('0.1s')  # Very fast for testing
        
        events = []
        async for event in source.receive():
            events.append(event)
            if len(events) >= 2:
                break
        
        assert len(events) == 2
        assert all(event['type'] == 'timer_event' for event in events)

class TestFileSource:
    
    def test_init(self):
        source = FileSource('/path/to/file.txt')
        assert source.path == '/path/to/file.txt'
    
    @pytest.mark.asyncio
    async def test_file_reading(self):
        source = FileSource('test_file.txt')
        
        with patch('builtins.open', mock_open(read_data='test content')):
            events = []
            async for event in source.receive():
                events.append(event)
                break
            
            assert len(events) == 1
            assert events[0]['type'] == 'file_content'
            assert events[0]['content'] == 'test content'

class TestEmailDestination:
    
    def test_init(self):
        uri = 'email://smtp.gmail.com:587?user=test@test.com&password=pass&to=dest@test.com'
        dest = EmailDestination(uri)
        
        assert dest.server == 'smtp.gmail.com'
        assert dest.port == 587
        assert dest.user == 'test@test.com'
        assert dest.password == 'pass'
        assert 'dest@test.com' in dest.recipients
    
    @pytest.mark.asyncio
    async def test_send_email(self):
        uri = 'email://smtp.test.com:587?user=test@test.com&password=pass&to=dest@test.com'
        dest = EmailDestination(uri)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server
            
            await dest.send({'test': 'message'})
            
            mock_smtp.assert_called_once_with('smtp.test.com', 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('test@test.com', 'pass')
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()

class TestHTTPDestination:
    
    def test_init(self):
        dest = HTTPDestination('http://example.com/webhook')
        assert dest.uri == 'http://example.com/webhook'
    
    @pytest.mark.asyncio
    async def test_send_http(self):
        dest = HTTPDestination('http://example.com/webhook')
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            await dest.send({'test': 'data'})
            
            # Verify that session.post was called
            mock_session.return_value.__aenter__.return_value.post.assert_called_once()

class TestLogDestination:
    
    def test_init(self):
        dest = LogDestination('log://test.log')
        assert dest.log_file == 'test.log'
    
    @pytest.mark.asyncio
    async def test_console_logging(self):
        dest = LogDestination('log://')  # No file, console only
        
        with patch('builtins.print') as mock_print:
            await dest.send('test message')
            mock_print.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_file_logging(self):
        dest = LogDestination('log://test.log')
        
        # Mock the built-in open function and os module
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs:
                
            await dest.send('test message')
            
            # Verify the file was opened in append mode
            mock_file.assert_called_once()
            args, kwargs = mock_file.call_args
            assert args[0] == 'test.log'
            assert 'a' in args or kwargs.get('mode') == 'a'
            assert 'utf-8' in kwargs.get('encoding', '')
            
            # Verify the write was called with the expected message
            write_calls = mock_file.return_value.__enter__.return_value.write.call_args_list
            assert len(write_calls) > 0
            
            # Check that the last write ends with a newline
            last_write = write_calls[-1][0][0]
            assert last_write.endswith('\n')

@pytest.mark.integration
class TestConnectorIntegration:
    
    @pytest.mark.asyncio
    async def test_timer_to_log_pipeline(self):
        """Test complete pipeline from timer source to log destination"""
        source = TimerSource('0.1s')
        dest = LogDestination('log://')
        
        with patch('builtins.print') as mock_print:
            async for event in source.receive():
                await dest.send(event)
                break
            
            mock_print.assert_called_once()