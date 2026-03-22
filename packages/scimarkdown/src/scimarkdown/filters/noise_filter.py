"""Orchestrator for noise filters — cleans markdown of headers, footers, page numbers."""

import io
import logging
import re
from typing import IO, Optional

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import ImageRef
from .repeated_text import RepeatedTextFilter
from .page_numbers import PageNumberFilter
from .decorative_images import DecorativeImageFilter

logger = logging.getLogger(__name__)


class NoiseFilter:
    """Orchestrates all noise filters and applies them to markdown text and images."""

    def __init__(self, config: SciMarkdownConfig):
        self.config = config
        self.repeated_filter = RepeatedTextFilter(
            min_repeat_pages=config.filters_min_repeat_pages,
            max_length=config.filters_max_header_length,
            y_tolerance=config.filters_position_tolerance,
        )
        self.page_number_filter = PageNumberFilter()
        self.decorative_filter = DecorativeImageFilter(
            min_size=config.filters_min_image_size,
            max_aspect_ratio=config.filters_max_image_aspect_ratio,
            min_repeat=config.filters_min_image_repeat,
        )

    def extract_page_blocks(self, stream: IO[bytes], file_extension: str) -> list[list[dict]]:
        """Extract per-page text blocks from a document for noise analysis.

        Currently supports PDF via PyMuPDF.
        Returns list of pages, each page a list of block dicts.
        """
        if file_extension.lower() != ".pdf":
            return []

        try:
            import fitz
        except ImportError:
            return []

        pages: list[list[dict]] = []
        data = stream.read()
        stream.seek(0)

        try:
            doc = fitz.open(stream=data, filetype="pdf")
            for page in doc:
                blocks = page.get_text("blocks")
                # blocks: (x0, y0, x1, y1, text, block_no, block_type)
                text_blocks = [
                    (b[1], b[4].strip())  # (y0, text)
                    for b in blocks if b[6] == 0 and b[4].strip()
                ]
                text_blocks.sort(key=lambda t: t[0])

                page_data: list[dict] = []
                for idx, (y, text) in enumerate(text_blocks):
                    is_boundary = (idx == 0) or (idx == len(text_blocks) - 1)
                    page_data.append({
                        "y": y,
                        "text": text,
                        "is_boundary": is_boundary,
                    })
                pages.append(page_data)
            doc.close()
        except Exception as e:
            logger.warning("Failed to extract page blocks: %s", e)

        return pages

    def detect_noise(self, pages: list[list[dict]]) -> set[str]:
        """Run text noise detection filters and return set of noise strings."""
        if not self.config.filters_enabled:
            return set()

        noise: set[str] = set()

        if self.config.filters_repeated_text:
            noise |= self.repeated_filter.detect(pages)

        if self.config.filters_page_numbers:
            noise |= self.page_number_filter.detect(pages)

        return noise

    def filter_images(self, images: list[ImageRef]) -> list[ImageRef]:
        """Filter decorative images."""
        if not self.config.filters_enabled or not self.config.filters_decorative_images:
            return images
        return self.decorative_filter.filter(images)

    def clean_standalone_numbers(self, markdown: str) -> str:
        """Remove standalone numbers that are likely page numbers.

        A standalone number is a paragraph containing ONLY a number (1-4 digits),
        optionally surrounded by whitespace.  Roman numerals (i–xx) are also removed.

        Does NOT remove numbers that are part of a sentence.
        """
        paragraphs = markdown.split('\n\n')
        cleaned = []
        for para in paragraphs:
            stripped = para.strip()
            # Standalone number (1-4 digits, possibly with whitespace)
            if re.match(r'^\s*\d{1,4}\s*$', stripped):
                continue
            # Roman numerals standalone (i, ii, ..., xx)
            if re.match(r'^\s*[ivxlc]{1,6}\s*$', stripped, re.IGNORECASE):
                continue
            cleaned.append(para)
        return '\n\n'.join(cleaned)

    def clean_repeated_paragraphs(self, markdown: str, min_occurrences: int = 3) -> str:
        """Remove short paragraphs that repeat too many times (likely headers/footers).

        Works at the markdown level — no PDF coordinates needed.

        Parameters
        ----------
        markdown:
            The full markdown text.
        min_occurrences:
            Minimum number of times a paragraph must appear to be considered noise.

        Rules:
        - Only considers paragraphs shorter than 100 characters.
        - Never removes headings (lines starting with ``#``).
        - Never removes image references (lines starting with ``![``).
        """
        if not markdown:
            return markdown

        paragraphs = markdown.split('\n\n')

        # Count occurrences of short paragraphs
        from collections import Counter
        counts: Counter[str] = Counter()
        for para in paragraphs:
            stripped = para.strip()
            if len(stripped) < 100:
                counts[stripped] += 1

        # Build set of noise paragraphs
        noise = {
            text for text, count in counts.items()
            if count >= min_occurrences
            and not text.startswith('#')
            and not text.startswith('![')
        }

        if not noise:
            return markdown

        cleaned = [p for p in paragraphs if p.strip() not in noise]

        logger.info(
            "Removed %d repeated paragraph patterns: %s",
            len(noise),
            [n[:50] for n in noise],
        )

        return '\n\n'.join(cleaned)

    def clean_text(self, markdown: str, noise_strings: set[str]) -> str:
        """Remove noise strings from markdown.

        Only removes noise that appears as a standalone paragraph
        (entire paragraph matches noise). Does NOT remove noise
        that appears inline within a longer sentence.
        """
        if not self.config.filters_enabled or not noise_strings:
            return markdown

        paragraphs = markdown.split("\n\n")
        cleaned: list[str] = []

        for para in paragraphs:
            stripped = para.strip()
            if stripped in noise_strings:
                logger.debug("Removed noise paragraph: '%s'", stripped[:50])
                continue
            cleaned.append(para)

        return "\n\n".join(cleaned)
