#!/usr/bin/env python3
"""
Environment Load Test

This script tests loading environment variables from .env file.
"""
import os
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path)
    
    print("=== Environment Variables ===")
    for var in ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 'ALERT_EMAIL']:
        value = os.getenv(var, 'NOT SET')
        # Mask the value for security
        masked = value[:3] + '*' * (len(value) - 3) if value and value != 'NOT SET' else 'NOT SET'
        print(f"{var}: {masked}")
    
    # Check if all required variables are set
    required_vars = ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 'ALERT_EMAIL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("\n❌ Missing required environment variables:", ", ".join(missing_vars))
        print("Please check your .env file.")
    else:
        print("\n✅ All required environment variables are set!")
        print("You can now run the SMTP test script with:")
        print("python scripts/test_smtp_debug.py")

if __name__ == "__main__":
    main()
