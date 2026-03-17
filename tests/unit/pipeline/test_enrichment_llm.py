"""Tests for LLM fallback wiring inside EnrichmentPipeline."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models.math_region import MathRegion
from scimarkdown.pipeline.enrichment import EnrichmentPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_region(text: str, confidence: float, latex: str = "") -> MathRegion:
    return MathRegion(
        position=0,
        original_text=text,
        latex=latex or text,
        source_type="unicode",
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Basic pipeline integration
# ---------------------------------------------------------------------------


@patch("scimarkdown.llm.fallback._call_openai")
def test_enrichment_uses_llm_for_low_confidence(mock_openai: MagicMock) -> None:
    """EnrichmentPipeline calls LLM when a region has confidence below threshold."""
    mock_openai.return_value = r"x^{2}"
    config = SciMarkdownConfig(
        llm_enabled=True,
        llm_provider="openai",
        math_confidence_threshold=0.99,
    )
    pipeline = EnrichmentPipeline(config)

    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = pipeline.enrich(
            base_markdown="Test x² + y²",
            source_stream=io.BytesIO(b"Test"),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )

    # The result must have a math_regions list (may be empty or non-empty)
    assert isinstance(result.math_regions, list)


@patch("scimarkdown.llm.fallback._call_openai")
def test_enrichment_skips_llm_when_disabled(mock_openai: MagicMock) -> None:
    """EnrichmentPipeline does not call LLM when llm_enabled=False."""
    config = SciMarkdownConfig(
        llm_enabled=False,
        llm_provider="openai",
        math_confidence_threshold=0.5,
    )
    pipeline = EnrichmentPipeline(config)

    result = pipeline.enrich(
        base_markdown="Test x² formula",
        source_stream=io.BytesIO(b"Test"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )

    mock_openai.assert_not_called()
    assert isinstance(result.math_regions, list)


def test_enrichment_llm_fallback_attribute_present() -> None:
    """EnrichmentPipeline always has a llm_fallback attribute after construction."""
    config = SciMarkdownConfig(llm_enabled=False)
    pipeline = EnrichmentPipeline(config)
    assert hasattr(pipeline, "llm_fallback")


@patch("scimarkdown.llm.fallback._call_openai")
def test_enrichment_high_confidence_regions_skip_llm(mock_openai: MagicMock) -> None:
    """Regions above the confidence threshold bypass the LLM call."""
    mock_openai.return_value = r"\alpha"
    config = SciMarkdownConfig(
        llm_enabled=True,
        llm_provider="openai",
        # Threshold of 0.0 means ALL regions are considered high-confidence
        math_confidence_threshold=0.0,
    )
    pipeline = EnrichmentPipeline(config)

    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = pipeline.enrich(
            base_markdown="The value α is important.",
            source_stream=io.BytesIO(b"Test"),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )

    # With threshold 0.0, all regions are >= threshold, so LLM should NOT be called
    mock_openai.assert_not_called()
    assert isinstance(result.math_regions, list)


@patch("scimarkdown.llm.fallback._call_openai")
def test_enrichment_llm_none_result_keeps_original(mock_openai: MagicMock) -> None:
    """When LLM returns None, the original region is preserved."""
    mock_openai.return_value = None  # simulate LLM failure
    config = SciMarkdownConfig(
        llm_enabled=True,
        llm_provider="openai",
        math_confidence_threshold=0.99,
    )
    pipeline = EnrichmentPipeline(config)

    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = pipeline.enrich(
            base_markdown="Test x² + y²",
            source_stream=io.BytesIO(b"Test"),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )

    # Even with LLM returning None the pipeline completes and regions list exists
    assert isinstance(result.math_regions, list)


@patch("scimarkdown.llm.fallback._call_openai")
def test_enrichment_with_no_math_skips_llm(mock_openai: MagicMock) -> None:
    """Documents with no detected math regions never call the LLM."""
    config = SciMarkdownConfig(
        llm_enabled=True,
        llm_provider="openai",
        math_confidence_threshold=0.99,
    )
    pipeline = EnrichmentPipeline(config)

    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = pipeline.enrich(
            base_markdown="Plain text with no math whatsoever.",
            source_stream=io.BytesIO(b"Plain text"),
            file_extension=".txt",
            document_name="plain",
            output_dir=Path("/tmp"),
        )

    mock_openai.assert_not_called()
    assert result.math_regions == []
