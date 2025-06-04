"""Unit tests for the connectors.destinations module."""
import json
import pytest
import aiohttp
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from dialogchain.connectors import (
    Destination,
    EmailDestination,
    HTTPDestination,
    MQTTDestination,
    FileDestination,
    LogDestination,
    GRPCDestination
)


class TestDestinationBase:
    """Test the base Destination class."""
    
    def test_destination_is_abstract(self):
        """Test that Destination is an abstract base class."""
        with pytest.raises(TypeError):
            Destination()  # Should raise TypeError as it's abstract


class TestEmailDestination:
    """Test the EmailDestination class."""
    
    @pytest.fixture
    def email_dest(self):
        """Create an EmailDestination instance for testing."""
        return EmailDestination("smtp://smtp.example.com:587?user=test@example.com&password=pass&to=recipient@example.com")
    
    @pytest.mark.asyncio
    async def test_send_email(self, email_dest):
        """Test sending an email."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Test with string message
            await email_dest.send("Test email content")
            
            # Verify SMTP connection and login
            mock_smtp.assert_called_once_with('smtp.example.com', 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('test@example.com', 'pass')
            
            # Verify email content
            msg = mock_server.send_message.call_args[0][0]
            assert msg['From'] == 'test@example.com'
            assert 'Test email content' in msg.as_string()
            
            # Verify recipient is set in the loop
            assert mock_server.send_message.call_count == 1
            
            # Test with dict message
            mock_smtp.reset_mock()
            mock_server.reset_mock()
            mock_smtp.return_value = mock_server
            
            await email_dest.send({"key": "value"})
            msg = mock_server.send_message.call_args[0][0]
            assert 'Camel Router Alert' in msg['Subject']
            assert '"key": "value"' in msg.as_string()
            
            # Clean up
            mock_server.quit.assert_called_once()


class TestHTTPDestination:
    """Test the HTTPDestination class."""
    
    @pytest.fixture
    def http_dest(self):
        """Create an HTTPDestination instance for testing."""
        return HTTPDestination("http://example.com/webhook")
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_send_http_request(self, mock_session_class, http_dest, capsys):
        """Test sending an HTTP request."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = "OK"
        
        # Setup mock post method
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value = mock_response
        
        # Setup mock session
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_post
        mock_session.__aenter__.return_value = mock_session
        mock_session_class.return_value = mock_session
        
        # Test with dict message
        await http_dest.send({"key": "value"})
        
        # Verify HTTP POST request was made
        mock_session.post.assert_called_once_with(
            'http://example.com/webhook',
            json={"key": "value"}
        )
        
        # Check output
        captured = capsys.readouterr()
        assert "🌐 HTTP sent to http://example.com/webhook" in captured.out
        
        # Reset mocks for next test
        mock_session.post.reset_mock()
        mock_response.status = 200
        
        # Test with string message
        await http_dest.send("test message")
        mock_session.post.assert_called_once_with(
            'http://example.com/webhook',
            json={"data": "test message"}
        )
        
        # Reset mocks for error test
        mock_session.post.reset_mock()
        mock_response.status = 400
        mock_response.text.return_value = "Bad Request"
        
        # Test error case
        await http_dest.send({"key": "value"})
        captured = capsys.readouterr()
        assert "❌ HTTP error 400: Bad Request" in captured.out


class TestMQTTDestination:
    """Test the MQTTDestination class."""
    
    @pytest.fixture
    def mqtt_dest(self):
        """Create an MQTTDestination instance for testing."""
        return MQTTDestination("mqtt://broker.example.com:1883/test/topic")
    
    @pytest.mark.asyncio
    async def test_send_mqtt_message(self, mqtt_dest, capsys):
        """Test sending an MQTT message."""
        # Test with string message
        await mqtt_dest.send("test message")
        
        # Check output
        captured = capsys.readouterr()
        assert "📡 MQTT sent to broker.example.com:1883/test/topic" in captured.out
        
        # Test with dict message
        await mqtt_dest.send({"key": "value"})
        
        # Check output
        captured = capsys.readouterr()
        assert "📡 MQTT sent to broker.example.com:1883/test/topic" in captured.out
        
        # Test error case
        with patch('json.dumps', side_effect=Exception("Test error")):
            await mqtt_dest.send({"key": "value"})
            captured = capsys.readouterr()
            assert "❌ MQTT error: Test error" in captured.out


class TestFileDestination:
    """Test the FileDestination class."""
    
    @pytest.fixture
    def file_dest(self, tmp_path):
        """Create a FileDestination instance for testing."""
        test_file = tmp_path / "output.txt"
        return FileDestination(f"file://{test_file}")
    
    @pytest.mark.asyncio
    async def test_write_to_file(self, file_dest, tmp_path, capsys):
        """Test writing to a file."""
        # Test with string message
        test_content = "Test file content"
        await file_dest.send(test_content)
        
        # Verify file was written
        output_file = tmp_path / "output.txt"
        assert output_file.exists()
        
        # Check the content includes the timestamp and the message
        content = output_file.read_text()
        assert test_content in content
        
        # Check output
        captured = capsys.readouterr()
        assert f"📄 Written to {output_file}" in captured.out
        
        # Test with dict message
        test_dict = {"key": "value"}
        await file_dest.send(test_dict)
        
        # Check the content includes the JSON string
        content = output_file.read_text()
        assert '"key": "value"' in content
        
        # Test error case
        with patch('json.dumps', side_effect=Exception("Test error")):
            await file_dest.send({"key": "value"})
            captured = capsys.readouterr()
            assert "❌ File destination error: Test error" in captured.out


class TestLogDestination:
    """Test the LogDestination class."""
    
    @pytest.fixture
    def log_dest(self, tmp_path):
        """Create a LogDestination instance for testing."""
        log_file = tmp_path / "test.log"
        return LogDestination(f"log://{log_file}")
    
    @pytest.mark.asyncio
    async def test_log_to_console(self, capsys):
        """Test logging to console."""
        log_dest = LogDestination("log://")
        test_message = "Test log message"
        
        await log_dest.send(test_message)
        
        # Verify message was printed to console with timestamp and emoji
        captured = capsys.readouterr()
        assert "📝" in captured.out
        assert test_message in captured.out
        assert datetime.now().isoformat()[:10] in captured.out  # Check date part of timestamp
    
    @pytest.fixture
    def log_dest(self, tmp_path):
        """Create a LogDestination instance for testing."""
        log_file = tmp_path / "test.log"
        return LogDestination(f"log://{log_file}")
    
    @pytest.mark.asyncio
    async def test_log_to_file(self, log_dest, tmp_path, capsys):
        """Test logging to a file."""
        test_message = "Test log message to file"
        
        # Test with string message
        await log_dest.send(test_message)
        
        # Get the log file path directly from the log_dest instance
        log_file = tmp_path / "test.log"
        
        # Verify file was created
        assert log_file.exists(), f"Log file {log_file} was not created"
        
        # Read the file content
        content = log_file.read_text()
        
        # Verify the log content
        assert "📝" in content, "Log entry emoji not found"
        assert test_message in content, "Log message not found in log file"
        
        # Check the date format (YYYY-MM-DD)
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        assert date_prefix in content, f"Date prefix {date_prefix} not found in log"
        
        # Verify message was also printed to console
        captured = capsys.readouterr()
        assert test_message in captured.out, "Log message not printed to console"
        
        # Clear the captured output
        capsys.readouterr()
        
        # Test with a subdirectory that doesn't exist
        log_dir = tmp_path / "logs"
        subdir_log_file = log_dir / "subdir_test.log"
        subdir_log_dest = LogDestination(f"log://{subdir_log_file}")
        
        await subdir_log_dest.send(test_message)
        assert subdir_log_file.exists(), f"Subdirectory log file {subdir_log_file} was not created"
        
        # Verify the subdirectory was created
        assert log_dir.exists(), f"Log directory {log_dir} was not created"
        
        # Read the subdirectory log file content
        subdir_content = subdir_log_file.read_text()
        assert test_message in subdir_content, "Log message not found in subdirectory log file"
        
        # Test error case for file writing
        with patch('builtins.open', side_effect=Exception("Test error")) as mock_open:
            await log_dest.send(test_message)
            captured = capsys.readouterr()
            assert "❌ Log file error: Test error" in captured.out, "Error message not found in output"
