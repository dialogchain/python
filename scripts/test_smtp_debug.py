#!/usr/bin/env python3
"""
SMTP Debug Script

This script helps debug SMTP connection issues by providing detailed logging.
"""
import os
import smtplib
import ssl
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def debug_smtp():
    # SMTP server configuration
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    to_email = os.getenv('ALERT_EMAIL', smtp_user)
    
    print(f"SMTP Server: {smtp_server}")
    print(f"SMTP Port: {smtp_port}")
    print(f"Username: {smtp_user}")
    print(f"To: {to_email}")
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = 'SMTP Debug Test'
    msg.attach(MIMEText('This is a test email from the debug script.', 'plain'))
    
    try:
        # Try STARTTLS first (port 587)
        print("\n=== Testing STARTTLS ===")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.set_debuglevel(2)  # Enable debug output
        
        print("Sending EHLO...")
        server.ehlo()
        
        print("Starting TLS...")
        server.starttls()
        
        print("Sending EHLO again...")
        server.ehlo()
        
        print("Logging in...")
        server.login(smtp_user, smtp_pass)
        
        print("Sending email...")
        server.send_message(msg)
        print("✅ Email sent successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Try SSL (port 465)
        if smtp_port != 465:
            try:
                print("\n=== Trying SSL (port 465) ===")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, 465, context=context, timeout=10) as server:
                    server.set_debuglevel(2)
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                    print("✅ Email sent successfully using SSL!")
            except Exception as ssl_error:
                print(f"\n❌ SSL Error: {ssl_error}")
                print(f"SSL Error type: {type(ssl_error).__name__}")
    
    finally:
        try:
            server.quit()
        except:
            pass

if __name__ == "__main__":
    debug_smtp()
