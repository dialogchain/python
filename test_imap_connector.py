#!/usr/bin/env python3
"""
Test script for IMAP connector

Usage:
    python test_imap_connector.py imap://username:password@server:port/folder

Example:
    python test_imap_connector.py 'imap://user:pass@imap.example.com:993/INBOX?limit=5&unseen=true&mark_read=false'
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from dialogchain.connectors import IMAPSource

async def process_email(email_data: Dict[str, Any]) -> None:
    """Process a single email"""
    print("\n" + "="*80)
    print(f"From: {email_data['data'].get('from')}")
    print(f"Subject: {email_data['data'].get('subject')}")
    print(f"Date: {email_data['data'].get('date')}")
    print(f"Message ID: {email_data['data'].get('message_id')}")
    
    # Print first 200 chars of content
    content = email_data['data'].get('content', '')
    if content:
        print("\nContent preview:")
        print(content[:200] + ("..." if len(content) > 200 else ""))
    
    # Print attachments if any
    attachments = email_data['data'].get('attachments', [])
    if attachments:
        print("\nAttachments:")
        for idx, attachment in enumerate(attachments, 1):
            print(f"  {idx}. {attachment['filename']} ({attachment['content_type']}, {attachment['size']} bytes)")

async def main(imap_uri: str) -> None:
    """Main function to test IMAP connector"""
    print(f"Testing IMAP connector with URI: {imap_uri}")
    
    # Replace placeholders with environment variables if needed
    if '{' in imap_uri and '}' in imap_uri:
        from string import Template
        env_vars = {k: v for k, v in os.environ.items()}
        imap_uri = Template(imap_uri).safe_substitute(env_vars)
    
    source = IMAPSource(imap_uri)
    
    try:
        print("Starting to fetch emails... (press Ctrl+C to stop)")
        async for email_data in source.receive():
            await process_email(email_data)
            # Exit after first batch for testing
            print("\nSuccessfully fetched emails. Exiting...")
            break
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_imap_connector.py imap://user:pass@server:port/folder")
        print("Or with .env: python test_imap_connector.py 'imap://${EMAIL_USER}:${EMAIL_PASSWORD}@${EMAIL_SERVER}:${EMAIL_PORT}/INBOX'")
        sys.exit(1)
    
    # Load environment variables from .env if it exists
    load_dotenv()
    
    asyncio.run(main(sys.argv[1]))
