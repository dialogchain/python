import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

def test_smtp_connection():
    """Test SMTP server connection and authentication"""
    print("\n🔍 Testing SMTP connection...")
    
    # Load environment variables
    load_dotenv()
    
    # Get SMTP settings from environment
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    alert_email = os.getenv("ALERT_EMAIL")
    
    if not all([smtp_server, smtp_user, smtp_pass, alert_email]):
        print("❌ Missing required SMTP environment variables. Please set these in your .env file:")
        print("SMTP_SERVER=smtp.example.com")
        print("SMTP_PORT=587")
        print("SMTP_USER=your_username")
        print("SMTP_PASS=your_password")
        print("ALERT_EMAIL=your@email.com")
        return False
    
    try:
        # Create a secure SSL context
        context = ssl.create_default_context()
        
        # Try to log in to server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print(f"✅ Connected to SMTP server: {smtp_server}:{smtp_port}")
            
            # Start TLS encryption
            server.starttls(context=context)
            print("✅ Started TLS encryption")
            
            # Login
            server.login(smtp_user, smtp_pass)
            print("✅ Successfully authenticated with SMTP server")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = alert_email
            msg['Subject'] = 'DialogChain SMTP Test'
            msg.attach(MIMEText('This is a test email from DialogChain SMTP test.', 'plain'))
            
            # Send email
            server.send_message(msg)
            print(f"✅ Sent test email to: {alert_email}")
            
            return True
            
    except Exception as e:
        print(f"❌ SMTP test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting SMTP connection test...")
    success = test_smtp_connection()
    
    if success:
        print("\n✅ SMTP test completed successfully!")
    else:
        print("\n❌ SMTP test failed. Check the error messages above.")
