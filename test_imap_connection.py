#!/usr/bin/env python3
"""
Simple IMAP connection test script
"""
import imaplib
import ssl
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get IMAP settings from environment
IMAP_SERVER = os.getenv('EMAIL_SERVER')
IMAP_PORT = int(os.getenv('EMAIL_PORT', '993'))
IMAP_USER = os.getenv('EMAIL_USER')
IMAP_PASSWORD = os.getenv('EMAIL_PASSWORD')

def test_imap_connection():
    print(f"Testing connection to {IMAP_SERVER}:{IMAP_PORT}...")
    
    try:
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect to the IMAP server with SSL
        print(f"Connecting to {IMAP_SERVER}:{IMAP_PORT}...")
        with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=context) as mail:
            print("✓ Connected to IMAP server")
            
            # Login
            print(f"Logging in as {IMAP_USER}...")
            mail.login(IMAP_USER, IMAP_PASSWORD)
            print("✓ Login successful")
            
            # List available mailboxes
            print("\nAvailable mailboxes:")
            status, mailboxes = mail.list()
            if status == 'OK':
                for mailbox in mailboxes:
                    print(f"- {mailbox.decode()}")
            
            # Select INBOX
            print("\nSelecting INBOX...")
            status, count = mail.select('INBOX')
            if status == 'OK':
                print(f"✓ INBOX selected ({count[0].decode()} messages)")
            
            mail.logout()
            print("\n✓ Logged out successfully")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_imap_connection()
