"""Filter decorative images: too small, extreme aspect ratio, or repeated."""

import logging
from collections import Counter

from scimarkdown.models import ImageRef

logger = logging.getLogger(__name__)


class DecorativeImageFilter:
    """Filters out decorative images based on size, aspect ratio, and repetition.

    An image is decorative if ANY of these are true:
    - Width OR height < min_size (too small — icon/bullet)
    - Aspect ratio > max_aspect_ratio (too narrow — line separator)
    - Same content hash appears min_repeat+ times (logo/watermark)
    """

    def __init__(
        self,
        min_size: int = 30,
        max_aspect_ratio: float = 8.0,
        min_repeat: int = 3,
    ):
        self.min_size = min_size
        self.max_aspect_ratio = max_aspect_ratio
        self.min_repeat = min_repeat

    def filter(self, images: list[ImageRef]) -> list[ImageRef]:
        """Return images that are NOT decorative."""
        if not images:
            return []

        # Find repeated image hashes
        hash_counts: Counter[str] = Counter()
        for img in images:
            h = getattr(img, "_content_hash", None)
            if h:
                hash_counts[h] += 1

        repeated_hashes = {h for h, c in hash_counts.items() if c >= self.min_repeat}

        result: list[ImageRef] = []
        for img in images:
            # Check size
            if img.width > 0 and img.width < self.min_size:
                logger.debug("Filtered small image: %s (%dx%d)", img.file_path, img.width, img.height)
                continue
            if img.height > 0 and img.height < self.min_size:
                logger.debug("Filtered small image: %s (%dx%d)", img.file_path, img.width, img.height)
                continue

            # Check aspect ratio
            if img.width > 0 and img.height > 0:
                ratio = max(img.width / img.height, img.height / img.width)
                if ratio > self.max_aspect_ratio:
                    logger.debug("Filtered line image: %s (ratio %.1f)", img.file_path, ratio)
                    continue

            # Check repetition
            h = getattr(img, "_content_hash", None)
            if h and h in repeated_hashes:
                logger.debug("Filtered repeated image: %s (hash %s)", img.file_path, h[:8])
                continue

            result.append(img)

        return result
