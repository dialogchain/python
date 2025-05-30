#!/usr/bin/env python3
"""
Script to process markdown files and extract code blocks into separate files.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)



def extract_code_blocks(content: str) -> List[Tuple[str, str, Optional[str]]]:
    """Extract code blocks from markdown content.

    Returns:
        List of tuples (filename, code, language)
    """
    pattern = r"```(?:python)?\n(.*?)\n```"
    blocks = re.findall(pattern, content, re.DOTALL)

    # Also try to capture language and filename from markdown headers
    pattern_with_lang = r"```(\w+)\s+(?:file=([^\s]+))?\n(.*?)\n```"
    blocks_with_lang = re.findall(pattern_with_lang, content, re.DOTALL)

    result = []

    # Process blocks with language and optional filename
    for lang, filename, code in blocks_with_lang:
        result.append(
            (filename if filename else f"unnamed_{len(result)}.py", code, lang)
        )

    # Process simple code blocks
    for i, code in enumerate(blocks):
        if not any(code in b[1] for b in result):  # Avoid duplicates
            result.append((f"unnamed_{len(result)}.py", code, None))

    return result


def process_markdown_file(md_path: Path, output_dir: Path) -> None:
    """Process a single markdown file and extract code blocks."""
    print(f"Processing {md_path}...")

    content = md_path.read_text(encoding="utf-8")
    code_blocks = extract_code_blocks(content)

    if not code_blocks:
        print(f"  No code blocks found in {md_path}")
        return

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each code block
    for filename, code, lang in code_blocks:
        # Clean up filename
        filename = filename.strip()
        if not filename.endswith(".py"):
            filename += ".py"

        # Create directory structure if needed
        file_path = output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        file_path.write_text(code, encoding="utf-8")
        print(f"  Created/Updated: {file_path}")


def main():
    # Define paths
    base_dir = Path(__file__).parent
    todo_dir = base_dir / "todo"
    output_base = base_dir / "generated"

    # Process all markdown files in the todo directory
    for md_file in todo_dir.glob("*.md"):
        # Create a subdirectory for each markdown file
        output_dir = output_base / md_file.stem
        process_markdown_file(md_file, output_dir)


if __name__ == "__main__":
    main()
