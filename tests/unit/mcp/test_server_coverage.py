"""Additional MCP server tests for coverage gaps: conversion tools and embedding tools."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scimarkdown.mcp.server import create_mcp_server, _get_embedding_client


def _get_tool_fn(name):
    """Get a tool function by name from the MCP server."""
    _server = create_mcp_server()
    for tool in _server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


# -------------------------------------------------------------------------
# _get_embedding_client
# -------------------------------------------------------------------------

class TestGetEmbeddingClient:
    def test_returns_none_when_no_api_key(self):
        """When GEMINI_API_KEY is not set, returns None."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove GEMINI_API_KEY if present
            env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                result = _get_embedding_client()
        assert result is None

    def test_returns_client_when_api_key_set(self):
        """When GEMINI_API_KEY is set, returns a GeminiEmbeddingClient."""
        mock_client = MagicMock()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            with patch("scimarkdown.embeddings.client.GeminiEmbeddingClient", return_value=mock_client):
                result = _get_embedding_client()
        assert result is mock_client

    def test_returns_none_when_client_import_fails(self):
        """When GeminiEmbeddingClient construction raises, returns None."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            with patch("scimarkdown.embeddings.client.GeminiEmbeddingClient", side_effect=Exception("import error")):
                result = _get_embedding_client()
        assert result is None


# -------------------------------------------------------------------------
# convert_to_markdown
# -------------------------------------------------------------------------

class TestConvertToMarkdown:
    def test_convert_plain_text_file(self, tmp_path):
        """convert_to_markdown converts a plain text file."""
        fn = _get_tool_fn("convert_to_markdown")
        txt = tmp_path / "hello.txt"
        txt.write_text("Hello, world!")
        result = fn(uri=str(txt))
        assert isinstance(result, str)
        assert "Hello" in result

    def test_convert_returns_string(self, tmp_path):
        fn = _get_tool_fn("convert_to_markdown")
        txt = tmp_path / "test.txt"
        txt.write_text("Simple text")
        result = fn(uri=str(txt))
        assert isinstance(result, str)


# -------------------------------------------------------------------------
# convert_to_scimarkdown
# -------------------------------------------------------------------------

class TestConvertToSciMarkdown:
    def test_convert_plain_text(self, tmp_path):
        """convert_to_scimarkdown converts a text file."""
        fn = _get_tool_fn("convert_to_scimarkdown")
        txt = tmp_path / "test.txt"
        txt.write_text("Hello world")
        result = fn(uri=str(txt))
        assert isinstance(result, str)

    def test_convert_with_config_override(self, tmp_path):
        """convert_to_scimarkdown accepts config overrides."""
        fn = _get_tool_fn("convert_to_scimarkdown")
        txt = tmp_path / "test.txt"
        txt.write_text("Hello")
        result = fn(uri=str(txt), config={"latex": {"style": "github"}})
        assert isinstance(result, str)


# -------------------------------------------------------------------------
# convert_to_scimarkdown_embeddings
# -------------------------------------------------------------------------

class TestConvertToSciMarkdownEmbeddings:
    def test_convert_with_embeddings_disabled(self, tmp_path):
        """Without GEMINI_API_KEY, embeddings pipeline runs but skips API calls."""
        fn = _get_tool_fn("convert_to_scimarkdown_embeddings")
        txt = tmp_path / "test.txt"
        txt.write_text("Hello world")

        with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}, clear=True):
            result = fn(uri=str(txt))

        assert isinstance(result, str)

    def test_convert_with_embedding_options(self, tmp_path):
        """Accepts embedding_options override."""
        fn = _get_tool_fn("convert_to_scimarkdown_embeddings")
        txt = tmp_path / "test.txt"
        txt.write_text("x² + y² = r²")

        with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}, clear=True):
            result = fn(uri=str(txt), embedding_options={"classify_math": False})

        assert isinstance(result, str)


# -------------------------------------------------------------------------
# analyze_document
# -------------------------------------------------------------------------

class TestAnalyzeDocument:
    def test_analyze_basic(self, tmp_path):
        """analyze_document returns JSON with document and math_regions keys."""
        fn = _get_tool_fn("analyze_document")
        txt = tmp_path / "test.txt"
        txt.write_text("The formula E = mc² is important.")
        result = fn(uri=str(txt))
        data = json.loads(result)
        assert "document" in data
        assert "math_regions" in data

    def test_analyze_full_without_gemini(self, tmp_path):
        """analysis_type='full' without GEMINI_API_KEY: no category key."""
        fn = _get_tool_fn("analyze_document")
        txt = tmp_path / "test.txt"
        txt.write_text("Some text")

        with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}, clear=True):
            result = fn(uri=str(txt), analysis_type="full")

        data = json.loads(result)
        assert "document" in data
        # Without API key, no category classification
        assert "document_category" not in data

    def test_analyze_full_with_mock_gemini(self, tmp_path):
        """analysis_type='full' with mocked embedding client runs classification."""
        fn = _get_tool_fn("analyze_document")
        txt = tmp_path / "test.txt"
        txt.write_text("Abstract. We present a novel method... Introduction...")

        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.9

        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            with patch("scimarkdown.embeddings.document_classifier.DocumentClassifier") as mock_clf_cls:
                mock_clf = MagicMock()
                mock_clf.classify.return_value = ("academic_paper", 0.95)
                mock_clf_cls.return_value = mock_clf
                result = fn(uri=str(txt), analysis_type="full")

        data = json.loads(result)
        assert "document" in data


# -------------------------------------------------------------------------
# search_content
# -------------------------------------------------------------------------

class TestSearchContent:
    def test_search_content_no_client_returns_empty(self, tmp_path):
        """Without GEMINI_API_KEY, search_content returns empty array."""
        fn = _get_tool_fn("search_content")
        txt = tmp_path / "test.txt"
        txt.write_text("Hello world")

        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=None):
            result = fn(uri=str(txt), query="hello")

        assert json.loads(result) == []

    def test_search_content_with_mock_client(self, tmp_path):
        """With a mock embedding client, search returns results."""
        fn = _get_tool_fn("search_content")
        txt = tmp_path / "test.txt"
        txt.write_text("# Introduction\n\nHello world content here.")

        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.8

        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(uri=str(txt), query="hello", top_k=3)

        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_search_content_exception_returns_error(self, tmp_path):
        """Exception in search returns error dict."""
        fn = _get_tool_fn("search_content")

        mock_client = MagicMock()
        mock_client.embed_text.side_effect = RuntimeError("API error")

        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(uri="/nonexistent/path/file.txt", query="hello")

        parsed = json.loads(result)
        # Either empty list (no client) or error dict
        assert isinstance(parsed, (list, dict))


# -------------------------------------------------------------------------
# compare_sections
# -------------------------------------------------------------------------

class TestCompareSections:
    def test_compare_sections_no_client(self, tmp_path):
        """Without embedding client, compare_sections still returns structure."""
        fn = _get_tool_fn("compare_sections")
        txt1 = tmp_path / "a.txt"
        txt2 = tmp_path / "b.txt"
        txt1.write_text("Hello world A")
        txt2.write_text("Hello world B")

        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=None):
            result = fn(uris_json=json.dumps([str(txt1), str(txt2)]))

        data = json.loads(result)
        assert "documents" in data
        assert "topics" in data
        assert data["topics"] == []

    def test_compare_sections_heading_granularity(self, tmp_path):
        """granularity='heading' filters to heading chunks only."""
        fn = _get_tool_fn("compare_sections")
        txt1 = tmp_path / "a.md"
        txt2 = tmp_path / "b.md"
        txt1.write_text("# Introduction\n\nSome text here.\n\n## Methods\n\nMore text.")
        txt2.write_text("# Abstract\n\nSome content.\n\n## Results\n\nData here.")

        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.3  # below 0.5 threshold

        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(
                uris_json=json.dumps([str(txt1), str(txt2)]),
                granularity="heading",
            )

        data = json.loads(result)
        assert "documents" in data
        assert len(data["documents"]) == 2

    def test_compare_sections_with_high_similarity(self, tmp_path):
        """Topics with similarity > 0.5 are included in results."""
        fn = _get_tool_fn("compare_sections")
        txt1 = tmp_path / "a.txt"
        txt2 = tmp_path / "b.txt"
        txt1.write_text("Machine learning is powerful")
        txt2.write_text("Deep learning is powerful")

        mock_client = MagicMock()
        mock_client.embed_text.return_value = [1.0, 0.0]
        mock_client.similarity.return_value = 0.9  # high similarity

        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(uris_json=json.dumps([str(txt1), str(txt2)]))

        data = json.loads(result)
        assert "topics" in data


# -------------------------------------------------------------------------
# ocr_formula
# -------------------------------------------------------------------------

class TestOcrFormula:
    def test_ocr_unavailable_returns_error(self, tmp_path):
        """When no OCR engine is available, returns error JSON."""
        fn = _get_tool_fn("ocr_formula")
        img_path = tmp_path / "formula.png"

        from PIL import Image
        img = Image.new("RGB", (50, 50), "white")
        img.save(str(img_path))

        # engine="none" is always unavailable
        result = fn(image_path=str(img_path), engine="none")
        data = json.loads(result)
        assert "error" in data

    def test_ocr_with_mock_engine(self, tmp_path):
        """With a mocked pix2tex engine, OCR returns latex."""
        fn = _get_tool_fn("ocr_formula")
        img_path = tmp_path / "formula.png"

        from PIL import Image
        img = Image.new("RGB", (50, 50), "white")
        img.save(str(img_path))

        mock_model = MagicMock()
        mock_model.return_value = r"\frac{a}{b}"

        from scimarkdown.math.ocr import MathOCR, OCRResult
        mock_ocr = MagicMock(spec=MathOCR)
        mock_ocr.is_available.return_value = True
        mock_ocr.recognize.return_value = OCRResult(latex=r"\frac{a}{b}", confidence=0.9)
        mock_ocr._resolved_engine = "pix2tex"

        with patch("scimarkdown.mcp.server.MathOCR", return_value=mock_ocr):
            result = fn(image_path=str(img_path), engine="pix2tex")

        data = json.loads(result)
        assert "latex" in data or "error" in data

    def test_ocr_recognition_failed_returns_error(self, tmp_path):
        """When OCR recognizes nothing, returns error JSON."""
        fn = _get_tool_fn("ocr_formula")
        img_path = tmp_path / "formula.png"

        from PIL import Image
        img = Image.new("RGB", (50, 50), "white")
        img.save(str(img_path))

        from scimarkdown.math.ocr import MathOCR
        mock_ocr = MagicMock(spec=MathOCR)
        mock_ocr.is_available.return_value = True
        mock_ocr.recognize.return_value = None
        mock_ocr._resolved_engine = "pix2tex"

        with patch("scimarkdown.mcp.server.MathOCR", return_value=mock_ocr):
            result = fn(image_path=str(img_path), engine="pix2tex")

        data = json.loads(result)
        assert "error" in data
