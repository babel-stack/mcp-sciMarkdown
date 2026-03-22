import io
from pathlib import Path
from scimarkdown.pipeline.enrichment import EnrichmentPipeline
from scimarkdown.config import SciMarkdownConfig


def test_enrichment_processes_toc():
    config = SciMarkdownConfig(filters_enabled=True)
    pipeline = EnrichmentPipeline(config)
    md = (
        "# Contents\n\n"
        "Introduction ......... 1\n"
        "Chapter 1 ......... 5\n"
        "Chapter 2 ......... 20\n"
        "Conclusion ......... 50\n\n"
        "# Introduction\n\nText here."
    )
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    assert "........." not in result.base_markdown
    assert "[Introduction]" in result.base_markdown or "[Chapter 1]" in result.base_markdown


def test_enrichment_toc_disabled():
    config = SciMarkdownConfig(filters_enabled=False)
    pipeline = EnrichmentPipeline(config)
    md = "Introduction ......... 1\nChapter 1 ......... 5\nChapter 2 ......... 20\n"
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    assert "........." in result.base_markdown
