"""Detect page numbers in boundary text blocks."""

import re
import logging

logger = logging.getLogger(__name__)

# Patterns that match page number formats
_PAGE_NUM_PATTERNS = [
    re.compile(r'^\s*[-–—]?\s*(\d{1,4})\s*[-–—]?\s*$'),              # "42", "- 42 -"
    re.compile(r'^[Pp](?:ág|age|ag)?\.?\s*(\d{1,4})$'),               # "pág. 42", "Page 42"
    re.compile(r'^\s*(i{1,4}|vi{0,3}|iv|ix|xi{0,3}|xiv|xv)\s*$'),   # Roman numerals i-xv
]


def _extract_number(text: str) -> int | None:
    """Extract a page number from text, or None if not a page number format."""
    text = text.strip()
    for pattern in _PAGE_NUM_PATTERNS:
        m = pattern.match(text)
        if m:
            val = m.group(1) if m.lastindex else text.strip()
            # Try arabic
            try:
                return int(val)
            except ValueError:
                pass
            # Try roman
            roman_map = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
                         "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
                         "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15}
            if val.lower() in roman_map:
                return roman_map[val.lower()]
    return None


class PageNumberFilter:
    """Detects isolated page numbers in boundary blocks.

    Looks for short numeric text in boundary positions that forms
    a sequential or near-sequential pattern across pages.
    """

    def detect(self, pages: list[list[dict]]) -> set[str]:
        """Detect page number strings.

        Returns set of text strings identified as page numbers.
        """
        if not pages:
            return set()

        # Collect boundary texts with extracted numbers
        candidates: list[tuple[str, int]] = []  # (original_text, extracted_number)

        for page_blocks in pages:
            for block in page_blocks:
                if not block.get("is_boundary", False):
                    continue
                text = block["text"].strip()
                num = _extract_number(text)
                if num is not None:
                    candidates.append((text, num))
                    break  # One page number per page max

        if len(candidates) < 3:
            return set()

        # Check if numbers form a sequential pattern
        numbers = [n for _, n in candidates]
        sequential_count = 0
        for i in range(1, len(numbers)):
            if numbers[i] == numbers[i - 1] + 1:
                sequential_count += 1

        # If at least 60% of transitions are sequential → page numbers
        if sequential_count >= len(numbers) * 0.6:
            noise = {text for text, _ in candidates}
            logger.debug("Detected %d page numbers", len(noise))
            return noise

        return set()
