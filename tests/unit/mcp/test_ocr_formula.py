"""Tests for the ocr_formula MCP tool using mocks."""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from scimarkdown.mcp.server import create_mcp_server


def _get_tool_fn(name):
    _server = create_mcp_server()
    for tool in _server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


def _make_png_file(tmp_path) -> str:
    """Create a minimal 2x2 white PNG in tmp_path and return its path."""
    from PIL import Image

    img = Image.new("RGB", (2, 2), color=(255, 255, 255))
    path = tmp_path / "formula.png"
    img.save(str(path), format="PNG")
    return str(path)


class TestOcrFormula:
    def test_unavailable_engine_returns_error(self, tmp_path):
        fn = _get_tool_fn("ocr_formula")
        image_path = _make_png_file(tmp_path)
        # "none" engine is always unavailable
        result = fn(image_path=image_path, engine="none")
        data = json.loads(result)
        assert "error" in data
        assert "not available" in data["error"].lower() or "none" in data["error"].lower()

    def test_auto_without_pix2tex_returns_error(self, tmp_path):
        fn = _get_tool_fn("ocr_formula")
        image_path = _make_png_file(tmp_path)
        # In this test environment, pix2tex and nougat are not installed,
        # so "auto" should resolve to "none" and return an error.
        result = fn(image_path=image_path, engine="auto")
        data = json.loads(result)
        assert "error" in data

    def test_success_with_mocked_ocr(self, tmp_path):
        fn = _get_tool_fn("ocr_formula")
        image_path = _make_png_file(tmp_path)

        from scimarkdown.math.ocr import OCRResult

        mock_result = OCRResult(latex=r"x^2 + y^2", confidence=0.95)

        with patch("scimarkdown.math.ocr.MathOCR.is_available", return_value=True), \
             patch("scimarkdown.math.ocr.MathOCR.recognize", return_value=mock_result), \
             patch.object(
                 __import__("scimarkdown.math.ocr", fromlist=["MathOCR"]).MathOCR,
                 "_resolved_engine",
                 new="pix2tex",
                 create=True,
             ):
            result = fn(image_path=image_path, engine="pix2tex")
            data = json.loads(result)
            assert data["latex"] == r"x^2 + y^2"
            assert data["confidence"] == 0.95

    def test_recognition_failure_returns_error(self, tmp_path):
        fn = _get_tool_fn("ocr_formula")
        image_path = _make_png_file(tmp_path)

        with patch("scimarkdown.math.ocr.MathOCR.is_available", return_value=True), \
             patch("scimarkdown.math.ocr.MathOCR.recognize", return_value=None):
            result = fn(image_path=image_path, engine="pix2tex")
            data = json.loads(result)
            assert "error" in data
            assert "recognition failed" in data["error"].lower()

    def test_result_is_valid_json(self, tmp_path):
        fn = _get_tool_fn("ocr_formula")
        image_path = _make_png_file(tmp_path)
        result = fn(image_path=image_path, engine="none")
        # Should parse without exception
        data = json.loads(result)
        assert isinstance(data, dict)
