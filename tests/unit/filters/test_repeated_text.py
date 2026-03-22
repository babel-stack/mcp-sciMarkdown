from scimarkdown.filters.repeated_text import RepeatedTextFilter


def _make_page_blocks(texts_with_positions):
    """Create mock page block data.

    Each item: (y_position, text, is_first_or_last_block)
    Returns list of dicts matching the format RepeatedTextFilter expects.
    """
    return [
        {"y": y, "text": text, "is_boundary": is_boundary}
        for y, text, is_boundary in texts_with_positions
    ]


class TestRepeatedTextDetection:
    def test_detect_repeated_header(self):
        """Same text at same Y on 3+ pages → noise."""
        f = RepeatedTextFilter(min_repeat_pages=3, max_length=100, y_tolerance=5.0)
        pages = [
            # Each page has: boundary blocks (first/last) with positions
            [{"y": 50.0, "text": "My Book Title", "is_boundary": True},
             {"y": 400.0, "text": "Content paragraph page 1 with real text.", "is_boundary": False},
             {"y": 750.0, "text": "42", "is_boundary": True}],
            [{"y": 50.0, "text": "My Book Title", "is_boundary": True},
             {"y": 400.0, "text": "Content paragraph page 2 is different.", "is_boundary": False},
             {"y": 750.0, "text": "43", "is_boundary": True}],
            [{"y": 50.0, "text": "My Book Title", "is_boundary": True},
             {"y": 400.0, "text": "Content paragraph page 3 another text.", "is_boundary": False},
             {"y": 750.0, "text": "44", "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert "My Book Title" in noise

    def test_non_repeated_text_not_filtered(self):
        """Text appearing only once is not noise."""
        f = RepeatedTextFilter(min_repeat_pages=3, max_length=100, y_tolerance=5.0)
        pages = [
            [{"y": 50.0, "text": "Chapter 1: Introduction", "is_boundary": True},
             {"y": 400.0, "text": "Some content.", "is_boundary": False}],
            [{"y": 50.0, "text": "Chapter 2: Methods", "is_boundary": True},
             {"y": 400.0, "text": "Different content.", "is_boundary": False}],
            [{"y": 50.0, "text": "Chapter 3: Results", "is_boundary": True},
             {"y": 400.0, "text": "More content.", "is_boundary": False}],
        ]
        noise = f.detect(pages)
        assert "Chapter 1: Introduction" not in noise
        assert "Chapter 2: Methods" not in noise

    def test_long_text_not_filtered(self):
        """Text longer than max_length is never header noise."""
        f = RepeatedTextFilter(min_repeat_pages=3, max_length=50, y_tolerance=5.0)
        long_text = "A" * 60  # 60 chars > max 50
        pages = [
            [{"y": 50.0, "text": long_text, "is_boundary": True}],
            [{"y": 50.0, "text": long_text, "is_boundary": True}],
            [{"y": 50.0, "text": long_text, "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert long_text not in noise

    def test_non_boundary_text_not_filtered(self):
        """Text in the middle of the page is not a header candidate."""
        f = RepeatedTextFilter(min_repeat_pages=3, max_length=100, y_tolerance=5.0)
        pages = [
            [{"y": 400.0, "text": "Repeated middle", "is_boundary": False}],
            [{"y": 400.0, "text": "Repeated middle", "is_boundary": False}],
            [{"y": 400.0, "text": "Repeated middle", "is_boundary": False}],
        ]
        noise = f.detect(pages)
        assert "Repeated middle" not in noise

    def test_y_tolerance(self):
        """Text at slightly different Y positions (within tolerance) is still detected."""
        f = RepeatedTextFilter(min_repeat_pages=3, max_length=100, y_tolerance=5.0)
        pages = [
            [{"y": 50.0, "text": "Header", "is_boundary": True}],
            [{"y": 52.0, "text": "Header", "is_boundary": True}],
            [{"y": 48.5, "text": "Header", "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert "Header" in noise

    def test_alternating_headers_both_detected(self):
        """Even/odd page headers (e.g. author on even, title on odd)."""
        f = RepeatedTextFilter(min_repeat_pages=3, max_length=100, y_tolerance=5.0)
        pages = [
            [{"y": 50.0, "text": "Author Name", "is_boundary": True}],    # page 1
            [{"y": 50.0, "text": "Book Title", "is_boundary": True}],     # page 2
            [{"y": 50.0, "text": "Author Name", "is_boundary": True}],    # page 3
            [{"y": 50.0, "text": "Book Title", "is_boundary": True}],     # page 4
            [{"y": 50.0, "text": "Author Name", "is_boundary": True}],    # page 5
            [{"y": 50.0, "text": "Book Title", "is_boundary": True}],     # page 6
        ]
        noise = f.detect(pages)
        assert "Author Name" in noise
        assert "Book Title" in noise

    def test_empty_pages(self):
        f = RepeatedTextFilter(min_repeat_pages=3, max_length=100, y_tolerance=5.0)
        assert f.detect([]) == set()
        assert f.detect([[], [], []]) == set()
