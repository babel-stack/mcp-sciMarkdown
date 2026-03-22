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

    def clean_intra_paragraph_breaks(self, markdown: str) -> str:
        """Merge single newlines within paragraphs into spaces.

        PDF converters often preserve the original line wrapping from the PDF,
        producing single ``\\n`` within what should be a single markdown paragraph.
        This method joins those wrapped lines with a space.

        Lines that are structural markdown (headings, lists, tables, images,
        code blocks) are left untouched.
        """
        if not markdown:
            return markdown

        paragraphs = markdown.split('\n\n')
        cleaned: list[str] = []

        in_code_block = False

        for para in paragraphs:
            # Track code blocks across paragraphs
            fence_count = para.count('```')
            if in_code_block:
                cleaned.append(para)
                if fence_count % 2 == 1:
                    in_code_block = False
                continue
            if fence_count % 2 == 1:
                in_code_block = True
                cleaned.append(para)
                continue
            # If the paragraph contains a code fence pair, leave it alone
            if fence_count > 0:
                cleaned.append(para)
                continue

            stripped = para.strip()

            # If paragraph starts with heading, split heading from body
            if stripped.startswith('#'):
                lines = para.split('\n')
                heading = lines[0]
                body_lines = lines[1:]
                if body_lines:
                    body = ' '.join(l for l in body_lines)
                    cleaned.append(heading + '\n' + body)
                else:
                    cleaned.append(para)
                continue

            # Check if this paragraph is structural markdown
            if (
                stripped.startswith('![')
                or stripped.startswith('|')
                or stripped.startswith('- ')
                or stripped.startswith('* ')
                or re.match(r'^\d+\.\s', stripped)
            ):
                cleaned.append(para)
                continue

            # Merge single newlines into spaces
            merged = re.sub(r'\n', ' ', para)
            cleaned.append(merged)

        return '\n\n'.join(cleaned)

    def clean_empty_lines(self, markdown: str) -> str:
        """Collapse 3+ consecutive empty lines into 2."""
        return re.sub(r'\n{4,}', '\n\n\n', markdown)

    def process(self, markdown: str) -> str:
        """Run all text cleaning steps.

        Note: ``clean_intra_paragraph_breaks`` is NOT called here because it
        must run AFTER noise filtering (repeated-line removal needs the
        original single-newline structure intact).  The enrichment pipeline
        calls it explicitly at the right point.
        """
        markdown = self.clean_cid(markdown)
        markdown = self.normalize_image_paths(markdown)
        markdown = self.clean_empty_lines(markdown)
        return markdown
