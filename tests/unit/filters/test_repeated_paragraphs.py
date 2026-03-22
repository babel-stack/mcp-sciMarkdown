"""Tests for markdown-level repeated paragraph removal."""

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.filters.noise_filter import NoiseFilter


class TestCleanRepeatedParagraphs:
    def setup_method(self):
        self.f = NoiseFilter(SciMarkdownConfig())

    def test_removes_repeated_header(self):
        md = "Header\n\nContent 1\n\nHeader\n\nContent 2\n\nHeader\n\nContent 3"
        result = self.f.clean_repeated_paragraphs(md, min_occurrences=3)
        assert result == "Content 1\n\nContent 2\n\nContent 3"

    def test_preserves_unique_paragraphs(self):
        md = "Unique 1\n\nUnique 2\n\nUnique 3"
        result = self.f.clean_repeated_paragraphs(md, min_occurrences=3)
        assert result == md

    def test_preserves_headings_even_if_repeated(self):
        md = "# Chapter 1\n\nText\n\n# Chapter 1\n\nMore\n\n# Chapter 1\n\nEnd"
        result = self.f.clean_repeated_paragraphs(md, min_occurrences=3)
        assert result == md

    def test_preserves_long_paragraphs(self):
        long_para = "A" * 150
        md = f"{long_para}\n\nContent\n\n{long_para}\n\nMore\n\n{long_para}"
        result = self.f.clean_repeated_paragraphs(md, min_occurrences=3)
        assert result == md

    def test_below_threshold_not_removed(self):
        md = "Header\n\nContent 1\n\nHeader\n\nContent 2"
        result = self.f.clean_repeated_paragraphs(md, min_occurrences=3)
        assert md == result

    def test_default_threshold_is_3(self):
        md = "Noise\n\nA\n\nNoise\n\nB\n\nNoise"
        result = self.f.clean_repeated_paragraphs(md)
        assert "Noise" not in result
        assert "A" in result
        assert "B" in result

    def test_real_world_header_footer(self):
        """Simulate the Quevedo book pattern."""
        parts = []
        for i in range(5):
            parts.append("INTRODUCCION A LA MECANICA DE FLUIDOS")
            parts.append(f"Chapter {i} content here.")
            parts.append("CEVALLOS, O., 2022")
        md = "\n\n".join(parts)
        result = self.f.clean_repeated_paragraphs(md, min_occurrences=3)
        assert "INTRODUCCION A LA MECANICA DE FLUIDOS" not in result
        assert "CEVALLOS, O., 2022" not in result
        for i in range(5):
            assert f"Chapter {i} content" in result

    def test_preserves_images(self):
        img = "![fig](image.png)"
        md = f"{img}\n\nText\n\n{img}\n\nMore\n\n{img}"
        result = self.f.clean_repeated_paragraphs(md, min_occurrences=3)
        # Images should be preserved even if repeated
        assert img in result

    def test_empty_input(self):
        assert self.f.clean_repeated_paragraphs("") == ""

    def test_single_paragraph(self):
        assert self.f.clean_repeated_paragraphs("Hello") == "Hello"
