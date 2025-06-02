#!/usr/bin/env python3
"""
Printer scanner script for DialogChain.
Provides printer discovery and basic printing capabilities.
"""

import cups
import argparse
import sys
from typing import Dict, Any, Optional
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)

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
            logger.error(f"❌ Printer '{printer_name}' not found")
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
        logger.error(f"❌ Print error: {e}")
        return 1

def main() -> int:
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Printer scanner for DialogChain',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  %(prog)s list
  %(prog)s print
  %(prog)s print --printer "My Printer" --text "Test page"
'''
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True, title='commands')
    
    # List command
    list_parser = subparsers.add_parser(
        'list', 
        help='List available printers',
        description='List all available printers with their details'
    )
    list_parser.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help='Show detailed printer information'
    )
    
    # Print command
    print_parser = subparsers.add_parser(
        'print', 
        help='Print a test page',
        description='Print a test page to the specified or default printer'
    )
    print_parser.add_argument(
        '--printer', '-p', 
        help='Printer name (default: default printer)'
    )
    print_parser.add_argument(
        '--text', '-t', 
        default='Hello from DialogChain!\nThis is a test print.',
        help='Text to print (default: a test message)'
    )
    print_parser.add_argument(
        '--file', '-f',
        help='File to print (overrides --text if specified)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'list':
            printers = list_printers()
            if not printers:
                print("❌ No printers found on the system")
                print("\nMake sure CUPS is installed and running:")
                print("  On Ubuntu/Debian: sudo apt install cups")
                print("  On RHEL/CentOS: sudo yum install cups")
                print("  Start service: sudo systemctl start cups")
                return 1
                
            print(f"\n🖨️  Found {len(printers)} printer(s):")
            print("=" * 60)
            
            for i, (name, attrs) in enumerate(printers.items(), 1):
                print(f"{i}. {name}")
                print(f"   URI: {attrs.get('device-uri', 'N/A')}")
                
                if args.verbose:
                    print("   Details:")
                    for key, value in attrs.items():
                        if key != 'device-uri':
                            print(f"     {key}: {value}")
                
                if i < len(printers):
                    print("-" * 60)
            
            print("=" * 60)
            return 0
            
        elif args.command == 'print':
            if args.file:
                try:
                    with open(args.file, 'r') as f:
                        content = f.read()
                    print(f"📄 Printing file: {args.file}")
                except Exception as e:
                    logger.error(f"❌ Error reading file: {e}")
                    return 1
            else:
                content = args.text
                print("📝 Printing text content...")
            
            return print_text(content, args.printer)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
