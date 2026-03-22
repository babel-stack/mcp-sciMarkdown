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
        # Insert images inline at their document position.
        #
        # Strategy:
        # 1. If image has context_text (text from above it in the source),
        #    find that text in the markdown and insert the image right after
        #    the paragraph containing it.
        # 2. Fallback: distribute proportionally by position ratio.
        # ---------------------------------------------------------------
        if enriched.images:
            sorted_images = sorted(enriched.images, key=lambda img: img.position)
            paragraphs = markdown.split("\n\n")
            num_paragraphs = len(paragraphs)

            if num_paragraphs > 0 and sorted_images:
                image_map: dict[int, list[str]] = {}  # paragraph_index → image lines

                # Position range for proportional fallback
                min_pos = sorted_images[0].position
                max_pos = sorted_images[-1].position
                pos_range = max(max_pos - min_pos, 1)

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
                    img_line = f"![{alt_text}]({img.file_path})"

                    para_idx = None

                    # Strategy 1: Match by context_text (text above image in source)
                    if img.context_text:
                        # Search for the context text in each paragraph
                        # Use last 60 chars for more precise matching
                        search_text = img.context_text[-60:].strip()
                        if search_text:
                            for idx, para in enumerate(paragraphs):
                                if search_text in para:
                                    para_idx = idx
                                    break
                            # If exact match fails, try shorter fragment
                            if para_idx is None and len(search_text) > 20:
                                short = search_text[-20:].strip()
                                for idx, para in enumerate(paragraphs):
                                    if short in para:
                                        para_idx = idx
                                        break

                    # Strategy 2: Proportional fallback
                    if para_idx is None:
                        ratio = (img.position - min_pos) / pos_range if pos_range > 0 else 0
                        para_idx = min(int(ratio * num_paragraphs), num_paragraphs - 1)

                    image_map.setdefault(para_idx, []).append(img_line)

                # Rebuild markdown with images inserted after their paragraphs
                result_parts: list[str] = []
                for idx, para in enumerate(paragraphs):
                    result_parts.append(para)
                    if idx in image_map:
                        for img_line in image_map[idx]:
                            result_parts.append(img_line)

                markdown = "\n\n".join(result_parts)

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
