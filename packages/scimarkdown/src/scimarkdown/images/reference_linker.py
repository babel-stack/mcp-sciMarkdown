"""Reference linker: matches figure references in text to extracted images."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import ImageRef

if TYPE_CHECKING:
    pass


class ReferenceLinker:
    """Links textual figure references to ``ImageRef`` objects by ordinal.

    The algorithm:
    1. Scan *text* for all pattern matches (e.g. "Figure 3", "Fig. 1").
    2. Collect the unique ordinal numbers in the order they first appear.
    3. Map ordinal *n* → *n*-th image (1-based index into *images*).
    4. For each match, set ``image.reference_label`` and ``image.ordinal``
       on the corresponding ``ImageRef``.

    Repeated references (e.g. "Figure 1 … Figure 1 again") point to the
    same image and do not create duplicates.

    Images that have no matching reference are left unchanged
    (``reference_label`` stays ``None``).
    """

    def __init__(self, config: SciMarkdownConfig) -> None:
        self.config = config
        self._compiled = [re.compile(p, re.IGNORECASE) for p in config.references_patterns]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def link(self, text: str, images: list[ImageRef]) -> list[ImageRef]:
        """Return *images* with ``reference_label`` and ``ordinal`` populated.

        Parameters
        ----------
        text:
            Full document text to scan for figure references.
        images:
            List of ``ImageRef`` objects extracted from the document,
            in extraction order.

        Returns
        -------
        The same list (mutated in-place) with matched images updated.
        """
        if not images:
            return images

        # Gather all (position_in_text, ordinal, full_match_text) tuples
        all_matches: list[tuple[int, int, str]] = []
        for pattern in self._compiled:
            for m in pattern.finditer(text):
                ordinal = int(m.group(1))
                all_matches.append((m.start(), ordinal, m.group(0)))

        # Sort by position to determine first-appearance order
        all_matches.sort(key=lambda t: t[0])

        # Build ordered list of unique ordinals (first-seen order)
        seen_ordinals: dict[int, str] = {}  # ordinal → full match text
        for _pos, ordinal, label in all_matches:
            if ordinal not in seen_ordinals:
                seen_ordinals[ordinal] = label

        # Map: ordinal → image index (1-based; ordinal 1 → images[0])
        for ordinal, label in seen_ordinals.items():
            img_index = ordinal - 1  # convert to 0-based
            if 0 <= img_index < len(images):
                images[img_index].reference_label = label
                images[img_index].ordinal = ordinal

        return images
