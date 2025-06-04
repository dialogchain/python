#!/usr/bin/env python3
"""
Test script for the updated IMAP connector with better error handling and logging.
"""
import asyncio
import logging
import sys
import os
from dotenv import load_dotenv
from typing import Dict, Any, AsyncIterator

# Add parent directory to path to import dialogchain
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dialogchain.connectors import IMAPSource

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('imap_connector_test.log')
    ]
)
logger = logging.getLogger(__name__)

async def process_emails(uri: str, max_emails: int = 5) -> None:
    """Process emails using the IMAP source connector.
    
    Args:
        uri: IMAP connection URI in the format:
            imap://username:password@server:port/folder?param=value
        max_emails: Maximum number of emails to process before stopping
    """
    logger.info(f"Starting email processing with URI: {uri}")
    
    try:
        source = IMAPSource(uri)
        count = 0
        
        async for email_data in source.receive():
            try:
                count += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"Processing email #{count}")
                
                # Extract and log email details
                data = email_data.get('data', {})
                logger.info(f"Subject: {data.get('subject')}")
                logger.info(f"From: {data.get('from')}")
                logger.info(f"To: {data.get('to')}")
                logger.info(f"Date: {data.get('date')}")
                logger.info(f"Message ID: {data.get('message_id')}")
                
                # Log headers if available
                if 'headers' in data and data['headers']:
                    logger.info("Headers:")
                    for key, value in data['headers'].items():
                        logger.info(f"  {key}: {value}")
                
                # Log content preview
                content = data.get('content', '')
                preview = (content[:200] + '...') if len(content) > 200 else content
                logger.info(f"Content Preview: {preview}")
                
                # Log attachments if any
                if 'attachments' in data and data['attachments']:
                    logger.info(f"Attachments ({len(data['attachments'])}):")
                    for i, attachment in enumerate(data['attachments'], 1):
                        logger.info(f"  {i}. {attachment.get('filename', 'unnamed')} "
                                  f"({len(attachment.get('data', ''))} bytes, "
                                  f"{attachment.get('content_type', 'unknown')})")
                
                logger.info(f"Processed email #{count} successfully")
                
                # Stop after processing max_emails
                if count >= max_emails:
                    logger.info(f"Reached maximum of {max_emails} emails. Stopping...")
                    break
                    
            except Exception as e:
                logger.error(f"Error processing email: {e}", exc_info=True)
                continue
                
    except Exception as e:
        logger.error(f"Fatal error in email processing: {e}", exc_info=True)
    finally:
        logger.info("Email processing completed")

def main():
    # Load environment variables
    load_dotenv()
    
    # Get IMAP settings from environment
    imap_server = os.getenv('EMAIL_SERVER')
    imap_port = os.getenv('EMAIL_PORT', '993')
    imap_user = os.getenv('EMAIL_USER')
    imap_password = os.getenv('EMAIL_PASSWORD')
    
    if not all([imap_server, imap_user, imap_password]):
        logger.error("Missing required environment variables. Please check your .env file.")
        sys.exit(1)
    
    # Build the IMAP URI with query parameters
    imap_uri = (
        f"imap://{imap_user}:{imap_password}@{imap_server}:{imap_port}/INBOX"
        "?unseen=true&limit=5&mark_read=false"
    )
    
    # Run the email processing
    try:
        asyncio.run(process_emails(imap_uri, max_emails=3))
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
