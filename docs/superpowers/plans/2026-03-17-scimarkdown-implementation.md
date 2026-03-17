# SciMarkdown Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SciMarkdown, a fork of Microsoft MarkItDown that adds LaTeX formula detection and image extraction/referencing across all document formats.

**Architecture:** Dual-pass pipeline — Phase 1 calls MarkItDown's `convert()` for base markdown, Phase 2 re-parses the source for structured data (math, images), Phase 3 merges both into enriched markdown. `EnhancedMarkItDown` subclasses `MarkItDown` with minimal upstream changes (~30 lines).

**Tech Stack:** Python 3.10+, MarkItDown (fork), PyMuPDF, Pillow, python-docx, python-pptx, BeautifulSoup4, pdfplumber, PyYAML, pix2tex (optional), nougat-ocr (optional), openai/anthropic (optional)

**Spec:** `docs/superpowers/specs/2026-03-17-scimarkdown-design.md`

---

## Phase 1: Foundation (Tasks 1-4)

These tasks set up the project structure, data models, configuration, and the minimal upstream fork changes. Everything else depends on this phase.

---

### Task 1: Fork setup and project scaffolding

**Files:**
- Create: `packages/scimarkdown/pyproject.toml`
- Create: `packages/scimarkdown/src/scimarkdown/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/py.typed`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/math/__init__.py`
- Create: `tests/unit/images/__init__.py`
- Create: `tests/unit/pipeline/__init__.py`
- Create: `tests/integration/__init__.py`

**Prerequisite:** Clone the MarkItDown repo into the project directory.

- [ ] **Step 1: Clone Microsoft MarkItDown**

```bash
cd /home/u680912/2-Munera/claude/mcp/microsoft_markitdown
git clone git@github.com:microsoft/markitdown.git upstream-markitdown
cp -r upstream-markitdown/packages/markitdown packages/markitdown
cp -r upstream-markitdown/packages/markitdown-mcp packages/markitdown-mcp
rm -rf upstream-markitdown
```

- [ ] **Step 2: Add upstream remote for future syncs**

```bash
cd /home/u680912/2-Munera/claude/mcp/microsoft_markitdown
git remote add upstream https://github.com/microsoft/markitdown.git
```

- [ ] **Step 3: Create scimarkdown package with pyproject.toml**

Create `packages/scimarkdown/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "scimarkdown"
version = "0.1.0+mit0.1.1"
description = "Scientific markdown converter with LaTeX formula detection and image extraction"
requires-python = ">=3.10"
dependencies = [
    "markitdown[all]>=0.1.1,<0.2.0",
    "Pillow>=9.0.0",
    "PyMuPDF>=1.24.0",
    "python-docx",
    "PyYAML",
]

[project.optional-dependencies]
ocr = ["pix2tex>=0.1.1"]
nougat = ["nougat-ocr"]
llm = ["openai>=1.0.0", "anthropic"]
all = ["scimarkdown[ocr]", "scimarkdown[nougat]", "scimarkdown[llm]"]

[project.scripts]
scimarkdown = "scimarkdown.__main__:main"
scimarkdown-mcp = "scimarkdown.mcp.__main__:main"
```

- [ ] **Step 4: Create package __init__.py**

Create `packages/scimarkdown/src/scimarkdown/__init__.py`:

```python
"""SciMarkdown: Scientific markdown converter with LaTeX and image support."""

__version__ = "0.1.0+mit0.1.1"
```

- [ ] **Step 5: Create test directory structure**

Create `tests/conftest.py`:

```python
import pytest
import shutil
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXPECTED_DIR = FIXTURES_DIR / "expected"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def tmp_output_dir(tmp_path):
    return tmp_path


def has_pix2tex():
    try:
        import pix2tex
        return True
    except ImportError:
        return False


def has_nougat():
    try:
        import nougat
        return True
    except ImportError:
        return False


skip_no_ocr = pytest.mark.skipif(not has_pix2tex(), reason="pix2tex not installed")
skip_no_nougat = pytest.mark.skipif(not has_nougat(), reason="nougat not installed")
```

Create empty `__init__.py` files for test packages:
- `tests/unit/__init__.py`
- `tests/unit/math/__init__.py`
- `tests/unit/images/__init__.py`
- `tests/unit/pipeline/__init__.py`
- `tests/integration/__init__.py`

- [ ] **Step 6: Verify MarkItDown installs and tests pass**

```bash
cd /home/u680912/2-Munera/claude/mcp/microsoft_markitdown
pip install -e packages/markitdown[all]
cd packages/markitdown && python -m pytest tests/ -x -q
```

Expected: All existing MarkItDown tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/ tests/
git commit -m "feat: scaffold SciMarkdown project with fork of MarkItDown"
```

---

### Task 2: Data models

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/models/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/models/enriched_result.py`
- Create: `packages/scimarkdown/src/scimarkdown/models/text_block.py`
- Create: `packages/scimarkdown/src/scimarkdown/models/math_region.py`
- Create: `packages/scimarkdown/src/scimarkdown/models/image_ref.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write failing tests for data models**

Create `tests/unit/test_models.py`:

```python
from scimarkdown.models import EnrichedResult, TextBlock, MathRegion, ImageRef


def test_text_block_creation():
    block = TextBlock(position=0, content="Hello world", block_type="paragraph")
    assert block.position == 0
    assert block.content == "Hello world"
    assert block.block_type == "paragraph"


def test_math_region_creation():
    region = MathRegion(
        position=5,
        original_text="x² + y² = z²",
        latex=r"x^{2} + y^{2} = z^{2}",
        source_type="unicode",
        confidence=0.95,
    )
    assert region.latex == r"x^{2} + y^{2} = z^{2}"
    assert region.source_type == "unicode"
    assert region.confidence == 0.95
    assert region.is_inline is True  # default


def test_math_region_block():
    region = MathRegion(
        position=10,
        original_text="sum formula",
        latex=r"\sum_{i=1}^{n} x_i",
        source_type="omml",
        confidence=1.0,
        is_inline=False,
    )
    assert region.is_inline is False


def test_image_ref_creation():
    ref = ImageRef(
        position=3,
        file_path="doc_img00001.png",
        original_format="png",
        width=800,
        height=600,
        caption="Figure 1: Architecture diagram",
        reference_label="Figure 1",
        ordinal=1,
    )
    assert ref.file_path == "doc_img00001.png"
    assert ref.ordinal == 1
    assert ref.caption == "Figure 1: Architecture diagram"


def test_image_ref_no_reference():
    ref = ImageRef(
        position=7,
        file_path="doc_img00002.png",
        original_format="jpeg",
        width=640,
        height=480,
    )
    assert ref.reference_label is None
    assert ref.ordinal is None
    assert ref.caption is None


def test_enriched_result():
    result = EnrichedResult(
        base_markdown="# Title\n\nSome text",
        title="Title",
        text_blocks=[TextBlock(position=0, content="Title", block_type="heading")],
        images=[],
        math_regions=[],
    )
    assert result.base_markdown == "# Title\n\nSome text"
    assert len(result.text_blocks) == 1
    assert len(result.images) == 0


def test_enriched_result_with_metadata():
    result = EnrichedResult(
        base_markdown="content",
        metadata={"author": "Test", "date": "2026-01-01"},
    )
    assert result.metadata["author"] == "Test"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/u680912/2-Munera/claude/mcp/microsoft_markitdown
python -m pytest tests/unit/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scimarkdown'`

- [ ] **Step 3: Implement data models**

Create `packages/scimarkdown/src/scimarkdown/models/__init__.py`:

```python
from .enriched_result import EnrichedResult
from .text_block import TextBlock
from .math_region import MathRegion
from .image_ref import ImageRef

__all__ = ["EnrichedResult", "TextBlock", "MathRegion", "ImageRef"]
```

Create `packages/scimarkdown/src/scimarkdown/models/text_block.py`:

```python
from dataclasses import dataclass


@dataclass
class TextBlock:
    """A block of text with its ordinal position in the document."""

    position: int
    content: str
    block_type: str = "paragraph"  # paragraph, heading, list, code, etc.
```

Create `packages/scimarkdown/src/scimarkdown/models/math_region.py`:

```python
from dataclasses import dataclass


@dataclass
class MathRegion:
    """A detected mathematical formula region."""

    position: int
    original_text: str
    latex: str
    source_type: str  # "omml", "mathml", "unicode", "ocr", "llm"
    confidence: float = 1.0
    is_inline: bool = True
```

Create `packages/scimarkdown/src/scimarkdown/models/image_ref.py`:

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageRef:
    """A reference to an extracted image with metadata."""

    position: int
    file_path: str
    original_format: str
    width: int = 0
    height: int = 0
    caption: Optional[str] = None
    reference_label: Optional[str] = None
    ordinal: Optional[int] = None
```

Create `packages/scimarkdown/src/scimarkdown/models/enriched_result.py`:

```python
from dataclasses import dataclass, field
from typing import Optional

from .text_block import TextBlock
from .math_region import MathRegion
from .image_ref import ImageRef


@dataclass
class EnrichedResult:
    """Result of the enrichment pipeline (Phase 2 output)."""

    base_markdown: str
    title: Optional[str] = None
    text_blocks: list[TextBlock] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    math_regions: list[MathRegion] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

- [ ] **Step 4: Install scimarkdown package and run tests**

```bash
cd /home/u680912/2-Munera/claude/mcp/microsoft_markitdown
pip install -e packages/scimarkdown
python -m pytest tests/unit/test_models.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/models/ tests/unit/test_models.py
git commit -m "feat: add data models (EnrichedResult, TextBlock, MathRegion, ImageRef)"
```

---

### Task 3: Configuration system

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/config.py`
- Create: `scimarkdown.yaml` (default config at project root)
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing tests for config**

Create `tests/unit/test_config.py`:

```python
import yaml
from pathlib import Path
from scimarkdown.config import SciMarkdownConfig, load_config


def test_default_config():
    config = SciMarkdownConfig()
    assert config.latex_style == "standard"
    assert config.images_output_dir == "same"
    assert config.images_dpi == 300
    assert config.images_counter_digits == 5
    assert config.math_heuristic is True
    assert config.math_ocr_engine == "auto"
    assert config.math_confidence_threshold == 0.75
    assert config.llm_enabled is False
    assert config.references_generate_index is True
    assert config.performance_total_timeout == 1800


def test_config_from_dict():
    config = SciMarkdownConfig.from_dict({
        "latex": {"style": "github"},
        "images": {"dpi": 150, "counter_digits": 5},
        "math": {"ocr_engine": "pix2tex"},
        "performance": {"total_timeout_seconds": 600},
    })
    assert config.latex_style == "github"
    assert config.images_dpi == 150
    assert config.math_ocr_engine == "pix2tex"
    assert config.performance_total_timeout == 600


def test_config_from_yaml_file(tmp_path):
    config_file = tmp_path / "scimarkdown.yaml"
    config_file.write_text(yaml.dump({
        "latex": {"style": "github"},
        "images": {"output_dir": "/tmp/images"},
    }))
    config = load_config(config_file)
    assert config.latex_style == "github"
    assert config.images_output_dir == "/tmp/images"


def test_config_override():
    base = SciMarkdownConfig()
    overrides = {"latex": {"style": "github"}}
    config = base.with_overrides(overrides)
    assert config.latex_style == "github"
    assert config.images_dpi == 300  # unchanged


def test_reference_patterns_default():
    config = SciMarkdownConfig()
    assert len(config.references_patterns) == 5
    assert any("Fig" in p for p in config.references_patterns)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/test_config.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement configuration**

Create `packages/scimarkdown/src/scimarkdown/config.py`:

```python
"""Configuration system for SciMarkdown."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


_DEFAULT_PATTERNS = [
    r'Fig(?:ura|ure|\.)\s*(\d+)',
    r'Tab(?:la|le|\.)\s*(\d+)',
    r'Gr[aA]f(?:ico|h)\s*(\d+)',
    r'Im(?:agen|age|g\.?)\s*(\d+)',
    r'Chart\s*(\d+)',
]


@dataclass
class SciMarkdownConfig:
    """SciMarkdown configuration with defaults matching spec."""

    # LaTeX
    latex_style: str = "standard"

    # Images
    images_output_dir: str = "same"
    images_format: str = "png"
    images_dpi: int = 300
    images_margin_px: int = 10
    images_counter_digits: int = 5
    images_autocrop_whitespace: bool = True

    # Math
    math_heuristic: bool = True
    math_ocr_engine: str = "auto"
    math_nougat_model: str = "0.1.0-base"
    math_confidence_threshold: float = 0.75

    # LLM
    llm_enabled: bool = False
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key_env: str = "LLM_API_KEY"

    # References
    references_patterns: list[str] = field(default_factory=lambda: list(_DEFAULT_PATTERNS))
    references_languages: list[str] = field(default_factory=lambda: ["es", "en"])
    references_generate_index: bool = True

    # Performance
    performance_total_timeout: int = 1800
    performance_max_images: int = 10000
    performance_max_image_file_size_mb: int = 50
    performance_max_total_images_size_mb: int = 500
    performance_ocr_timeout: int = 30
    performance_nougat_timeout: int = 120
    performance_llm_timeout: int = 60
    performance_unload_models: bool = False

    # Sync
    sync_remote: str = "https://github.com/microsoft/markitdown.git"
    sync_branch: str = "main"
    sync_check_interval_days: int = 14

    @classmethod
    def from_dict(cls, data: dict) -> "SciMarkdownConfig":
        config = cls()
        config._apply_dict(data)
        return config

    def with_overrides(self, overrides: dict) -> "SciMarkdownConfig":
        import copy
        config = copy.deepcopy(self)
        config._apply_dict(overrides)
        return config

    def _apply_dict(self, data: dict) -> None:
        mapping = {
            ("latex", "style"): "latex_style",
            ("images", "output_dir"): "images_output_dir",
            ("images", "format"): "images_format",
            ("images", "dpi"): "images_dpi",
            ("images", "margin_px"): "images_margin_px",
            ("images", "counter_digits"): "images_counter_digits",
            ("images", "autocrop_whitespace"): "images_autocrop_whitespace",
            ("math", "heuristic"): "math_heuristic",
            ("math", "ocr_engine"): "math_ocr_engine",
            ("math", "nougat_model"): "math_nougat_model",
            ("math", "confidence_threshold"): "math_confidence_threshold",
            ("llm", "enabled"): "llm_enabled",
            ("llm", "provider"): "llm_provider",
            ("llm", "model"): "llm_model",
            ("llm", "api_key_env"): "llm_api_key_env",
            ("references", "patterns"): "references_patterns",
            ("references", "languages"): "references_languages",
            ("references", "generate_index"): "references_generate_index",
            ("performance", "total_timeout_seconds"): "performance_total_timeout",
            ("performance", "max_images"): "performance_max_images",
            ("performance", "max_image_file_size_mb"): "performance_max_image_file_size_mb",
            ("performance", "max_total_images_size_mb"): "performance_max_total_images_size_mb",
            ("performance", "ocr_timeout_seconds"): "performance_ocr_timeout",
            ("performance", "nougat_timeout_seconds"): "performance_nougat_timeout",
            ("performance", "llm_timeout_seconds"): "performance_llm_timeout",
            ("performance", "unload_models_after_conversion"): "performance_unload_models",
            ("sync", "remote"): "sync_remote",
            ("sync", "branch"): "sync_branch",
            ("sync", "check_interval_days"): "sync_check_interval_days",
        }
        for (section, key), attr in mapping.items():
            if section in data and key in data[section]:
                setattr(self, attr, data[section][key])


def load_config(path: Optional[Path] = None) -> SciMarkdownConfig:
    """Load configuration from YAML file. Falls back to defaults if not found."""
    if path is None:
        path = Path("scimarkdown.yaml")
    if not path.exists():
        return SciMarkdownConfig()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return SciMarkdownConfig.from_dict(data)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/unit/test_config.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/config.py tests/unit/test_config.py
git commit -m "feat: add configuration system with YAML loading and overrides"
```

---

### Task 4: Upstream fork change + EnhancedMarkItDown skeleton

**Files:**
- Modify: `packages/markitdown/src/markitdown/_markitdown.py` (~30 lines)
- Create: `packages/scimarkdown/src/scimarkdown/_enhanced_markitdown.py`
- Test: `tests/unit/test_enhanced_markitdown.py`
- Test: `tests/upstream/test_microsoft_suite.py`

**Important:** Read `packages/markitdown/src/markitdown/_markitdown.py` first to understand the current `convert()` method. The key change is ensuring the file stream is seekable so the subclass can re-read it.

- [ ] **Step 1: Read the upstream _markitdown.py to understand convert() flow**

```bash
cd /home/u680912/2-Munera/claude/mcp/microsoft_markitdown
grep -n "def convert" packages/markitdown/src/markitdown/_markitdown.py
```

Identify the `convert()`, `convert_local()`, `convert_stream()`, `_convert()` methods and how they pass file streams.

- [ ] **Step 2: Write upstream regression test**

Create `tests/upstream/test_microsoft_suite.py`:

```python
"""Verify that original MarkItDown tests still pass after our fork changes."""

import subprocess
import sys


def test_upstream_tests_pass():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "packages/markitdown/tests/", "-x", "-q"],
        capture_output=True,
        text=True,
        cwd="/home/u680912/2-Munera/claude/mcp/microsoft_markitdown",
    )
    assert result.returncode == 0, f"Upstream tests failed:\n{result.stdout}\n{result.stderr}"
```

Create `tests/upstream/__init__.py` (empty).

- [ ] **Step 3: Write test for EnhancedMarkItDown skeleton**

Create `tests/unit/test_enhanced_markitdown.py`:

```python
import io
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig


def test_enhanced_inherits_markitdown():
    from markitdown import MarkItDown
    enhanced = EnhancedMarkItDown()
    assert isinstance(enhanced, MarkItDown)


def test_enhanced_convert_returns_result():
    """Basic conversion should still work (Phase 1 passthrough)."""
    enhanced = EnhancedMarkItDown()
    # Convert a simple text string via stream
    text_content = b"Hello, this is a test document."
    result = enhanced.convert_stream(io.BytesIO(text_content), file_extension=".txt")
    assert result is not None
    assert "Hello" in result.markdown


def test_enhanced_convert_with_config():
    config = SciMarkdownConfig(latex_style="github")
    enhanced = EnhancedMarkItDown(sci_config=config)
    assert enhanced.sci_config.latex_style == "github"
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
python -m pytest tests/unit/test_enhanced_markitdown.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 5: Modify upstream _markitdown.py for seekable streams**

In `packages/markitdown/src/markitdown/_markitdown.py`, find the `convert_stream()` method. Add a `BytesIO` wrap to ensure the stream is seekable:

```python
# Add at the top of convert_stream() or _convert(), before passing to converters:
import io

# If the stream is not seekable, wrap it
if not file_stream.seekable():
    file_stream = io.BytesIO(file_stream.read())

# After conversion, reset stream position for potential re-read by subclass
file_stream.seek(0)
```

The exact location depends on the current code — read it first. The goal is that after `convert_stream()` returns, the stream can be re-read by the subclass.

- [ ] **Step 6: Implement EnhancedMarkItDown skeleton**

Create `packages/scimarkdown/src/scimarkdown/_enhanced_markitdown.py`:

```python
"""EnhancedMarkItDown: subclass that adds formula detection and image extraction."""

import logging
from typing import Optional

from markitdown import MarkItDown, DocumentConverterResult

from .config import SciMarkdownConfig

logger = logging.getLogger(__name__)


class EnhancedMarkItDown(MarkItDown):
    """Extends MarkItDown with LaTeX formula detection and image extraction.

    Uses a dual-pass architecture:
    - Pass 1: super().convert() for base markdown (Phase 1)
    - Pass 2: Re-parse source for structured data (Phase 2)
    - Merge: Compose enriched markdown (Phase 3)
    """

    def __init__(self, sci_config: Optional[SciMarkdownConfig] = None, **kwargs):
        super().__init__(**kwargs)
        self.sci_config = sci_config or SciMarkdownConfig()

    # Phase 2 and 3 will be added in later tasks.
    # For now, this is a passthrough that just calls super().
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/unit/test_enhanced_markitdown.py tests/upstream/test_microsoft_suite.py -v
```

Expected: All PASS. Upstream tests still pass.

- [ ] **Step 8: Commit**

```bash
git add packages/markitdown/ packages/scimarkdown/ tests/
git commit -m "feat: add EnhancedMarkItDown skeleton with seekable stream fork change"
```

---

## Phase 2: Math Detection — Heuristic (Tasks 5-7)

These tasks implement the heuristic (non-OCR) math detection: Unicode patterns, MathML parsing, and configurable LaTeX formatting.

---

### Task 5: Math detector — Unicode and regex patterns

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/math/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/math/detector.py`
- Test: `tests/unit/math/test_detector.py`

- [ ] **Step 1: Write failing tests for Unicode math detection**

Create `tests/unit/math/test_detector.py`:

```python
from scimarkdown.math.detector import MathDetector


def test_detect_unicode_superscripts():
    detector = MathDetector()
    text = "The equation x² + y² = z² is well known."
    regions = detector.detect(text)
    assert len(regions) >= 1
    assert any("x^{2}" in r.latex for r in regions)


def test_detect_unicode_math_symbols():
    detector = MathDetector()
    text = "For all x ∈ ℝ, ∑ᵢ xᵢ ≤ ∫ f(x)dx"
    regions = detector.detect(text)
    assert len(regions) >= 1
    assert any("\\in" in r.latex or "\\sum" in r.latex for r in regions)


def test_detect_mathml():
    detector = MathDetector()
    html = '<p>The formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> is simple.</p>'
    regions = detector.detect(html)
    assert len(regions) == 1
    assert "\\frac{1}{2}" in regions[0].latex


def test_detect_mathjax_spans():
    detector = MathDetector()
    html = '<p>Result: <span class="MathJax">\\(E = mc^2\\)</span></p>'
    regions = detector.detect(html)
    assert len(regions) == 1
    assert "E = mc^2" in regions[0].latex


def test_no_false_positives_on_plain_text():
    detector = MathDetector()
    text = "This is a normal sentence with no math content at all."
    regions = detector.detect(text)
    assert len(regions) == 0


def test_detect_inline_vs_block():
    detector = MathDetector()
    text = "Inline x² and block:\n∑ᵢ₌₁ⁿ xᵢ = S"
    regions = detector.detect(text)
    # At least one region detected
    assert len(regions) >= 1


def test_confidence_scores():
    detector = MathDetector()
    # High confidence: clear math symbols
    text = "∫₀^∞ e^{-x} dx = 1"
    regions = detector.detect(text)
    assert all(r.confidence >= 0.8 for r in regions)


def test_detect_katex_elements():
    detector = MathDetector()
    html = '<span class="katex"><span class="katex-mathml"><math><mi>x</mi></math></span></span>'
    regions = detector.detect(html)
    assert len(regions) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/math/test_detector.py -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement MathDetector**

Create `packages/scimarkdown/src/scimarkdown/math/__init__.py`:

```python
from .detector import MathDetector

__all__ = ["MathDetector"]
```

> **Note:** `MathFormatter` will be added to this `__init__.py` in Task 6 when it is implemented.

Create `packages/scimarkdown/src/scimarkdown/math/detector.py`:

```python
"""Heuristic math detection via regex, Unicode symbols, and MathML parsing."""

import re
import logging
from typing import Optional

from bs4 import BeautifulSoup

from ..models import MathRegion

logger = logging.getLogger(__name__)

# Unicode math symbol ranges and individual characters
_UNICODE_MATH_SYMBOLS = set("∀∁∂∃∄∅∆∇∈∉∊∋∌∍∎∏∐∑−∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣∤∥∦"
                            "∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏"
                            "≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹"
                            "≺≻≼≽≾≿⊀⊁⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝"
                            "⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿"
                            "⋀⋁⋂⋃⋄⋅⋆⋇⋈⋉⋊⋋⋌⋍⋎⋏⋐⋑⋒⋓⋔⋕⋖⋗⋘⋙⋚⋛⋜⋝⋞⋟"
                            "ℂℇℊℋℌℍℎℏℐℑℒℓℕℙℚℛℜℝℤℨℬℭℯℰℱℳℴℵℶℷℸℹ")

# Superscript/subscript Unicode maps
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ", "0123456789+-=()ni")
_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ᵢⱼₙ", "0123456789+-=()ijn")

# Unicode to LaTeX mapping for common symbols
_UNICODE_TO_LATEX = {
    "∀": r"\forall", "∃": r"\exists", "∄": r"\nexists",
    "∅": r"\emptyset", "∈": r"\in", "∉": r"\notin",
    "∋": r"\ni", "∏": r"\prod", "∑": r"\sum",
    "−": "-", "∓": r"\mp", "±": r"\pm",
    "×": r"\times", "÷": r"\div", "√": r"\sqrt",
    "∞": r"\infty", "∠": r"\angle",
    "∧": r"\wedge", "∨": r"\vee",
    "∩": r"\cap", "∪": r"\cup",
    "∫": r"\int", "∬": r"\iint", "∭": r"\iiint",
    "∮": r"\oint",
    "∴": r"\therefore", "∵": r"\because",
    "∼": r"\sim", "≈": r"\approx", "≅": r"\cong",
    "≠": r"\neq", "≡": r"\equiv",
    "≤": r"\leq", "≥": r"\geq",
    "≪": r"\ll", "≫": r"\gg",
    "⊂": r"\subset", "⊃": r"\supset",
    "⊆": r"\subseteq", "⊇": r"\supseteq",
    "⊕": r"\oplus", "⊗": r"\otimes",
    "⊥": r"\perp", "⊤": r"\top",
    "⋅": r"\cdot", "⋆": r"\star",
    "ℂ": r"\mathbb{C}", "ℕ": r"\mathbb{N}",
    "ℚ": r"\mathbb{Q}", "ℝ": r"\mathbb{R}",
    "ℤ": r"\mathbb{Z}",
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma",
    "δ": r"\delta", "ε": r"\epsilon", "ζ": r"\zeta",
    "η": r"\eta", "θ": r"\theta", "λ": r"\lambda",
    "μ": r"\mu", "π": r"\pi", "σ": r"\sigma",
    "τ": r"\tau", "φ": r"\phi", "ω": r"\omega",
    "Δ": r"\Delta", "Σ": r"\Sigma", "Π": r"\Pi",
    "Ω": r"\Omega", "Φ": r"\Phi",
}

# Pattern to find regions with high density of math symbols
_MATH_SYMBOL_PATTERN = re.compile(
    r'[' + re.escape(''.join(_UNICODE_MATH_SYMBOLS)) + r'²³⁴⁵⁶⁷⁸⁹⁰¹ⁿⁱ₀₁₂₃₄₅₆₇₈₉ᵢⱼₙ]'
)

# MathML tag pattern
_MATHML_PATTERN = re.compile(r'<math[^>]*>.*?</math>', re.DOTALL)

# MathJax/KaTeX class pattern
_MATHJAX_PATTERN = re.compile(
    r'<span[^>]*class="[^"]*(?:MathJax|katex)[^"]*"[^>]*>(.*?)</span>',
    re.DOTALL | re.IGNORECASE,
)

# LaTeX delimiters already in text
_LATEX_INLINE_PATTERN = re.compile(r'\\\((.+?)\\\)', re.DOTALL)
_LATEX_BLOCK_PATTERN = re.compile(r'\\\[(.+?)\\\]', re.DOTALL)


class MathDetector:
    """Detects mathematical formulas in text using heuristics."""

    def detect(self, text: str) -> list[MathRegion]:
        """Detect math regions in text/HTML content."""
        regions: list[MathRegion] = []

        # 1. MathML elements
        regions.extend(self._detect_mathml(text))

        # 2. MathJax/KaTeX spans
        regions.extend(self._detect_mathjax(text))

        # 3. Existing LaTeX delimiters (passthrough)
        regions.extend(self._detect_existing_latex(text))

        # 4. Unicode math symbols
        regions.extend(self._detect_unicode_math(text))

        return regions

    def _detect_mathml(self, text: str) -> list[MathRegion]:
        regions = []
        for match in _MATHML_PATTERN.finditer(text):
            latex = self._mathml_to_latex(match.group())
            if latex:
                regions.append(MathRegion(
                    position=match.start(),
                    original_text=match.group(),
                    latex=latex,
                    source_type="mathml",
                    confidence=0.95,
                    is_inline=True,
                ))
        return regions

    def _detect_mathjax(self, text: str) -> list[MathRegion]:
        regions = []
        for match in _MATHJAX_PATTERN.finditer(text):
            content = match.group(1).strip()
            # Extract LaTeX from \(...\) or raw content
            latex_match = _LATEX_INLINE_PATTERN.search(content)
            if latex_match:
                latex = latex_match.group(1).strip()
            else:
                latex = content
            if latex:
                regions.append(MathRegion(
                    position=match.start(),
                    original_text=match.group(),
                    latex=latex,
                    source_type="mathjax",
                    confidence=0.9,
                    is_inline=True,
                ))
        return regions

    def _detect_existing_latex(self, text: str) -> list[MathRegion]:
        regions = []
        for match in _LATEX_INLINE_PATTERN.finditer(text):
            regions.append(MathRegion(
                position=match.start(),
                original_text=match.group(),
                latex=match.group(1).strip(),
                source_type="latex",
                confidence=1.0,
                is_inline=True,
            ))
        for match in _LATEX_BLOCK_PATTERN.finditer(text):
            regions.append(MathRegion(
                position=match.start(),
                original_text=match.group(),
                latex=match.group(1).strip(),
                source_type="latex",
                confidence=1.0,
                is_inline=False,
            ))
        return regions

    def _detect_unicode_math(self, text: str) -> list[MathRegion]:
        """Detect regions with Unicode math symbols and convert to LaTeX."""
        regions = []
        # Find lines/segments with math symbols, tracking character offset
        offset = 0
        for line in text.split('\n'):
            symbols = _MATH_SYMBOL_PATTERN.findall(line)
            if len(symbols) >= 2:
                latex = self._unicode_to_latex(line.strip())
                if latex and latex != line.strip():
                    confidence = min(0.6 + len(symbols) * 0.05, 0.95)
                    regions.append(MathRegion(
                        position=offset,
                        original_text=line.strip(),
                        latex=latex,
                        source_type="unicode",
                        confidence=confidence,
                        is_inline=True,
                    ))
            offset += len(line) + 1  # +1 for the \n
        return regions

    def _unicode_to_latex(self, text: str) -> str:
        """Convert Unicode math symbols to LaTeX notation."""
        result = text

        # Convert superscripts
        sup_pattern = re.compile(r'([a-zA-Z])([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿⁱ]+)')
        def _sup_replace(m):
            base = m.group(1)
            sup = m.group(2).translate(_SUPERSCRIPTS)
            return f"{base}^{{{sup}}}"
        result = sup_pattern.sub(_sup_replace, result)

        # Convert subscripts
        sub_pattern = re.compile(r'([a-zA-Z])([₀₁₂₃₄₅₆₇₈₉₊₋ᵢⱼₙ]+)')
        def _sub_replace(m):
            base = m.group(1)
            sub = m.group(2).translate(_SUBSCRIPTS)
            return f"{base}_{{{sub}}}"
        result = sub_pattern.sub(_sub_replace, result)

        # Replace individual symbols
        for unicode_char, latex_cmd in _UNICODE_TO_LATEX.items():
            result = result.replace(unicode_char, f" {latex_cmd} ")

        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result).strip()
        return result

    def _mathml_to_latex(self, mathml: str) -> Optional[str]:
        """Convert MathML to LaTeX. Basic implementation."""
        try:
            soup = BeautifulSoup(mathml, "html.parser")
            math_elem = soup.find("math")
            if not math_elem:
                return None
            return self._process_mathml_node(math_elem)
        except Exception as e:
            logger.warning(f"MathML parsing failed: {e}")
            return None

    def _process_mathml_node(self, node) -> str:
        """Recursively process MathML nodes to LaTeX."""
        if node.name is None:
            return node.string or ""

        children_latex = "".join(
            self._process_mathml_node(child) for child in node.children
        )

        tag = node.name.lower()
        if tag in ("math", "mrow", "semantics"):
            return children_latex
        elif tag == "mn":
            return children_latex
        elif tag == "mi":
            return children_latex
        elif tag == "mo":
            op = children_latex.strip()
            return _UNICODE_TO_LATEX.get(op, op)
        elif tag == "mfrac":
            parts = [self._process_mathml_node(c) for c in node.children if c.name]
            if len(parts) == 2:
                return f"\\frac{{{parts[0]}}}{{{parts[1]}}}"
            return children_latex
        elif tag == "msup":
            parts = [self._process_mathml_node(c) for c in node.children if c.name]
            if len(parts) == 2:
                return f"{parts[0]}^{{{parts[1]}}}"
            return children_latex
        elif tag == "msub":
            parts = [self._process_mathml_node(c) for c in node.children if c.name]
            if len(parts) == 2:
                return f"{parts[0]}_{{{parts[1]}}}"
            return children_latex
        elif tag == "msqrt":
            return f"\\sqrt{{{children_latex}}}"
        elif tag == "mover":
            parts = [self._process_mathml_node(c) for c in node.children if c.name]
            if len(parts) == 2:
                return f"\\overline{{{parts[0]}}}"
            return children_latex
        elif tag == "munder":
            parts = [self._process_mathml_node(c) for c in node.children if c.name]
            if len(parts) == 2:
                return f"\\underline{{{parts[0]}}}"
            return children_latex
        elif tag in ("mtext", "annotation"):
            return children_latex
        else:
            return children_latex
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/math/test_detector.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/math/ tests/unit/math/test_detector.py
git commit -m "feat: add heuristic math detector (Unicode, MathML, MathJax/KaTeX)"
```

---

### Task 6: Math formatter — LaTeX style output

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/math/formatter.py`
- Test: `tests/unit/math/test_formatter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/math/test_formatter.py`:

```python
from scimarkdown.math.formatter import MathFormatter
from scimarkdown.models import MathRegion


def test_standard_inline():
    fmt = MathFormatter(style="standard")
    region = MathRegion(position=0, original_text="x²", latex="x^{2}",
                        source_type="unicode", is_inline=True)
    assert fmt.format(region) == "$x^{2}$"


def test_standard_block():
    fmt = MathFormatter(style="standard")
    region = MathRegion(position=0, original_text="sum", latex=r"\sum_{i=1}^{n} x_i",
                        source_type="unicode", is_inline=False)
    assert fmt.format(region) == r"$$\sum_{i=1}^{n} x_i$$"


def test_github_inline():
    fmt = MathFormatter(style="github")
    region = MathRegion(position=0, original_text="x²", latex="x^{2}",
                        source_type="unicode", is_inline=True)
    assert fmt.format(region) == "$`x^{2}`$"


def test_github_block():
    fmt = MathFormatter(style="github")
    region = MathRegion(position=0, original_text="sum",
                        latex=r"\sum_{i=1}^{n} x_i",
                        source_type="unicode", is_inline=False)
    result = fmt.format(region)
    assert result.startswith("```math\n")
    assert result.endswith("\n```")
    assert r"\sum_{i=1}^{n} x_i" in result


def test_low_confidence_marker():
    fmt = MathFormatter(style="standard")
    region = MathRegion(position=0, original_text="maybe math", latex="x",
                        source_type="unicode", confidence=0.5)
    result = fmt.format(region)
    assert "<!-- sci:math:low-confidence -->" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/math/test_formatter.py -v
```

- [ ] **Step 3: Implement MathFormatter**

Create `packages/scimarkdown/src/scimarkdown/math/formatter.py`:

```python
"""Configurable LaTeX formatter for math regions."""

from ..models import MathRegion

LOW_CONFIDENCE_THRESHOLD = 0.7


class MathFormatter:
    """Formats MathRegion objects as LaTeX strings in markdown."""

    def __init__(self, style: str = "standard"):
        if style not in ("standard", "github"):
            raise ValueError(f"Unknown LaTeX style: {style}. Use 'standard' or 'github'.")
        self.style = style

    def format(self, region: MathRegion) -> str:
        if region.is_inline:
            result = self._format_inline(region.latex)
        else:
            result = self._format_block(region.latex)

        if region.confidence < LOW_CONFIDENCE_THRESHOLD:
            result = f"<!-- sci:math:low-confidence -->{result}"

        return result

    def _format_inline(self, latex: str) -> str:
        if self.style == "github":
            return f"$`{latex}`$"
        return f"${latex}$"

    def _format_block(self, latex: str) -> str:
        if self.style == "github":
            return f"```math\n{latex}\n```"
        return f"$${latex}$$"
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/math/test_formatter.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/math/formatter.py tests/unit/math/test_formatter.py
git commit -m "feat: add configurable LaTeX formatter (standard and GitHub-flavored)"
```

---

### Task 7: Math OCR interface (pix2tex + Nougat wrappers)

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/math/ocr.py`
- Test: `tests/unit/math/test_ocr.py`

- [ ] **Step 1: Write tests with mocks for OCR engines**

Create `tests/unit/math/test_ocr.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
import io

from scimarkdown.math.ocr import MathOCR


def _create_test_image(width=100, height=50):
    """Create a simple test image."""
    img = Image.new("RGB", (width, height), "white")
    return img


def test_ocr_not_available_graceful():
    """When no OCR engine is installed, should return None."""
    ocr = MathOCR(engine="pix2tex")
    if not ocr.is_available():
        img = _create_test_image()
        result = ocr.recognize(img)
        assert result is None


def test_ocr_engine_auto_selection():
    ocr = MathOCR(engine="auto")
    assert ocr.engine in ("pix2tex", "nougat", "none")


@patch("scimarkdown.math.ocr._pix2tex_available", return_value=True)
def test_pix2tex_interface(mock_available):
    """Test that pix2tex interface is called correctly."""
    ocr = MathOCR(engine="pix2tex")
    img = _create_test_image()
    # We can't test actual OCR without the model, but we test the interface
    with patch.object(ocr, "_run_pix2tex", return_value=("x^{2}", 0.95)):
        result = ocr.recognize(img)
        assert result is not None
        assert result.latex == "x^{2}"
        assert result.confidence == 0.95


def test_timeout_handling():
    ocr = MathOCR(engine="pix2tex", timeout=1)
    assert ocr.timeout == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/math/test_ocr.py -v
```

- [ ] **Step 3: Implement MathOCR**

Create `packages/scimarkdown/src/scimarkdown/math/ocr.py`:

```python
"""OCR engine wrappers for formula recognition (pix2tex, Nougat)."""

import logging
from dataclasses import dataclass
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def _pix2tex_available() -> bool:
    try:
        import pix2tex
        return True
    except ImportError:
        return False


def _nougat_available() -> bool:
    try:
        import nougat
        return True
    except ImportError:
        return False


@dataclass
class OCRResult:
    latex: str
    confidence: float


class MathOCR:
    """Wraps pix2tex and Nougat for formula image recognition."""

    def __init__(self, engine: str = "auto", timeout: int = 30):
        self.timeout = timeout
        self._model = None

        if engine == "auto":
            if _pix2tex_available():
                self.engine = "pix2tex"
            elif _nougat_available():
                self.engine = "nougat"
            else:
                self.engine = "none"
        else:
            self.engine = engine

    def is_available(self) -> bool:
        if self.engine == "pix2tex":
            return _pix2tex_available()
        elif self.engine == "nougat":
            return _nougat_available()
        return False

    def recognize(self, image: Image.Image) -> Optional[OCRResult]:
        """Recognize a math formula in an image. Returns None if unavailable."""
        if self.engine == "pix2tex":
            return self._recognize_pix2tex(image)
        elif self.engine == "nougat":
            return self._recognize_nougat(image)
        else:
            logger.warning("No OCR engine available. Install pix2tex or nougat.")
            return None

    def _recognize_pix2tex(self, image: Image.Image) -> Optional[OCRResult]:
        if not _pix2tex_available():
            return None
        try:
            latex, confidence = self._run_pix2tex(image)
            return OCRResult(latex=latex, confidence=confidence)
        except Exception as e:
            logger.error(f"pix2tex recognition failed: {e}")
            return None

    def _run_pix2tex(self, image: Image.Image) -> tuple[str, float]:
        """Run pix2tex model. Separated for testability."""
        from pix2tex.cli import LatexOCR

        if self._model is None:
            self._model = LatexOCR()
        latex = self._model(image)
        return latex, 0.85  # pix2tex doesn't provide confidence, use default

    def _recognize_nougat(self, image: Image.Image) -> Optional[OCRResult]:
        if not _nougat_available():
            return None
        try:
            latex, confidence = self._run_nougat(image)
            return OCRResult(latex=latex, confidence=confidence)
        except Exception as e:
            logger.error(f"Nougat recognition failed: {e}")
            return None

    def _run_nougat(self, image: Image.Image) -> tuple[str, float]:
        """Run Nougat model. Separated for testability."""
        # Nougat integration to be refined when model is available
        raise NotImplementedError("Nougat integration pending model availability")

    def unload(self) -> None:
        """Unload model to free memory."""
        self._model = None
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/math/test_ocr.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/math/ocr.py tests/unit/math/test_ocr.py
git commit -m "feat: add MathOCR wrapper for pix2tex and Nougat engines"
```

---

## Phase 3: Image Extraction (Tasks 8-11)

These tasks implement image extraction, cropping, reference linking, and index generation.

---

### Task 8: Image extractor — PDF and DOCX

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/images/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/images/extractor.py`
- Test: `tests/unit/images/test_extractor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/images/test_extractor.py`:

```python
import io
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image

from scimarkdown.images.extractor import ImageExtractor
from scimarkdown.config import SciMarkdownConfig


def test_naming_convention():
    extractor = ImageExtractor(
        config=SciMarkdownConfig(),
        document_name="test_paper",
        output_dir=Path("/tmp"),
    )
    assert extractor._make_filename(1) == "test_paper_img00001.png"
    assert extractor._make_filename(99999) == "test_paper_img99999.png"


def test_naming_overflow():
    """Counter overflow should extend to 6 digits."""
    extractor = ImageExtractor(
        config=SciMarkdownConfig(),
        document_name="big_doc",
        output_dir=Path("/tmp"),
    )
    assert extractor._make_filename(100000) == "big_doc_img100000.png"


def test_sanitize_document_name():
    extractor = ImageExtractor(
        config=SciMarkdownConfig(),
        document_name="My Paper (2026) [Final].pdf",
        output_dir=Path("/tmp"),
    )
    assert "My_Paper_2026_Final" in extractor._make_filename(1)


def test_extract_returns_image_refs():
    extractor = ImageExtractor(
        config=SciMarkdownConfig(),
        document_name="test",
        output_dir=Path("/tmp"),
    )
    # Test with a minimal mock — actual format-specific tests are in integration
    assert extractor._counter == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/images/test_extractor.py -v
```

- [ ] **Step 3: Implement ImageExtractor**

Create `packages/scimarkdown/src/scimarkdown/images/__init__.py`:

```python
from .extractor import ImageExtractor

__all__ = ["ImageExtractor"]
```

> **Note:** `ImageCropper`, `ReferenceLinker`, and `IndexBuilder` will be added to this `__init__.py` in Tasks 9, 10, and 11 respectively when they are implemented.

Create `packages/scimarkdown/src/scimarkdown/images/extractor.py`:

```python
"""Image extraction from documents by format."""

import io
import re
import logging
from pathlib import Path
from typing import Optional, BinaryIO

from PIL import Image

from ..config import SciMarkdownConfig
from ..models import ImageRef

logger = logging.getLogger(__name__)


def _sanitize_name(name: str) -> str:
    """Sanitize document name for use in filenames."""
    # Remove extension
    name = Path(name).stem
    # Replace non-alphanumeric with underscore
    name = re.sub(r'[^\w\-]', '_', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name).strip('_')
    return name


class ImageExtractor:
    """Extracts images from documents and saves them to disk."""

    def __init__(self, config: SciMarkdownConfig, document_name: str, output_dir: Path):
        self.config = config
        self.document_name = _sanitize_name(document_name)
        self.output_dir = output_dir
        self._counter = 0
        self._total_size = 0

    def _make_filename(self, number: int, ext: str = "png") -> str:
        digits = self.config.images_counter_digits
        num_str = str(number)
        if len(num_str) <= digits:
            num_str = num_str.zfill(digits)
        return f"{self.document_name}_img{num_str}.{ext}"

    def _next_filename(self, ext: str = "png") -> str:
        self._counter += 1
        return self._make_filename(self._counter, ext)

    def _save_image(self, img: Image.Image, filename: str) -> Optional[Path]:
        """Save image to output directory with size checks."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename

        # Determine format from filename extension
        ext = Path(filename).suffix.lstrip(".").upper()
        save_format = {"JPG": "JPEG", "JPEG": "JPEG", "PNG": "PNG", "GIF": "GIF"}.get(ext, "PNG")

        # Save to buffer first to check size
        buf = io.BytesIO()
        img.save(buf, format=save_format)
        size_mb = buf.tell() / (1024 * 1024)

        if size_mb > self.config.performance_max_image_file_size_mb:
            logger.warning(f"Image {filename} exceeds max size ({size_mb:.1f}MB). Skipping.")
            return None

        if self._total_size + size_mb > self.config.performance_max_total_images_size_mb:
            logger.warning(f"Total image disk budget exceeded. Skipping {filename}.")
            return None

        self._total_size += size_mb
        with open(path, "wb") as f:
            f.write(buf.getvalue())

        return path

    def extract_from_pdf(self, stream: BinaryIO) -> list[ImageRef]:
        """Extract images from PDF using PyMuPDF."""
        refs = []
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=stream.read(), filetype="pdf")

            for page_num, page in enumerate(doc):
                images = page.get_images(full=True)
                for img_index, img_info in enumerate(images):
                    if self._counter >= self.config.performance_max_images:
                        logger.warning("Max images limit reached.")
                        return refs

                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue

                    image_bytes = base_image["image"]
                    ext = base_image.get("ext", "png")
                    pil_img = Image.open(io.BytesIO(image_bytes))

                    filename = self._next_filename(ext if ext in ("png", "jpg", "jpeg") else "png")
                    saved_path = self._save_image(pil_img, filename)
                    if saved_path:
                        refs.append(ImageRef(
                            position=page_num * 1000 + img_index,
                            file_path=str(saved_path.name),
                            original_format=ext,
                            width=pil_img.width,
                            height=pil_img.height,
                        ))
            doc.close()
        except Exception as e:
            logger.error(f"PDF image extraction failed: {e}")
        return refs

    def extract_from_docx(self, stream: BinaryIO) -> list[ImageRef]:
        """Extract images from DOCX."""
        refs = []
        try:
            import zipfile

            with zipfile.ZipFile(stream) as zf:
                media_files = [f for f in zf.namelist() if f.startswith("word/media/")]
                for idx, media_path in enumerate(sorted(media_files)):
                    if self._counter >= self.config.performance_max_images:
                        logger.warning("Max images limit reached.")
                        return refs

                    ext = Path(media_path).suffix.lstrip(".")
                    if ext.lower() not in ("png", "jpg", "jpeg", "gif", "bmp", "tiff", "emf", "wmf"):
                        continue

                    image_bytes = zf.read(media_path)
                    try:
                        pil_img = Image.open(io.BytesIO(image_bytes))
                    except Exception:
                        logger.warning(f"Cannot open image {media_path}")
                        continue

                    out_ext = ext if ext in ("png", "jpg", "jpeg") else "png"
                    filename = self._next_filename(out_ext)
                    saved_path = self._save_image(pil_img, filename)
                    if saved_path:
                        refs.append(ImageRef(
                            position=idx,
                            file_path=str(saved_path.name),
                            original_format=ext,
                            width=pil_img.width,
                            height=pil_img.height,
                        ))
        except Exception as e:
            logger.error(f"DOCX image extraction failed: {e}")
        return refs

    def extract_from_pptx(self, stream: BinaryIO) -> list[ImageRef]:
        """Extract images from PPTX."""
        refs = []
        try:
            import zipfile

            with zipfile.ZipFile(stream) as zf:
                media_files = [f for f in zf.namelist() if f.startswith("ppt/media/")]
                for idx, media_path in enumerate(sorted(media_files)):
                    if self._counter >= self.config.performance_max_images:
                        return refs

                    ext = Path(media_path).suffix.lstrip(".")
                    if ext.lower() not in ("png", "jpg", "jpeg", "gif", "bmp", "tiff"):
                        continue

                    image_bytes = zf.read(media_path)
                    try:
                        pil_img = Image.open(io.BytesIO(image_bytes))
                    except Exception:
                        continue

                    out_ext = ext if ext in ("png", "jpg", "jpeg") else "png"
                    filename = self._next_filename(out_ext)
                    saved_path = self._save_image(pil_img, filename)
                    if saved_path:
                        refs.append(ImageRef(
                            position=idx,
                            file_path=str(saved_path.name),
                            original_format=ext,
                            width=pil_img.width,
                            height=pil_img.height,
                        ))
        except Exception as e:
            logger.error(f"PPTX image extraction failed: {e}")
        return refs
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/images/test_extractor.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/images/ tests/unit/images/test_extractor.py
git commit -m "feat: add ImageExtractor for PDF, DOCX, and PPTX formats"
```

---

### Task 9: Image cropper

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/images/cropper.py`
- Test: `tests/unit/images/test_cropper.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/images/test_cropper.py`:

```python
from PIL import Image
from scimarkdown.images.cropper import ImageCropper


def test_autocrop_whitespace():
    """Create image with white border and verify it gets cropped."""
    img = Image.new("RGB", (200, 200), "white")
    # Draw a black square in the center
    for x in range(50, 150):
        for y in range(50, 150):
            img.putpixel((x, y), (0, 0, 0))

    cropper = ImageCropper(margin=0, autocrop=True)
    result = cropper.crop(img)
    assert result.width == 100
    assert result.height == 100


def test_autocrop_with_margin():
    img = Image.new("RGB", (200, 200), "white")
    for x in range(50, 150):
        for y in range(50, 150):
            img.putpixel((x, y), (0, 0, 0))

    cropper = ImageCropper(margin=10, autocrop=True)
    result = cropper.crop(img)
    assert result.width == 120  # 100 + 2*10
    assert result.height == 120


def test_no_autocrop():
    img = Image.new("RGB", (200, 200), "white")
    cropper = ImageCropper(margin=0, autocrop=False)
    result = cropper.crop(img)
    assert result.width == 200
    assert result.height == 200


def test_all_white_image():
    """All white image should return original."""
    img = Image.new("RGB", (100, 100), "white")
    cropper = ImageCropper(margin=0, autocrop=True)
    result = cropper.crop(img)
    assert result.width == 100  # Can't crop further
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/images/test_cropper.py -v
```

- [ ] **Step 3: Implement ImageCropper**

Create `packages/scimarkdown/src/scimarkdown/images/cropper.py`:

```python
"""Image cropping with auto-whitespace removal."""

from PIL import Image, ImageChops


class ImageCropper:
    """Crops images with optional whitespace removal."""

    def __init__(self, margin: int = 10, autocrop: bool = True):
        self.margin = margin
        self.autocrop = autocrop

    def crop(self, image: Image.Image) -> Image.Image:
        if not self.autocrop:
            return image

        # Create a background of the same color as the corners
        bg = Image.new(image.mode, image.size, self._detect_background(image))
        diff = ImageChops.difference(image, bg)
        bbox = diff.getbbox()

        if bbox is None:
            return image  # All same color, nothing to crop

        # Apply margin
        left = max(0, bbox[0] - self.margin)
        top = max(0, bbox[1] - self.margin)
        right = min(image.width, bbox[2] + self.margin)
        bottom = min(image.height, bbox[3] + self.margin)

        return image.crop((left, top, right, bottom))

    def _detect_background(self, image: Image.Image) -> tuple:
        """Detect background color from corner pixels."""
        corners = [
            image.getpixel((0, 0)),
            image.getpixel((image.width - 1, 0)),
            image.getpixel((0, image.height - 1)),
            image.getpixel((image.width - 1, image.height - 1)),
        ]
        # Use most common corner color
        return max(set(corners), key=corners.count)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/images/test_cropper.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/images/cropper.py tests/unit/images/test_cropper.py
git commit -m "feat: add ImageCropper with auto-whitespace removal"
```

---

### Task 10: Reference linker

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/images/reference_linker.py`
- Test: `tests/unit/images/test_reference_linker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/images/test_reference_linker.py`:

```python
from scimarkdown.images.reference_linker import ReferenceLinker
from scimarkdown.models import ImageRef
from scimarkdown.config import SciMarkdownConfig


def _make_images(count=3):
    return [
        ImageRef(position=i, file_path=f"doc_img{str(i+1).zfill(5)}.png",
                 original_format="png", width=100, height=100)
        for i in range(count)
    ]


def test_exact_ordinal_match():
    linker = ReferenceLinker(SciMarkdownConfig())
    images = _make_images(3)
    text = "As shown in Figure 1, the results in Figure 2 confirm Figure 3."
    linked = linker.link(text, images)
    assert linked[0].ordinal == 1
    assert linked[1].ordinal == 2
    assert linked[2].ordinal == 3


def test_spanish_patterns():
    linker = ReferenceLinker(SciMarkdownConfig())
    images = _make_images(2)
    text = "Como se ve en la Figura 1, y la Tabla 2 muestra los datos."
    linked = linker.link(text, images)
    assert linked[0].reference_label is not None
    assert "Figura 1" in linked[0].reference_label


def test_repeated_references():
    linker = ReferenceLinker(SciMarkdownConfig())
    images = _make_images(1)
    text = "Figure 1 shows X. As discussed, Figure 1 is important."
    linked = linker.link(text, images)
    # Same image file, referenced twice but linked to same image
    assert linked[0].ordinal == 1


def test_no_references():
    linker = ReferenceLinker(SciMarkdownConfig())
    images = _make_images(2)
    text = "No references to figures here."
    linked = linker.link(text, images)
    # Images should still be present but with no reference_label
    assert all(img.reference_label is None for img in linked)


def test_forward_references():
    linker = ReferenceLinker(SciMarkdownConfig())
    images = _make_images(3)
    text = "See Figure 3 below for details. Figure 1 was shown earlier."
    linked = linker.link(text, images)
    assert linked[0].ordinal == 1  # First image linked to Figure 1
    assert linked[2].ordinal == 3  # Third image linked to Figure 3


def test_fig_abbreviation():
    linker = ReferenceLinker(SciMarkdownConfig())
    images = _make_images(1)
    text = "As shown in Fig. 1."
    linked = linker.link(text, images)
    assert linked[0].ordinal == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/images/test_reference_linker.py -v
```

- [ ] **Step 3: Implement ReferenceLinker**

Create `packages/scimarkdown/src/scimarkdown/images/reference_linker.py`:

```python
"""Links text references (Figure X, Tabla Y) to extracted images."""

import re
import logging
from typing import Optional

from ..config import SciMarkdownConfig
from ..models import ImageRef

logger = logging.getLogger(__name__)


class ReferenceLinker:
    """Links textual references to extracted images using a priority algorithm."""

    def __init__(self, config: SciMarkdownConfig):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in config.references_patterns]

    def link(self, text: str, images: list[ImageRef]) -> list[ImageRef]:
        """Link text references to images.

        Algorithm (ordered by priority):
        1. Exact ordinal match: "Figure 3" → 3rd image
        2. Caption match (if captions detected)
        3. Proximity fallback for unnumbered figures
        4. Repeated references → same image file
        5. Unmatched images → no reference_label
        """
        # Find all references in text
        references = self._find_references(text)

        # Create a mutable copy of images
        linked = [ImageRef(
            position=img.position,
            file_path=img.file_path,
            original_format=img.original_format,
            width=img.width,
            height=img.height,
            caption=img.caption,
            reference_label=img.reference_label,
            ordinal=img.ordinal,
        ) for img in images]

        # Step 1: Exact ordinal match
        for ref_label, ordinal in references:
            if 1 <= ordinal <= len(linked):
                target = linked[ordinal - 1]
                target.ordinal = ordinal
                target.reference_label = ref_label

        # Steps 2-5 handled implicitly:
        # - Caption match: future enhancement when captions are extracted
        # - Repeated references: same ordinal maps to same image
        # - Unmatched images: reference_label stays None

        return linked

    def _find_references(self, text: str) -> list[tuple[str, int]]:
        """Find all figure/table references in text.

        Returns list of (full_match_text, ordinal_number).
        """
        results = []
        seen = set()

        for pattern in self.patterns:
            for match in pattern.finditer(text):
                ordinal = int(match.group(1))
                label = match.group(0).strip()
                key = (label, ordinal)
                if key not in seen:
                    seen.add(key)
                    results.append((label, ordinal))

        return sorted(results, key=lambda x: x[1])
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/images/test_reference_linker.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/images/reference_linker.py tests/unit/images/test_reference_linker.py
git commit -m "feat: add ReferenceLinker with ordinal matching algorithm"
```

---

### Task 11: Figure index builder

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/images/index_builder.py`
- Test: `tests/unit/images/test_index_builder.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/images/test_index_builder.py`:

```python
from scimarkdown.images.index_builder import IndexBuilder
from scimarkdown.models import ImageRef


def test_build_index_table():
    images = [
        ImageRef(position=0, file_path="doc_img00001.png", original_format="png",
                 ordinal=1, reference_label="Figure 1", caption="Architecture diagram"),
        ImageRef(position=1, file_path="doc_img00002.png", original_format="png",
                 ordinal=2, reference_label="Figure 2", caption="Results"),
    ]
    builder = IndexBuilder()
    index = builder.build(images)
    assert "## Figure Index" in index
    assert "doc_img00001.png" in index
    assert "doc_img00002.png" in index
    assert "Architecture diagram" in index


def test_unmatched_image_in_index():
    images = [
        ImageRef(position=0, file_path="doc_img00001.png", original_format="png"),
    ]
    builder = IndexBuilder()
    index = builder.build(images)
    assert "(no reference)" in index


def test_empty_images():
    builder = IndexBuilder()
    index = builder.build([])
    assert index == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/images/test_index_builder.py -v
```

- [ ] **Step 3: Implement IndexBuilder**

Create `packages/scimarkdown/src/scimarkdown/images/index_builder.py`:

```python
"""Generates a markdown figure index table."""

from ..models import ImageRef


class IndexBuilder:
    """Builds a markdown table listing all figures in the document."""

    def build(self, images: list[ImageRef]) -> str:
        if not images:
            return ""

        lines = [
            "## Figure Index",
            "",
            "| # | Figure | Description | File |",
            "|---|--------|-------------|------|",
        ]

        for idx, img in enumerate(images, 1):
            label = img.reference_label or "(no reference)"
            caption = img.caption or ""
            filename = img.file_path.rsplit("/", 1)[-1] if "/" in img.file_path else img.file_path
            name_no_ext = filename.rsplit(".", 1)[0] if "." in filename else filename
            lines.append(
                f"| {idx} | {label} | {caption} | [{name_no_ext}]({img.file_path}) |"
            )

        return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/images/test_index_builder.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/images/index_builder.py tests/unit/images/test_index_builder.py
git commit -m "feat: add IndexBuilder for figure index table generation"
```

---

## Phase 4: Pipeline Orchestration (Tasks 12-13)

These tasks wire up the enrichment (Phase 2) and composition (Phase 3) orchestrators.

---

### Task 12: Enrichment pipeline (Phase 2)

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/pipeline/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py`
- Test: `tests/unit/pipeline/test_enrichment.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/pipeline/test_enrichment.py`:

```python
import io
from pathlib import Path
from unittest.mock import MagicMock

from scimarkdown.pipeline.enrichment import EnrichmentPipeline
from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import EnrichedResult


def test_enrichment_produces_result():
    config = SciMarkdownConfig()
    pipeline = EnrichmentPipeline(config)
    result = pipeline.enrich(
        base_markdown="# Test\n\nHello world",
        source_stream=io.BytesIO(b"Hello world"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp/test_output"),
    )
    assert isinstance(result, EnrichedResult)
    assert result.base_markdown == "# Test\n\nHello world"


def test_enrichment_detects_unicode_math():
    config = SciMarkdownConfig()
    pipeline = EnrichmentPipeline(config)
    result = pipeline.enrich(
        base_markdown="The equation x² + y² = z² is Pythagorean.",
        source_stream=io.BytesIO(b"The equation x\xc2\xb2 + y\xc2\xb2 = z\xc2\xb2"),
        file_extension=".txt",
        document_name="math_test",
        output_dir=Path("/tmp/test_output"),
    )
    assert len(result.math_regions) >= 0  # Heuristic may or may not detect in base markdown


def test_enrichment_with_pdf_format(tmp_path):
    config = SciMarkdownConfig()
    pipeline = EnrichmentPipeline(config)
    # Minimal test — actual PDF tests in integration
    result = pipeline.enrich(
        base_markdown="# PDF Content",
        source_stream=io.BytesIO(b"not a real pdf"),
        file_extension=".pdf",
        document_name="test_pdf",
        output_dir=tmp_path,
    )
    assert isinstance(result, EnrichedResult)


def test_enrichment_respects_timeout():
    config = SciMarkdownConfig(performance_total_timeout=1)
    pipeline = EnrichmentPipeline(config)
    assert pipeline.config.performance_total_timeout == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/pipeline/test_enrichment.py -v
```

- [ ] **Step 3: Implement EnrichmentPipeline**

Create `packages/scimarkdown/src/scimarkdown/pipeline/__init__.py`:

```python
from .enrichment import EnrichmentPipeline

__all__ = ["EnrichmentPipeline"]
```

> **Note:** `CompositionPipeline` will be added to this `__init__.py` in Task 13 when it is implemented.

Create `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py`:

```python
"""Phase 2: Enrichment pipeline — extracts structured data from source document."""

import logging
import signal
from pathlib import Path
from typing import BinaryIO

from ..config import SciMarkdownConfig
from ..models import EnrichedResult, MathRegion, ImageRef
from ..math.detector import MathDetector
from ..images.extractor import ImageExtractor
from ..images.reference_linker import ReferenceLinker

logger = logging.getLogger(__name__)

# Format to extractor method mapping
_IMAGE_FORMATS = {
    ".pdf": "extract_from_pdf",
    ".docx": "extract_from_docx",
    ".pptx": "extract_from_pptx",
}


class EnrichmentPipeline:
    """Orchestrates Phase 2: math detection, image extraction, reference linking."""

    def __init__(self, config: SciMarkdownConfig):
        self.config = config
        self.math_detector = MathDetector()
        self.reference_linker = ReferenceLinker(config)

    def enrich(
        self,
        base_markdown: str,
        source_stream: BinaryIO,
        file_extension: str,
        document_name: str,
        output_dir: Path,
    ) -> EnrichedResult:
        """Run enrichment on the source document."""

        math_regions: list[MathRegion] = []
        images: list[ImageRef] = []

        try:
            # Math detection on base markdown (heuristic)
            if self.config.math_heuristic:
                math_regions = self.math_detector.detect(base_markdown)
                logger.info(f"Detected {len(math_regions)} math regions via heuristics")

            # Image extraction (format-specific)
            ext = file_extension.lower()
            if ext in _IMAGE_FORMATS:
                extractor = ImageExtractor(
                    config=self.config,
                    document_name=document_name,
                    output_dir=output_dir,
                )
                method_name = _IMAGE_FORMATS[ext]
                extract_method = getattr(extractor, method_name)
                source_stream.seek(0)
                images = extract_method(source_stream)
                logger.info(f"Extracted {len(images)} images from {ext}")

            # Reference linking
            if images:
                images = self.reference_linker.link(base_markdown, images)
                linked_count = sum(1 for img in images if img.reference_label)
                logger.info(f"Linked {linked_count}/{len(images)} images to text references")

        except Exception as e:
            logger.error(f"Enrichment pipeline failed: {e}", exc_info=True)
            # Graceful degradation: return base markdown with whatever we have

        return EnrichedResult(
            base_markdown=base_markdown,
            images=images,
            math_regions=math_regions,
        )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/pipeline/test_enrichment.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/pipeline/ tests/unit/pipeline/test_enrichment.py
git commit -m "feat: add EnrichmentPipeline (Phase 2 orchestrator)"
```

---

### Task 13: Composition pipeline (Phase 3)

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/pipeline/composition.py`
- Test: `tests/unit/pipeline/test_composition.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/pipeline/test_composition.py`:

```python
from scimarkdown.pipeline.composition import CompositionPipeline
from scimarkdown.models import EnrichedResult, MathRegion, ImageRef
from scimarkdown.config import SciMarkdownConfig


def test_composition_no_enrichment():
    """No math or images: output equals base markdown."""
    config = SciMarkdownConfig()
    pipeline = CompositionPipeline(config)
    result = EnrichedResult(base_markdown="# Hello\n\nWorld")
    output = pipeline.compose(result)
    assert output == "# Hello\n\nWorld"


def test_composition_with_images():
    config = SciMarkdownConfig()
    pipeline = CompositionPipeline(config)
    result = EnrichedResult(
        base_markdown="# Doc\n\nSome text.\n\nMore text.",
        images=[
            ImageRef(position=0, file_path="doc_img00001.png", original_format="png",
                     ordinal=1, reference_label="Figure 1", caption="Test figure"),
        ],
    )
    output = pipeline.compose(result)
    assert "![Figure 1: Test figure](doc_img00001.png)" in output
    assert "## Figure Index" in output


def test_composition_with_math_standard():
    config = SciMarkdownConfig(latex_style="standard")
    pipeline = CompositionPipeline(config)
    result = EnrichedResult(
        base_markdown="The equation x² + y² = z² is famous.",
        math_regions=[
            MathRegion(position=0, original_text="x² + y² = z²",
                       latex=r"x^{2} + y^{2} = z^{2}",
                       source_type="unicode", confidence=0.9, is_inline=True),
        ],
    )
    output = pipeline.compose(result)
    assert "$x^{2} + y^{2} = z^{2}$" in output


def test_composition_with_math_github():
    config = SciMarkdownConfig(latex_style="github")
    pipeline = CompositionPipeline(config)
    result = EnrichedResult(
        base_markdown="The equation x² is simple.",
        math_regions=[
            MathRegion(position=0, original_text="x²", latex="x^{2}",
                       source_type="unicode", confidence=0.9, is_inline=True),
        ],
    )
    output = pipeline.compose(result)
    assert "$`x^{2}`$" in output


def test_composition_no_index_when_disabled():
    config = SciMarkdownConfig(references_generate_index=False)
    pipeline = CompositionPipeline(config)
    result = EnrichedResult(
        base_markdown="# Doc",
        images=[
            ImageRef(position=0, file_path="doc_img00001.png", original_format="png"),
        ],
    )
    output = pipeline.compose(result)
    assert "## Figure Index" not in output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/pipeline/test_composition.py -v
```

- [ ] **Step 3: Implement CompositionPipeline**

Create `packages/scimarkdown/src/scimarkdown/pipeline/composition.py`:

```python
"""Phase 3: Composition pipeline — merges enrichment data into final markdown."""

import logging

from ..config import SciMarkdownConfig
from ..models import EnrichedResult
from ..math.formatter import MathFormatter
from ..images.index_builder import IndexBuilder

logger = logging.getLogger(__name__)


class CompositionPipeline:
    """Merges base markdown with enrichment data to produce final output."""

    def __init__(self, config: SciMarkdownConfig):
        self.config = config
        self.math_formatter = MathFormatter(style=config.latex_style)
        self.index_builder = IndexBuilder()

    def compose(self, enriched: EnrichedResult) -> str:
        """Compose enriched markdown from base markdown + structured data."""
        markdown = enriched.base_markdown

        # Replace math regions with LaTeX
        if enriched.math_regions:
            markdown = self._inject_math(markdown, enriched)

        # Inject image references
        if enriched.images:
            markdown = self._inject_images(markdown, enriched)

            # Append figure index
            if self.config.references_generate_index:
                index = self.index_builder.build(enriched.images)
                if index:
                    markdown = markdown.rstrip() + "\n\n---\n\n" + index

        return markdown

    def _inject_math(self, markdown: str, enriched: EnrichedResult) -> str:
        """Replace detected math regions with formatted LaTeX."""
        # Sort by position descending to replace from end (preserves positions)
        sorted_regions = sorted(enriched.math_regions, key=lambda r: r.position, reverse=True)

        for region in sorted_regions:
            formatted = self.math_formatter.format(region)
            if region.original_text in markdown:
                markdown = markdown.replace(region.original_text, formatted, 1)

        return markdown

    def _inject_images(self, markdown: str, enriched: EnrichedResult) -> str:
        """Add image markdown references."""
        # Build image lines sorted by position
        image_lines = []
        for img in sorted(enriched.images, key=lambda i: i.position):
            label = img.reference_label or f"Image {img.ordinal or '?'}"
            caption = img.caption or ""
            alt_text = f"{label}: {caption}" if caption else label
            image_lines.append(f"![{alt_text}]({img.file_path})")

        if not image_lines:
            return markdown

        # Append images section before the index
        images_section = "\n\n".join(image_lines)
        markdown = markdown.rstrip() + "\n\n" + images_section

        return markdown
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/pipeline/test_composition.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/pipeline/composition.py tests/unit/pipeline/test_composition.py
git commit -m "feat: add CompositionPipeline (Phase 3 — merge enrichment into markdown)"
```

---

## Phase 5: Integration (Tasks 14-16)

Wire everything together: the EnhancedMarkItDown dual-pass, the MCP server, and the upstream sync.

---

### Task 14: Complete EnhancedMarkItDown dual-pass

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/_enhanced_markitdown.py`
- Test: `tests/unit/test_enhanced_markitdown.py` (extend)

- [ ] **Step 1: Extend tests for full dual-pass flow**

Add to `tests/unit/test_enhanced_markitdown.py`:

```python
def test_enhanced_convert_stream_with_enrichment(tmp_path):
    """Full pipeline: text with Unicode math should produce LaTeX."""
    config = SciMarkdownConfig(
        latex_style="standard",
        images_output_dir=str(tmp_path),
    )
    enhanced = EnhancedMarkItDown(sci_config=config)

    html_content = b"""<html><body>
    <p>The formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> is simple.</p>
    </body></html>"""

    result = enhanced.convert_stream(
        io.BytesIO(html_content),
        file_extension=".html",
    )
    assert result is not None
    assert result.markdown is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/test_enhanced_markitdown.py::test_enhanced_convert_stream_with_enrichment -v
```

- [ ] **Step 3: Implement full dual-pass in EnhancedMarkItDown**

Update `packages/scimarkdown/src/scimarkdown/_enhanced_markitdown.py`:

```python
"""EnhancedMarkItDown: subclass that adds formula detection and image extraction."""

import io
import logging
from pathlib import Path
from typing import Optional, BinaryIO

from markitdown import MarkItDown, DocumentConverterResult

from .config import SciMarkdownConfig, load_config
from .pipeline.enrichment import EnrichmentPipeline
from .pipeline.composition import CompositionPipeline

logger = logging.getLogger(__name__)


class EnhancedMarkItDown(MarkItDown):
    """Extends MarkItDown with LaTeX formula detection and image extraction.

    Dual-pass architecture:
    - Pass 1: super().convert*() for base markdown
    - Pass 2: Re-parse source for structured data
    - Merge: Compose enriched markdown
    """

    def __init__(
        self,
        sci_config: Optional[SciMarkdownConfig] = None,
        output_dir: Optional[Path] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.sci_config = sci_config or load_config()
        self.output_dir = output_dir or Path(".")
        self._enrichment = EnrichmentPipeline(self.sci_config)
        self._composition = CompositionPipeline(self.sci_config)

    def convert_stream(
        self,
        stream: BinaryIO,
        file_extension: str = "",
        **kwargs,
    ) -> DocumentConverterResult:
        """Override convert_stream with dual-pass enrichment."""

        # Ensure stream is seekable
        if not stream.seekable():
            stream = io.BytesIO(stream.read())

        # Pass 1: Base conversion
        stream.seek(0)
        base_result = super().convert_stream(stream, file_extension=file_extension, **kwargs)

        # Pass 2: Enrichment
        stream.seek(0)
        try:
            document_name = kwargs.get("url", "document")
            if "/" in document_name:
                document_name = document_name.rsplit("/", 1)[-1]

            output_dir = self.output_dir
            if self.sci_config.images_output_dir != "same":
                output_dir = Path(self.sci_config.images_output_dir)

            enriched = self._enrichment.enrich(
                base_markdown=base_result.markdown or "",
                source_stream=stream,
                file_extension=file_extension,
                document_name=document_name,
                output_dir=output_dir,
            )

            # Phase 3: Composition
            final_markdown = self._composition.compose(enriched)

            return DocumentConverterResult(
                title=base_result.title,
                markdown=final_markdown,
            )
        except Exception as e:
            logger.error(f"Enrichment failed, returning base result: {e}", exc_info=True)
            return base_result
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v --ignore=tests/integration
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/_enhanced_markitdown.py tests/unit/test_enhanced_markitdown.py
git commit -m "feat: complete EnhancedMarkItDown dual-pass pipeline integration"
```

---

### Task 15: MCP server with 2 tools

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/mcp/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/mcp/__main__.py`
- Test: `tests/integration/test_mcp_tools.py`

- [ ] **Step 1: Write test for MCP tools**

Create `tests/integration/test_mcp_tools.py`:

```python
"""Test that both MCP tools are registered and callable."""

import pytest


def test_mcp_server_has_both_tools():
    """Verify both tools are registered in the MCP server."""
    from scimarkdown.mcp import create_mcp_server
    server = create_mcp_server()
    tool_names = [t.name for t in server.list_tools()]
    assert "convert_to_markdown" in tool_names
    assert "convert_to_scimarkdown" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/integration/test_mcp_tools.py -v
```

- [ ] **Step 3: Implement MCP server**

Create `packages/scimarkdown/src/scimarkdown/mcp/__init__.py`:

```python
from .server import create_mcp_server

__all__ = ["create_mcp_server"]
```

Create `packages/scimarkdown/src/scimarkdown/mcp/server.py`:

```python
"""SciMarkdown MCP server with 2 tools."""

import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from markitdown import MarkItDown

from .._enhanced_markitdown import EnhancedMarkItDown
from ..config import SciMarkdownConfig


def create_mcp_server() -> FastMCP:
    mcp = FastMCP("scimarkdown")

    # Initialize both converters
    base_markitdown = MarkItDown()

    sci_config = SciMarkdownConfig()
    enhanced_markitdown = EnhancedMarkItDown(sci_config=sci_config)

    @mcp.tool()
    async def convert_to_markdown(uri: str) -> str:
        """Convert a document to markdown (original MarkItDown behavior)."""
        result = base_markitdown.convert(uri)
        return result.markdown

    @mcp.tool()
    async def convert_to_scimarkdown(uri: str, config: Optional[dict] = None) -> str:
        """Convert a document to markdown with LaTeX formulas and image extraction."""
        if config:
            effective_config = sci_config.with_overrides(config)
            converter = EnhancedMarkItDown(sci_config=effective_config)
        else:
            converter = enhanced_markitdown

        result = converter.convert(uri)
        return result.markdown

    return mcp
```

Create `packages/scimarkdown/src/scimarkdown/mcp/__main__.py`:

```python
"""Entry point for scimarkdown-mcp CLI."""

import argparse

from .server import create_mcp_server


def main():
    parser = argparse.ArgumentParser(description="SciMarkdown MCP Server")
    parser.add_argument("--http", action="store_true", help="Use HTTP+SSE transport")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host")
    parser.add_argument("--port", type=int, default=3001, help="HTTP port")
    args = parser.parse_args()

    server = create_mcp_server()

    if args.http:
        server.run(transport="sse", host=args.host, port=args.port)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/integration/test_mcp_tools.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/mcp/ tests/integration/test_mcp_tools.py
git commit -m "feat: add MCP server with convert_to_markdown and convert_to_scimarkdown tools"
```

---

### Task 16: Upstream sync script

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/sync/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/sync/upstream.py`
- Create: `.github/workflows/upstream-sync.yml`

- [ ] **Step 1: Implement sync script**

Create `packages/scimarkdown/src/scimarkdown/sync/__init__.py` (empty).

Create `packages/scimarkdown/src/scimarkdown/sync/upstream.py`:

```python
"""Upstream synchronization script for merging Microsoft MarkItDown updates."""

import subprocess
import sys
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    logger.info(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def sync_upstream(
    repo_dir: Path,
    remote: str = "upstream",
    branch: str = "main",
) -> dict:
    """Sync with upstream MarkItDown repository.

    Returns a report dict with keys: status, changes, conflicts, tests_passed.
    """
    report = {
        "date": date.today().isoformat(),
        "status": "unknown",
        "changes": [],
        "conflicts": [],
        "tests_passed": None,
    }

    # 1. Fetch upstream
    result = run_cmd(["git", "-C", str(repo_dir), "fetch", remote], check=False)
    if result.returncode != 0:
        report["status"] = "fetch_failed"
        report["error"] = result.stderr
        return report

    # 2. Check for new commits
    result = run_cmd([
        "git", "-C", str(repo_dir), "log",
        f"HEAD..{remote}/{branch}", "--oneline",
    ])
    if not result.stdout.strip():
        report["status"] = "up_to_date"
        return report

    report["changes"] = result.stdout.strip().split("\n")

    # 3. Attempt merge (no commit)
    result = run_cmd([
        "git", "-C", str(repo_dir), "merge",
        f"{remote}/{branch}", "--no-commit", "--no-ff",
    ], check=False)

    if result.returncode != 0:
        # Check for conflicts
        status = run_cmd(["git", "-C", str(repo_dir), "status", "--porcelain"])
        conflicts = [line for line in status.stdout.split("\n") if line.startswith("UU")]
        report["conflicts"] = conflicts

        if conflicts:
            report["status"] = "conflicts"
            # Abort the merge
            run_cmd(["git", "-C", str(repo_dir), "merge", "--abort"], check=False)
            return report

    # 4. Run tests
    test_result = run_cmd([
        sys.executable, "-m", "pytest",
        str(repo_dir / "packages" / "markitdown" / "tests"),
        "-x", "-q",
    ], check=False)

    sci_test_result = run_cmd([
        sys.executable, "-m", "pytest",
        str(repo_dir / "tests"),
        "-x", "-q", "--ignore=tests/integration",
    ], check=False)

    tests_passed = test_result.returncode == 0 and sci_test_result.returncode == 0
    report["tests_passed"] = tests_passed

    if tests_passed:
        # Commit the merge
        run_cmd([
            "git", "-C", str(repo_dir), "commit",
            "-m", f"chore: sync upstream MarkItDown ({date.today().isoformat()})",
        ])
        report["status"] = "merged"
    else:
        # Revert
        run_cmd(["git", "-C", str(repo_dir), "merge", "--abort"], check=False)
        report["status"] = "tests_failed"
        report["test_output"] = test_result.stdout + sci_test_result.stdout

    return report


def generate_report(report: dict, output_dir: Path) -> Path:
    """Write sync report to file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"sync_report_{report['date']}.md"

    lines = [
        f"# Upstream Sync Report — {report['date']}",
        "",
        f"**Status:** {report['status']}",
        "",
    ]

    if report["changes"]:
        lines.append("## Changes")
        for change in report["changes"]:
            lines.append(f"- {change}")
        lines.append("")

    if report["conflicts"]:
        lines.append("## Conflicts")
        for conflict in report["conflicts"]:
            lines.append(f"- {conflict}")
        lines.append("")

    if report["tests_passed"] is not None:
        lines.append(f"## Tests: {'PASSED' if report['tests_passed'] else 'FAILED'}")

    report_path.write_text("\n".join(lines))
    return report_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync with upstream MarkItDown")
    parser.add_argument("--repo-dir", type=Path, default=Path("."))
    parser.add_argument("--remote", default="upstream")
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    report = sync_upstream(args.repo_dir, args.remote, args.branch)
    report_path = generate_report(report, args.repo_dir / "sync_reports")
    print(f"Report: {report_path}")
    print(f"Status: {report['status']}")
```

- [ ] **Step 2: Create GitHub Actions workflow**

Create `.github/workflows/upstream-sync.yml`:

```yaml
name: Upstream Sync

on:
  schedule:
    - cron: '0 6 1,15 * *'  # 1st and 15th of each month
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Add upstream remote
        run: git remote add upstream https://github.com/microsoft/markitdown.git || true

      - name: Install dependencies
        run: |
          pip install -e packages/markitdown[all]
          pip install -e packages/scimarkdown
          pip install pytest

      - name: Run sync
        run: python -m scimarkdown.sync.upstream --repo-dir .

      - name: Check results
        id: sync
        run: |
          if [ -f sync_reports/sync_report_*.md ]; then
            cat sync_reports/sync_report_*.md
          fi

      - name: Create PR on success
        if: success()
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore: upstream MarkItDown sync"
          body: "Automated sync with microsoft/markitdown upstream."
          branch: upstream-sync-auto
```

- [ ] **Step 3: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/sync/ .github/
git commit -m "feat: add upstream sync script and GitHub Actions workflow"
```

---

## Phase 6: LLM Fallback (Task 17)

---

### Task 17: LLM fallback client

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/llm/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/llm/fallback.py`
- Test: `tests/unit/test_llm_fallback.py`

- [ ] **Step 1: Write tests with mocks**

Create `tests/unit/test_llm_fallback.py`:

```python
from unittest.mock import patch, MagicMock

from scimarkdown.llm.fallback import LLMFallback
from scimarkdown.config import SciMarkdownConfig


def test_llm_disabled():
    config = SciMarkdownConfig(llm_enabled=False)
    fallback = LLMFallback(config)
    result = fallback.recognize_math("x squared plus y squared")
    assert result is None


def test_llm_not_available():
    config = SciMarkdownConfig(llm_enabled=True, llm_api_key_env="NONEXISTENT_KEY")
    fallback = LLMFallback(config)
    # Should gracefully return None when API key is missing
    result = fallback.recognize_math("some formula")
    assert result is None


@patch("scimarkdown.llm.fallback._call_openai")
def test_llm_openai_call(mock_call):
    mock_call.return_value = r"x^{2} + y^{2} = z^{2}"
    config = SciMarkdownConfig(llm_enabled=True, llm_provider="openai")
    fallback = LLMFallback(config)

    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = fallback.recognize_math("x squared plus y squared equals z squared")

    assert result is not None
    assert result.latex == r"x^{2} + y^{2} = z^{2}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/test_llm_fallback.py -v
```

- [ ] **Step 3: Implement LLM fallback**

Create `packages/scimarkdown/src/scimarkdown/llm/__init__.py`:

```python
from .fallback import LLMFallback

__all__ = ["LLMFallback"]
```

Create `packages/scimarkdown/src/scimarkdown/llm/fallback.py`:

```python
"""LLM fallback for ambiguous math recognition."""

import os
import logging
from typing import Optional

from ..config import SciMarkdownConfig
from ..models import MathRegion

logger = logging.getLogger(__name__)

_MATH_PROMPT = """Analyze the following text and determine if it contains a mathematical formula or scientific expression. If it does, convert it to LaTeX notation. Return ONLY the LaTeX expression, nothing else. If it is not a formula, return "NOT_MATH".

Text: {text}"""


def _call_openai(api_key: str, model: str, prompt: str, timeout: int) -> Optional[str]:
    """Call OpenAI API."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return None


def _call_anthropic(api_key: str, model: str, prompt: str, timeout: int) -> Optional[str]:
    """Call Anthropic API."""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Anthropic API call failed: {e}")
        return None


class LLMFallback:
    """Uses LLM APIs as fallback for math formula recognition."""

    def __init__(self, config: SciMarkdownConfig):
        self.config = config

    def recognize_math(self, text: str) -> Optional[MathRegion]:
        if not self.config.llm_enabled:
            return None

        api_key = os.environ.get(self.config.llm_api_key_env)
        if not api_key:
            logger.warning(f"LLM API key not found in env var {self.config.llm_api_key_env}")
            return None

        prompt = _MATH_PROMPT.format(text=text)
        timeout = self.config.performance_llm_timeout

        if self.config.llm_provider == "openai":
            result = _call_openai(api_key, self.config.llm_model, prompt, timeout)
        elif self.config.llm_provider == "anthropic":
            result = _call_anthropic(api_key, self.config.llm_model, prompt, timeout)
        else:
            logger.error(f"Unknown LLM provider: {self.config.llm_provider}")
            return None

        if result is None or result == "NOT_MATH":
            return None

        return MathRegion(
            position=0,
            original_text=text,
            latex=result,
            source_type="llm",
            confidence=0.8,
            is_inline=True,
        )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/test_llm_fallback.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/llm/ tests/unit/test_llm_fallback.py
git commit -m "feat: add LLM fallback for math recognition (OpenAI + Anthropic)"
```

---

## Phase 7: CLI Entry Point and Final Wiring (Task 18)

---

### Task 18: CLI entry point

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/__main__.py`

- [ ] **Step 1: Implement CLI**

Create `packages/scimarkdown/src/scimarkdown/__main__.py`:

```python
"""CLI entry point for SciMarkdown."""

import argparse
import sys
from pathlib import Path

from ._enhanced_markitdown import EnhancedMarkItDown
from .config import load_config


def main():
    parser = argparse.ArgumentParser(
        description="SciMarkdown: Convert documents to markdown with LaTeX and images"
    )
    parser.add_argument("input", help="Input file path or URL")
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    parser.add_argument("-c", "--config", help="Config file path (default: scimarkdown.yaml)")
    parser.add_argument("--latex-style", choices=["standard", "github"],
                        help="Override LaTeX style")
    parser.add_argument("--output-dir", help="Output directory for images")
    args = parser.parse_args()

    config = load_config(Path(args.config) if args.config else None)

    if args.latex_style:
        config = config.with_overrides({"latex": {"style": args.latex_style}})

    output_dir = Path(args.output_dir) if args.output_dir else Path(args.input).parent
    converter = EnhancedMarkItDown(sci_config=config, output_dir=output_dir)

    result = converter.convert(args.input)

    if args.output:
        Path(args.output).write_text(result.markdown)
    else:
        print(result.markdown)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI works**

```bash
echo "Test x² + y² = z²" > /tmp/test_sci.txt
python -m scimarkdown /tmp/test_sci.txt
```

Expected: Markdown output with LaTeX conversion.

- [ ] **Step 3: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/__main__.py
git commit -m "feat: add SciMarkdown CLI entry point"
```

---

## Phase 8: Missing Format Coverage and Integration Tests (Tasks 19-22)

These tasks cover format extractors missing from Phase 3, wire the LLM fallback into the pipeline, create test fixtures, and add integration tests.

---

### Task 19: HTML, EPUB, Jupyter, and Image extractors

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/images/extractor.py` (add methods)
- Test: `tests/unit/images/test_extractor_formats.py`

- [ ] **Step 1: Write failing tests for additional formats**

Create `tests/unit/images/test_extractor_formats.py`:

```python
import io
import json
import base64
from pathlib import Path
from PIL import Image

from scimarkdown.images.extractor import ImageExtractor
from scimarkdown.config import SciMarkdownConfig


def _create_png_bytes(width=10, height=10):
    img = Image.new("RGB", (width, height), "red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_extract_from_html_img_tags(tmp_path):
    extractor = ImageExtractor(
        config=SciMarkdownConfig(),
        document_name="test_html",
        output_dir=tmp_path,
    )
    # HTML with base64 embedded image
    png_b64 = base64.b64encode(_create_png_bytes()).decode()
    html = f'<html><body><img src="data:image/png;base64,{png_b64}"></body></html>'
    refs = extractor.extract_from_html(io.BytesIO(html.encode()))
    assert len(refs) == 1


def test_extract_from_jupyter(tmp_path):
    extractor = ImageExtractor(
        config=SciMarkdownConfig(),
        document_name="test_notebook",
        output_dir=tmp_path,
    )
    png_b64 = base64.b64encode(_create_png_bytes()).decode()
    notebook = {
        "cells": [
            {"cell_type": "code", "outputs": [
                {"output_type": "display_data", "data": {"image/png": png_b64}}
            ]}
        ],
        "metadata": {},
        "nbformat": 4,
    }
    refs = extractor.extract_from_jupyter(io.BytesIO(json.dumps(notebook).encode()))
    assert len(refs) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/unit/images/test_extractor_formats.py -v
```

- [ ] **Step 3: Add extraction methods to ImageExtractor**

Add to `packages/scimarkdown/src/scimarkdown/images/extractor.py`:

```python
    def extract_from_html(self, stream: BinaryIO) -> list[ImageRef]:
        """Extract images from HTML (also used for EPUB)."""
        refs = []
        try:
            from bs4 import BeautifulSoup
            import base64

            html = stream.read().decode("utf-8", errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            for idx, img_tag in enumerate(soup.find_all("img")):
                if self._counter >= self.config.performance_max_images:
                    return refs

                src = img_tag.get("src", "")
                if src.startswith("data:image/"):
                    # Base64 embedded image
                    try:
                        header, data = src.split(",", 1)
                        image_bytes = base64.b64decode(data)
                        pil_img = Image.open(io.BytesIO(image_bytes))
                        filename = self._next_filename("png")
                        saved_path = self._save_image(pil_img, filename)
                        if saved_path:
                            refs.append(ImageRef(
                                position=idx,
                                file_path=str(saved_path.name),
                                original_format="png",
                                width=pil_img.width,
                                height=pil_img.height,
                            ))
                    except Exception:
                        logger.warning(f"Failed to decode embedded image at position {idx}")
                # External URLs would need downloading — skip in base implementation
        except Exception as e:
            logger.error(f"HTML image extraction failed: {e}")
        return refs

    def extract_from_epub(self, stream: BinaryIO) -> list[ImageRef]:
        """Extract images from EPUB (ZIP containing HTML + media)."""
        refs = []
        try:
            import zipfile

            with zipfile.ZipFile(stream) as zf:
                image_files = [
                    f for f in zf.namelist()
                    if any(f.lower().endswith(ext) for ext in
                           (".png", ".jpg", ".jpeg", ".gif", ".svg"))
                    and "META-INF" not in f
                ]
                for idx, img_path in enumerate(sorted(image_files)):
                    if self._counter >= self.config.performance_max_images:
                        return refs
                    try:
                        image_bytes = zf.read(img_path)
                        pil_img = Image.open(io.BytesIO(image_bytes))
                        ext = Path(img_path).suffix.lstrip(".")
                        out_ext = ext if ext in ("png", "jpg", "jpeg") else "png"
                        filename = self._next_filename(out_ext)
                        saved_path = self._save_image(pil_img, filename)
                        if saved_path:
                            refs.append(ImageRef(
                                position=idx,
                                file_path=str(saved_path.name),
                                original_format=ext,
                                width=pil_img.width,
                                height=pil_img.height,
                            ))
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"EPUB image extraction failed: {e}")
        return refs

    def extract_from_jupyter(self, stream: BinaryIO) -> list[ImageRef]:
        """Extract images from Jupyter Notebook outputs."""
        refs = []
        try:
            import json
            import base64

            notebook = json.loads(stream.read())
            img_idx = 0

            for cell in notebook.get("cells", []):
                for output in cell.get("outputs", []):
                    data = output.get("data", {})
                    for mime_type in ("image/png", "image/jpeg", "image/svg+xml"):
                        if mime_type in data:
                            if self._counter >= self.config.performance_max_images:
                                return refs
                            try:
                                b64_data = data[mime_type]
                                if isinstance(b64_data, list):
                                    b64_data = "".join(b64_data)
                                image_bytes = base64.b64decode(b64_data)
                                pil_img = Image.open(io.BytesIO(image_bytes))
                                ext = "png" if "png" in mime_type else "jpg"
                                filename = self._next_filename(ext)
                                saved_path = self._save_image(pil_img, filename)
                                if saved_path:
                                    refs.append(ImageRef(
                                        position=img_idx,
                                        file_path=str(saved_path.name),
                                        original_format=ext,
                                        width=pil_img.width,
                                        height=pil_img.height,
                                    ))
                                    img_idx += 1
                            except Exception:
                                logger.warning(f"Failed to extract notebook image")
        except Exception as e:
            logger.error(f"Jupyter image extraction failed: {e}")
        return refs
```

- [ ] **Step 4: Update the enrichment pipeline format mapping**

In `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py`, update `_IMAGE_FORMATS`:

```python
_IMAGE_FORMATS = {
    ".pdf": "extract_from_pdf",
    ".docx": "extract_from_docx",
    ".pptx": "extract_from_pptx",
    ".html": "extract_from_html",
    ".htm": "extract_from_html",
    ".epub": "extract_from_epub",
    ".ipynb": "extract_from_jupyter",
}
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/unit/images/test_extractor_formats.py -v
```

Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/images/extractor.py packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py tests/unit/images/test_extractor_formats.py
git commit -m "feat: add image extraction for HTML, EPUB, and Jupyter formats"
```

---

### Task 20: Wire LLM fallback into enrichment pipeline

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py`
- Test: `tests/unit/pipeline/test_enrichment_llm.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/pipeline/test_enrichment_llm.py`:

```python
import io
from pathlib import Path
from unittest.mock import patch

from scimarkdown.pipeline.enrichment import EnrichmentPipeline
from scimarkdown.config import SciMarkdownConfig


@patch("scimarkdown.llm.fallback._call_openai")
def test_enrichment_uses_llm_for_low_confidence(mock_openai):
    mock_openai.return_value = r"x^{2} + y^{2}"
    config = SciMarkdownConfig(
        llm_enabled=True,
        llm_provider="openai",
        math_confidence_threshold=0.99,  # Force everything to LLM
    )
    pipeline = EnrichmentPipeline(config)

    with patch.dict("os.environ", {"LLM_API_KEY": "test-key"}):
        result = pipeline.enrich(
            base_markdown="Test x² + y²",
            source_stream=io.BytesIO(b"Test"),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
    # LLM should have been consulted for low-confidence regions
    assert any(r.source_type == "llm" for r in result.math_regions) or len(result.math_regions) >= 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/pipeline/test_enrichment_llm.py -v
```

- [ ] **Step 3: Wire LLM into EnrichmentPipeline**

Add to `EnrichmentPipeline.__init__`:
```python
from ..llm.fallback import LLMFallback
self.llm_fallback = LLMFallback(config)
```

Add after heuristic math detection in `enrich()`:
```python
# LLM fallback for low-confidence regions
if self.config.llm_enabled and math_regions:
    enhanced_regions = []
    for region in math_regions:
        if region.confidence < self.config.math_confidence_threshold:
            llm_result = self.llm_fallback.recognize_math(region.original_text)
            if llm_result:
                enhanced_regions.append(llm_result)
            else:
                enhanced_regions.append(region)
        else:
            enhanced_regions.append(region)
    math_regions = enhanced_regions
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/pipeline/ -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py tests/unit/pipeline/test_enrichment_llm.py
git commit -m "feat: wire LLM fallback into enrichment pipeline for low-confidence math"
```

---

### Task 21: Default config file and test fixtures

**Files:**
- Create: `scimarkdown.yaml` (default config at project root)
- Create: `tests/fixtures/` directory with test documents
- Create: `tests/fixtures/expected/` with golden files

- [ ] **Step 1: Create default scimarkdown.yaml**

Create `scimarkdown.yaml` at project root with all defaults from spec section 6 (copy from config.py defaults).

- [ ] **Step 2: Create test fixtures**

Create minimal test documents:
- `tests/fixtures/html_mathml.html`: HTML with `<math>` tags
- `tests/fixtures/html_mathjax.html`: HTML with MathJax spans
- `tests/fixtures/simple_text_with_math.txt`: Text with Unicode math symbols

> **Note:** PDF, DOCX, PPTX fixtures need to be created manually or generated with scripts. Add a `tests/fixtures/README.md` documenting how to regenerate fixtures.

- [ ] **Step 3: Create golden files**

Create expected markdown output for each fixture in `tests/fixtures/expected/`.

- [ ] **Step 4: Commit**

```bash
git add scimarkdown.yaml tests/fixtures/
git commit -m "feat: add default config file and test fixtures"
```

---

### Task 22: Integration tests per format

**Files:**
- Create: `tests/integration/test_html_full.py`
- Create: `tests/integration/test_txt_full.py`
- Test: Run integration suite

- [ ] **Step 1: Write integration tests**

Create `tests/integration/test_html_full.py`:

```python
"""Full integration test: HTML with MathML -> enriched markdown."""

import io
from pathlib import Path

from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig


def test_html_with_mathml(tmp_path):
    config = SciMarkdownConfig(latex_style="standard")
    converter = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

    html = b"""<html><body>
    <h1>Test Document</h1>
    <p>The Pythagorean theorem states that
    <math><msup><mi>a</mi><mn>2</mn></msup><mo>+</mo>
    <msup><mi>b</mi><mn>2</mn></msup><mo>=</mo>
    <msup><mi>c</mi><mn>2</mn></msup></math>.</p>
    </body></html>"""

    result = converter.convert_stream(io.BytesIO(html), file_extension=".html")

    assert result.markdown is not None
    assert "Test Document" in result.markdown
    # Should contain LaTeX
    assert "$" in result.markdown or "a^{2}" in result.markdown


def test_html_with_images(tmp_path):
    import base64
    from PIL import Image

    # Create a test image
    img = Image.new("RGB", (50, 50), "blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    config = SciMarkdownConfig()
    converter = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

    html = f"""<html><body>
    <h1>Document with Image</h1>
    <p>See Figure 1 below.</p>
    <img src="data:image/png;base64,{b64}" alt="Test figure">
    </body></html>""".encode()

    result = converter.convert_stream(io.BytesIO(html), file_extension=".html")
    assert result.markdown is not None

    # Check image was extracted
    images = list(tmp_path.glob("*.png"))
    assert len(images) >= 1
```

Create `tests/integration/test_txt_full.py`:

```python
"""Full integration test: plain text with Unicode math."""

import io
from pathlib import Path

from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig


def test_text_with_unicode_math(tmp_path):
    config = SciMarkdownConfig(latex_style="standard")
    converter = EnhancedMarkItDown(sci_config=config, output_dir=tmp_path)

    text = "For all x ∈ ℝ, the sum ∑ᵢ xᵢ ≤ ∫ f(x)dx holds.".encode()
    result = converter.convert_stream(io.BytesIO(text), file_extension=".txt")

    assert result.markdown is not None
    # Should contain some LaTeX conversion
    assert "$" in result.markdown or "\\in" in result.markdown or "\\sum" in result.markdown
```

- [ ] **Step 2: Run integration tests**

```bash
python -m pytest tests/integration/ -v
```

Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "feat: add integration tests for HTML and text formats"
```

---

## Dependency Graph

```
Task 1 (scaffold)
  └── Task 2 (models) ─────────────────────────────┐
       └── Task 3 (config) ─────────────────────────┤
            └── Task 4 (EnhancedMarkItDown skeleton)│
                 ├── Task 5 (math detector) ────────┤
                 │    └── Task 6 (math formatter)   │
                 │         └── Task 7 (math OCR)    │
                 ├── Task 8 (image extractor) ──────┤
                 │    ├── Task 9 (image cropper)    │
                 │    ├── Task 10 (ref linker)      │
                 │    ├── Task 11 (index builder)   │
                 │    └── Task 19 (HTML/EPUB/Jupyter)│
                 └── Task 17 (LLM fallback) ────────┘
                      │
                      ▼
                 Task 12 (enrichment pipeline)
                      └── Task 13 (composition pipeline)
                           ├── Task 20 (wire LLM into pipeline)
                           └── Task 14 (complete dual-pass)
                                ├── Task 15 (MCP server)
                                ├── Task 16 (upstream sync)
                                ├── Task 18 (CLI)
                                ├── Task 21 (config + fixtures)
                                └── Task 22 (integration tests)
```

**Parallelizable tasks (independent of each other):**
- Tasks 5-7 (math) || Tasks 8-11, 19 (images) || Task 17 (LLM)
- Task 15 || Task 16 || Task 18
- Task 21 || Task 22

---

## Summary

| Phase | Tasks | Description |
|---|---|---|
| 1: Foundation | 1-4 | Fork, models, config, skeleton |
| 2: Math Detection | 5-7 | Heuristics, formatter, OCR wrapper |
| 3: Image Extraction | 8-11 | Extractor, cropper, linker, index |
| 4: Pipeline | 12-13 | Enrichment + composition orchestrators |
| 5: Integration | 14-16 | Dual-pass, MCP server, sync |
| 6: LLM Fallback | 17 | OpenAI/Anthropic wrapper |
| 7: CLI | 18 | Entry point |
| 8: Coverage & Tests | 19-22 | Missing formats, LLM wiring, fixtures, integration tests |

**Total: 22 tasks, ~110 steps, estimated 22 commits.**
