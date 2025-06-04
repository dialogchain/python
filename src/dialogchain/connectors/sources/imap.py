"""IMAP email source implementation for DialogChain."""

import asyncio
import email
import imaplib
import logging
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Dict, Any, AsyncIterator, List, Optional, Tuple

from ..base import Source

logger = logging.getLogger(__name__)

class IMAPSource(Source):
    """IMAP email source for fetching emails from an IMAP server."""
    
    def __init__(
        self, 
        uri: str, 
        mailbox: str = 'INBOX', 
        mark_read: bool = False,
        batch_size: int = 10,
        poll_interval: int = 60
    ):
        """Initialize IMAP source.
        
        Args:
            uri: IMAP connection URI (e.g., 'imap://user:pass@imap.example.com:993')
            mailbox: Mailbox to monitor (default: 'INBOX')
            mark_read: Whether to mark messages as read when fetched
            batch_size: Number of messages to fetch in each batch
            poll_interval: Seconds between mailbox checks
        """
        super().__init__(uri)
        self.mailbox = mailbox
        self.mark_read = mark_read
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self._imap = None
        self._last_uid = '1'
        self._stop_event = asyncio.Event()
    
    async def _connect(self):
        """Connect to IMAP server and select mailbox."""
        if self._imap is not None:
            return
        
        parsed = self.parsed_uri
        use_ssl = parsed.scheme.lower() == 'imaps' or parsed.port == 993
        
        try:
            if use_ssl:
                self._imap = imaplib.IMAP4_SSL(parsed.hostname or 'localhost', parsed.port or 993)
            else:
                self._imap = imaplib.IMAP4(parsed.hostname or 'localhost', parsed.port or 143)
            
            # Login
            username = parsed.username or ''
            password = parsed.password or ''
            self._imap.login(username, password)
            
            # Select mailbox
            self._imap.select(self.mailbox)
            logger.info(f"Connected to IMAP server and selected mailbox: {self.mailbox}")
            
        except Exception as e:
            self._imap = None
            logger.error(f"IMAP connection failed: {e}")
            raise ConnectionError(f"IMAP connection failed: {e}") from e
    
    async def _disconnect(self):
        """Close IMAP connection."""
        if self._imap is not None:
            try:
                self._imap.close()
                self._imap.logout()
            except Exception as e:
                logger.warning(f"Error closing IMAP connection: {e}")
            finally:
                self._imap = None
    
    async def _fetch_emails(self) -> List[Dict[str, Any]]:
        """Fetch new emails from the server."""
        if not self.is_connected:
            await self.connect()
        
        try:
            # Search for unseen messages with UID > last_uid
            status, data = self._imap.uid('SEARCH', None, f'UID {self._last_uid}:*')
            if status != 'OK':
                logger.error(f"IMAP search failed: {data}")
                return []
            
            email_uids = data[0].split()
            if not email_uids:
                return []
            
            emails = []
            for uid in email_uids[-self.batch_size:]:  # Limit batch size
                try:
                    # Fetch the email by UID
                    status, msg_data = self._imap.uid('FETCH', uid, '(RFC822)')
                    if status != 'OK':
                        logger.warning(f"Failed to fetch email {uid}")
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    # Extract email data
                    email_data = self._parse_email(email_message)
                    email_data['uid'] = uid
                    emails.append(email_data)
                    
                    # Mark as read if configured
                    if self.mark_read:
                        self._imap.uid('STORE', uid, '+FLAGS', '\\Seen')
                    
                    # Update last UID
                    if uid > self._last_uid:
                        self._last_uid = uid
                        
                except Exception as e:
                    logger.error(f"Error processing email {uid}: {e}")
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            await self.disconnect()
            return []
    
    def _parse_email(self, msg: email.message.Message) -> Dict[str, Any]:
        """Parse email message into a dictionary."""
        subject, encoding = decode_header(msg['Subject'])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or 'utf-8', errors='replace')
        
        from_ = msg['From']
        to = msg['To']
        date = parsedate_to_datetime(msg['Date']) if msg['Date'] else None
        
        # Get email body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except Exception:
                        pass
        else:
            body = msg.get_payload(decode=True).decode(errors='replace')
        
        # Get attachments
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if not filename:
                    continue
                    
                attachments.append({
                    'filename': filename,
                    'content_type': part.get_content_type(),
                    'size': len(part.get_payload(decode=True)),
                })
        
        return {
            'subject': subject,
            'from': from_,
            'to': to,
            'date': date.isoformat() if date else None,
            'body': body,
            'attachments': attachments,
            'headers': dict(msg.items())
        }
    
    async def receive(self) -> AsyncIterator[Dict[str, Any]]:
        """Continuously poll for new emails.
        
        Yields:
            Dictionary containing email data
        """
        while not self._stop_event.is_set():
            try:
                if not self.is_connected:
                    await self.connect()
                
                emails = await self._fetch_emails()
                for email_data in emails:
                    yield {
                        'type': 'email',
                        'data': email_data,
                        'source': self.uri,
                        'timestamp': asyncio.get_event_loop().time()
                    }
                
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in IMAP receive loop: {e}")
                await asyncio.sleep(min(60, self.poll_interval * 2))  # Backoff on error
    
    async def stop(self):
        """Stop the email polling."""
        self._stop_event.set()
        await self.disconnect()
    
    def __str__(self):
        """String representation of the source."""
        return f"IMAP Source: {self.uri} ({self.mailbox})"
