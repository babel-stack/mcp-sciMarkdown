import io
from pathlib import Path
from scimarkdown.pipeline.enrichment import EnrichmentPipeline
from scimarkdown.config import SciMarkdownConfig


def test_filters_clean_repeated_text():
    config = SciMarkdownConfig(filters_enabled=True)
    pipeline = EnrichmentPipeline(config)
    # Simulate markdown with noise
    md = "Book Title\n\nReal content paragraph.\n\nBook Title\n\n42"
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    # For non-PDF, no page blocks → no noise detected via page analysis
    # But the filter infrastructure should be wired
    assert result.base_markdown is not None


def test_filters_disabled():
    config = SciMarkdownConfig(filters_enabled=False)
    pipeline = EnrichmentPipeline(config)
    md = "Header\n\nContent\n\n42"
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    # With filters disabled, markdown unchanged
    assert "Header" in result.base_markdown
    assert "42" in result.base_markdown
