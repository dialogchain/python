#!/usr/bin/env python3
"""
Printer scanner script for DialogChain.
Provides printer discovery and basic printing capabilities.
"""

import cups
import argparse
import sys
from typing import Dict, Any, Optional

def list_printers() -> Dict[str, Dict[str, Any]]:
    """List all available printers."""
    try:
        conn = cups.Connection()
        return conn.getPrinters()
    except RuntimeError as e:
        print(f"Error connecting to CUPS: {e}")
        print("Make sure CUPS is installed and running.")
        print("On Ubuntu/Debian: sudo apt install cups")
        print("On RHEL/CentOS: sudo yum install cups")
        return {}

def print_text(text: str, printer_name: Optional[str] = None) -> int:
    """Print text to the specified or default printer."""
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
        
        if not printers:
            print("❌ No printers available")
            return 1
            
        if printer_name and printer_name not in printers:
            print(f"❌ Printer '{printer_name}' not found")
            print("\nAvailable printers:")
            for name, attrs in printers.items():
                print(f"- {name} ({attrs.get('device-uri', 'no URI')})")
            return 1
            
        printer = printer_name or list(printers.keys())[0]
        job_id = conn.printFile(
            printer, 
            '/dev/stdin', 
            "DialogChain Print", 
            {"raw": "True"},
            text
        )
        
        print(f"✅ Sent print job {job_id} to {printer}")
        return 0
        
    except cups.IPPError as e:
        print(f"❌ Print error: {e}")
        return 1

def main() -> int:
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Printer scanner for DialogChain')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available printers')
    
    # Print command
    print_parser = subparsers.add_parser('print', help='Print a test page')
    print_parser.add_argument('--printer', '-p', help='Printer name (default: default printer)')
    print_parser.add_argument('--text', '-t', default='Hello from DialogChain!',
                            help='Text to print')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        printers = list_printers()
        if not printers:
            print("No printers found")
            return 1
            
        print("\nAvailable Printers:")
        print("-" * 60)
        for name, attrs in printers.items():
            print(f"Name: {name}")
            print(f"  URI: {attrs.get('device-uri', 'N/A')}")
            print(f"  Info: {attrs.get('printer-info', 'N/A')}")
            print(f"  State: {attrs.get('printer-state-message', 'N/A')}")
            print("-" * 60)
        return 0
        
    elif args.command == 'print':
        return print_text(args.text, args.printer)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
