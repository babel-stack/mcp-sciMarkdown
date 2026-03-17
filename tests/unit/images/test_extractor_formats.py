"""Tests for HTML, EPUB, and Jupyter image extractors."""

from __future__ import annotations

import io
import json
import base64
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from scimarkdown.images.extractor import ImageExtractor
from scimarkdown.config import SciMarkdownConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_png_bytes(width: int = 10, height: int = 10) -> bytes:
    """Create a minimal PNG image and return its raw bytes."""
    img = Image.new("RGB", (width, height), "red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_extractor(tmp_path: Path, document_name: str = "test_doc") -> ImageExtractor:
    return ImageExtractor(
        config=SciMarkdownConfig(),
        document_name=document_name,
        output_dir=tmp_path,
    )


# ---------------------------------------------------------------------------
# HTML extractor tests
# ---------------------------------------------------------------------------


def test_extract_from_html_base64(tmp_path: Path) -> None:
    """A single base64 PNG <img> tag is extracted correctly."""
    extractor = _make_extractor(tmp_path, "test_html")
    png_b64 = base64.b64encode(_create_png_bytes()).decode()
    html = f'<html><body><img src="data:image/png;base64,{png_b64}"></body></html>'
    refs = extractor.extract_from_html(io.BytesIO(html.encode()))
    assert len(refs) == 1
    saved = Path(refs[0].file_path)
    assert saved.exists()
    assert saved.suffix == ".png"


def test_extract_from_html_multiple_images(tmp_path: Path) -> None:
    """Multiple base64 images in one HTML document are all extracted."""
    extractor = _make_extractor(tmp_path, "multi_html")
    png_b64 = base64.b64encode(_create_png_bytes()).decode()
    html = (
        f'<html><body>'
        f'<img src="data:image/png;base64,{png_b64}">'
        f'<img src="data:image/png;base64,{png_b64}">'
        f'</body></html>'
    )
    refs = extractor.extract_from_html(io.BytesIO(html.encode()))
    assert len(refs) == 2
    # Filenames should be unique
    assert refs[0].file_path != refs[1].file_path


def test_extract_from_html_skips_external_src(tmp_path: Path) -> None:
    """<img> tags with external URLs (not data URIs) are skipped."""
    extractor = _make_extractor(tmp_path, "ext_html")
    html = '<html><body><img src="https://example.com/image.png"></body></html>'
    refs = extractor.extract_from_html(io.BytesIO(html.encode()))
    assert refs == []


def test_extract_from_html_no_images(tmp_path: Path) -> None:
    """HTML with no <img> tags returns an empty list."""
    extractor = _make_extractor(tmp_path, "empty_html")
    html = "<html><body><p>No images here.</p></body></html>"
    refs = extractor.extract_from_html(io.BytesIO(html.encode()))
    assert refs == []


# ---------------------------------------------------------------------------
# EPUB extractor tests
# ---------------------------------------------------------------------------


def _make_epub_bytes(image_files: dict[str, bytes]) -> bytes:
    """Build a minimal ZIP/EPUB archive containing the given image files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Always add a META-INF entry (should be skipped by extractor)
        zf.writestr("META-INF/container.xml", "<container/>")
        for name, data in image_files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_extract_from_epub_single_image(tmp_path: Path) -> None:
    """A single PNG inside the EPUB (outside META-INF) is extracted."""
    extractor = _make_extractor(tmp_path, "test_epub")
    png_bytes = _create_png_bytes()
    epub_bytes = _make_epub_bytes({"OEBPS/images/cover.png": png_bytes})
    refs = extractor.extract_from_epub(io.BytesIO(epub_bytes))
    assert len(refs) == 1
    assert Path(refs[0].file_path).exists()


def test_extract_from_epub_skips_meta_inf(tmp_path: Path) -> None:
    """Images inside META-INF/ are skipped."""
    extractor = _make_extractor(tmp_path, "epub_meta")
    png_bytes = _create_png_bytes()
    epub_bytes = _make_epub_bytes(
        {
            "META-INF/cover.png": png_bytes,  # should be skipped
            "OEBPS/images/page.png": png_bytes,  # should be extracted
        }
    )
    refs = extractor.extract_from_epub(io.BytesIO(epub_bytes))
    assert len(refs) == 1


def test_extract_from_epub_multiple_images(tmp_path: Path) -> None:
    """Multiple images across the archive are all extracted."""
    extractor = _make_extractor(tmp_path, "multi_epub")
    png_bytes = _create_png_bytes()
    epub_bytes = _make_epub_bytes(
        {
            "OEBPS/images/fig1.png": png_bytes,
            "OEBPS/images/fig2.png": png_bytes,
            "OEBPS/images/fig3.png": png_bytes,
        }
    )
    refs = extractor.extract_from_epub(io.BytesIO(epub_bytes))
    assert len(refs) == 3


def test_extract_from_epub_no_images(tmp_path: Path) -> None:
    """EPUB with no image files returns an empty list."""
    extractor = _make_extractor(tmp_path, "empty_epub")
    epub_bytes = _make_epub_bytes({"OEBPS/content.opf": b"<package/>"})
    refs = extractor.extract_from_epub(io.BytesIO(epub_bytes))
    assert refs == []


# ---------------------------------------------------------------------------
# Jupyter extractor tests
# ---------------------------------------------------------------------------


def _make_notebook(outputs: list[dict]) -> bytes:
    """Build a minimal .ipynb JSON with one code cell containing *outputs*."""
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
        "cells": [
            {
                "cell_type": "code",
                "source": [],
                "metadata": {},
                "outputs": outputs,
            }
        ],
    }
    return json.dumps(notebook).encode()


def test_extract_from_jupyter(tmp_path: Path) -> None:
    """A single image/png output in a notebook cell is extracted."""
    extractor = _make_extractor(tmp_path, "test_nb")
    png_b64 = base64.b64encode(_create_png_bytes()).decode()
    notebook_bytes = _make_notebook(
        [{"output_type": "display_data", "data": {"image/png": png_b64}}]
    )
    refs = extractor.extract_from_jupyter(io.BytesIO(notebook_bytes))
    assert len(refs) == 1
    assert Path(refs[0].file_path).exists()
    assert refs[0].original_format == "png"


def test_extract_from_jupyter_multiple_outputs(tmp_path: Path) -> None:
    """Multiple image outputs across outputs are all extracted."""
    extractor = _make_extractor(tmp_path, "multi_nb")
    png_b64 = base64.b64encode(_create_png_bytes()).decode()
    notebook_bytes = _make_notebook(
        [
            {"output_type": "display_data", "data": {"image/png": png_b64}},
            {"output_type": "execute_result", "data": {"image/png": png_b64}},
        ]
    )
    refs = extractor.extract_from_jupyter(io.BytesIO(notebook_bytes))
    assert len(refs) == 2


def test_extract_from_jupyter_list_lines(tmp_path: Path) -> None:
    """Notebook image data stored as a list of strings (line-split) is handled."""
    extractor = _make_extractor(tmp_path, "lines_nb")
    png_b64 = base64.b64encode(_create_png_bytes()).decode()
    # Split base64 into chunks as some notebook serializers do
    chunk_size = 76
    b64_lines = [png_b64[i : i + chunk_size] for i in range(0, len(png_b64), chunk_size)]
    notebook_bytes = _make_notebook(
        [{"output_type": "display_data", "data": {"image/png": b64_lines}}]
    )
    refs = extractor.extract_from_jupyter(io.BytesIO(notebook_bytes))
    assert len(refs) == 1


def test_extract_from_jupyter_no_images(tmp_path: Path) -> None:
    """Notebook with no image outputs returns an empty list."""
    extractor = _make_extractor(tmp_path, "empty_nb")
    notebook_bytes = _make_notebook(
        [{"output_type": "stream", "name": "stdout", "text": ["hello\n"]}]
    )
    refs = extractor.extract_from_jupyter(io.BytesIO(notebook_bytes))
    assert refs == []


def test_extract_from_jupyter_empty_cells(tmp_path: Path) -> None:
    """Notebook with no cells returns an empty list without error."""
    extractor = _make_extractor(tmp_path, "nocells_nb")
    notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": []}
    refs = extractor.extract_from_jupyter(io.BytesIO(json.dumps(notebook).encode()))
    assert refs == []
