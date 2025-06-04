"""
Migration script to update imports from scanner.py to the new scanner package.

This script helps migrate code that imports from the old scanner.py to the new
modular scanner package structure.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Map old imports to new imports
IMPORT_MAP = {
    'from dialogchain.scanner import': 'from dialogchain.scanner import',  # No change needed
    'from dialogchain.scanner import ScannerError': 'from dialogchain.scanner import ScannerError',
    'from dialogchain.scanner import BaseScanner': 'from dialogchain.scanner import BaseScanner',
    'from dialogchain.scanner import FileScanner': 'from dialogchain.scanner import FileScanner',
    'from dialogchain.scanner import HttpScanner': 'from dialogchain.scanner import HttpScanner',
    'from dialogchain.scanner import NetworkScanner': 'from dialogchain.scanner import NetworkScanner',
    'from dialogchain.scanner import NetworkService': 'from dialogchain.scanner.network_scanner import NetworkService',
    'from dialogchain.scanner import create_scanner': 'from dialogchain.scanner import create_scanner',
    'from dialogchain.scanner import ConfigScanner': 'from dialogchain.scanner import ConfigScanner',
}


def find_python_files(directory: str) -> List[str]:
    """Find all Python files in the given directory."""
    py_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                py_files.append(os.path.join(root, file))
    return py_files


def update_imports(file_path: str) -> Tuple[bool, List[str]]:
    """Update imports in the given file.
    
    Returns:
        Tuple of (modified, changes) where modified is a boolean indicating if the file
        was modified, and changes is a list of strings describing the changes made.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_lines = content.splitlines()
    modified = False
    changes = []
    
    # Check if the file imports from the old scanner module
    if 'from dialogchain.scanner ' in content or 'import dialogchain.scanner' in content:
        new_lines = []
        for line in original_lines:
            new_line = line
            for old_import, new_import in IMPORT_MAP.items():
                if line.strip().startswith(old_import.split()[0]) and old_import in line:
                    new_line = line.replace(old_import, new_import)
                    if new_line != line:
                        modified = True
                        changes.append(f"Updated import: {line.strip()} -> {new_line.strip()}")
                        break
            new_lines.append(new_line)
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines) + '\n')
    
    return modified, changes


def main():
    """Main migration function."""
    # Get the project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    
    # Find all Python files in the project
    python_files = find_python_files(project_root)
    
    # Process each file
    total_modified = 0
    for file_path in python_files:
        # Skip files in the scanner package itself
        if os.path.abspath(file_path).startswith(os.path.abspath(os.path.dirname(__file__))):
            continue
            
        try:
            modified, changes = update_imports(file_path)
            if modified:
                total_modified += 1
                print(f"\nUpdated {os.path.relpath(file_path, project_root)}:")
                for change in changes:
                    print(f"  - {change}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    print(f"\nMigration complete. Updated {total_modified} files.")
    print("\nNext steps:")
    print("1. Review the changes made by this script")
    print("2. Remove the old scanner.py file if it's no longer needed")
    print("3. Update any documentation that references the old module structure")
    print("4. Run tests to ensure everything still works as expected")


if __name__ == "__main__":
    main()
