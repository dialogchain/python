import asyncio
import json
import smtplib
import ssl
import aiohttp
import cv2
import os
import logging
import imaplib
import email
import email.policy
from email.header import decode_header
from email.utils import parsedate_to_datetime
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any, Dict, Optional, List, Tuple, Union
from urllib.parse import urlparse, parse_qs, unquote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
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


class IMAPSource(Source):
    """IMAP email source for fetching emails from an IMAP server.
    
    URI format: imap://username:password@server:port/folder?param=value
    
    Query parameters:
    - since: Only fetch emails since this date (YYYY-MM-DD)
    - before: Only fetch emails before this date (YYYY-MM-DD)
    - subject: Filter emails by subject (case-insensitive contains)
    - from: Filter emails by sender (case-insensitive contains)
    - to: Filter emails by recipient (case-insensitive contains)
    - unseen: Only fetch unseen emails (true/false)
    - limit: Maximum number of emails to fetch per poll (default: 10, max: 100)
    - mark_read: Mark emails as read after fetching (true/false, default: false)
    - rate_limit: Maximum number of requests per minute (default: 30)
    - timeout: Connection timeout in seconds (default: 30)
    - idle_timeout: Time in seconds to keep connection alive (default: 300)
    - skip_ssl_verify: Skip SSL certificate verification (true/false, default: false)
    """
    
    def __init__(self, uri: str):
        parsed = urlparse(uri)
        self.server = parsed.hostname
        self.port = parsed.port or 993
        self.username = unquote(parsed.username or "")
        self.password = unquote(parsed.password or "")
        self.folder = parsed.path.strip("/") or "INBOX"
        
        # Parse query parameters
        query = parse_qs(parsed.query)
        self.since = query.get("since", [None])[0]
        self.before = query.get("before", [None])[0]
        self.subject = query.get("subject", [None])[0]
        self.sender = query.get("from", [None])[0]
        self.recipient = query.get("to", [None])[0]
        self.unseen_only = query.get("unseen", ["false"])[0].lower() == "true"
        self.limit = min(int(query.get("limit", ["10"])[0]), 100)  # Max 100 emails per poll
        self.mark_read = query.get("mark_read", ["false"])[0].lower() == "true"
        self.rate_limit = int(query.get("rate_limit", ["30"])[0])
        self.timeout = int(query.get("timeout", ["30"])[0])
        self.idle_timeout = int(query.get("idle_timeout", ["300"])[0])
        self.skip_ssl_verify = query.get("skip_ssl_verify", ["false"])[0].lower() == "true"
        
        self.imap = None
        self._connection_lock = asyncio.Lock()
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_reset_time = 0
    
    async def _ensure_connected(self) -> None:
        """Ensure we have an active IMAP connection with proper error handling and recovery"""
        if self.imap:
            try:
                # Test if connection is still alive
                self.imap.noop()
                if hasattr(self.imap, 'state') and self.imap.state == 'SELECTED':
                    return
            except (imaplib.IMAP4.error, ConnectionError, TimeoutError, OSError) as e:
                logger.warning(f"IMAP connection test failed, will reconnect: {e}")
                self.imap = None
        
        async with self._connection_lock:
            if self.imap:  # Check again in case another coroutine reconnected
                return
                
            logger.info(f"Connecting to IMAP server: {self.server}:{self.port}")
            
            # Create SSL context with secure defaults
            context = ssl.create_default_context()
            
            if self.skip_ssl_verify:
                logger.warning("SSL certificate verification is disabled - this is not recommended for production")
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            try:
                # Apply rate limiting
                await self._rate_limit()
                
                # Connect with timeout
                logger.debug(f"Establishing IMAP4_SSL connection to {self.server}:{self.port}")
                self.imap = imaplib.IMAP4_SSL(
                    host=self.server,
                    port=self.port,
                    ssl_context=context,
                    timeout=self.timeout
                )
                
                # Enable UTF-8 support if available
                try:
                    self.imap.enable('UTF8=ACCEPT')
                except Exception as e:
                    logger.debug(f"UTF8=ACCEPT not supported: {e}")
                
                # Login
                logger.debug(f"Authenticating as {self.username}")
                self.imap.login(self.username, self.password)
                
                # List available mailboxes for debugging
                if logger.isEnabledFor(logging.DEBUG):
                    try:
                        status, mailboxes = self.imap.list()
                        if status == 'OK':
                            logger.debug("Available mailboxes:" + "\n  " + 
                                       "\n  ".join(m.decode('utf-8', errors='replace') for m in mailboxes))
                    except Exception as e:
                        logger.debug(f"Could not list mailboxes: {e}")
                
                # Select folder
                logger.info(f"Selecting folder: {self.folder}")
                status, response = self.imap.select(self.folder, readonly=not self.mark_read)
                if status != 'OK':
                    error_msg = response[0].decode('utf-8', errors='replace') if response else 'Unknown error'
                    logger.error(f"Failed to select folder {self.folder}: {error_msg}")
                    
                    # Try to create folder if it doesn't exist
                    if b'[NONEXISTENT]' in response[0].upper():
                        logger.info(f"Folder {self.folder} does not exist, attempting to create it")
                        status, response = self.imap.create(self.folder)
                        if status == 'OK':
                            status, response = self.imap.select(self.folder, readonly=not self.mark_read)
                
                if status != 'OK':
                    error_msg = response[0].decode('utf-8', errors='replace') if response else 'Unknown error'
                    raise ConnectionError(f"Failed to select folder {self.folder}: {error_msg}")
                
                logger.info(f"Successfully connected to IMAP server and selected folder: {self.folder}")
                
            except (imaplib.IMAP4.error, ConnectionError, TimeoutError, OSError) as e:
                self.imap = None
                logger.error(f"IMAP connection failed: {e}")
                raise ConnectionError(f"Failed to connect to IMAP server: {e}")
            except Exception as e:
                self.imap = None
                logger.error(f"Unexpected error during IMAP connection: {e}", exc_info=True)
                raise ConnectionError(f"Unexpected error during IMAP connection: {e}")
    
    async def _rate_limit(self) -> None:
        """Implement rate limiting for IMAP requests"""
        now = time.time()
        
        # Reset counter if we're in a new rate limit window
        if now > self._rate_limit_reset_time:
            self._request_count = 0
            self._rate_limit_reset_time = now + 60  # 1 minute window
        
        # If we've exceeded the rate limit, wait until the next window
        if self._request_count >= self.rate_limit:
            sleep_time = self._rate_limit_reset_time - now
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, waiting {sleep_time:.2f} seconds...")
                await asyncio.sleep(sleep_time)
                self._request_count = 0
                self._rate_limit_reset_time = time.time() + 60
        
        self._request_count += 1
        self._last_request_time = time.time()
    
    def _parse_email(self, msg_data: bytes) -> Dict[str, Any]:
        """Parse email message into a dictionary"""
        msg = email.message_from_bytes(msg_data, policy=email.policy.default)
        
        # Get basic headers
        email_data = {
            'subject': self._decode_header(msg.get('Subject', '')),
            'from': self._decode_header(msg.get('From', '')),
            'to': self._decode_header(msg.get('To', '')),
            'date': self._parse_date(msg.get('Date')),
            'message_id': msg.get('Message-ID', '').strip('<>'),
            'in_reply_to': msg.get('In-Reply-To', '').strip('<>'),
            'references': [ref.strip() for ref in msg.get('References', '').split()],
            'content': '',
            'attachments': [],
            'headers': {k: self._decode_header(v) for k, v in msg.items()}
        }
        
        # Parse email parts
        self._parse_email_parts(msg, email_data)
        
        return email_data
    
    def _parse_email_parts(self, msg: email.message.Message, email_data: Dict[str, Any]) -> None:
        """Recursively parse email parts"""
        if msg.is_multipart():
            for part in msg.get_payload():
                self._parse_email_parts(part, email_data)
        else:
            try:
                content_type = msg.get_content_type()
                content_disposition = msg.get('Content-Disposition', '')
                
                # Handle attachments
                if 'attachment' in content_disposition or 'filename' in content_disposition:
                    filename = msg.get_filename()
                    if filename:
                        filename = self._decode_header(filename)
                        payload = msg.get_payload(decode=True) or b''
                        email_data['attachments'].append({
                            'filename': filename,
                            'content_type': content_type,
                            'size': len(payload),
                            'data': payload
                        })
                # Handle text content - prefer plain text over HTML
                elif content_type == 'text/plain' and not email_data['content']:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            charset = msg.get_content_charset() or 'utf-8'
                            email_data['content'] = payload.decode(charset, errors='replace')
                    except Exception as e:
                        logger.warning(f"Failed to decode email content: {e}")
                # Fallback to HTML if no plain text content
                elif content_type == 'text/html' and not email_data['content']:
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            charset = msg.get_content_charset() or 'utf-8'
                            email_data['content'] = payload.decode(charset, errors='replace')
                    except Exception as e:
                        logger.warning(f"Failed to decode HTML email content: {e}")
            except Exception as e:
                logger.error(f"Error parsing email part: {e}", exc_info=True)
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        try:
            decoded = []
            for part, encoding in decode_header(header):
                if isinstance(part, bytes):
                    try:
                        part = part.decode(encoding or 'utf-8', errors='replace')
                    except (UnicodeDecodeError, LookupError):
                        part = part.decode('latin-1', errors='replace')
                decoded.append(part)
            return ''.join(decoded)
        except Exception as e:
            logger.warning(f"Failed to decode header: {e}")
            return str(header)
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """Parse email date into ISO format"""
        if not date_str:
            return datetime.utcnow().isoformat()
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return datetime.utcnow().isoformat()
    
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Asynchronously fetch emails from the IMAP server.
        
        Yields:
            Dict containing email data with the following structure:
            {
                'type': 'email',
                'timestamp': ISO timestamp,
                'data': {
                    'subject': str,
                    'from': str,
                    'to': str,
                    'date': str (ISO format),
                    'message_id': str,
                    'in_reply_to': str,
                    'references': List[str],
                    'content': str,
                    'attachments': List[Dict],
                    'headers': Dict[str, str]
                }
            }
        """
        retry_count = 0
        max_retries = 3
        base_delay = 30  # seconds
        
        while True:
            try:
                # Reset retry count on successful iteration
                retry_count = 0
                
                # Ensure we have a valid connection
                await self._ensure_connected()
                
                # Build search criteria
                criteria = []
                if self.since:
                    try:
                        since_date = datetime.strptime(self.since, "%Y-%m-%d")
                        criteria.append(f'SINCE "{since_date.strftime("%d-%b-%Y")}"')
                    except ValueError as e:
                        logger.warning(f"Invalid since date format: {self.since}. Using default.")
                
                if self.unseen_only:
                    criteria.append('UNSEEN')
                
                search_criteria = ' '.join(criteria) if criteria else 'ALL'
                logger.debug(f"Search criteria: {search_criteria}")
                
                # Search for emails
                try:
                    status, messages = self.imap.search(None, search_criteria)
                    if status != 'OK':
                        raise Exception(f"IMAP search failed: {messages}")
                    
                    message_ids = messages[0].split()
                    if not message_ids:
                        logger.debug("No new messages found")
                        await asyncio.sleep(60)  # No new messages, wait before next poll
                        continue
                    
                    # Process messages (newest first)
                    message_ids = message_ids[-self.limit:]  # Get most recent N messages
                    logger.info(f"Found {len(message_ids)} messages to process")
                    
                    for msg_id in message_ids:
                        msg_id_str = None
                        try:
                            msg_id_str = msg_id.decode('utf-8')
                            logger.debug(f"Processing message ID: {msg_id_str}")
                            
                            # Fetch the email
                            status, msg_data = self.imap.fetch(msg_id, '(RFC822)')
                            if status != 'OK' or not msg_data or not msg_data[0]:
                                logger.error(f"Failed to fetch message {msg_id_str}")
                                continue
                            
                            # Parse the email
                            if isinstance(msg_data[0], tuple) and len(msg_data[0]) > 1:
                                email_data = self._parse_email(msg_data[0][1])
                                email_data['message_id'] = email_data.get('message_id') or msg_id_str
                                
                                # Mark as read if requested
                                if self.mark_read:
                                    try:
                                        self.imap.store(msg_id, '+FLAGS', '\\Seen')
                                        logger.debug(f"Marked message {msg_id_str} as read")
                                    except Exception as e:
                                        logger.warning(f"Failed to mark message {msg_id_str} as read: {e}")
                                
                                # Yield the email data
                                result = {
                                    'type': 'email',
                                    'timestamp': datetime.utcnow().isoformat(),
                                    'data': email_data
                                }
                                
                                yield result
                                
                                # Small delay between processing messages to prevent overwhelming the server
                                await asyncio.sleep(0.5)
                                
                        except Exception as e:
                            logger.error(f"Error processing message {msg_id_str if msg_id_str else 'unknown'}: {e}")
                            continue
                
                    # Wait before next poll
                    await asyncio.sleep(60)
                
                except Exception as e:
                    logger.error(f"Error during email search/fetch: {e}")
                    raise
                
            except (imaplib.IMAP4.error, ConnectionError, TimeoutError, OSError) as e:
                retry_count += 1
                logger.error(f"IMAP connection error (attempt {retry_count}/{max_retries}): {e}")
                self.imap = None  # Force reconnect on next iteration
                
                # Exponential backoff for retries
                if retry_count <= max_retries:
                    delay = min(base_delay * (2 ** (retry_count - 1)), 300)  # Cap at 5 minutes
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached. Waiting before next attempt...")
                    await asyncio.sleep(300)  # 5 minutes before next attempt
                    retry_count = 0  # Reset counter after long wait
                    
            except Exception as e:
                logger.error(f"Unexpected error in IMAP receive loop: {e}", exc_info=True)
                self.imap = None
                await asyncio.sleep(60)  # Wait before retrying on unexpected errors


class FileSource(Source):
    """File watcher source"""

    def __init__(self, path: str):
        self.path = path

    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Watch file for changes"""
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"File not found: {self.path}")

        last_modified = 0
        while True:
            try:
                current_modified = os.path.getmtime(self.path)
                if current_modified > last_modified:
                    with open(self.path, "r") as f:
                        content = f.read()
                    yield {
                        "type": "file_update",
                        "path": self.path,
                        "content": content,
                        "timestamp": datetime.now().isoformat(),
                    }
                    last_modified = current_modified
            except Exception as e:
                logger.error(f"Error reading file {self.path}: {e}")
            
            await asyncio.sleep(1)  # Check every second


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
