# SciMarkdown — Table of Contents Hyperlinks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect book/document table of contents, clean up filler characters and page numbers, and convert TOC entries into markdown hyperlinks that point to the actual sections within the document.

**Architecture:** A new `filters/toc_processor.py` module that: (1) detects TOC regions in markdown using pattern matching, (2) parses entries into title + page number, (3) generates slug anchors matching markdown heading conventions, (4) replaces TOC entries with `[Title](#slug)` links, and (5) ensures headings in the document body have matching anchor IDs.

**Tech Stack:** Python 3.12, regex, existing scimarkdown pipeline

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `packages/scimarkdown/src/scimarkdown/filters/toc_processor.py` | TOC detection, parsing, and hyperlink generation | Create |
| `packages/scimarkdown/src/scimarkdown/filters/__init__.py` | Add TocProcessor export | Modify |
| `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py` | Wire TocProcessor into pipeline | Modify |
| `tests/unit/filters/test_toc_processor.py` | Full test suite | Create |

---

### Task 1: TOC entry parser

Parse individual TOC lines into (title, page_number) pairs. Handles multiple filler styles.

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/filters/toc_processor.py`
- Create: `tests/unit/filters/test_toc_processor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/filters/test_toc_processor.py`:

```python
from scimarkdown.filters.toc_processor import TocProcessor


class TestParseTocEntry:
    """Test parsing individual TOC lines into (title, page_number)."""

    def test_dots_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 1: Introduction ......... 15")
        assert title == "Chapter 1: Introduction"
        assert page == 15

    def test_spaces_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 2: Methods                    23")
        assert title == "Chapter 2: Methods"
        assert page == 23

    def test_dashes_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 3: Results ----------- 45")
        assert title == "Chapter 3: Results"
        assert page == 45

    def test_underscores_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 4: Discussion _______ 67")
        assert title == "Chapter 4: Discussion"
        assert page == 67

    def test_no_filler_just_spaces(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Appendix A   89")
        assert title == "Appendix A"
        assert page == 89

    def test_roman_numeral_page(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Preface ......... iii")
        assert title == "Preface"
        assert page == "iii"

    def test_section_numbering(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("  3.2.1 Experimental Setup .... 112")
        assert title == "3.2.1 Experimental Setup"
        assert page == 112

    def test_spanish_toc(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Capítulo 5: Conclusiones ......... 89")
        assert title == "Capítulo 5: Conclusiones"
        assert page == 89

    def test_not_a_toc_entry(self):
        proc = TocProcessor()
        result = proc.parse_entry("This is a normal paragraph without page numbers.")
        assert result is None

    def test_not_a_toc_number_in_middle(self):
        proc = TocProcessor()
        result = proc.parse_entry("In equation 42 we see the result clearly.")
        assert result is None

    def test_indented_subentry(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("    2.1 Background .... 18")
        assert title == "2.1 Background"
        assert page == 18
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/filters/test_toc_processor.py::TestParseTocEntry -v`

- [ ] **Step 3: Implement parse_entry**

Create `packages/scimarkdown/src/scimarkdown/filters/toc_processor.py`:

```python
"""Table of Contents processor: detect, parse, and convert TOC entries to hyperlinks."""

import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Filler patterns between title and page number
_FILLER_PATTERN = re.compile(
    r'^'
    r'(?P<title>.+?)'           # Title (non-greedy)
    r'\s*'                       # Optional space before filler
    r'[.\-–—_\s]{3,}'           # Filler: 3+ dots, dashes, underscores, or spaces
    r'\s*'                       # Optional space after filler
    r'(?P<page>\d{1,4}|[ivxlc]{1,10})' # Page number (arabic or roman)
    r'\s*$'                      # End of line
)

# Simpler pattern: title followed by spaces and a number at end of line
_SPACES_PATTERN = re.compile(
    r'^'
    r'(?P<title>.+\S)'          # Title ending in non-space
    r'\s{3,}'                   # 3+ spaces
    r'(?P<page>\d{1,4}|[ivxlc]{1,10})' # Page number
    r'\s*$'
)

_ROMAN_NUMERALS = {
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxx", "xl", "l",
}


@dataclass
class TocEntry:
    """A parsed table of contents entry."""
    title: str
    page: int | str  # int for arabic, str for roman
    indent_level: int = 0
    slug: str = ""


class TocProcessor:
    """Detects and processes table of contents in markdown.

    Converts TOC entries from:
        Chapter 1: Introduction ......... 15
    To:
        [Chapter 1: Introduction](#chapter-1-introduction)
    """

    def parse_entry(self, line: str) -> Optional[tuple[str, int | str]]:
        """Parse a single line as a TOC entry.

        Returns (title, page_number) or None if not a TOC entry.
        """
        stripped = line.strip()
        if not stripped or len(stripped) < 5:
            return None

        # Try filler pattern first (dots, dashes, etc.)
        m = _FILLER_PATTERN.match(stripped)
        if not m:
            m = _SPACES_PATTERN.match(stripped)
        if not m:
            return None

        title = m.group("title").strip()
        page_str = m.group("page").strip()

        # Validate title: must have at least 2 non-digit chars
        alpha_chars = sum(1 for c in title if c.isalpha())
        if alpha_chars < 2:
            return None

        # Parse page number
        if page_str.lower() in _ROMAN_NUMERALS:
            return title, page_str
        try:
            return title, int(page_str)
        except ValueError:
            return None

    def generate_slug(self, title: str) -> str:
        """Generate a markdown-compatible anchor slug from a title.

        Follows GitHub-flavored markdown anchor generation:
        - Lowercase
        - Replace spaces with hyphens
        - Remove non-alphanumeric chars (except hyphens)
        - Strip leading/trailing hyphens
        """
        slug = title.lower()
        # Remove section numbers at the start (e.g., "3.2.1 ")
        slug = re.sub(r'^\d+(?:\.\d+)*\s+', '', slug)
        # Replace spaces and special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        slug = slug.strip('-')
        return slug

    def detect_toc_region(self, markdown: str) -> Optional[tuple[int, int]]:
        """Detect the start and end positions of a TOC region in markdown.

        A TOC region is a sequence of 3+ consecutive lines that parse as TOC entries.
        Returns (start_line_index, end_line_index) or None.
        """
        lines = markdown.split('\n')
        consecutive = 0
        start = -1

        regions: list[tuple[int, int]] = []

        for i, line in enumerate(lines):
            if self.parse_entry(line) is not None:
                if consecutive == 0:
                    start = i
                consecutive += 1
            else:
                if consecutive >= 3:
                    regions.append((start, i))
                consecutive = 0
                start = -1

        # Handle TOC at end of document
        if consecutive >= 3:
            regions.append((start, len(lines)))

        # Return the largest region (likely the main TOC)
        if regions:
            return max(regions, key=lambda r: r[1] - r[0])
        return None

    def process(self, markdown: str) -> str:
        """Process markdown: detect TOC, convert entries to hyperlinks.

        Returns the modified markdown with TOC entries as links.
        """
        region = self.detect_toc_region(markdown)
        if region is None:
            return markdown

        lines = markdown.split('\n')
        start, end = region

        # Parse all entries in the TOC region
        entries: list[TocEntry] = []
        for i in range(start, end):
            result = self.parse_entry(lines[i])
            if result:
                title, page = result
                indent = len(lines[i]) - len(lines[i].lstrip())
                slug = self.generate_slug(title)
                entries.append(TocEntry(
                    title=title, page=page,
                    indent_level=indent, slug=slug,
                ))

        if not entries:
            return markdown

        # Replace TOC lines with hyperlinks
        new_lines = list(lines)
        entry_idx = 0
        for i in range(start, end):
            if self.parse_entry(lines[i]) is not None and entry_idx < len(entries):
                entry = entries[entry_idx]
                indent = "  " * (entry.indent_level // 2)
                new_lines[i] = f"{indent}- [{entry.title}](#{entry.slug})"
                entry_idx += 1

        # Ensure headings in the body have matching anchors
        # Markdown renderers auto-generate anchors from heading text,
        # so we just need to verify headings exist. No modification needed
        # if the document uses standard markdown headings.

        return '\n'.join(new_lines)
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(filters): add TocProcessor — parse TOC entries with filler detection"
```

---

### Task 2: TOC region detection and slug generation

**Files:**
- Modify: `tests/unit/filters/test_toc_processor.py`

- [ ] **Step 1: Write tests for slug generation and region detection**

Add to `tests/unit/filters/test_toc_processor.py`:

```python
class TestGenerateSlug:
    def test_simple_title(self):
        proc = TocProcessor()
        assert proc.generate_slug("Introduction") == "introduction"

    def test_title_with_spaces(self):
        proc = TocProcessor()
        assert proc.generate_slug("Chapter 1: Introduction") == "chapter-1-introduction"

    def test_title_with_accents(self):
        proc = TocProcessor()
        slug = proc.generate_slug("Capítulo 5: Conclusiones")
        assert "capítulo" in slug or "capitulo" in slug

    def test_section_number_stripped(self):
        proc = TocProcessor()
        assert proc.generate_slug("3.2.1 Experimental Setup") == "experimental-setup"

    def test_special_chars_removed(self):
        proc = TocProcessor()
        slug = proc.generate_slug("Results & Discussion (Final)")
        assert "&" not in slug
        assert "(" not in slug


class TestDetectTocRegion:
    def test_detect_simple_toc(self):
        proc = TocProcessor()
        md = (
            "# Table of Contents\n"
            "\n"
            "Chapter 1 ......... 1\n"
            "Chapter 2 ......... 15\n"
            "Chapter 3 ......... 30\n"
            "Chapter 4 ......... 45\n"
            "\n"
            "# Chapter 1\n"
            "\n"
            "Content starts here."
        )
        region = proc.detect_toc_region(md)
        assert region is not None
        start, end = region
        assert end - start >= 4

    def test_no_toc(self):
        proc = TocProcessor()
        md = "# Title\n\nJust a normal document.\n\nWith paragraphs."
        assert proc.detect_toc_region(md) is None

    def test_less_than_3_entries_not_toc(self):
        proc = TocProcessor()
        md = "Chapter 1 .... 1\nChapter 2 .... 2\nNormal text."
        assert proc.detect_toc_region(md) is None


class TestProcess:
    def test_full_toc_conversion(self):
        proc = TocProcessor()
        md = (
            "# Índice\n"
            "\n"
            "Introducción ......... 1\n"
            "Capítulo 1: Fundamentos ......... 15\n"
            "Capítulo 2: Métodos ......... 30\n"
            "Conclusiones ......... 89\n"
            "\n"
            "# Introducción\n"
            "\n"
            "This is the introduction."
        )
        result = proc.process(md)
        assert "[Introducción](#introducción)" in result or "[Introducción](#introduccion)" in result
        assert "........." not in result
        assert " 15" not in result.split("\n")[3]  # Page number removed
        assert " 30" not in result.split("\n")[4]

    def test_preserves_non_toc_content(self):
        proc = TocProcessor()
        md = (
            "Chapter 1 .... 1\n"
            "Chapter 2 .... 2\n"
            "Chapter 3 .... 3\n"
            "\n"
            "# Chapter 1\n"
            "\n"
            "Real content paragraph with numbers like 42 and references."
        )
        result = proc.process(md)
        assert "Real content paragraph" in result
        assert "42" in result

    def test_indented_subentries(self):
        proc = TocProcessor()
        md = (
            "Chapter 1 ......... 1\n"
            "  1.1 Background ......... 3\n"
            "  1.2 Theory ......... 7\n"
            "Chapter 2 ......... 15\n"
        )
        result = proc.process(md)
        assert "[Chapter 1]" in result
        assert "[Background]" in result or "[1.1 Background]" in result

    def test_no_toc_returns_unchanged(self):
        proc = TocProcessor()
        md = "# Title\n\nNormal document content."
        assert proc.process(md) == md
```

- [ ] **Step 2: Run tests**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/filters/test_toc_processor.py -v`
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git commit -m "test(filters): add TOC region detection, slug generation, and full process tests"
```

---

### Task 3: Wire TocProcessor into pipeline and update exports

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/filters/__init__.py`
- Modify: `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py`
- Create: `tests/unit/pipeline/test_enrichment_toc.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/pipeline/test_enrichment_toc.py`:

```python
import io
from pathlib import Path
from scimarkdown.pipeline.enrichment import EnrichmentPipeline
from scimarkdown.config import SciMarkdownConfig


def test_enrichment_processes_toc():
    config = SciMarkdownConfig(filters_enabled=True)
    pipeline = EnrichmentPipeline(config)
    md = (
        "# Contents\n\n"
        "Introduction ......... 1\n"
        "Chapter 1 ......... 5\n"
        "Chapter 2 ......... 20\n"
        "Conclusion ......... 50\n\n"
        "# Introduction\n\nText here."
    )
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    assert "........." not in result.base_markdown
    assert "[Introduction]" in result.base_markdown or "[Chapter 1]" in result.base_markdown


def test_enrichment_toc_disabled():
    config = SciMarkdownConfig(filters_enabled=False)
    pipeline = EnrichmentPipeline(config)
    md = "Introduction ......... 1\nChapter 1 ......... 5\nChapter 2 ......... 20\n"
    result = pipeline.enrich(
        base_markdown=md,
        source_stream=io.BytesIO(b"dummy"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    assert "........." in result.base_markdown
```

- [ ] **Step 2: Update `__init__.py`**

Add to `packages/scimarkdown/src/scimarkdown/filters/__init__.py`:

```python
from .toc_processor import TocProcessor
```

And add `"TocProcessor"` to `__all__`.

- [ ] **Step 3: Wire into enrichment pipeline**

In `enrichment.py`, inside the noise filtering block (after `clean_text` and before decorative image filter), add:

```python
                # TOC processing: detect and convert to hyperlinks
                try:
                    from scimarkdown.filters.toc_processor import TocProcessor
                    toc = TocProcessor()
                    base_markdown = toc.process(base_markdown)
                    result.base_markdown = base_markdown
                except Exception as e:
                    logger.warning("TOC processing failed: %s", e)
```

- [ ] **Step 4: Run all tests**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/ --ignore=tests/upstream -q`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(filters): wire TocProcessor into enrichment pipeline"
```

---

## Dependency Graph

```
Task 1 (parser + processor) → Task 2 (tests) → Task 3 (pipeline wiring)
```

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | TocProcessor | Parse TOC entries, generate slugs, detect regions, convert to hyperlinks |
| 2 | Tests | Full test coverage: parsing, slugs, region detection, process |
| 3 | Pipeline wiring | Integrate into enrichment, update exports |

**Total: 3 tasks, ~15 steps, 3 commits.**
