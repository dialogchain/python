"""Unit tests for the connectors.destinations module."""
import json
import pytest
import aiohttp
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
        mock_smtp = MagicMock()
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        with patch('smtplib.SMTP', mock_smtp):
            await email_dest.send("Test email content")
            
            # Verify SMTP connection and login
            mock_smtp.assert_called_once_with('smtp.example.com', 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with('test@example.com', 'pass')
            
            # Verify email content
            msg = mock_server.send_message.call_args[0][0]
            assert msg['From'] == 'test@example.com'
            assert msg['To'] == 'recipient@example.com'
            assert 'Test email content' in msg.as_string()


class TestHTTPDestination:
    """Test the HTTPDestination class."""
    
    @pytest.fixture
    def http_dest(self):
        """Create an HTTPDestination instance for testing."""
        return HTTPDestination("http://example.com/webhook")
    
    @pytest.mark.asyncio
    async def test_send_http_request(self, http_dest):
        """Test sending an HTTP request."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            await http_dest.send({"key": "value"})
            
            # Verify HTTP POST request was made
            mock_session.post.assert_awaited_once_with(
                'http://example.com/webhook',
                json={"key": "value"},
                headers={'Content-Type': 'application/json'}
            )


class TestMQTTDestination:
    """Test the MQTTDestination class."""
    
    @pytest.fixture
    def mqtt_dest(self):
        """Create an MQTTDestination instance for testing."""
        return MQTTDestination("mqtt://broker.example.com:1883/test/topic")
    
    @pytest.mark.asyncio
    async def test_send_mqtt_message(self, mqtt_dest):
        """Test sending an MQTT message."""
        mock_client = AsyncMock()
        
        with patch('paho.mqtt.client.Client', return_value=mock_client):
            # Mock the connect method to avoid actual connection
            with patch.object(mqtt_dest, 'connect', new_callable=AsyncMock) as mock_connect:
                await mqtt_dest.send("test message")
                
                # Verify connection and message publishing
                mock_connect.assert_awaited_once()
                mock_client.publish.assert_called_once_with(
                    'test/topic',
                    'test message'
                )


class TestFileDestination:
    """Test the FileDestination class."""
    
    @pytest.fixture
    def file_dest(self, tmp_path):
        """Create a FileDestination instance for testing."""
        test_file = tmp_path / "output.txt"
        return FileDestination(f"file://{test_file}")
    
    @pytest.mark.asyncio
    async def test_write_to_file(self, file_dest, tmp_path):
        """Test writing to a file."""
        test_content = "Test file content"
        
        await file_dest.send(test_content)
        
        # Verify file was written
        output_file = tmp_path / "output.txt"
        assert output_file.exists()
        assert output_file.read_text() == test_content


class TestLogDestination:
    """Test the LogDestination class."""
    
    @pytest.fixture
    def log_dest(self, tmp_path):
        """Create a LogDestination instance for testing."""
        log_file = tmp_path / "test.log"
        return LogDestination(f"log://{log_file}")
    
    def test_log_to_console(self, capsys):
        """Test logging to console."""
        log_dest = LogDestination("log://")
        test_message = "Test log message"
        
        log_dest.send(test_message)
        
        # Verify message was printed to console
        captured = capsys.readouterr()
        assert test_message in captured.out
    
    @pytest.mark.asyncio
    async def test_log_to_file(self, log_dest, tmp_path):
        """Test logging to a file."""
        test_message = "Test log message to file"
        
        await log_dest.send(test_message)
        
        # Verify message was written to log file
        log_file = tmp_path / "test.log"
        assert log_file.exists()
        assert test_message in log_file.read_text()
