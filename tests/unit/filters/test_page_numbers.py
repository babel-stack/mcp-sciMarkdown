from scimarkdown.filters.page_numbers import PageNumberFilter


class TestPageNumberDetection:
    def test_simple_numbers(self):
        f = PageNumberFilter()
        pages = [
            [{"y": 750.0, "text": "1", "is_boundary": True}],
            [{"y": 750.0, "text": "2", "is_boundary": True}],
            [{"y": 750.0, "text": "3", "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert "1" in noise
        assert "2" in noise
        assert "3" in noise

    def test_dashed_numbers(self):
        f = PageNumberFilter()
        pages = [
            [{"y": 750.0, "text": "- 1 -", "is_boundary": True}],
            [{"y": 750.0, "text": "- 2 -", "is_boundary": True}],
            [{"y": 750.0, "text": "- 3 -", "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert len(noise) == 3

    def test_roman_numerals(self):
        f = PageNumberFilter()
        pages = [
            [{"y": 750.0, "text": "i", "is_boundary": True}],
            [{"y": 750.0, "text": "ii", "is_boundary": True}],
            [{"y": 750.0, "text": "iii", "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert len(noise) == 3

    def test_page_prefix(self):
        f = PageNumberFilter()
        pages = [
            [{"y": 750.0, "text": "pág. 1", "is_boundary": True}],
            [{"y": 750.0, "text": "pág. 2", "is_boundary": True}],
            [{"y": 750.0, "text": "pág. 3", "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert len(noise) == 3

    def test_non_sequential_not_filtered(self):
        """Random numbers that don't form a sequence are not page numbers."""
        f = PageNumberFilter()
        pages = [
            [{"y": 750.0, "text": "42", "is_boundary": True}],
            [{"y": 750.0, "text": "7", "is_boundary": True}],
            [{"y": 750.0, "text": "99", "is_boundary": True}],
        ]
        noise = f.detect(pages)
        assert len(noise) == 0

    def test_non_boundary_not_filtered(self):
        f = PageNumberFilter()
        pages = [
            [{"y": 400.0, "text": "1", "is_boundary": False}],
            [{"y": 400.0, "text": "2", "is_boundary": False}],
            [{"y": 400.0, "text": "3", "is_boundary": False}],
        ]
        noise = f.detect(pages)
        assert len(noise) == 0

    def test_empty_pages(self):
        f = PageNumberFilter()
        assert f.detect([]) == set()
