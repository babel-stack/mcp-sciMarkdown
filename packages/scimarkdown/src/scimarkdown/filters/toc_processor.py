"""Table of Contents processor: detect, parse, and convert TOC entries to hyperlinks."""

import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Filler patterns between title and page number
_FILLER_PATTERN = re.compile(
    r'^'
    r'(?P<title>.+?)'           # Title (non-greedy)
    r'\s*'                       # Optional space before filler
    r'[.\-–—_\s]{3,}'           # Filler: 3+ dots, dashes, underscores, or spaces
    r'\s*'                       # Optional space after filler
    r'(?P<page>\d{1,4}|[ivxlc]{1,10})' # Page number (arabic or roman)
    r'\s*$'                      # End of line
)

# Simpler pattern: title followed by spaces and a number at end of line
_SPACES_PATTERN = re.compile(
    r'^'
    r'(?P<title>.+\S)'          # Title ending in non-space
    r'\s{3,}'                   # 3+ spaces
    r'(?P<page>\d{1,4}|[ivxlc]{1,10})' # Page number
    r'\s*$'
)

_ROMAN_NUMERALS = {
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxx", "xl", "l",
}


@dataclass
class TocEntry:
    """A parsed table of contents entry."""
    title: str
    page: int | str  # int for arabic, str for roman
    indent_level: int = 0
    slug: str = ""


class TocProcessor:
    """Detects and processes table of contents in markdown.

    Converts TOC entries from:
        Chapter 1: Introduction ......... 15
    To:
        [Chapter 1: Introduction](#chapter-1-introduction)
    """

    def parse_entry(self, line: str) -> Optional[tuple[str, int | str]]:
        """Parse a single line as a TOC entry.

        Returns (title, page_number) or None if not a TOC entry.
        """
        stripped = line.strip()
        if not stripped or len(stripped) < 5:
            return None

        # Try filler pattern first (dots, dashes, etc.)
        m = _FILLER_PATTERN.match(stripped)
        if not m:
            m = _SPACES_PATTERN.match(stripped)
        if not m:
            return None

        title = m.group("title").strip()
        page_str = m.group("page").strip()

        # Validate title: must have at least 2 non-digit chars
        alpha_chars = sum(1 for c in title if c.isalpha())
        if alpha_chars < 2:
            return None

        # Parse page number
        if page_str.lower() in _ROMAN_NUMERALS:
            return title, page_str
        try:
            return title, int(page_str)
        except ValueError:
            return None

    def generate_slug(self, title: str) -> str:
        """Generate a markdown-compatible anchor slug from a title.

        Follows GitHub-flavored markdown anchor generation:
        - Lowercase
        - Replace spaces with hyphens
        - Remove non-alphanumeric chars (except hyphens)
        - Strip leading/trailing hyphens
        """
        slug = title.lower()
        # Remove section numbers at the start (e.g., "3.2.1 ")
        slug = re.sub(r'^\d+(?:\.\d+)*\s+', '', slug)
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        slug = slug.strip('-')
        return slug

    def detect_toc_region(self, markdown: str) -> Optional[tuple[int, int]]:
        """Detect the start and end positions of a TOC region in markdown.

        A TOC region is a sequence of 3+ consecutive lines that parse as TOC entries.
        Returns (start_line_index, end_line_index) or None.
        """
        lines = markdown.split('\n')
        consecutive = 0
        start = -1

        regions: list[tuple[int, int]] = []

        for i, line in enumerate(lines):
            if self.parse_entry(line) is not None:
                if consecutive == 0:
                    start = i
                consecutive += 1
            else:
                if consecutive >= 3:
                    regions.append((start, i))
                consecutive = 0
                start = -1

        # Handle TOC at end of document
        if consecutive >= 3:
            regions.append((start, len(lines)))

        # Return the largest region (likely the main TOC)
        if regions:
            return max(regions, key=lambda r: r[1] - r[0])
        return None

    def process(self, markdown: str) -> str:
        """Process markdown: detect TOC, convert entries to hyperlinks.

        Returns the modified markdown with TOC entries as links.
        """
        region = self.detect_toc_region(markdown)
        if region is None:
            return markdown

        lines = markdown.split('\n')
        start, end = region

        # Parse all entries in the TOC region
        entries: list[TocEntry] = []
        for i in range(start, end):
            result = self.parse_entry(lines[i])
            if result:
                title, page = result
                indent = len(lines[i]) - len(lines[i].lstrip())
                slug = self.generate_slug(title)
                entries.append(TocEntry(
                    title=title, page=page,
                    indent_level=indent, slug=slug,
                ))

        if not entries:
            return markdown

        # Replace TOC lines with hyperlinks
        new_lines = list(lines)
        entry_idx = 0
        for i in range(start, end):
            if self.parse_entry(lines[i]) is not None and entry_idx < len(entries):
                entry = entries[entry_idx]
                indent = "  " * (entry.indent_level // 2)
                new_lines[i] = f"{indent}- [{entry.title}](#{entry.slug})"
                entry_idx += 1

        # Ensure headings in the body have matching anchors
        # Markdown renderers auto-generate anchors from heading text,
        # so we just need to verify headings exist. No modification needed
        # if the document uses standard markdown headings.

        return '\n'.join(new_lines)
