"""Image cropper with automatic whitespace removal."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage


class ImageCropper:
    """Crops images, optionally removing surrounding whitespace.

    Parameters
    ----------
    margin:
        Pixels of padding to re-add around the detected content area.
    autocrop:
        When ``True`` (default) detect background colour from corners and
        crop to the tight bounding box of non-background content, then
        expand by *margin* on each side.
    """

    def __init__(self, margin: int = 10, autocrop: bool = True) -> None:
        self.margin = margin
        self.autocrop = autocrop

    def crop(self, image: "PILImage.Image") -> "PILImage.Image":
        """Return a (possibly) cropped copy of *image*.

        If *autocrop* is ``False`` the original image object is returned
        unchanged.  If the image is all-background (e.g. all-white) the
        original is returned unchanged as well.
        """
        if not self.autocrop:
            return image

        from PIL import Image, ImageChops

        # Work in RGBA so that we can compare uniformly
        img_rgb = image.convert("RGB")

        # Detect background colour from the four corners
        width, height = img_rgb.size
        corners = [
            img_rgb.getpixel((0, 0)),
            img_rgb.getpixel((width - 1, 0)),
            img_rgb.getpixel((0, height - 1)),
            img_rgb.getpixel((width - 1, height - 1)),
        ]
        # Use the most common corner colour as the background
        bg_color = max(set(corners), key=corners.count)

        # Create a solid-background image of the same size for diffing
        bg_image = Image.new("RGB", img_rgb.size, bg_color)

        # Diff: bright pixels = pixels that differ from background
        diff = ImageChops.difference(img_rgb, bg_image)

        # Find bounding box of non-background content
        bbox = diff.getbbox()

        if bbox is None:
            # All pixels match background — all-white (or all-solid) image
            return image

        # Expand bbox by margin, clamped to image boundaries
        left = max(0, bbox[0] - self.margin)
        upper = max(0, bbox[1] - self.margin)
        right = min(width, bbox[2] + self.margin)
        lower = min(height, bbox[3] + self.margin)

        return image.crop((left, upper, right, lower))
