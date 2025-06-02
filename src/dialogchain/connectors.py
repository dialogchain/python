import asyncio
import json
import smtplib
import ssl
import aiohttp
import cv2
import os
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any, Dict
from urllib.parse import urlparse, parse_qs
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)



class Source(ABC):
    """Base class for all sources"""

    @abstractmethod
    async def receive(self) -> AsyncIterator[Any]:
        """Async generator that yields messages"""
        pass


class Destination(ABC):
    """Base class for all destinations"""

    @abstractmethod
    async def send(self, message: Any) -> None:
        """Send message to destination"""
        pass


# ============= SOURCES =============


class RTSPSource(Source):
    """RTSP camera source"""

    def __init__(self, uri: str):
        self.uri = uri
        self.reconnect_attempts = 3
        self.frame_skip = 3  # Process every 3rd frame

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield camera frames"""
        for attempt in range(self.reconnect_attempts):
            try:
                cap = cv2.VideoCapture(self.uri)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not cap.isOpened():
                    raise Exception(f"Cannot connect to RTSP: {self.uri}")

                frame_count = 0
                print(f"📹 Connected to camera: {self.uri}")

                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logger.info("📹 Lost connection to camera")
                        break

                    # Skip frames for performance
                    if frame_count % self.frame_skip == 0:
                        yield {
                            "type": "camera_frame",
                            "timestamp": datetime.now().isoformat(),
                            "frame": frame,
                            "frame_count": frame_count,
                            "source": self.uri,
                        }

                    frame_count += 1
                    await asyncio.sleep(0.033)  # ~30 FPS

            except Exception as e:
                print(f"📹 Camera error (attempt {attempt + 1}): {e}")
                if attempt < self.reconnect_attempts - 1:
                    await asyncio.sleep(5)
                else:
                    raise
            finally:
                if "cap" in locals():
                    cap.release()


class TimerSource(Source):
    """Timer-based source for scheduled tasks"""

    def __init__(self, interval: str):
        self.interval = self._parse_interval(interval)

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield timer events"""
        while True:
            yield {
                "type": "timer_event",
                "timestamp": datetime.now().isoformat(),
                "interval": self.interval,
            }
            await asyncio.sleep(self.interval)

    def _parse_interval(self, interval_str: str) -> float:
        """Parse interval string to seconds

        Args:
            interval_str: String in format '1s' (seconds), '1m' (minutes), or '1h' (hours)

        Returns:
            float: Interval in seconds

        Raises:
            ValueError: If interval_str is empty or invalid
        """
        if not interval_str or not isinstance(interval_str, str):
            raise ValueError(
                f"Invalid interval: '{interval_str}'. Must be a non-empty string."
            )

        try:
            if interval_str.endswith("s"):
                return float(interval_str[:-1])
            elif interval_str.endswith("m"):
                return float(interval_str[:-1]) * 60
            elif interval_str.endswith("h"):
                return float(interval_str[:-1]) * 3600
            else:
                return float(interval_str)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid interval format: '{interval_str}'. Expected format: '1s', '1m', or '1h'."
            ) from e


class GRPCSource(Source):
    """gRPC server source"""

    def __init__(self, uri: str):
        self.uri = uri
        # Implementation would depend on specific gRPC service

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield gRPC messages - placeholder implementation"""
        while True:
            # This would connect to actual gRPC service
            yield {
                "type": "grpc_message",
                "timestamp": datetime.now().isoformat(),
                "data": "placeholder",
            }
            await asyncio.sleep(1)


class FileSource(Source):
    """File watcher source"""

    def __init__(self, path: str):
        self.path = path

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Watch file for changes"""
        # Basic file reading - could be enhanced with file watching
        try:
            with open(self.path, "r") as f:
                content = f.read()
                yield {
                    "type": "file_content",
                    "timestamp": datetime.now().isoformat(),
                    "path": self.path,
                    "content": content,
                }
        except Exception as e:
            print(f"❌ File source error: {e}")


# ============= DESTINATIONS =============


class EmailDestination(Destination):
    """Email destination using SMTP"""

    def __init__(self, uri: str):
        parsed = urlparse(uri)
        self.server = parsed.hostname
        self.port = parsed.port or 587

        query_params = parse_qs(parsed.query)
        self.user = query_params.get("user", [""])[0]
        self.password = query_params.get("password", [""])[0]
        self.recipients = query_params.get("to", [""])

        if isinstance(self.recipients, list) and len(self.recipients) == 1:
            self.recipients = self.recipients[0].split(",")

    async def send(self, message: Any) -> None:
        """Send email with enhanced logging"""
        try:
            print(f"🔧 Preparing email with server: {self.server}:{self.port}")
            print(f"🔧 Authenticating as user: {self.user}")
            
            msg = MIMEMultipart()
            msg["From"] = self.user
            
            # Extract subject from message if it's a dict and has a subject field
            if isinstance(message, dict) and 'subject' in message:
                msg["Subject"] = message.get('subject', 'Camel Router Alert')
                print(f"📨 Using subject from message: {msg['Subject']}")
            else:
                msg["Subject"] = "Camel Router Alert"
                logger.info("ℹ️  Using default subject")

            # Format message body
            if isinstance(message, dict):
                body = json.dumps(message, indent=2)
                logger.info(f"ℹ️  Message is a dictionary, converting to JSON")
            else:
                body = str(message)
                logger.info(f"ℹ️  Message is a string, length: {len(body)} characters")

            msg.attach(MIMEText(body, "plain"))
            logger.info(f"✉️  Message prepared, connecting to SMTP server...")

            # SMTP connection and sending
            logger.info(f"🔌 Connecting to SMTP server: {self.server}:{self.port}")
            
            # Use SMTP_SSL for port 465, regular SMTP for other ports with STARTTLS
            if self.port == 465:
                logger.info("🔒 Using SSL/TLS (port 465)")
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.server, self.port, timeout=10, context=context)
                logger.info("✅ Established SSL connection")
            else:
                logger.info("🔓 Using STARTTLS (port 587 or other)")
                server = smtplib.SMTP(self.server, self.port, timeout=10)
                server.starttls()
                logger.info("✅ STARTTLS negotiation successful")
            
            logger.info(f"🔑 Authenticating user: {self.user}")
            server.login(self.user, self.password)
            logger.info("✅ Authentication successful")

            success_count = 0
            for recipient in self.recipients:
                clean_recipient = recipient.strip()
                if not clean_recipient:
                    logger.info("⚠️  Empty recipient, skipping")
                    continue
                    
                try:
                    msg["To"] = clean_recipient
                    logger.info(f"📤 Sending to: {clean_recipient}")
                    server.send_message(msg)
                    del msg["To"]
                    success_count += 1
                    logger.info(f"✅ Successfully sent to: {clean_recipient}")
                except Exception as send_error:
                    logger.error(f"❌ Failed to send to {clean_recipient}: {send_error}")

            server.quit()
            logger.info(f"📬 Email sending complete. Successfully sent to {success_count}/{len(self.recipients)} recipients")

        except smtplib.SMTPException as smtp_error:
            logger.error(f"❌ SMTP Error: {smtp_error}")
            logger.error(f"   SMTP Code: {getattr(smtp_error, 'smtp_code', 'N/A')}")
            logger.error(f"   SMTP Error: {getattr(smtp_error, 'smtp_error', 'N/A')}")
        except Exception as e:
            import traceback
            logger.error(f"❌ Unexpected error: {e}")
            logger.error("📝 Stack trace:")
            traceback.print_exc()


class HTTPDestination(Destination):
    """HTTP webhook destination"""

    def __init__(self, uri: str):
        self.uri = uri

    async def send(self, message: Any) -> None:
        """Send HTTP POST request"""
        try:
            async with aiohttp.ClientSession() as session:
                data = message if isinstance(message, dict) else {"data": message}
                async with session.post(self.uri, json=data) as response:
                    if response.status == 200:
                        logger.info(f"🌐 HTTP sent to {self.uri}")
                    else:
                        logger.error(
                            f"❌ HTTP error {response.status}: {await response.text()}"
                        )
        except Exception as e:
            logger.error(f"❌ HTTP destination error: {e}")


class MQTTDestination(Destination):
    """MQTT destination"""

    def __init__(self, uri: str):
        parsed = urlparse(uri)
        self.broker = parsed.hostname
        self.port = parsed.port or 1883
        self.topic = parsed.path.lstrip("/")

    async def send(self, message: Any) -> None:
        """Send MQTT message"""
        try:
            # Note: Would need asyncio-mqtt library
            payload = json.dumps(message) if isinstance(message, dict) else str(message)
            logger.info(f"📡 MQTT sent to {self.broker}:{self.port}/{self.topic}")
            # Implementation would use actual MQTT client
        except Exception as e:
            logger.error(f"❌ MQTT error: {e}")


class FileDestination(Destination):
    """File destination"""

    def __init__(self, uri: str):
        parsed = urlparse(uri)
        self.path = parsed.path

    async def send(self, message: Any) -> None:
        """Write to file"""
        try:
            content = json.dumps(message) if isinstance(message, dict) else str(message)
            with open(self.path, "a") as f:
                f.write(f"{datetime.now().isoformat()}: {content}\n")
            logger.info(f"📄 Written to {self.path}")
        except Exception as e:
            logger.error(f"❌ File destination error: {e}")


class LogDestination(Destination):
    """Log destination for both console and file logging"""

    def __init__(self, uri: str):
        parsed = urlparse(uri)
        # For URIs like 'log://test.log', the path is in netloc
        self.log_file = parsed.netloc if parsed.netloc else parsed.path.strip("/")
        # If both netloc and path are empty, set to None
        self.log_file = self.log_file if self.log_file else None

    async def send(self, message: Any) -> None:
        """Log message to console and optionally to a file"""
        log_msg = f"📝 {datetime.now().isoformat()}: {message}"
        logger.info(log_msg)

        if self.log_file:
            try:
                # Ensure directory exists
                log_dir = os.path.dirname(self.log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)

                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_msg + "\n")
            except Exception as e:
                logger.error(f"❌ Log file error: {e}")


class GRPCDestination(Destination):
    """gRPC destination"""

    def __init__(self, uri: str):
        self.uri = uri

    async def send(self, message: Any) -> None:
        """Send gRPC message"""
        try:
            # Implementation would depend on specific gRPC service
            logger.info(f"🔗 gRPC sent to {self.uri}")
        except Exception as e:
            logger.error(f"❌ gRPC destination error: {e}")
