"""Detect repeated header/footer text across pages."""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RepeatedTextFilter:
    """Detects text repeated at the same position across multiple pages.

    Only considers text that is:
    - In a boundary position (first or last block on the page)
    - Short (< max_length characters)
    - Appears at the same Y coordinate (± tolerance) on min_repeat_pages+ pages
    """

    def __init__(
        self,
        min_repeat_pages: int = 3,
        max_length: int = 100,
        y_tolerance: float = 5.0,
    ):
        self.min_repeat_pages = min_repeat_pages
        self.max_length = max_length
        self.y_tolerance = y_tolerance

    def detect(self, pages: list[list[dict]]) -> set[str]:
        """Detect noise text strings.

        Args:
            pages: List of pages, each page is a list of block dicts with
                   keys: "y" (float), "text" (str), "is_boundary" (bool).

        Returns:
            Set of text strings identified as repeated header/footer noise.
        """
        if not pages:
            return set()

        # Collect (text, y_bucket) → count of pages where it appears as boundary
        # y_bucket groups nearby Y coordinates; use two overlapping grids to handle
        # values near bucket boundaries (half-offset grid)
        occurrences: dict[tuple[str, int], int] = defaultdict(int)
        occurrences_offset: dict[tuple[str, int], int] = defaultdict(int)

        for page_blocks in pages:
            seen_on_page: set[tuple[str, int]] = set()
            seen_on_page_offset: set[tuple[str, int]] = set()
            for block in page_blocks:
                if not block.get("is_boundary", False):
                    continue
                text = block["text"].strip()
                if not text or len(text) > self.max_length:
                    continue
                y = block["y"]
                # Primary grid
                y_bucket = int(y / self.y_tolerance)
                key = (text, y_bucket)
                if key not in seen_on_page:
                    seen_on_page.add(key)
                    occurrences[key] += 1
                # Offset grid (shifted by half tolerance to catch boundary cases)
                y_bucket_off = int((y + self.y_tolerance / 2) / self.y_tolerance)
                key_off = (text, y_bucket_off)
                if key_off not in seen_on_page_offset:
                    seen_on_page_offset.add(key_off)
                    occurrences_offset[key_off] += 1

        # Texts appearing on enough pages in either grid are noise
        noise: set[str] = set()
        for (text, _), count in occurrences.items():
            if count >= self.min_repeat_pages:
                noise.add(text)
                logger.debug("Repeated text noise (%d pages): '%s'", count, text[:50])
        for (text, _), count in occurrences_offset.items():
            if count >= self.min_repeat_pages:
                noise.add(text)
                logger.debug("Repeated text noise offset (%d pages): '%s'", count, text[:50])

        return noise
