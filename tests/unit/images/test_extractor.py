"""Tests for ImageExtractor — naming, sanitization, and counter behaviour."""

import pytest
from pathlib import Path
from scimarkdown.config import SciMarkdownConfig
from scimarkdown.images import ImageExtractor


def _make_extractor(doc_name: str = "test_doc", output_dir: Path | None = None) -> ImageExtractor:
    config = SciMarkdownConfig()
    out = output_dir or Path("/tmp/scimarkdown_test_images")
    return ImageExtractor(config=config, document_name=doc_name, output_dir=out)


class TestNamingConvention:
    def test_naming_five_digits_zero_padded(self):
        extractor = _make_extractor("report")
        filename = extractor._make_filename(1)
        assert filename == "report_img00001.png"

    def test_naming_five_digits_max_value(self):
        extractor = _make_extractor("report")
        filename = extractor._make_filename(99999)
        assert filename == "report_img99999.png"

    def test_naming_with_custom_extension(self):
        extractor = _make_extractor("doc")
        filename = extractor._make_filename(3, ext="jpg")
        assert filename == "doc_img00003.jpg"

    def test_naming_middle_number(self):
        extractor = _make_extractor("paper")
        filename = extractor._make_filename(42)
        assert filename == "paper_img00042.png"


class TestNamingOverflow:
    def test_overflow_six_digits(self):
        """Numbers > 99999 should extend beyond 5 digits."""
        extractor = _make_extractor("report")
        filename = extractor._make_filename(100000)
        assert filename == "report_img100000.png"

    def test_overflow_large_number(self):
        extractor = _make_extractor("report")
        filename = extractor._make_filename(1234567)
        assert filename == "report_img1234567.png"

    def test_overflow_boundary(self):
        extractor = _make_extractor("doc")
        filename = extractor._make_filename(99999)
        assert filename == "doc_img99999.png"
        filename2 = extractor._make_filename(100000)
        assert filename2 == "doc_img100000.png"


class TestSanitizeDocumentName:
    def test_extension_removed(self):
        extractor = _make_extractor("report.pdf")
        assert extractor.document_name == "report"

    def test_spaces_replaced_with_underscores(self):
        extractor = _make_extractor("my report.pdf")
        assert extractor.document_name == "my_report"

    def test_special_chars_replaced_with_underscores(self):
        extractor = _make_extractor("report-2024 (v2).pdf")
        assert extractor.document_name == "report_2024__v2_"

    def test_alphanumeric_unchanged(self):
        extractor = _make_extractor("MyDocument123")
        assert extractor.document_name == "MyDocument123"

    def test_dots_in_stem_replaced(self):
        extractor = _make_extractor("my.report.v2.pdf")
        assert extractor.document_name == "my_report_v2"

    def test_hyphens_replaced(self):
        extractor = _make_extractor("annual-report-2024.docx")
        assert extractor.document_name == "annual_report_2024"


class TestCounterStartsAtZero:
    def test_counter_starts_at_zero(self):
        extractor = _make_extractor("doc")
        assert extractor._counter == 0

    def test_first_next_filename_is_one(self):
        extractor = _make_extractor("doc")
        filename = extractor._next_filename()
        assert filename == "doc_img00001.png"
        assert extractor._counter == 1

    def test_counter_increments_sequentially(self):
        extractor = _make_extractor("doc")
        f1 = extractor._next_filename()
        f2 = extractor._next_filename()
        f3 = extractor._next_filename()
        assert f1 == "doc_img00001.png"
        assert f2 == "doc_img00002.png"
        assert f3 == "doc_img00003.png"

    def test_counter_independent_per_instance(self):
        e1 = _make_extractor("doc1")
        e2 = _make_extractor("doc2")
        e1._next_filename()
        e1._next_filename()
        assert e2._counter == 0
        f = e2._next_filename()
        assert f == "doc2_img00001.png"
