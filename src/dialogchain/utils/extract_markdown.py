#!/usr/bin/env python3
"""
Extract code blocks from markdown files and save them to the correct locations.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)



class MarkdownExtractor:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.todo_dir = self.base_dir / "todo"
        self.output_dir = self.base_dir

    def extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract code blocks with their file paths."""
        # Pattern to match headers and subsequent code blocks
        pattern = r"##\s+(.*?)\n```(?:\w*)\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        blocks = []
        for header, code in matches:
            # Clean up the header to get the file path
            filepath = header.strip()
            if not filepath or not any(
                filepath.endswith(ext)
                for ext in [
                    ".py",
                    ".js",
                    ".go",
                    ".rs",
                    ".cpp",
                    ".h",
                    ".yaml",
                    ".yml",
                    ".json",
                ]
            ):
                continue

            blocks.append(
                {
                    "filepath": filepath,
                    "code": code.strip(),
                }
            )

        return blocks

    def process_markdown_file(self, md_path: Path) -> None:
        """Process a single markdown file."""
        print(f"Processing {md_path}...")
        content = md_path.read_text(encoding="utf-8")
        code_blocks = self.extract_code_blocks(content)

        if not code_blocks:
            print(f"  No code blocks found in {md_path}")
            return

        for block in code_blocks:
            filepath = Path(block["filepath"])
            code = block["code"]

            # Handle absolute paths in the markdown
            if not filepath.is_absolute():
                filepath = self.output_dir / filepath

            # Create parent directories if they don't exist
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            filepath.write_text(code, encoding="utf-8")
            print(f"  Created/Updated: {filepath}")

    def run(self):
        """Run the extraction process."""
        if not self.todo_dir.exists():
            print(f"Error: Todo directory '{self.todo_dir}' does not exist")
            return 1

        md_files = list(self.todo_dir.glob("*.md"))
        if not md_files:
            print(f"No markdown files found in {self.todo_dir}")
            return 0

        print(f"Found {len(md_files)} markdown file(s) in {self.todo_dir}")

        for md_file in md_files:
            self.process_markdown_file(md_file)

    logger.info("\nExtraction complete!")
        return 0


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    extractor = MarkdownExtractor(base_dir)
    return extractor.run()


if __name__ == "__main__":
    exit(main())
