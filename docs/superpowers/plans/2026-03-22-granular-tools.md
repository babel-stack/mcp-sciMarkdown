# SciMarkdown v2 — Granular MCP Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose 6 existing SciMarkdown subcomponents as individual MCP tools for granular control: `detect_math`, `format_latex`, `extract_images`, `link_references`, `build_figure_index`, `ocr_formula`.

**Architecture:** All 6 tools are thin wrappers around existing classes (MathDetector, MathFormatter, ImageExtractor, ReferenceLinker, IndexBuilder, MathOCR). No new logic — only MCP tool registration and data serialization. The existing `server.py` is extended with the new tools.

**Tech Stack:** Python 3.12, FastMCP, existing scimarkdown modules

**Spec:** `docs/superpowers/specs/2026-03-20-scimarkdown-v2-embeddings-prd.md` (Section 3.2)

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `packages/scimarkdown/src/scimarkdown/mcp/server.py` | MCP tool registration | Modify — add 6 new tools |
| `packages/scimarkdown/src/scimarkdown/mcp/serializers.py` | Convert dataclasses to dicts for MCP responses | Create |
| `tests/unit/mcp/__init__.py` | Test package | Create |
| `tests/unit/mcp/test_tools.py` | Tests for all 6 granular tools | Create |
| `tests/unit/mcp/test_serializers.py` | Tests for serialization | Create |

---

### Task 1: Serializers for MCP responses

MCP tools return JSON-serializable data. Our dataclasses (MathRegion, ImageRef) need conversion to dicts.

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/mcp/serializers.py`
- Create: `tests/unit/mcp/__init__.py`
- Create: `tests/unit/mcp/test_serializers.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/mcp/__init__.py` (empty).

Create `tests/unit/mcp/test_serializers.py`:

```python
from scimarkdown.models import MathRegion, ImageRef
from scimarkdown.mcp.serializers import math_region_to_dict, image_ref_to_dict


def test_math_region_to_dict():
    region = MathRegion(
        position=42,
        original_text="x² + y²",
        latex=r"x^{2} + y^{2}",
        source_type="unicode",
        confidence=0.85,
        is_inline=True,
    )
    d = math_region_to_dict(region)
    assert d == {
        "original_text": "x² + y²",
        "latex": r"x^{2} + y^{2}",
        "source_type": "unicode",
        "confidence": 0.85,
        "position": 42,
        "is_inline": True,
    }


def test_image_ref_to_dict():
    ref = ImageRef(
        position=0,
        file_path="doc_img00001.png",
        original_format="png",
        width=800,
        height=600,
        ordinal=1,
        reference_label="Figure 1",
        caption="Architecture diagram",
    )
    d = image_ref_to_dict(ref)
    assert d["file_path"] == "doc_img00001.png"
    assert d["width"] == 800
    assert d["ordinal"] == 1
    assert d["reference_label"] == "Figure 1"
    assert d["caption"] == "Architecture diagram"


def test_image_ref_to_dict_minimal():
    ref = ImageRef(position=0, file_path="img.png", original_format="png")
    d = image_ref_to_dict(ref)
    assert d["ordinal"] is None
    assert d["reference_label"] is None
    assert d["caption"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_serializers.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement serializers**

Create `packages/scimarkdown/src/scimarkdown/mcp/serializers.py`:

```python
"""Serialize scimarkdown dataclasses to JSON-compatible dicts for MCP responses."""

from scimarkdown.models import MathRegion, ImageRef


def math_region_to_dict(region: MathRegion) -> dict:
    """Convert a MathRegion to a JSON-serializable dict."""
    return {
        "original_text": region.original_text,
        "latex": region.latex,
        "source_type": region.source_type,
        "confidence": region.confidence,
        "position": region.position,
        "is_inline": region.is_inline,
    }


def image_ref_to_dict(ref: ImageRef) -> dict:
    """Convert an ImageRef to a JSON-serializable dict."""
    return {
        "file_path": ref.file_path,
        "width": ref.width,
        "height": ref.height,
        "position": ref.position,
        "original_format": ref.original_format,
        "ordinal": ref.ordinal,
        "reference_label": ref.reference_label,
        "caption": ref.caption,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_serializers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/mcp/serializers.py tests/unit/mcp/
git commit -m "feat(mcp): add serializers for MathRegion and ImageRef to dict"
```

---

### Task 2: `detect_math` and `format_latex` tools

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/mcp/server.py`
- Create: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/mcp/test_tools.py`:

```python
"""Tests for granular MCP tools.

These test the tool functions directly (not via MCP protocol),
since they are regular Python functions registered as MCP tools.
"""

import json
import pytest

# We import the tool functions after creating the server
from scimarkdown.mcp.server import create_mcp_server

_server = create_mcp_server()


def _get_tool_fn(name: str):
    """Extract a tool function from the MCP server by name."""
    for tool in _server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


class TestDetectMath:
    def test_detect_unicode_math(self):
        fn = _get_tool_fn("detect_math")
        result = fn(text="La suma ∑ᵢ xᵢ ≤ ∫ f(x)dx es conocida.")
        assert isinstance(result, str)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "latex" in data[0]
        assert "confidence" in data[0]

    def test_detect_mathml(self):
        fn = _get_tool_fn("detect_math")
        result = fn(text='<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>')
        data = json.loads(result)
        assert len(data) >= 1
        assert "frac" in data[0]["latex"]

    def test_detect_no_math(self):
        fn = _get_tool_fn("detect_math")
        result = fn(text="This is plain text with no math.")
        data = json.loads(result)
        assert data == []

    def test_detect_with_methods_filter(self):
        fn = _get_tool_fn("detect_math")
        # Only unicode detection, should still find ∑
        result = fn(text="∑ᵢ xᵢ ≤ ∫ f(x)dx", methods=["unicode"])
        data = json.loads(result)
        assert len(data) >= 1


class TestFormatLatex:
    def test_format_standard(self):
        fn = _get_tool_fn("format_latex")
        formulas = [{"latex": "x^{2}", "is_inline": True}]
        result = fn(formulas=json.dumps(formulas), style="standard")
        data = json.loads(result)
        assert data[0]["formatted"] == "$x^{2}$"

    def test_format_github(self):
        fn = _get_tool_fn("format_latex")
        formulas = [{"latex": "x^{2}", "is_inline": True}]
        result = fn(formulas=json.dumps(formulas), style="github")
        data = json.loads(result)
        assert data[0]["formatted"] == "$`x^{2}`$"

    def test_format_block(self):
        fn = _get_tool_fn("format_latex")
        formulas = [{"latex": r"\sum_{i=1}^{n} x_i", "is_inline": False}]
        result = fn(formulas=json.dumps(formulas), style="standard")
        data = json.loads(result)
        assert data[0]["formatted"].startswith("$$")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestDetectMath -v`
Expected: FAIL with `KeyError: "Tool 'detect_math' not found"`

- [ ] **Step 3: Implement detect_math and format_latex tools**

Add to `packages/scimarkdown/src/scimarkdown/mcp/server.py`:

```python
import json
from scimarkdown.math.detector import MathDetector
from scimarkdown.math.formatter import MathFormatter
from scimarkdown.models import MathRegion
from .serializers import math_region_to_dict, image_ref_to_dict
```

Add inside `create_mcp_server()`, after the existing tools:

```python
    @mcp.tool()
    def detect_math(
        text: str,
        methods: Optional[list[str]] = None,
    ) -> str:
        """Detect mathematical formulas in text or HTML.

        Returns a JSON array of detected formula regions with LaTeX conversions.

        Args:
            text: Text or HTML content to analyze for math formulas.
            methods: Optional list of detection methods to use.
                     Values: "unicode", "mathml", "mathjax", "latex".
                     Default: all methods.

        Returns:
            JSON string: list of objects with keys: original_text, latex,
            source_type, confidence, position, is_inline.
        """
        detector = MathDetector()
        regions = detector.detect(text)

        if methods:
            allowed = set(methods)
            # Map source_type to method name
            type_to_method = {
                "unicode": "unicode",
                "mathml": "mathml",
                "mathjax": "mathjax",
                "latex": "latex",
            }
            regions = [
                r for r in regions
                if type_to_method.get(r.source_type, r.source_type) in allowed
            ]

        return json.dumps([math_region_to_dict(r) for r in regions], ensure_ascii=False)

    @mcp.tool()
    def format_latex(
        formulas: str,
        style: str = "standard",
    ) -> str:
        """Format detected math formulas into LaTeX-delimited strings.

        Takes the output of detect_math and formats each formula with the
        chosen LaTeX delimiter style.

        Args:
            formulas: JSON string — array of objects with at least "latex"
                      and "is_inline" keys (as returned by detect_math).
            style: LaTeX delimiter style. "standard" for $...$/$$...$$.
                   "github" for $`...`$ and ```math blocks.

        Returns:
            JSON string: array of objects with "original_text" and "formatted" keys.
        """
        formatter = MathFormatter(style=style)
        items = json.loads(formulas)
        results = []
        for item in items:
            region = MathRegion(
                position=item.get("position", 0),
                original_text=item.get("original_text", ""),
                latex=item["latex"],
                source_type=item.get("source_type", "unknown"),
                confidence=item.get("confidence", 1.0),
                is_inline=item.get("is_inline", True),
            )
            results.append({
                "original_text": region.original_text,
                "formatted": formatter.format(region),
            })
        return json.dumps(results, ensure_ascii=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestDetectMath tests/unit/mcp/test_tools.py::TestFormatLatex -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/mcp/server.py tests/unit/mcp/test_tools.py
git commit -m "feat(mcp): add detect_math and format_latex granular tools"
```

---

### Task 3: `extract_images` tool

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/mcp/server.py`
- Modify: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/mcp/test_tools.py`:

```python
import base64
import io
import os
import tempfile
from pathlib import Path
from PIL import Image


def _create_html_with_image(tmp_dir: Path) -> Path:
    """Create a temporary HTML file with an embedded base64 image."""
    img = Image.new("RGB", (20, 20), "blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    html_path = tmp_dir / "test_doc.html"
    html_path.write_text(
        f'<html><body><img src="data:image/png;base64,{b64}"></body></html>'
    )
    return html_path


class TestExtractImages:
    def test_extract_from_html(self, tmp_path):
        html_path = _create_html_with_image(tmp_path)
        fn = _get_tool_fn("extract_images")
        result = fn(uri=str(html_path), output_dir=str(tmp_path))
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["width"] == 20
        assert data[0]["height"] == 20
        assert "file_path" in data[0]

    def test_extract_no_images(self, tmp_path):
        txt_path = tmp_path / "plain.txt"
        txt_path.write_text("No images here.")
        fn = _get_tool_fn("extract_images")
        result = fn(uri=str(txt_path))
        data = json.loads(result)
        assert data == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestExtractImages -v`
Expected: FAIL

- [ ] **Step 3: Implement extract_images tool**

Add inside `create_mcp_server()`:

```python
    @mcp.tool()
    def extract_images(
        uri: str,
        output_dir: Optional[str] = None,
        dpi: int = 300,
        autocrop: bool = True,
    ) -> str:
        """Extract images from a document and save them to disk.

        Supports PDF, DOCX, PPTX, HTML, EPUB, and Jupyter Notebook formats.
        Images are saved with the naming convention {document}_img{NNNNN}.png.

        Args:
            uri: File path to the document.
            output_dir: Directory to save extracted images.
                        Default: same directory as the source document.
            dpi: Resolution for rasterizing vector graphics (default: 300).
            autocrop: Whether to auto-crop white borders (default: true).

        Returns:
            JSON string: array of image objects with keys: file_path, width,
            height, position, original_format, ordinal, reference_label, caption.
        """
        from scimarkdown.images.extractor import ImageExtractor

        path = Path(uri)
        ext = path.suffix.lower()
        out = Path(output_dir) if output_dir else path.parent

        config = SciMarkdownConfig(
            images_dpi=dpi,
            images_autocrop_whitespace=autocrop,
        )
        extractor = ImageExtractor(
            config=config,
            document_name=path.name,
            output_dir=out,
        )

        _FORMAT_MAP = {
            ".pdf": "extract_from_pdf",
            ".docx": "extract_from_docx",
            ".pptx": "extract_from_pptx",
            ".html": "extract_from_html",
            ".htm": "extract_from_html",
            ".epub": "extract_from_epub",
            ".ipynb": "extract_from_jupyter",
        }

        method_name = _FORMAT_MAP.get(ext)
        if not method_name:
            return json.dumps([])

        with open(uri, "rb") as f:
            method = getattr(extractor, method_name)
            images = method(f)

        return json.dumps([image_ref_to_dict(img) for img in images], ensure_ascii=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestExtractImages -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/mcp/server.py tests/unit/mcp/test_tools.py
git commit -m "feat(mcp): add extract_images granular tool"
```

---

### Task 4: `link_references` and `build_figure_index` tools

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/mcp/server.py`
- Modify: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/mcp/test_tools.py`:

```python
class TestLinkReferences:
    def test_link_basic(self):
        fn = _get_tool_fn("link_references")
        images = [
            {"file_path": "doc_img00001.png", "position": 0, "original_format": "png",
             "width": 100, "height": 100},
            {"file_path": "doc_img00002.png", "position": 1, "original_format": "png",
             "width": 200, "height": 200},
        ]
        result = fn(
            text="As shown in Figure 1, and Figure 2 confirms.",
            images=json.dumps(images),
        )
        data = json.loads(result)
        assert data[0]["ordinal"] == 1
        assert data[0]["reference_label"] == "Figure 1"
        assert data[1]["ordinal"] == 2

    def test_link_spanish(self):
        fn = _get_tool_fn("link_references")
        images = [{"file_path": "img.png", "position": 0, "original_format": "png",
                    "width": 10, "height": 10}]
        result = fn(
            text="Como se ve en la Figura 1.",
            images=json.dumps(images),
        )
        data = json.loads(result)
        assert data[0]["ordinal"] == 1

    def test_link_no_references(self):
        fn = _get_tool_fn("link_references")
        images = [{"file_path": "img.png", "position": 0, "original_format": "png",
                    "width": 10, "height": 10}]
        result = fn(text="No references here.", images=json.dumps(images))
        data = json.loads(result)
        assert data[0]["reference_label"] is None


class TestBuildFigureIndex:
    def test_build_index(self):
        fn = _get_tool_fn("build_figure_index")
        images = [
            {"file_path": "doc_img00001.png", "position": 0, "original_format": "png",
             "width": 100, "height": 100, "ordinal": 1, "reference_label": "Figure 1",
             "caption": "Architecture"},
        ]
        result = fn(images=json.dumps(images))
        assert "## Figure Index" in result
        assert "Architecture" in result
        assert "doc_img00001.png" in result

    def test_build_empty(self):
        fn = _get_tool_fn("build_figure_index")
        result = fn(images=json.dumps([]))
        assert result == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestLinkReferences tests/unit/mcp/test_tools.py::TestBuildFigureIndex -v`
Expected: FAIL

- [ ] **Step 3: Implement link_references and build_figure_index tools**

Add inside `create_mcp_server()`:

```python
    @mcp.tool()
    def link_references(
        text: str,
        images: str,
        patterns: Optional[list[str]] = None,
    ) -> str:
        """Link textual references (e.g. "Figure 1") to extracted images.

        Matches figure/table references in text to image objects by ordinal number.

        Args:
            text: Document text to scan for references.
            images: JSON string — array of image objects (as returned by extract_images).
            patterns: Optional regex patterns for reference detection.
                      Default: built-in patterns for English and Spanish.

        Returns:
            JSON string: array of image objects with ordinal, reference_label,
            and caption populated where matches were found.
        """
        from scimarkdown.images.reference_linker import ReferenceLinker

        config = SciMarkdownConfig()
        if patterns:
            config = config.with_overrides({"references": {"patterns": patterns}})

        linker = ReferenceLinker(config)

        image_dicts = json.loads(images)
        image_refs = [
            ImageRef(
                position=d.get("position", 0),
                file_path=d["file_path"],
                original_format=d.get("original_format", "png"),
                width=d.get("width", 0),
                height=d.get("height", 0),
                ordinal=d.get("ordinal"),
                reference_label=d.get("reference_label"),
                caption=d.get("caption"),
            )
            for d in image_dicts
        ]

        linked = linker.link(text, image_refs)
        return json.dumps([image_ref_to_dict(img) for img in linked], ensure_ascii=False)

    @mcp.tool()
    def build_figure_index(images: str) -> str:
        """Generate a markdown figure index table from a list of images.

        Args:
            images: JSON string — array of image objects (as returned by
                    extract_images or link_references).

        Returns:
            Markdown string with a figure index table, or empty string if
            no images are provided.
        """
        from scimarkdown.images.index_builder import IndexBuilder

        image_dicts = json.loads(images)
        image_refs = [
            ImageRef(
                position=d.get("position", 0),
                file_path=d["file_path"],
                original_format=d.get("original_format", "png"),
                width=d.get("width", 0),
                height=d.get("height", 0),
                ordinal=d.get("ordinal"),
                reference_label=d.get("reference_label"),
                caption=d.get("caption"),
            )
            for d in image_dicts
        ]

        builder = IndexBuilder()
        return builder.build(image_refs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestLinkReferences tests/unit/mcp/test_tools.py::TestBuildFigureIndex -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/mcp/server.py tests/unit/mcp/test_tools.py
git commit -m "feat(mcp): add link_references and build_figure_index granular tools"
```

---

### Task 5: `ocr_formula` tool

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/mcp/server.py`
- Modify: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/mcp/test_tools.py`:

```python
from unittest.mock import patch


class TestOcrFormula:
    def test_ocr_no_engine(self):
        """When no OCR engine is installed, returns error message."""
        fn = _get_tool_fn("ocr_formula")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (50, 50), "white")
            img.save(f, format="PNG")
            tmp_path = f.name

        try:
            result = fn(image_path=tmp_path)
            data = json.loads(result)
            # Should either return a result or an error
            assert "latex" in data or "error" in data
        finally:
            os.unlink(tmp_path)

    @patch("scimarkdown.math.ocr._pix2tex_available", return_value=True)
    def test_ocr_with_mock_engine(self, mock_avail):
        fn = _get_tool_fn("ocr_formula")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new("RGB", (50, 50), "white")
            img.save(f, format="PNG")
            tmp_path = f.name

        try:
            with patch("scimarkdown.math.ocr.MathOCR._run_pix2tex", return_value=("E=mc^{2}", 0.95)):
                result = fn(image_path=tmp_path, engine="pix2tex")
                data = json.loads(result)
                assert data["latex"] == "E=mc^{2}"
                assert data["confidence"] == 0.95
                assert data["engine_used"] == "pix2tex"
        finally:
            os.unlink(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestOcrFormula -v`
Expected: FAIL

- [ ] **Step 3: Implement ocr_formula tool**

Add inside `create_mcp_server()`:

```python
    @mcp.tool()
    def ocr_formula(
        image_path: str,
        engine: str = "auto",
    ) -> str:
        """Recognize a mathematical formula in an image using OCR.

        Requires the [ocr] optional dependency (pix2tex) or [nougat].

        Args:
            image_path: Path to an image file containing a formula.
            engine: OCR engine to use. "auto" selects the best available.
                    Options: "auto", "pix2tex", "nougat".

        Returns:
            JSON string with keys: latex, confidence, engine_used.
            On failure: JSON with "error" key explaining the issue.
        """
        from scimarkdown.math.ocr import MathOCR

        try:
            img = Image.open(image_path)
        except Exception as e:
            return json.dumps({"error": f"Cannot open image: {e}"})

        ocr = MathOCR(engine=engine)
        if not ocr.is_available():
            return json.dumps({
                "error": f"OCR engine '{ocr.engine}' is not available. "
                         f"Install with: pip install scimarkdown[ocr]"
            })

        result = ocr.recognize(img)
        if result is None:
            return json.dumps({"error": "OCR recognition failed"})

        return json.dumps({
            "latex": result.latex,
            "confidence": result.confidence,
            "engine_used": ocr.engine,
        })
```

Also add at the top of `create_mcp_server()`:

```python
    from PIL import Image
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/test_tools.py::TestOcrFormula -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/mcp/server.py tests/unit/mcp/test_tools.py
git commit -m "feat(mcp): add ocr_formula granular tool"
```

---

### Task 6: Full integration test and MCP tool listing

**Files:**
- Modify: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write integration test**

Add to `tests/unit/mcp/test_tools.py`:

```python
class TestToolListing:
    """Verify all 8 tools are registered in the MCP server."""

    EXPECTED_TOOLS = [
        "convert_to_markdown",
        "convert_to_scimarkdown",
        "detect_math",
        "format_latex",
        "extract_images",
        "link_references",
        "build_figure_index",
        "ocr_formula",
    ]

    def test_all_tools_registered(self):
        tool_names = [t.name for t in _server._tool_manager._tools.values()]
        for name in self.EXPECTED_TOOLS:
            assert name in tool_names, f"Tool {name!r} not registered"

    def test_tool_count(self):
        tool_names = [t.name for t in _server._tool_manager._tools.values()]
        assert len(tool_names) == len(self.EXPECTED_TOOLS)


class TestPipelineChaining:
    """Test that tools can be chained: detect → format → compose."""

    def test_detect_then_format(self):
        detect_fn = _get_tool_fn("detect_math")
        format_fn = _get_tool_fn("format_latex")

        # Step 1: Detect
        detected = detect_fn(text="La ecuación x² + y² = z² es famosa.")

        # Step 2: Format
        formatted = format_fn(formulas=detected, style="standard")
        data = json.loads(formatted)
        assert len(data) >= 1
        assert "$" in data[0]["formatted"]

    def test_extract_then_link_then_index(self, tmp_path):
        extract_fn = _get_tool_fn("extract_images")
        link_fn = _get_tool_fn("link_references")
        index_fn = _get_tool_fn("build_figure_index")

        # Create test HTML with image
        html_path = _create_html_with_image(tmp_path)

        # Step 1: Extract
        extracted = extract_fn(uri=str(html_path), output_dir=str(tmp_path))

        # Step 2: Link
        linked = link_fn(
            text="Figure 1 shows the test image.",
            images=extracted,
        )

        # Step 3: Build index
        index = index_fn(images=linked)
        assert "## Figure Index" in index
        assert "Figure 1" in index
```

- [ ] **Step 2: Run all MCP tests**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/mcp/ -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/ --ignore=tests/upstream -q`
Expected: All pass (218 existing + new MCP tests)

- [ ] **Step 4: Commit**

```bash
git add tests/unit/mcp/test_tools.py
git commit -m "test(mcp): add tool listing, count, and pipeline chaining tests"
```

---

## Dependency Graph

```
Task 1 (serializers)
  └── Task 2 (detect_math + format_latex)
  └── Task 3 (extract_images)
  └── Task 4 (link_references + build_figure_index)
  └── Task 5 (ocr_formula)
       └── Task 6 (integration tests + listing)
```

Tasks 2-5 depend on Task 1 but are independent of each other.

## Summary

| Task | Tools added | Files |
|------|-------------|-------|
| 1 | — (serializers) | serializers.py, test_serializers.py |
| 2 | `detect_math`, `format_latex` | server.py, test_tools.py |
| 3 | `extract_images` | server.py, test_tools.py |
| 4 | `link_references`, `build_figure_index` | server.py, test_tools.py |
| 5 | `ocr_formula` | server.py, test_tools.py |
| 6 | — (integration tests) | test_tools.py |

**Total: 6 tasks, ~30 steps, 6 commits. Result: 8 MCP tools (2 existing + 6 new).**
