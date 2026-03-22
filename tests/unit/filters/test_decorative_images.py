import hashlib
from scimarkdown.models import ImageRef
from scimarkdown.filters.decorative_images import DecorativeImageFilter


def _img(file_path="img.png", width=100, height=100, content_hash=None):
    ref = ImageRef(position=0, file_path=file_path, original_format="png",
                   width=width, height=height)
    ref._content_hash = content_hash or hashlib.md5(file_path.encode()).hexdigest()
    return ref


class TestDecorativeImageDetection:
    def test_very_small_image_filtered(self):
        f = DecorativeImageFilter(min_size=30, max_aspect_ratio=8.0, min_repeat=3)
        images = [_img(width=20, height=20)]
        filtered = f.filter(images)
        assert len(filtered) == 0

    def test_normal_image_kept(self):
        f = DecorativeImageFilter(min_size=30, max_aspect_ratio=8.0, min_repeat=3)
        images = [_img(width=200, height=150)]
        filtered = f.filter(images)
        assert len(filtered) == 1

    def test_extreme_aspect_ratio_filtered(self):
        """Very narrow image (like a line separator)."""
        f = DecorativeImageFilter(min_size=30, max_aspect_ratio=8.0, min_repeat=3)
        images = [_img(width=500, height=5)]  # Ratio 100:1
        filtered = f.filter(images)
        assert len(filtered) == 0

    def test_repeated_image_filtered(self):
        """Same image (by hash) appearing 3+ times → decorative."""
        f = DecorativeImageFilter(min_size=30, max_aspect_ratio=8.0, min_repeat=3)
        same_hash = "abc123"
        images = [
            _img(file_path="p1.png", content_hash=same_hash),
            _img(file_path="p2.png", content_hash=same_hash),
            _img(file_path="p3.png", content_hash=same_hash),
        ]
        filtered = f.filter(images)
        assert len(filtered) == 0

    def test_unique_images_kept(self):
        f = DecorativeImageFilter(min_size=30, max_aspect_ratio=8.0, min_repeat=3)
        images = [
            _img(file_path="a.png", content_hash="hash_a"),
            _img(file_path="b.png", content_hash="hash_b"),
            _img(file_path="c.png", content_hash="hash_c"),
        ]
        filtered = f.filter(images)
        assert len(filtered) == 3

    def test_mixed_keeps_only_valid(self):
        f = DecorativeImageFilter(min_size=30, max_aspect_ratio=8.0, min_repeat=3)
        images = [
            _img(file_path="good.png", width=200, height=150, content_hash="unique1"),
            _img(file_path="tiny.png", width=10, height=10, content_hash="unique2"),
            _img(file_path="line.png", width=400, height=2, content_hash="unique3"),
        ]
        filtered = f.filter(images)
        assert len(filtered) == 1
        assert filtered[0].file_path == "good.png"

    def test_empty_input(self):
        f = DecorativeImageFilter(min_size=30, max_aspect_ratio=8.0, min_repeat=3)
        assert f.filter([]) == []
