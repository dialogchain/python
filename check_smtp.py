#!/usr/bin/env python3
"""
Simple script to test SMTP connection using environment variables.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

def check_smtp():
    # Load environment variables from .env file
    load_dotenv()
    
    # Required environment variables
    required_vars = [
        'SMTP_SERVER',
        'SMTP_PORT',
        'SMTP_USER',
        'SMTP_PASS',
        'ALERT_EMAIL'
    ]
    
    # Check if all required variables are set
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease add them to your .env file:")
        for var in missing_vars:
            print(f"{var}=your_value_here")
        return False
    
    # Get SMTP settings
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    to_email = os.getenv('ALERT_EMAIL')
    
    print(f"🔧 Testing SMTP connection to {smtp_server}:{smtp_port}")
    print(f"🔑 Using username: {smtp_user}")
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = 'SMTP Test from DialogChain'
        
        body = """
        This is a test email to verify SMTP configuration.
        
        If you're reading this, the SMTP configuration is working correctly!
        """
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            print(f"🔒 Attempting to authenticate with {smtp_user}:{'*' * len(smtp_pass)}")
            server.login(smtp_user, smtp_pass)
            print("✅ Successfully authenticated with SMTP server")
            
            print(f"📤 Sending test email to {to_email}...")
            server.send_message(msg)
            print("✅ Test email sent successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    check_smtp()
