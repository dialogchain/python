#!/usr/bin/env python3
"""
SMTP Test Script

This script tests SMTP connection and sends a test email.
"""
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)

def test_smtp_connection(server, port, username, password, recipient):
    """Test SMTP connection and send a test email."""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = recipient
        msg['Subject'] = f"SMTP Test {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Email body
        body = "This is a test email sent from the SMTP test script."
        msg.attach(MIMEText(body, 'plain'))
        
        # Try STARTTLS first (port 587)
        try:
            print(f"\nTrying STARTTLS on {server}:{port}...")
            with smtplib.SMTP(server, port, timeout=10) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
                print("✅ Email sent successfully using STARTTLS")
                return True
        except Exception as e:
            logger.error(f"❌ STARTTLS failed: {e}")
            
        # Try SSL (port 465)
        try:
            print(f"\nTrying SSL on {server}:465...")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, 465, context=context, timeout=10) as server:
                server.login(username, password)
                server.send_message(msg)
                print("✅ Email sent successfully using SSL")
                return True
        except Exception as e:
            logger.error(f"❌ SSL failed: {e}")
            
        return False
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Get credentials from environment variables
    server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    port = int(os.getenv('SMTP_PORT', '587'))
    username = os.getenv('SMTP_USER', '')
    password = os.getenv('SMTP_PASS', '')
    recipient = os.getenv('ALERT_EMAIL', username)
    
    if not all([server, username, password, recipient]):
        print("❌ Error: Missing required environment variables")
        print("Please set SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, and ALERT_EMAIL")
        exit(1)
    
    print(f"Testing SMTP connection to {server}:{port}")
    print(f"Username: {username}")
    print(f"Recipient: {recipient}")
    
    if test_smtp_connection(server, port, username, password, recipient):
        print("\n✅ SMTP test completed successfully")
    else:
        print("\n❌ SMTP test failed")
