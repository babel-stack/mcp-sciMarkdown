# SciMarkdown — Header/Footer Noise Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Filter out headers, footers, page numbers, and decorative images from document conversions — without removing legitimate content like chapter starts or section titles.

**Architecture:** A new `filters/` module with 3 filters (repeated text, page numbers, decorative images) applied during Phase 2 enrichment. Filters analyze source document structure (not markdown text) using PyMuPDF page-level data. Each filter is independent and configurable.

**Tech Stack:** Python 3.12, PyMuPDF (fitz), Pillow, existing scimarkdown pipeline

**Spec:** Conversation-agreed strategy — detect by repetition patterns, not by zone position.

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `packages/scimarkdown/src/scimarkdown/filters/__init__.py` | Package exports | Create |
| `packages/scimarkdown/src/scimarkdown/filters/repeated_text.py` | Detect text repeated across pages at same position | Create |
| `packages/scimarkdown/src/scimarkdown/filters/page_numbers.py` | Detect isolated page numbers | Create |
| `packages/scimarkdown/src/scimarkdown/filters/decorative_images.py` | Detect decorative/repeated small images | Create |
| `packages/scimarkdown/src/scimarkdown/filters/noise_filter.py` | Orchestrator: runs all 3 filters, cleans markdown | Create |
| `packages/scimarkdown/src/scimarkdown/config.py` | Add filters config section | Modify |
| `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py` | Wire noise filter into pipeline | Modify |
| `tests/unit/filters/__init__.py` | Test package | Create |
| `tests/unit/filters/test_repeated_text.py` | Tests | Create |
| `tests/unit/filters/test_page_numbers.py` | Tests | Create |
| `tests/unit/filters/test_decorative_images.py` | Tests | Create |
| `tests/unit/filters/test_noise_filter.py` | Orchestrator tests | Create |

---

### Task 1: Config extension for filters

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/config.py`
- Modify: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_config.py`:

```python
def test_filters_config_defaults():
    config = SciMarkdownConfig()
    assert config.filters_enabled is True
    assert config.filters_repeated_text is True
    assert config.filters_page_numbers is True
    assert config.filters_decorative_images is True
    assert config.filters_min_repeat_pages == 3
    assert config.filters_max_header_length == 100
    assert config.filters_position_tolerance == 5.0
    assert config.filters_min_image_size == 30
    assert config.filters_max_image_aspect_ratio == 8.0
    assert config.filters_min_image_repeat == 3


def test_filters_config_from_dict():
    config = SciMarkdownConfig.from_dict({
        "filters": {
            "enabled": False,
            "min_repeat_pages": 5,
        }
    })
    assert config.filters_enabled is False
    assert config.filters_min_repeat_pages == 5
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Add filter fields to SciMarkdownConfig**

Add new fields to the dataclass:

```python
    # Filters
    filters_enabled: bool = True
    filters_repeated_text: bool = True
    filters_page_numbers: bool = True
    filters_decorative_images: bool = True
    filters_min_repeat_pages: int = 3       # Pages text must repeat to be considered noise
    filters_max_header_length: int = 100    # Max chars for a header candidate
    filters_position_tolerance: float = 5.0 # Y-coordinate tolerance in points
    filters_min_image_size: int = 30        # Min width/height to keep (px)
    filters_max_image_aspect_ratio: float = 8.0  # Max aspect ratio before flagging as decorative
    filters_min_image_repeat: int = 3       # Pages image must repeat to be filtered
```

Add mapping entries to `_apply_dict`:

```python
            ("filters", "enabled"): "filters_enabled",
            ("filters", "repeated_text"): "filters_repeated_text",
            ("filters", "page_numbers"): "filters_page_numbers",
            ("filters", "decorative_images"): "filters_decorative_images",
            ("filters", "min_repeat_pages"): "filters_min_repeat_pages",
            ("filters", "max_header_length"): "filters_max_header_length",
            ("filters", "position_tolerance"): "filters_position_tolerance",
            ("filters", "min_image_size"): "filters_min_image_size",
            ("filters", "max_image_aspect_ratio"): "filters_max_image_aspect_ratio",
            ("filters", "min_image_repeat"): "filters_min_image_repeat",
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(filters): add noise filter configuration fields"
```

---

### Task 2: Repeated text filter

Detects text that appears at the same Y-coordinate across multiple pages. Only considers first/last text blocks on each page, and only short text (< max_header_length).

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/filters/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/filters/repeated_text.py`
- Create: `tests/unit/filters/__init__.py`
- Create: `tests/unit/filters/test_repeated_text.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/filters/__init__.py` (empty).

Create `tests/unit/filters/test_repeated_text.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement RepeatedTextFilter**

Create `packages/scimarkdown/src/scimarkdown/filters/__init__.py`:

```python
"""Noise filters for removing headers, footers, page numbers, and decorative images."""
```

Create `packages/scimarkdown/src/scimarkdown/filters/repeated_text.py`:

```python
"""Detect repeated header/footer text across pages."""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RepeatedTextFilter:
    """Detects text repeated at the same position across multiple pages.

    Only considers text that is:
    - In a boundary position (first or last block on the page)
    - Short (< max_length characters)
    - Appears at the same Y coordinate (± tolerance) on min_repeat_pages+ pages
    """

    def __init__(
        self,
        min_repeat_pages: int = 3,
        max_length: int = 100,
        y_tolerance: float = 5.0,
    ):
        self.min_repeat_pages = min_repeat_pages
        self.max_length = max_length
        self.y_tolerance = y_tolerance

    def detect(self, pages: list[list[dict]]) -> set[str]:
        """Detect noise text strings.

        Args:
            pages: List of pages, each page is a list of block dicts with
                   keys: "y" (float), "text" (str), "is_boundary" (bool).

        Returns:
            Set of text strings identified as repeated header/footer noise.
        """
        if not pages:
            return set()

        # Collect (text, y_bucket) → count of pages where it appears as boundary
        # y_bucket groups nearby Y coordinates
        occurrences: dict[tuple[str, int], int] = defaultdict(int)

        for page_blocks in pages:
            seen_on_page: set[tuple[str, int]] = set()
            for block in page_blocks:
                if not block.get("is_boundary", False):
                    continue
                text = block["text"].strip()
                if not text or len(text) > self.max_length:
                    continue
                # Bucket Y position by tolerance
                y_bucket = int(block["y"] / self.y_tolerance)
                key = (text, y_bucket)
                if key not in seen_on_page:
                    seen_on_page.add(key)
                    occurrences[key] += 1

        # Texts appearing on enough pages are noise
        noise: set[str] = set()
        for (text, _), count in occurrences.items():
            if count >= self.min_repeat_pages:
                noise.add(text)
                logger.debug("Repeated text noise (%d pages): '%s'", count, text[:50])

        return noise
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(filters): add RepeatedTextFilter for header/footer detection"
```

---

### Task 3: Page number filter

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/filters/page_numbers.py`
- Create: `tests/unit/filters/test_page_numbers.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/filters/test_page_numbers.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement PageNumberFilter**

Create `packages/scimarkdown/src/scimarkdown/filters/page_numbers.py`:

```python
"""Detect page numbers in boundary text blocks."""

import re
import logging

logger = logging.getLogger(__name__)

# Patterns that match page number formats
_PAGE_NUM_PATTERNS = [
    re.compile(r'^\s*[-–—]?\s*(\d{1,4})\s*[-–—]?\s*$'),              # "42", "- 42 -"
    re.compile(r'^[Pp](?:ág|age|ag)?\.?\s*(\d{1,4})$'),               # "pág. 42", "Page 42"
    re.compile(r'^\s*(i{1,4}|vi{0,3}|iv|ix|xi{0,3}|xiv|xv)\s*$'),   # Roman numerals i-xv
]


def _extract_number(text: str) -> int | None:
    """Extract a page number from text, or None if not a page number format."""
    text = text.strip()
    for pattern in _PAGE_NUM_PATTERNS:
        m = pattern.match(text)
        if m:
            val = m.group(1) if m.lastindex else text.strip()
            # Try arabic
            try:
                return int(val)
            except ValueError:
                pass
            # Try roman
            roman_map = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
                         "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
                         "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15}
            if val.lower() in roman_map:
                return roman_map[val.lower()]
    return None


class PageNumberFilter:
    """Detects isolated page numbers in boundary blocks.

    Looks for short numeric text in boundary positions that forms
    a sequential or near-sequential pattern across pages.
    """

    def detect(self, pages: list[list[dict]]) -> set[str]:
        """Detect page number strings.

        Returns set of text strings identified as page numbers.
        """
        if not pages:
            return set()

        # Collect boundary texts with extracted numbers
        candidates: list[tuple[str, int]] = []  # (original_text, extracted_number)

        for page_blocks in pages:
            for block in page_blocks:
                if not block.get("is_boundary", False):
                    continue
                text = block["text"].strip()
                num = _extract_number(text)
                if num is not None:
                    candidates.append((text, num))
                    break  # One page number per page max

        if len(candidates) < 3:
            return set()

        # Check if numbers form a sequential pattern
        numbers = [n for _, n in candidates]
        sequential_count = 0
        for i in range(1, len(numbers)):
            if numbers[i] == numbers[i - 1] + 1:
                sequential_count += 1

        # If at least 60% of transitions are sequential → page numbers
        if sequential_count >= len(numbers) * 0.6:
            noise = {text for text, _ in candidates}
            logger.debug("Detected %d page numbers", len(noise))
            return noise

        return set()
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(filters): add PageNumberFilter for sequential page number detection"
```

---

### Task 4: Decorative image filter

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/filters/decorative_images.py`
- Create: `tests/unit/filters/test_decorative_images.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/filters/test_decorative_images.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement DecorativeImageFilter**

Create `packages/scimarkdown/src/scimarkdown/filters/decorative_images.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(filters): add DecorativeImageFilter for small/narrow/repeated images"
```

---

### Task 5: NoiseFilter orchestrator

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/filters/noise_filter.py`
- Create: `tests/unit/filters/test_noise_filter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/filters/test_noise_filter.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement NoiseFilter**

Create `packages/scimarkdown/src/scimarkdown/filters/noise_filter.py`:

```python
"""Orchestrator for noise filters — cleans markdown of headers, footers, page numbers."""

import io
import logging
from typing import IO, Optional

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import ImageRef
from .repeated_text import RepeatedTextFilter
from .page_numbers import PageNumberFilter
from .decorative_images import DecorativeImageFilter

logger = logging.getLogger(__name__)


class NoiseFilter:
    """Orchestrates all noise filters and applies them to markdown text and images."""

    def __init__(self, config: SciMarkdownConfig):
        self.config = config
        self.repeated_filter = RepeatedTextFilter(
            min_repeat_pages=config.filters_min_repeat_pages,
            max_length=config.filters_max_header_length,
            y_tolerance=config.filters_position_tolerance,
        )
        self.page_number_filter = PageNumberFilter()
        self.decorative_filter = DecorativeImageFilter(
            min_size=config.filters_min_image_size,
            max_aspect_ratio=config.filters_max_image_aspect_ratio,
            min_repeat=config.filters_min_image_repeat,
        )

    def extract_page_blocks(self, stream: IO[bytes], file_extension: str) -> list[list[dict]]:
        """Extract per-page text blocks from a document for noise analysis.

        Currently supports PDF via PyMuPDF.
        Returns list of pages, each page a list of block dicts.
        """
        if file_extension.lower() != ".pdf":
            return []

        try:
            import fitz
        except ImportError:
            return []

        pages: list[list[dict]] = []
        data = stream.read()
        stream.seek(0)

        try:
            doc = fitz.open(stream=data, filetype="pdf")
            for page in doc:
                blocks = page.get_text("blocks")
                # blocks: (x0, y0, x1, y1, text, block_no, block_type)
                text_blocks = [
                    (b[1], b[4].strip())  # (y0, text)
                    for b in blocks if b[6] == 0 and b[4].strip()
                ]
                text_blocks.sort(key=lambda t: t[0])

                page_data: list[dict] = []
                for idx, (y, text) in enumerate(text_blocks):
                    is_boundary = (idx == 0) or (idx == len(text_blocks) - 1)
                    page_data.append({
                        "y": y,
                        "text": text,
                        "is_boundary": is_boundary,
                    })
                pages.append(page_data)
            doc.close()
        except Exception as e:
            logger.warning("Failed to extract page blocks: %s", e)

        return pages

    def detect_noise(self, pages: list[list[dict]]) -> set[str]:
        """Run text noise detection filters and return set of noise strings."""
        if not self.config.filters_enabled:
            return set()

        noise: set[str] = set()

        if self.config.filters_repeated_text:
            noise |= self.repeated_filter.detect(pages)

        if self.config.filters_page_numbers:
            noise |= self.page_number_filter.detect(pages)

        return noise

    def filter_images(self, images: list[ImageRef]) -> list[ImageRef]:
        """Filter decorative images."""
        if not self.config.filters_enabled or not self.config.filters_decorative_images:
            return images
        return self.decorative_filter.filter(images)

    def clean_text(self, markdown: str, noise_strings: set[str]) -> str:
        """Remove noise strings from markdown.

        Only removes noise that appears as a standalone paragraph
        (entire paragraph matches noise). Does NOT remove noise
        that appears inline within a longer sentence.
        """
        if not self.config.filters_enabled or not noise_strings:
            return markdown

        paragraphs = markdown.split("\n\n")
        cleaned: list[str] = []

        for para in paragraphs:
            stripped = para.strip()
            if stripped in noise_strings:
                logger.debug("Removed noise paragraph: '%s'", stripped[:50])
                continue
            cleaned.append(para)

        return "\n\n".join(cleaned)
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Update `__init__.py` exports**

```python
"""Noise filters for removing headers, footers, page numbers, and decorative images."""

from .noise_filter import NoiseFilter
from .repeated_text import RepeatedTextFilter
from .page_numbers import PageNumberFilter
from .decorative_images import DecorativeImageFilter

__all__ = ["NoiseFilter", "RepeatedTextFilter", "PageNumberFilter", "DecorativeImageFilter"]
```

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(filters): add NoiseFilter orchestrator for text and image cleaning"
```

---

### Task 6: Wire filters into enrichment pipeline

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py`
- Create: `tests/unit/pipeline/test_enrichment_filters.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/pipeline/test_enrichment_filters.py`:

```python
import io
from pathlib import Path
from scimarkdown.pipeline.enrichment import EnrichmentPipeline
from scimarkdown.config import SciMarkdownConfig


def test_filters_clean_repeated_text():
    config = SciMarkdownConfig(filters_enabled=True)
    pipeline = EnrichmentPipeline(config)
    # Simulate markdown with noise
    md = "Book Title\n\nReal content paragraph.\n\nBook Title\n\n42"
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    # For non-PDF, no page blocks → no noise detected via page analysis
    # But the filter infrastructure should be wired
    assert result.base_markdown is not None


def test_filters_disabled():
    config = SciMarkdownConfig(filters_enabled=False)
    pipeline = EnrichmentPipeline(config)
    md = "Header\n\nContent\n\n42"
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    # With filters disabled, markdown unchanged
    assert "Header" in result.base_markdown
    assert "42" in result.base_markdown
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Wire NoiseFilter into enrichment**

In `enrichment.py`, after image extraction and before reference linking, add:

```python
        # ---------------------------------------------------------------
        # Noise filtering (headers, footers, page numbers, decorative images)
        # ---------------------------------------------------------------
        if self.config.filters_enabled:
            try:
                from scimarkdown.filters.noise_filter import NoiseFilter
                noise_filter = NoiseFilter(self.config)

                # Extract page blocks for text noise detection (PDF only)
                source_stream.seek(0)
                page_blocks = noise_filter.extract_page_blocks(source_stream, file_extension)
                source_stream.seek(0)

                if page_blocks:
                    noise_strings = noise_filter.detect_noise(page_blocks)
                    if noise_strings:
                        base_markdown = noise_filter.clean_text(base_markdown, noise_strings)
                        result.base_markdown = base_markdown
                        logger.info("Removed %d noise strings", len(noise_strings))

                # Filter decorative images
                if images:
                    images = noise_filter.filter_images(images)
                    logger.info("After decorative filter: %d images", len(images))

            except Exception as e:
                logger.warning("Noise filtering failed: %s", e)
```

- [ ] **Step 4: Run all tests**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/ --ignore=tests/upstream -q`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(filters): wire noise filters into enrichment pipeline"
```

---

## Dependency Graph

```
Task 1 (config) ─────────────────────┐
                                      ▼
Task 2 (repeated text) ──→ Task 5 (orchestrator) ──→ Task 6 (pipeline)
Task 3 (page numbers) ───┘              │
Task 4 (decorative images) ─────────────┘
```

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | Config | 10 new filter config fields |
| 2 | RepeatedTextFilter | Detect text repeated across pages at same Y |
| 3 | PageNumberFilter | Detect sequential page numbers in boundary blocks |
| 4 | DecorativeImageFilter | Filter small, narrow, or repeated images |
| 5 | NoiseFilter | Orchestrator: extract page blocks, run filters, clean text |
| 6 | Pipeline wiring | Integrate into enrichment phase |

**Total: 6 tasks, ~30 steps, 6 commits.**
