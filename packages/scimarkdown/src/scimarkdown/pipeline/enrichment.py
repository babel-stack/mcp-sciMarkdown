"""Enrichment pipeline: Phase 2 — extract math regions and images from a document."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import IO, Optional

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import EnrichedResult

logger = logging.getLogger(__name__)


def _create_embedding_client(config: SciMarkdownConfig) -> Optional[object]:
    """Create a GeminiEmbeddingClient if embeddings are enabled and an API key is available.

    Returns ``None`` if embeddings are disabled or the API key is missing.
    """
    if not config.embeddings_enabled:
        return None

    api_key = os.environ.get(config.embeddings_api_key_env)
    if not api_key:
        logger.debug(
            "Embeddings enabled but %r env var not set — skipping.", config.embeddings_api_key_env
        )
        return None

    try:
        from scimarkdown.embeddings.client import GeminiEmbeddingClient
        cache_dir = Path(config.embeddings_cache_dir)
        return GeminiEmbeddingClient(
            api_key=api_key,
            cache_dir=cache_dir,
            model=config.embeddings_model,
        )
    except Exception as exc:
        logger.warning("Could not create embedding client: %s", exc)
        return None

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
        from ..llm.fallback import LLMFallback
        self.llm_fallback = LLMFallback(config)

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
        math_regions = []
        if self.config.math_heuristic:
            try:
                from scimarkdown.math.detector import MathDetector

                detector = MathDetector()
                math_regions = detector.detect(base_markdown)
            except Exception as exc:
                logger.warning("Math detection failed: %s", exc, exc_info=True)

        # LLM fallback for low-confidence math regions
        if self.config.llm_enabled and math_regions:
            enhanced_regions = []
            for region in math_regions:
                if region.confidence < self.config.math_confidence_threshold:
                    llm_result = self.llm_fallback.recognize_math(region.original_text)
                    if llm_result:
                        llm_result.position = region.position
                        llm_result.original_text = region.original_text
                        enhanced_regions.append(llm_result)
                    else:
                        enhanced_regions.append(region)
                else:
                    enhanced_regions.append(region)
            math_regions = enhanced_regions

        result.math_regions = math_regions

        # ---------------------------------------------------------------
        # Embedding enrichment (math classifier + semantic linker)
        # ---------------------------------------------------------------
        embedding_client = _create_embedding_client(self.config)

        if embedding_client is not None and result.math_regions:
            if self.config.embeddings_classify_math:
                try:
                    from scimarkdown.embeddings.math_classifier import MathClassifier
                    classifier = MathClassifier(
                        client=embedding_client,
                        threshold=self.config.embeddings_math_similarity_threshold,
                    )
                    result.math_regions = classifier.classify(result.math_regions)
                except Exception as exc:
                    logger.warning("MathClassifier failed, keeping original regions: %s", exc)

        # ---------------------------------------------------------------
        # TOC processing: detect and convert to hyperlinks
        # ---------------------------------------------------------------
        if self.config.filters_enabled:
            try:
                from scimarkdown.filters.toc_processor import TocProcessor
                toc = TocProcessor()
                base_markdown = toc.process(base_markdown)
                result.base_markdown = base_markdown
            except Exception as e:
                logger.warning("TOC processing failed: %s", e)

            # Heading detection: convert chapter/section patterns to markdown headings
            try:
                from scimarkdown.filters.heading_detector import HeadingDetector
                heading_detector = HeadingDetector()
                base_markdown = heading_detector.process(base_markdown)
                result.base_markdown = base_markdown
            except Exception as e:
                logger.warning("Heading detection failed: %s", e)

            # Text cleaning: CID chars, absolute paths, empty lines
            try:
                from scimarkdown.filters.text_cleaner import TextCleaner
                cleaner = TextCleaner()
                base_markdown = cleaner.process(base_markdown)
                result.base_markdown = base_markdown
            except Exception as e:
                logger.warning("Text cleaning failed: %s", e)

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
            # Noise filtering (headers, footers, page numbers, decorative images)
            # ---------------------------------------------------------------
            if self.config.filters_enabled:
                try:
                    from scimarkdown.filters.noise_filter import NoiseFilter
                    noise_filter = NoiseFilter(self.config)

                    # Extract page blocks for text noise detection (PDF only)
                    source_stream.seek(0)
                    page_blocks = noise_filter.extract_page_blocks(source_stream, file_extension)
                    source_stream.seek(0)

                    if page_blocks:
                        noise_strings = noise_filter.detect_noise(page_blocks)
                        if noise_strings:
                            base_markdown = noise_filter.clean_text(base_markdown, noise_strings)
                            result.base_markdown = base_markdown
                            logger.info("Removed %d noise strings", len(noise_strings))

                    # Filter decorative images
                    if images:
                        images = noise_filter.filter_images(images)
                        logger.info("After decorative filter: %d images", len(images))

                    # Remove standalone page numbers from markdown text
                    base_markdown = noise_filter.clean_standalone_numbers(base_markdown)
                    result.base_markdown = base_markdown

                    # Remove repeated short paragraphs (headers/footers at markdown level)
                    base_markdown = noise_filter.clean_repeated_paragraphs(base_markdown)
                    result.base_markdown = base_markdown

                except Exception as e:
                    logger.warning("Noise filtering failed: %s", e)

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

        # ---------------------------------------------------------------
        # Semantic linking — images to text
        # ---------------------------------------------------------------
        if embedding_client is not None and self.config.embeddings_semantic_linking:
            try:
                from scimarkdown.embeddings.semantic_linker import SemanticLinker
                # Extract text paragraphs from the base markdown for linking.
                import re
                paragraphs = [
                    p.strip() for p in re.split(r"\n\s*\n", base_markdown)
                    if p.strip() and not p.strip().startswith("#")
                ]
                linker = SemanticLinker(
                    client=embedding_client,
                    threshold=self.config.embeddings_image_link_threshold,
                )
                result.images = linker.link(result.images, paragraphs)
            except Exception as exc:
                logger.warning("SemanticLinker failed: %s", exc)

        return result
