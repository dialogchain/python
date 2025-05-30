#!/usr/bin/env python3
"""
Extract code blocks from markdown files and save them to the correct locations.
"""
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)



class MarkdownExtractor:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.todo_dir = self.base_dir / "todo"
        self.output_dir = self.base_dir

    def clean_filename(self, filename: str) -> str:
        """Clean up and validate filename."""
        # Remove code formatting
        filename = re.sub(r"`([^`]+)`", r"\1", filename)  # Remove backticks
        # Remove special characters
        filename = re.sub(r"[^\w\s-]", "", filename)
        # Replace spaces and underscores with single underscore
        filename = re.sub(r"[\s_]+", "_", filename)
        # Remove leading/trailing underscores/dashes
        filename = filename.strip("_-")
        # Truncate if too long
        if len(filename) > 100:
            filename = filename[:100]
        return filename

    def extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract code blocks with their file paths."""
        # Split content into sections by headers
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        blocks = []

        for section in sections[1:]:  # Skip first empty section
            if not section.strip():
                continue

            # Split into header and content
            header, *content_parts = section.split("\n", 1)
            if not content_parts:
                continue

            content = content_parts[0]

            # Find all code blocks in this section
            code_blocks = re.findall(r"```(?:\w*)\n(.*?)```", content, re.DOTALL)
            if not code_blocks:
                continue

            # Clean up the header to get the file path
            filepath = self.clean_filename(header.strip())
            if not filepath:
                continue

            # Take the first code block for this header
            blocks.append(
                {
                    "filepath": filepath,
                    "code": code_blocks[0].strip(),
                }
            )

        return blocks

    def process_markdown_file(self, md_path: Path) -> None:
        """Process a single markdown file."""
        print(f"Processing {md_path}...")
        try:
            content = md_path.read_text(encoding="utf-8")
            code_blocks = self.extract_code_blocks(content)

            if not code_blocks:
                print(f"  No valid code blocks found in {md_path}")
                return

            for block in code_blocks:
                try:
                    # Clean and validate the filename
                    clean_path = self.clean_filename(block["filepath"])
                    if not clean_path:
                        print(f"  Invalid filename: {block['filepath']}")
                        continue

                    # Determine file extension based on content
                    ext = ".py"  # default
                    if any(
                        clean_path.endswith(e)
                        for e in [
                            ".js",
                            ".py",
                            ".yaml",
                            ".json",
                            ".toml",
                            ".md",
                            ".rs",
                            ".cpp",
                            ".go",
                        ]
                    ):
                        filepath = Path(clean_path)
                    else:
                        # Try to guess extension from code content
                        first_line = block["code"].split("\n", 1)[0].lower()
                        if first_line.startswith(("def ", "import ", "from ")):
                            ext = ".py"
                        elif (
                            first_line.startswith(
                                ("function", "const ", "let ", "var ")
                            )
                            or "=>" in first_line
                        ):
                            ext = ".js"
                        elif first_line.strip().startswith(("fn ", "pub fn ", "mod ")):
                            ext = ".rs"
                        elif (
                            first_line.strip().startswith(("package ", "import "))
                            and "main" in block["code"]
                        ):
                            ext = ".go"
                        filepath = Path(f"{clean_path}{ext}")

                    # Make path relative to output directory
                    if not filepath.is_absolute():
                        filepath = self.output_dir / filepath

                    # Skip very large files or non-text content
                    if len(block["code"]) > 1000000:  # 1MB limit
                        print(f"  Skipping large file: {filepath}")
                        continue

                    # Create parent directories if they don't exist
                    filepath.parent.mkdir(parents=True, exist_ok=True)

                    # Write the file
                    filepath.write_text(block["code"], encoding="utf-8")
                    print(f"  Created/Updated: {filepath}")

                except Exception as e:
                    print(f"  Error processing block in {md_path}: {str(e)}")
                    continue

        except Exception as e:
            print(f"  Error processing {md_path}: {str(e)}")
            return

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
