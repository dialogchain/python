import imaplib
import ssl
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get IMAP settings from environment variables
IMAP_SERVER = os.getenv('EMAIL_SERVER')
IMAP_PORT = int(os.getenv('EMAIL_PORT', '993'))
IMAP_USER = os.getenv('EMAIL_USER')
IMAP_PASSWORD = os.getenv('EMAIL_PASSWORD')

print(f"Attempting to connect to {IMAP_SERVER}:{IMAP_PORT} as {IMAP_USER}...")

try:
    # Create SSL context
    context = ssl.create_default_context()
    
    # Connect to the IMAP server with SSL
    with imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=context) as mail:
        print("✓ Connected to IMAP server")
        
        # Login
        mail.login(IMAP_USER, IMAP_PASSWORD)
        print("✓ Login successful")
        
        # List available mailboxes
        print("\nAvailable mailboxes:")
        status, mailboxes = mail.list()
        if status == 'OK':
            for mailbox in mailboxes:
                print(f"- {mailbox.decode()}")
        
        # Select INBOX
        mail.select('INBOX')
        print("\n✓ INBOX selected")
        
        # Search for recent emails
        status, messages = mail.search(None, 'ALL')
        if status == 'OK':
            message_ids = messages[0].split()
            print(f"\nFound {len(message_ids)} messages in INBOX")
            if message_ids:
                print(f"Most recent message ID: {message_ids[-1].decode()}")
        
        mail.logout()
        print("\n✓ Logged out successfully")

except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    if "AUTHENTICATE failed" in str(e):
        print("\nAuthentication failed. Please check your email and password.")
    elif "Connection refused" in str(e):
        print("\nConnection refused. Check if the server and port are correct, and if the server is running.")
    elif "certificate verify failed" in str(e).lower():
        print("\nSSL certificate verification failed. This might be due to a self-signed certificate.")
    print(f"\nDebug info:")
    print(f"Server: {IMAP_SERVER}")
    print(f"Port: {IMAP_PORT}")
    print(f"Username: {IMAP_USER}")
    print(f"Password: {'*' * (len(IMAP_PASSWORD) if IMAP_PASSWORD else 0)}")
