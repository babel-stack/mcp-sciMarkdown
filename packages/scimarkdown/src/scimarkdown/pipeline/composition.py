"""Composition pipeline: Phase 3 — merge enriched data into final markdown."""

from __future__ import annotations

import logging

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import EnrichedResult

logger = logging.getLogger(__name__)


class CompositionPipeline:
    """Phase 3: compose final markdown from an :class:`EnrichedResult`.

    Steps:
    1. Replace math regions in the markdown with formatted LaTeX strings.
    2. Insert image reference lines (``![label: caption](file_path)``).
    3. Optionally append a figure index table.

    Parameters
    ----------
    config:
        SciMarkdown configuration instance.
    """

    def __init__(self, config: SciMarkdownConfig) -> None:
        self.config = config

    def compose(self, enriched: EnrichedResult) -> str:
        """Return the final markdown string.

        Parameters
        ----------
        enriched:
            The enriched result produced by :class:`EnrichmentPipeline`.
        """
        from scimarkdown.math.formatter import MathFormatter
        from scimarkdown.images.index_builder import IndexBuilder

        markdown = enriched.base_markdown

        # ---------------------------------------------------------------
        # Step 1: Math injection
        # Replace each math region's original_text with formatted LaTeX.
        # Process in descending position order to preserve string offsets.
        # ---------------------------------------------------------------
        if enriched.math_regions:
            formatter = MathFormatter(style=self.config.latex_style)
            sorted_regions = sorted(
                enriched.math_regions, key=lambda r: r.position, reverse=True
            )
            for region in sorted_regions:
                formatted = formatter.format(region)
                original = region.original_text
                # Only replace the first occurrence at the known position to
                # avoid replacing unrelated identical strings.
                pos = region.position
                if (
                    pos >= 0
                    and pos + len(original) <= len(markdown)
                    and markdown[pos : pos + len(original)] == original
                ):
                    markdown = markdown[:pos] + formatted + markdown[pos + len(original):]
                else:
                    # Fallback: replace first occurrence
                    markdown = markdown.replace(original, formatted, 1)

        # ---------------------------------------------------------------
        # Step 2: Image injection
        # Append image markdown lines, sorted by position (ascending).
        # ---------------------------------------------------------------
        if enriched.images:
            image_lines: list[str] = []
            sorted_images = sorted(enriched.images, key=lambda img: img.position)
            for img in sorted_images:
                label = img.reference_label or ""
                caption = img.caption or ""
                if label and caption:
                    alt_text = f"{label}: {caption}"
                elif label:
                    alt_text = label
                elif caption:
                    alt_text = caption
                else:
                    alt_text = ""
                image_lines.append(f"![{alt_text}]({img.file_path})")

            if image_lines:
                if markdown and not markdown.endswith("\n"):
                    markdown += "\n"
                markdown += "\n".join(image_lines)

        # ---------------------------------------------------------------
        # Step 3: Figure index
        # ---------------------------------------------------------------
        if self.config.references_generate_index and enriched.images:
            builder = IndexBuilder()
            index = builder.build(enriched.images)
            if index:
                if markdown and not markdown.endswith("\n"):
                    markdown += "\n"
                markdown += "\n" + index

        return markdown
