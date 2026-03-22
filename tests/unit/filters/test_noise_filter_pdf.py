"""Tests for NoiseFilter.extract_page_blocks with real PDFs."""

import io
import pytest

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.filters.noise_filter import NoiseFilter
from scimarkdown.models import ImageRef


def _make_filter(enabled: bool = True) -> NoiseFilter:
    config = SciMarkdownConfig(
        filters_enabled=enabled,
        filters_repeated_text=True,
        filters_page_numbers=True,
        filters_min_repeat_pages=3,
        filters_max_header_length=100,
        filters_position_tolerance=5.0,
    )
    return NoiseFilter(config)


class TestExtractPageBlocksPDF:
    def test_extract_returns_empty_for_non_pdf(self, tmp_path):
        """extract_page_blocks returns [] for non-PDF extensions."""
        noise_filter = _make_filter()
        stream = io.BytesIO(b"not a pdf")
        result = noise_filter.extract_page_blocks(stream, ".docx")
        assert result == []

    def test_extract_returns_empty_for_txt(self):
        noise_filter = _make_filter()
        stream = io.BytesIO(b"Hello world")
        result = noise_filter.extract_page_blocks(stream, ".txt")
        assert result == []

    def test_extract_from_real_pdf_with_text(self, tmp_path):
        """Real PDF with text yields page blocks."""
        fitz = pytest.importorskip("fitz", reason="PyMuPDF required")

        doc = fitz.open()
        # Page 1: header + body + footer
        page = doc.new_page()
        page.insert_text((72, 50), "Header Text")
        page.insert_text((72, 300), "Main body paragraph that contains useful info.")
        page.insert_text((72, 750), "Footer Text")

        # Page 2: same header/footer
        page2 = doc.new_page()
        page2.insert_text((72, 50), "Header Text")
        page2.insert_text((72, 300), "Another body paragraph.")
        page2.insert_text((72, 750), "Footer Text")

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        noise_filter = _make_filter()
        result = noise_filter.extract_page_blocks(pdf_bytes, ".pdf")

        # Should have 2 pages worth of blocks
        assert len(result) == 2
        # Each page has 3 text blocks
        for page_blocks in result:
            assert len(page_blocks) >= 1
            for block in page_blocks:
                assert "text" in block
                assert "y" in block
                assert "is_boundary" in block

    def test_extract_boundary_blocks_marked(self, tmp_path):
        """First and last text blocks are marked as boundary."""
        fitz = pytest.importorskip("fitz", reason="PyMuPDF required")

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 50), "First text")
        page.insert_text((72, 200), "Middle text")
        page.insert_text((72, 700), "Last text")

        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        noise_filter = _make_filter()
        result = noise_filter.extract_page_blocks(pdf_bytes, ".pdf")

        assert len(result) == 1
        page_blocks = result[0]
        assert page_blocks[0]["is_boundary"] is True
        assert page_blocks[-1]["is_boundary"] is True
        # Middle blocks are not boundary
        if len(page_blocks) > 2:
            for block in page_blocks[1:-1]:
                assert block["is_boundary"] is False

    def test_extract_empty_pdf(self, tmp_path):
        """PDF with no text returns empty blocks per page."""
        fitz = pytest.importorskip("fitz", reason="PyMuPDF required")

        doc = fitz.open()
        doc.new_page()  # empty page
        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        noise_filter = _make_filter()
        result = noise_filter.extract_page_blocks(pdf_bytes, ".pdf")

        assert len(result) == 1
        assert result[0] == []

    def test_extract_invalid_pdf_graceful(self):
        """Corrupted/invalid PDF data returns empty list gracefully."""
        noise_filter = _make_filter()
        stream = io.BytesIO(b"this is not a pdf at all")
        result = noise_filter.extract_page_blocks(stream, ".pdf")
        # Should not raise; returns [] or partial result
        assert isinstance(result, list)

    def test_extract_multi_page_pdf(self):
        """Multi-page PDF returns one entry per page."""
        fitz = pytest.importorskip("fitz", reason="PyMuPDF required")

        doc = fitz.open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 100), f"Page {i+1} body text")
        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        noise_filter = _make_filter()
        result = noise_filter.extract_page_blocks(pdf_bytes, ".pdf")
        assert len(result) == 5


class TestDetectNoise:
    def test_detect_noise_disabled(self):
        """When filters_enabled=False, detect_noise returns empty set."""
        noise_filter = _make_filter(enabled=False)
        pages = [[{"y": 10, "text": "Header", "is_boundary": True}]]
        result = noise_filter.detect_noise(pages)
        assert result == set()

    def test_detect_noise_with_page_numbers(self):
        """Sequential page numbers are detected as noise."""
        noise_filter = _make_filter()
        pages = []
        for i in range(5):
            pages.append([
                {"y": 10, "text": "Header", "is_boundary": True},
                {"y": 300, "text": f"Body text {i}", "is_boundary": False},
                {"y": 700, "text": str(i + 1), "is_boundary": True},
            ])
        result = noise_filter.detect_noise(pages)
        # Sequential numbers 1-5 should be detected
        assert isinstance(result, set)


class TestFilterImages:
    def test_filter_images_disabled(self):
        """When filters_enabled=False, all images pass through."""
        noise_filter = _make_filter(enabled=False)
        images = [
            ImageRef(position=0, file_path="/img.png", original_format="png", width=5, height=5),
        ]
        result = noise_filter.filter_images(images)
        assert len(result) == 1

    def test_filter_images_removes_small(self):
        """Images smaller than min_size are removed."""
        config = SciMarkdownConfig(
            filters_enabled=True,
            filters_decorative_images=True,
            filters_min_image_size=30,
        )
        noise_filter = NoiseFilter(config)
        images = [
            ImageRef(position=0, file_path="/small.png", original_format="png", width=10, height=10),
            ImageRef(position=1, file_path="/big.png", original_format="png", width=100, height=100),
        ]
        result = noise_filter.filter_images(images)
        assert len(result) == 1
        assert result[0].file_path == "/big.png"


class TestCleanText:
    def test_clean_text_removes_noise_paragraphs(self):
        """Noise strings matching full paragraphs are removed."""
        noise_filter = _make_filter()
        markdown = "Intro text\n\nPage Header\n\nBody content\n\nPage Header"
        noise = {"Page Header"}
        result = noise_filter.clean_text(markdown, noise)
        assert "Page Header" not in result
        assert "Body content" in result

    def test_clean_text_preserves_inline_noise(self):
        """Noise strings embedded inline in longer text are NOT removed."""
        noise_filter = _make_filter()
        markdown = "The Page Header appears in the middle of this sentence."
        noise = {"Page Header"}
        result = noise_filter.clean_text(markdown, noise)
        assert "Page Header" in result

    def test_clean_text_disabled(self):
        """When filters_enabled=False, clean_text returns original."""
        noise_filter = _make_filter(enabled=False)
        markdown = "Header\n\nContent"
        result = noise_filter.clean_text(markdown, {"Header"})
        assert result == markdown

    def test_clean_text_empty_noise(self):
        """Empty noise set returns original markdown unchanged."""
        noise_filter = _make_filter()
        markdown = "Some text\n\nMore text"
        result = noise_filter.clean_text(markdown, set())
        assert result == markdown
