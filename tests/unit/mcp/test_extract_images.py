"""Tests for the extract_images MCP tool."""

import base64
import io
import json
import tempfile
from pathlib import Path

import pytest

from scimarkdown.mcp.server import create_mcp_server


def _get_tool_fn(name):
    _server = create_mcp_server()
    for tool in _server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


def _make_minimal_png() -> bytes:
    """Return a minimal valid 1x1 white PNG as bytes."""
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGB", (2, 2), color=(255, 255, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_html_with_embedded_png() -> str:
    """Return HTML with a base64-embedded PNG img tag."""
    png_bytes = _make_minimal_png()
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f'<html><body><img src="data:image/png;base64,{b64}"/></body></html>'


class TestExtractImages:
    def test_extract_from_html(self, tmp_path):
        fn = _get_tool_fn("extract_images")
        html_content = _make_html_with_embedded_png()
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)
        output_dir = str(tmp_path / "images")

        result = fn(uri=str(html_file), output_dir=output_dir)
        refs = json.loads(result)

        assert isinstance(refs, list)
        assert len(refs) == 1
        ref = refs[0]
        assert ref["original_format"] == "png"
        assert ref["width"] == 2
        assert ref["height"] == 2
        assert Path(ref["file_path"]).exists()

    def test_extract_returns_json_array(self, tmp_path):
        fn = _get_tool_fn("extract_images")
        html_content = "<html><body>no images</body></html>"
        html_file = tmp_path / "empty.html"
        html_file.write_text(html_content)
        output_dir = str(tmp_path / "images")

        result = fn(uri=str(html_file), output_dir=output_dir)
        refs = json.loads(result)
        assert isinstance(refs, list)
        assert refs == []

    def test_extract_multiple_images(self, tmp_path):
        fn = _get_tool_fn("extract_images")
        png_bytes = _make_minimal_png()
        b64 = base64.b64encode(png_bytes).decode("ascii")
        html_content = (
            f'<html><body>'
            f'<img src="data:image/png;base64,{b64}"/>'
            f'<img src="data:image/png;base64,{b64}"/>'
            f'</body></html>'
        )
        html_file = tmp_path / "multi.html"
        html_file.write_text(html_content)
        output_dir = str(tmp_path / "images")

        result = fn(uri=str(html_file), output_dir=output_dir)
        refs = json.loads(result)
        assert len(refs) == 2

    def test_result_dict_has_required_keys(self, tmp_path):
        fn = _get_tool_fn("extract_images")
        html_content = _make_html_with_embedded_png()
        html_file = tmp_path / "keys.html"
        html_file.write_text(html_content)
        output_dir = str(tmp_path / "images")

        result = fn(uri=str(html_file), output_dir=output_dir)
        refs = json.loads(result)
        keys = {"position", "file_path", "original_format", "width", "height",
                "caption", "reference_label", "ordinal"}
        assert keys.issubset(refs[0].keys())

    def test_unsupported_format_raises(self, tmp_path):
        fn = _get_tool_fn("extract_images")
        bogus = tmp_path / "doc.xyz"
        bogus.write_text("content")

        with pytest.raises(ValueError, match="Unsupported file format"):
            fn(uri=str(bogus))
