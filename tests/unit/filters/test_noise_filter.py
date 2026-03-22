from scimarkdown.config import SciMarkdownConfig
from scimarkdown.filters.noise_filter import NoiseFilter


class TestNoiseFilter:
    def test_clean_text_removes_noise(self):
        f = NoiseFilter(SciMarkdownConfig())
        noise_strings = {"My Book Title", "42"}
        text = "My Book Title\n\nFirst paragraph of content.\n\n42\n\nSecond paragraph."
        cleaned = f.clean_text(text, noise_strings)
        assert "My Book Title" not in cleaned
        assert "42" not in cleaned
        assert "First paragraph" in cleaned
        assert "Second paragraph" in cleaned

    def test_clean_text_no_noise(self):
        f = NoiseFilter(SciMarkdownConfig())
        text = "Normal content here."
        cleaned = f.clean_text(text, set())
        assert cleaned == "Normal content here."

    def test_clean_text_preserves_inline_numbers(self):
        """Number '42' in a sentence should NOT be removed."""
        f = NoiseFilter(SciMarkdownConfig())
        noise_strings = {"42"}
        text = "The answer is 42 according to the book.\n\n42\n\nMore content."
        cleaned = f.clean_text(text, noise_strings)
        # The standalone "42" paragraph should be removed
        # But "The answer is 42" should be kept
        assert "The answer is 42" in cleaned

    def test_disabled_returns_unchanged(self):
        config = SciMarkdownConfig(filters_enabled=False)
        f = NoiseFilter(config)
        text = "Header\n\nContent\n\n42"
        cleaned = f.clean_text(text, {"Header", "42"})
        assert cleaned == text

    def test_extract_page_blocks_from_pdf_data(self):
        """Test the page block extraction helper."""
        f = NoiseFilter(SciMarkdownConfig())
        # This tests the interface; actual PDF parsing is integration-level
        assert hasattr(f, 'extract_page_blocks')
