"""Tests for HeadingDetector and TextCleaner wired into the enrichment pipeline."""

import io
from pathlib import Path

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.pipeline.enrichment import EnrichmentPipeline


def _enrich(markdown: str) -> str:
    """Helper: run enrichment pipeline with filters enabled and return result markdown."""
    config = SciMarkdownConfig(filters_enabled=True)
    pipeline = EnrichmentPipeline(config)
    result = pipeline.enrich(
        base_markdown=markdown,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    return result.base_markdown


class TestEnrichmentConvertsHeadings:
    def test_capitulo_converted(self):
        md = "Capítulo 1. Introducción\n\nSome content here."
        result = _enrich(md)
        assert "# Capítulo 1. Introducción" in result
        assert "Some content here." in result

    def test_chapter_english_converted(self):
        md = "Chapter 3. Methods\n\nContent follows."
        result = _enrich(md)
        assert "# Chapter 3. Methods" in result

    def test_numbered_section_converted(self):
        md = "4.3. Ecuación de Euler\n\nText about equations."
        result = _enrich(md)
        assert "## 4.3. Ecuación de Euler" in result

    def test_existing_heading_preserved(self):
        md = "# Already a heading\n\nSome content."
        result = _enrich(md)
        assert "# Already a heading" in result

    def test_plain_text_not_converted(self):
        md = "This is a normal sentence with no heading pattern."
        result = _enrich(md)
        assert result.strip().startswith("#") is False


class TestEnrichmentCleansCid:
    def test_cid_removed(self):
        md = "fl(cid:3)uido incompresible"
        result = _enrich(md)
        assert "(cid:3)" not in result
        assert "fluido incompresible" in result

    def test_multiple_cids_removed(self):
        md = "(cid:131)(cid:135) garbage text"
        result = _enrich(md)
        assert "(cid:" not in result


class TestEnrichmentNormalizesPaths:
    def test_absolute_path_normalized(self):
        md = "![figura](/home/u680912/0-Advecta/project/fig1.png)"
        result = _enrich(md)
        assert "/home/u680912" not in result
        assert "fig1.png" in result

    def test_relative_path_unchanged(self):
        md = "![fig](relative_image.png)"
        result = _enrich(md)
        assert "![fig](relative_image.png)" in result


class TestEnrichmentFiltersDisabled:
    def test_disabled_leaves_patterns_unchanged(self):
        config = SciMarkdownConfig(filters_enabled=False)
        pipeline = EnrichmentPipeline(config)
        md = "Capítulo 1. Introducción\n\n(cid:3)text"
        result = pipeline.enrich(
            base_markdown=md,
            source_stream=io.BytesIO(b"dummy"),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
        # With filters disabled, no heading conversion or CID cleanup
        assert "# Capítulo" not in result.base_markdown
        assert "(cid:3)" in result.base_markdown
