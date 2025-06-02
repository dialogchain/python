import smtplib
import ssl
from datetime import datetime
import os
from dotenv import load_dotenv
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
TO_EMAIL = os.getenv('ALERT_EMAIL')

def test_smtp_connection():
    print(f"Testing SMTP connection to {SMTP_SERVER}:{SMTP_PORT}")
    print(f"Username: {SMTP_USER}")
    
    try:
        # Create SSL context
        context = ssl.create_default_context()
        
        print("\nAttempting to connect with SSL...")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            print("✅ Connected to SMTP server with SSL")
            
            print(f"Authenticating as {SMTP_USER}...")
            server.login(SMTP_USER, SMTP_PASS)
            print("✅ Authentication successful")
            
            # Test sending an email
            message = f"Subject: SMTP Test\n\nThis is a test email sent at {datetime.now()}"
            server.sendmail(SMTP_USER, TO_EMAIL, message)
            print(f"✅ Test email sent to {TO_EMAIL}")
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'smtp_code'):
            print(f"SMTP Code: {e.smtp_code}")
        if hasattr(e, 'smtp_error'):
            print(f"SMTP Error: {e.smtp_error}")

if __name__ == "__main__":
    test_smtp_connection()
