"""Email destination implementation for DialogChain."""

import asyncio
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate
from typing import Any, Dict, List, Optional, Union, BinaryIO
from pathlib import Path

from ....exceptions import DestinationError
from ..base import Destination

logger = logging.getLogger(__name__)

class EmailDestination(Destination):
    """Email destination for sending messages via SMTP."""
    
    def __init__(
        self,
        uri: str,
        from_addr: Optional[str] = None,
        to_addrs: Optional[Union[str, List[str]]] = None,
        subject: str = "DialogChain Notification",
        smtp_server: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_pass: Optional[str] = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout: int = 30,
    ):
        """Initialize email destination.
        
        Args:
            uri: SMTP URI (e.g., 'smtp://user:pass@smtp.example.com:587')
            from_addr: Sender email address (overrides URI)
            to_addrs: Recipient email address(es) (overrides URI)
            subject: Default email subject
            smtp_server: SMTP server hostname (overrides URI)
            smtp_port: SMTP server port (overrides URI)
            smtp_user: SMTP username (overrides URI)
            smtp_pass: SMTP password (overrides URI)
            use_tls: Use STARTTLS for encryption
            use_ssl: Use SSL/TLS from the start
            timeout: Connection timeout in seconds
        """
        super().__init__(uri)
        
        # Parse URI if provided
        parsed = self.parsed_uri
        
        self.smtp_server = smtp_server or parsed.hostname or 'localhost'
        self.smtp_port = smtp_port or (parsed.port if parsed.port else (465 if use_ssl else 587))
        
        # Get credentials from URI if not provided
        self.smtp_user = smtp_user or (parsed.username or '')
        self.smtp_pass = smtp_pass or (parsed.password or '')
        
        # If username/password in URI but not in parameters, use them
        if not smtp_user and parsed.username:
            self.smtp_user = parsed.username
        if not smtp_pass and parsed.password:
            self.smtp_pass = parsed.password
            
        # Get from/to from URI query parameters if not provided
        query = parse_qs(parsed.query)
        self.from_addr = from_addr or (query.get('from', [None])[0])
        
        if to_addrs is None:
            self.to_addrs = query.get('to', [])
            if not self.to_addrs and parsed.path.strip('/'):
                self.to_addrs = [parsed.path.strip('/')]
        else:
            self.to_addrs = [to_addrs] if isinstance(to_addrs, str) else to_addrs
            
        self.subject = subject
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self._lock = asyncio.Lock()
    
    async def _connect(self):
        """Establish SMTP connection."""
        if hasattr(self, '_smtp') and self._smtp:
            try:
                self._smtp.noop()
                return
            except (smtplib.SMTPException, OSError):
                # Connection is dead, will recreate
                pass
        
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                self._smtp = smtplib.SMTP_SSL(
                    self.smtp_server, 
                    self.smtp_port,
                    timeout=self.timeout,
                    context=context
                )
            else:
                self._smtp = smtplib.SMTP(
                    self.smtp_server,
                    self.smtp_port,
                    timeout=self.timeout
                )
                
                if self.use_tls:
                    self._smtp.starttls()
                
            if self.smtp_user and self.smtp_pass:
                self._smtp.login(self.smtp_user, self.smtp_pass)
                
            logger.info(f"Connected to SMTP server: {self.smtp_server}:{self.smtp_port}")
            
        except Exception as e:
            self._smtp = None
            raise DestinationError(f"Failed to connect to SMTP server: {e}") from e
    
    async def _disconnect(self):
        """Close SMTP connection."""
        if hasattr(self, '_smtp') and self._smtp:
            try:
                self._smtp.quit()
            except Exception as e:
                logger.warning(f"Error disconnecting from SMTP server: {e}")
            finally:
                self._smtp = None
    
    async def send(
        self,
        data: Any,
        subject: Optional[str] = None,
        from_addr: Optional[str] = None,
        to_addrs: Optional[Union[str, List[str]]] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[Union[str, bytes, BinaryIO]]] = None,
        content_type: str = 'plain',
    ) -> None:
        """Send an email.
        
        Args:
            data: Email body content (text or HTML)
            subject: Email subject
            from_addr: Sender email address
            to_addrs: Recipient email address(es)
            cc: CC recipient(s)
            bcc: BCC recipient(s)
            attachments: List of file paths or file-like objects to attach
            content_type: 'plain' or 'html'
            
        Raises:
            DestinationError: If sending fails
        """
        if not self.is_connected:
            await self.connect()
            
        # Use instance defaults if not provided
        from_addr = from_addr or self.from_addr
        if not from_addr:
            raise DestinationError("No 'from' address specified")
            
        to_addrs = to_addrs or self.to_addrs
        if not to_addrs:
            raise DestinationError("No 'to' address(es) specified")
            
        # Convert to lists if needed
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        if cc and isinstance(cc, str):
            cc = [cc]
        if bcc and isinstance(bcc, str):
            bcc = [bcc]
            
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            msg['Bcc'] = ', '.join(bcc)
            
        msg['Subject'] = subject or self.subject
        msg['Date'] = formatdate(localtime=True)
        
        # Add body
        body = str(data)
        msg.attach(MIMEText(body, content_type, 'utf-8'))
        
        # Add attachments if any
        if attachments:
            for attachment in attachments:
                if isinstance(attachment, str):
                    # File path
                    with open(attachment, 'rb') as f:
                        part = MIMEApplication(
                            f.read(),
                            Name=Path(attachment).name
                        )
                elif hasattr(attachment, 'read') and hasattr(attachment, 'name'):
                    # File-like object with name
                    part = MIMEApplication(
                        attachment.read(),
                        Name=Path(attachment.name).name
                    )
                else:
                    # Raw bytes
                    part = MIMEApplication(attachment)
                    
                part['Content-Disposition'] = f'attachment; filename="{part["Name"]}"'
                msg.attach(part)
        
        # Send the email with retry logic
        max_retries = 3
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                async with self._lock:  # Ensure thread safety
                    if not self.is_connected:
                        await self.connect()
                        
                    recipients = to_addrs.copy()
                    if cc:
                        recipients.extend(cc)
                    if bcc:
                        recipients.extend(bcc)
                        
                    self._smtp.sendmail(
                        from_addr,
                        recipients,
                        msg.as_string()
                    )
                    
                logger.debug(f"Email sent to {', '.join(to_addrs)}")
                return
                
            except (smtplib.SMTPException, OSError) as e:
                last_error = str(e)
                logger.warning(f"Failed to send email (attempt {attempt}/{max_retries}): {last_error}")
                
                # Reconnect on error
                await self.disconnect()
                
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # If we get here, all retries failed
        raise DestinationError(f"Failed to send email after {max_retries} attempts. Last error: {last_error}")
    
    def __str__(self):
        """String representation of the destination."""
        return f"Email Destination: {self.smtp_server}:{self.smtp_port} (User: {self.smtp_user})"
