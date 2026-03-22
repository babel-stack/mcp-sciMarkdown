"""Clean CID characters and normalize image paths in markdown."""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Match (cid:NNN) patterns
_CID_PATTERN = re.compile(r'\(cid:\d+\)')


class TextCleaner:
    """Cleans various text artifacts from PDF conversion."""

    def clean_cid(self, markdown: str) -> str:
        """Remove (cid:NNN) character encoding artifacts."""
        return _CID_PATTERN.sub('', markdown)

    def normalize_image_paths(self, markdown: str) -> str:
        """Convert absolute image paths to relative (filename only).

        Changes: ![alt](/home/user/dir/img.png) → ![alt](img.png)
        """
        def _replace_path(m):
            alt = m.group(1)
            path = m.group(2)
            # Extract just the filename
            filename = Path(path).name if '/' in path else path
            return f'![{alt}]({filename})'

        return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _replace_path, markdown)

    def clean_empty_lines(self, markdown: str) -> str:
        """Collapse 3+ consecutive empty lines into 2."""
        return re.sub(r'\n{4,}', '\n\n\n', markdown)

    def process(self, markdown: str) -> str:
        """Run all text cleaning steps."""
        markdown = self.clean_cid(markdown)
        markdown = self.normalize_image_paths(markdown)
        markdown = self.clean_empty_lines(markdown)
        return markdown
