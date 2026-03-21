"""Tests for embedding MCP tools."""

from __future__ import annotations

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


class TestToolsExist:
    def test_convert_to_scimarkdown_embeddings_exists(self):
        fn = _get_tool_fn("convert_to_scimarkdown_embeddings")
        assert callable(fn)

    def test_analyze_document_exists(self):
        fn = _get_tool_fn("analyze_document")
        assert callable(fn)

    def test_search_content_exists(self):
        fn = _get_tool_fn("search_content")
        assert callable(fn)

    def test_compare_sections_exists(self):
        fn = _get_tool_fn("compare_sections")
        assert callable(fn)


class TestAnalyzeDocument:
    def test_returns_json_string(self, tmp_path):
        # Create a minimal text file
        doc = tmp_path / "test.txt"
        doc.write_text("Introduction\n\nThis document analyzes equations like E=mc^2.")
        fn = _get_tool_fn("analyze_document")
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=None):
            result = fn(uri=str(doc))
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_result_has_math_regions_key(self, tmp_path):
        doc = tmp_path / "test.txt"
        doc.write_text("Some text.")
        fn = _get_tool_fn("analyze_document")
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=None):
            result = fn(uri=str(doc))
        data = json.loads(result)
        assert "math_regions" in data

    def test_result_has_document_info(self, tmp_path):
        doc = tmp_path / "test.txt"
        doc.write_text("Some text.")
        fn = _get_tool_fn("analyze_document")
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=None):
            result = fn(uri=str(doc))
        data = json.loads(result)
        assert "document" in data


class TestSearchContent:
    def test_returns_json_string(self, tmp_path):
        doc = tmp_path / "test.txt"
        doc.write_text("# Introduction\n\nThis is the introduction.\n\n## Methods\n\nWe used statistics.")
        fn = _get_tool_fn("search_content")
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.8
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(uri=str(doc), query="introduction methods")
        data = json.loads(result)
        assert isinstance(data, list)

    def test_top_k_parameter_accepted(self, tmp_path):
        doc = tmp_path / "test.txt"
        doc.write_text("# A\n\nSome text.\n\n## B\n\nMore text.")
        fn = _get_tool_fn("search_content")
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.7
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(uri=str(doc), query="text", top_k=1)
        data = json.loads(result)
        assert len(data) <= 1

    def test_returns_empty_when_no_client(self, tmp_path):
        doc = tmp_path / "test.txt"
        doc.write_text("Some text.")
        fn = _get_tool_fn("search_content")
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=None):
            result = fn(uri=str(doc), query="anything")
        data = json.loads(result)
        assert isinstance(data, list)


class TestCompareSections:
    def test_returns_json_string(self, tmp_path):
        doc1 = tmp_path / "doc1.txt"
        doc1.write_text("# Introduction\n\nThis is doc1.")
        doc2 = tmp_path / "doc2.txt"
        doc2.write_text("# Introduction\n\nThis is doc2.")
        fn = _get_tool_fn("compare_sections")
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.9
        uris = json.dumps([str(doc1), str(doc2)])
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(uris_json=uris)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_result_has_documents_key(self, tmp_path):
        doc1 = tmp_path / "doc1.txt"
        doc1.write_text("Some content.")
        fn = _get_tool_fn("compare_sections")
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2]
        mock_client.similarity.return_value = 0.5
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=mock_client):
            result = fn(uris_json=json.dumps([str(doc1)]))
        data = json.loads(result)
        assert "documents" in data


class TestConvertToScimarkdownEmbeddings:
    def test_returns_markdown_string(self, tmp_path):
        doc = tmp_path / "test.txt"
        doc.write_text("Hello world, this is a test document.")
        fn = _get_tool_fn("convert_to_scimarkdown_embeddings")
        with patch("scimarkdown.mcp.server._get_embedding_client", return_value=None):
            result = fn(uri=str(doc))
        assert isinstance(result, str)
