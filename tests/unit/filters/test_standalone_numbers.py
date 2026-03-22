"""Tests for NoiseFilter.clean_standalone_numbers — standalone page number removal."""

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.filters.noise_filter import NoiseFilter


class TestCleanStandaloneNumbers:
    def setup_method(self):
        self.f = NoiseFilter(SciMarkdownConfig())

    # --- Should be removed ---

    def test_single_digit_removed(self):
        result = self.f.clean_standalone_numbers("5")
        assert result == ""

    def test_two_digit_number_removed(self):
        result = self.f.clean_standalone_numbers("75")
        assert result == ""

    def test_three_digit_number_removed(self):
        result = self.f.clean_standalone_numbers("541")
        assert result == ""

    def test_four_digit_number_removed(self):
        result = self.f.clean_standalone_numbers("1024")
        assert result == ""

    def test_number_with_surrounding_whitespace_removed(self):
        result = self.f.clean_standalone_numbers("\n75\n")
        assert "75" not in result.strip()

    def test_roman_numeral_lowercase_removed(self):
        result = self.f.clean_standalone_numbers("ix")
        assert result == ""

    def test_roman_numeral_uppercase_removed(self):
        result = self.f.clean_standalone_numbers("XIV")
        assert result == ""

    def test_roman_numeral_i_removed(self):
        result = self.f.clean_standalone_numbers("i")
        assert result == ""

    def test_roman_numeral_ii_removed(self):
        result = self.f.clean_standalone_numbers("ii")
        assert result == ""

    def test_roman_numeral_xv_removed(self):
        result = self.f.clean_standalone_numbers("xv")
        assert result == ""

    # --- Should NOT be removed ---

    def test_sentence_with_number_kept(self):
        result = self.f.clean_standalone_numbers("The answer is 75")
        assert "The answer is 75" in result

    def test_content_paragraph_kept(self):
        text = "Content paragraph with real text."
        result = self.f.clean_standalone_numbers(text)
        assert result == text

    def test_five_digit_number_kept(self):
        """5-digit numbers are not page numbers; keep them."""
        text = "12345"
        result = self.f.clean_standalone_numbers(text)
        assert "12345" in result

    def test_heading_kept(self):
        text = "# Chapter heading"
        result = self.f.clean_standalone_numbers(text)
        assert "# Chapter heading" in result

    # --- Multi-paragraph documents ---

    def test_standalone_number_in_document_removed(self):
        md = "First paragraph.\n\n75\n\nSecond paragraph."
        result = self.f.clean_standalone_numbers(md)
        assert "First paragraph." in result
        assert "75" not in result
        assert "Second paragraph." in result

    def test_multiple_standalone_numbers_removed(self):
        md = "Intro\n\n1\n\nContent.\n\n541\n\nConclusion."
        result = self.f.clean_standalone_numbers(md)
        assert "Intro" in result
        assert "\n\n1\n\n" not in result
        assert "\n\n541\n\n" not in result
        assert "Content." in result
        assert "Conclusion." in result

    def test_roman_in_document_removed(self):
        md = "Preface text.\n\nix\n\nChapter 1 text."
        result = self.f.clean_standalone_numbers(md)
        assert "Preface text." in result
        assert "\n\nix\n\n" not in result
        assert "Chapter 1 text." in result

    def test_empty_string(self):
        result = self.f.clean_standalone_numbers("")
        assert result == ""

    def test_no_standalone_numbers_unchanged(self):
        md = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = self.f.clean_standalone_numbers(md)
        assert result == md
