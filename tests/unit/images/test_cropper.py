"""Tests for ImageCropper — autocrop, margin, and edge cases."""

import pytest
from PIL import Image, ImageDraw
from scimarkdown.images import ImageCropper


def _white_image_with_black_square() -> Image.Image:
    """Create a 200×200 white image with a 100×100 black square in the centre."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Centre square: columns 50-149, rows 50-149 (100×100 px)
    draw.rectangle([50, 50, 149, 149], fill=(0, 0, 0))
    return img


class TestAutocropWhitespace:
    def test_autocrop_removes_whitespace(self):
        """200×200 white + 100×100 black square at centre → cropped to 100×100."""
        img = _white_image_with_black_square()
        cropper = ImageCropper(margin=0, autocrop=True)
        cropped = cropper.crop(img)
        assert cropped.size == (100, 100)

    def test_autocrop_content_is_black(self):
        """After cropping, the result should be the black square."""
        img = _white_image_with_black_square()
        cropper = ImageCropper(margin=0, autocrop=True)
        cropped = cropper.crop(img)
        # Top-left pixel of the cropped image should be black (0,0,0)
        assert cropped.getpixel((0, 0)) == (0, 0, 0)


class TestAutocropWithMargin:
    def test_margin_adds_padding(self):
        """Same setup with margin=10 → 120×120 (100 + 10*2 on each axis)."""
        img = _white_image_with_black_square()
        cropper = ImageCropper(margin=10, autocrop=True)
        cropped = cropper.crop(img)
        assert cropped.size == (120, 120)

    def test_margin_clamped_at_image_boundary(self):
        """Margin that would exceed image bounds is clamped to the edge."""
        img = Image.new("RGB", (50, 50), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # A small 10×10 square in the centre
        draw.rectangle([20, 20, 29, 29], fill=(0, 0, 0))
        cropper = ImageCropper(margin=100, autocrop=True)
        cropped = cropper.crop(img)
        # Clamped to the full image; should not exceed 50×50
        assert cropped.size[0] <= 50
        assert cropped.size[1] <= 50


class TestNoAutocrop:
    def test_no_autocrop_returns_original_size(self):
        """autocrop=False must return original image without resizing."""
        img = _white_image_with_black_square()
        cropper = ImageCropper(margin=10, autocrop=False)
        result = cropper.crop(img)
        assert result.size == (200, 200)

    def test_no_autocrop_returns_same_object(self):
        """autocrop=False should return the original image object."""
        img = _white_image_with_black_square()
        cropper = ImageCropper(autocrop=False)
        result = cropper.crop(img)
        assert result is img


class TestAllWhiteImage:
    def test_all_white_returns_original(self):
        """A fully white image has nothing to crop → return original."""
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        cropper = ImageCropper(margin=0, autocrop=True)
        result = cropper.crop(img)
        assert result.size == (200, 200)

    def test_all_white_returns_same_object(self):
        """All-white image: the original object is returned unchanged."""
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        cropper = ImageCropper(autocrop=True)
        result = cropper.crop(img)
        assert result is img
