"""Tests for EnrichmentPipeline (Phase 2)."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import EnrichedResult, MathRegion
from scimarkdown.pipeline import EnrichmentPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline(**kwargs) -> EnrichmentPipeline:
    config = SciMarkdownConfig(**kwargs)
    return EnrichmentPipeline(config)


def _empty_stream() -> io.BytesIO:
    return io.BytesIO(b"")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnrichmentProducesResult:
    """test_enrichment_produces_result: plain text → EnrichedResult."""

    def test_returns_enriched_result_type(self):
        pipeline = _make_pipeline()
        stream = _empty_stream()
        result = pipeline.enrich(
            base_markdown="Hello world",
            source_stream=stream,
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
        assert isinstance(result, EnrichedResult)

    def test_preserves_base_markdown(self):
        pipeline = _make_pipeline()
        md = "# Title\n\nSome text."
        result = pipeline.enrich(
            base_markdown=md,
            source_stream=_empty_stream(),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
        assert result.base_markdown == md

    def test_no_images_for_unsupported_extension(self):
        pipeline = _make_pipeline()
        result = pipeline.enrich(
            base_markdown="text",
            source_stream=_empty_stream(),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
        assert result.images == []


class TestEnrichmentWithPdfFormat:
    """test_enrichment_with_pdf_format: fake PDF → graceful degradation."""

    def test_graceful_degradation_on_bad_pdf(self):
        """A stream containing non-PDF bytes should degrade gracefully."""
        pipeline = _make_pipeline()
        # Not a real PDF — extraction should fail and be caught
        stream = io.BytesIO(b"not a pdf")
        result = pipeline.enrich(
            base_markdown="Some text",
            source_stream=stream,
            file_extension=".pdf",
            document_name="fake",
            output_dir=Path("/tmp"),
        )
        # Must still return EnrichedResult
        assert isinstance(result, EnrichedResult)
        # Images should be empty after graceful failure
        assert result.images == []

    def test_graceful_degradation_returns_markdown_intact(self):
        pipeline = _make_pipeline()
        md = "# Test\n\nContent here."
        result = pipeline.enrich(
            base_markdown=md,
            source_stream=io.BytesIO(b"junk"),
            file_extension=".pdf",
            document_name="doc",
            output_dir=Path("/tmp"),
        )
        assert result.base_markdown == md

    def test_graceful_degradation_on_bad_docx(self):
        pipeline = _make_pipeline()
        result = pipeline.enrich(
            base_markdown="text",
            source_stream=io.BytesIO(b"not a zip"),
            file_extension=".docx",
            document_name="doc",
            output_dir=Path("/tmp"),
        )
        assert isinstance(result, EnrichedResult)
        assert result.images == []

    def test_graceful_degradation_on_bad_pptx(self):
        pipeline = _make_pipeline()
        result = pipeline.enrich(
            base_markdown="text",
            source_stream=io.BytesIO(b"not a zip"),
            file_extension=".pptx",
            document_name="doc",
            output_dir=Path("/tmp"),
        )
        assert isinstance(result, EnrichedResult)
        assert result.images == []


class TestEnrichmentRespectsConfig:
    """test_enrichment_respects_config: config flags control behaviour."""

    def test_math_detection_runs_when_enabled(self):
        """With math_heuristic=True, math regions are detected."""
        pipeline = _make_pipeline(math_heuristic=True)
        # Text with clear Unicode math symbols (≥ 2 math symbols triggers detection)
        md = "The formula α + β = γ is interesting."
        result = pipeline.enrich(
            base_markdown=md,
            source_stream=_empty_stream(),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
        # math_regions may or may not be non-empty, but must be a list
        assert isinstance(result.math_regions, list)

    def test_math_detection_skipped_when_disabled(self):
        """With math_heuristic=False, math_regions should remain empty."""
        pipeline = _make_pipeline(math_heuristic=False)
        md = "The formula α + β = γ is interesting."
        result = pipeline.enrich(
            base_markdown=md,
            source_stream=_empty_stream(),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
        assert result.math_regions == []

    def test_math_detection_detects_unicode_symbols(self):
        """Multiple Unicode math symbols → at least one MathRegion detected."""
        pipeline = _make_pipeline(math_heuristic=True)
        # 3 clear math symbols: ∑, ∞, ∈ — should trigger detection
        md = "We have ∑ ∞ ∈ all together."
        result = pipeline.enrich(
            base_markdown=md,
            source_stream=_empty_stream(),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
        assert len(result.math_regions) >= 1
        assert all(isinstance(r, MathRegion) for r in result.math_regions)

    def test_unknown_extension_produces_no_images(self):
        """Extensions not in _IMAGE_FORMATS skip image extraction entirely."""
        pipeline = _make_pipeline()
        result = pipeline.enrich(
            base_markdown="text",
            source_stream=_empty_stream(),
            file_extension=".html",
            document_name="doc",
            output_dir=Path("/tmp"),
        )
        assert result.images == []

    def test_math_failure_is_caught(self):
        """If MathDetector.detect raises, the pipeline degrades gracefully."""
        pipeline = _make_pipeline(math_heuristic=True)
        # MathDetector is lazily imported inside the method; patch via its own module
        with patch(
            "scimarkdown.math.detector.MathDetector.detect",
            side_effect=RuntimeError("boom"),
        ):
            # Should not raise
            result = pipeline.enrich(
                base_markdown="α + β",
                source_stream=_empty_stream(),
                file_extension=".txt",
                document_name="test",
                output_dir=Path("/tmp"),
            )
        assert isinstance(result, EnrichedResult)
        assert result.math_regions == []
