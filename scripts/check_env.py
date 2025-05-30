#!/usr/bin/env python3
"""
Environment Check Script

This script checks if environment variables are loaded correctly.
"""
import os

def main():
    print("=== Environment Variables ===")
    for var in ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 'ALERT_EMAIL']:
        value = os.getenv(var, 'NOT SET')
        masked = value[:3] + '*' * (len(value) - 3) if value and value != 'NOT SET' else 'NOT SET'
        print(f"{var}: {masked}")

if __name__ == "__main__":
    main()
