"""Enrichment pipeline: Phase 2 — extract math regions and images from a document."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import IO, Optional

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import EnrichedResult

logger = logging.getLogger(__name__)

_IMAGE_FORMATS: dict[str, str] = {
    ".pdf": "extract_from_pdf",
    ".docx": "extract_from_docx",
    ".pptx": "extract_from_pptx",
    ".html": "extract_from_html",
    ".htm": "extract_from_html",
    ".epub": "extract_from_epub",
    ".ipynb": "extract_from_jupyter",
}


class EnrichmentPipeline:
    """Phase 2: enrich base markdown with math regions and image references.

    Parameters
    ----------
    config:
        SciMarkdown configuration instance.
    """

    def __init__(self, config: SciMarkdownConfig) -> None:
        self.config = config

    def enrich(
        self,
        base_markdown: str,
        source_stream: IO[bytes],
        file_extension: str,
        document_name: str,
        output_dir: Path,
    ) -> EnrichedResult:
        """Run the enrichment pipeline and return an :class:`EnrichedResult`.

        Gracefully degrades on any error: if a step fails, it is skipped and
        a partial (or empty) result is returned.

        Parameters
        ----------
        base_markdown:
            The markdown text produced by Pass 1 (base MarkItDown conversion).
        source_stream:
            Seekable byte stream pointing to the original document.
        file_extension:
            Lowercase extension including the dot, e.g. ``".pdf"``.
        document_name:
            Human-readable name used for generated image filenames.
        output_dir:
            Directory where extracted images should be saved.
        """
        result = EnrichedResult(base_markdown=base_markdown)

        # ---------------------------------------------------------------
        # Math detection
        # ---------------------------------------------------------------
        if self.config.math_heuristic:
            try:
                from scimarkdown.math.detector import MathDetector

                detector = MathDetector()
                result.math_regions = detector.detect(base_markdown)
            except Exception as exc:
                logger.warning("Math detection failed: %s", exc, exc_info=True)

        # ---------------------------------------------------------------
        # Image extraction
        # ---------------------------------------------------------------
        method_name = _IMAGE_FORMATS.get(file_extension.lower())
        if method_name:
            try:
                from scimarkdown.images.extractor import ImageExtractor

                extractor = ImageExtractor(
                    config=self.config,
                    document_name=document_name,
                    output_dir=output_dir,
                )
                extract_method = getattr(extractor, method_name)
                images = extract_method(source_stream)
            except Exception as exc:
                logger.warning(
                    "Image extraction (%s) failed: %s", method_name, exc, exc_info=True
                )
                images = []

            # ---------------------------------------------------------------
            # Reference linking
            # ---------------------------------------------------------------
            if images:
                try:
                    from scimarkdown.images.reference_linker import ReferenceLinker

                    linker = ReferenceLinker(self.config)
                    images = linker.link(base_markdown, images)
                except Exception as exc:
                    logger.warning(
                        "Reference linking failed: %s", exc, exc_info=True
                    )

            result.images = images

        return result
