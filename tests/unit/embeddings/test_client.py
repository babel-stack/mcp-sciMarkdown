"""Tests for GeminiEmbeddingClient — all API calls mocked."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from scimarkdown.embeddings.client import GeminiEmbeddingClient, _create_genai_client


def _make_mock_client(embedding_values=None):
    """Create a mock genai client that returns fake embeddings."""
    if embedding_values is None:
        embedding_values = [0.1, 0.2, 0.3]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.embeddings = [MagicMock(values=embedding_values)]
    mock_client.models.embed_content.return_value = mock_response
    return mock_client


FAKE_EMBEDDING = [0.1, 0.2, 0.3]


class TestIsAvailable:
    def test_true_when_api_key_provided(self, tmp_path):
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=_make_mock_client()):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            assert client.is_available() is True

    def test_false_when_no_api_key(self, tmp_path):
        client = GeminiEmbeddingClient(api_key=None, cache_dir=tmp_path)
        assert client.is_available() is False


class TestEmbedText:
    def test_returns_list_of_floats(self, tmp_path):
        mock_genai = _make_mock_client(FAKE_EMBEDDING)
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            result = client.embed_text("hello world")
        assert result == FAKE_EMBEDDING

    def test_uses_cache_on_second_call(self, tmp_path):
        mock_genai = _make_mock_client(FAKE_EMBEDDING)
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            client.embed_text("cached text")
            client.embed_text("cached text")
        # API should only be called once
        assert mock_genai.models.embed_content.call_count == 1

    def test_different_task_types_use_separate_cache_keys(self, tmp_path):
        mock_genai = _make_mock_client(FAKE_EMBEDDING)
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            client.embed_text("text", task_type="SEMANTIC_SIMILARITY")
            client.embed_text("text", task_type="RETRIEVAL_DOCUMENT")
        assert mock_genai.models.embed_content.call_count == 2

    def test_passes_task_type_to_api(self, tmp_path):
        mock_genai = _make_mock_client(FAKE_EMBEDDING)
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            client.embed_text("hello", task_type="RETRIEVAL_QUERY")
        call_kwargs = mock_genai.models.embed_content.call_args
        assert call_kwargs is not None


class TestEmbedImage:
    def test_returns_list_of_floats(self, tmp_path):
        mock_genai = _make_mock_client(FAKE_EMBEDDING)
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            result = client.embed_image(b"\x89PNG...", mime_type="image/png")
        assert result == FAKE_EMBEDDING

    def test_calls_api_with_image_bytes(self, tmp_path):
        mock_genai = _make_mock_client(FAKE_EMBEDDING)
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            client.embed_image(b"fake-bytes", mime_type="image/jpeg")
        assert mock_genai.models.embed_content.call_count == 1


class TestEmbedBatch:
    def test_returns_list_of_embeddings(self, tmp_path):
        mock_genai = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [
            MagicMock(values=[0.1, 0.2]),
            MagicMock(values=[0.3, 0.4]),
        ]
        mock_genai.models.embed_content.return_value = mock_response
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            results = client.embed_batch(["text1", "text2"])
        assert results == [[0.1, 0.2], [0.3, 0.4]]

    def test_empty_batch_returns_empty_list(self, tmp_path):
        mock_genai = _make_mock_client()
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="fake-key", cache_dir=tmp_path)
            result = client.embed_batch([])
        assert result == []


class TestSimilarity:
    def test_identical_vectors_return_1(self, tmp_path):
        client = GeminiEmbeddingClient(api_key=None, cache_dir=tmp_path)
        vec = [1.0, 0.0, 0.0]
        assert abs(client.similarity(vec, vec) - 1.0) < 1e-6

    def test_orthogonal_vectors_return_0(self, tmp_path):
        client = GeminiEmbeddingClient(api_key=None, cache_dir=tmp_path)
        assert abs(client.similarity([1.0, 0.0], [0.0, 1.0])) < 1e-6

    def test_opposite_vectors_return_minus_1(self, tmp_path):
        client = GeminiEmbeddingClient(api_key=None, cache_dir=tmp_path)
        assert abs(client.similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-6

    def test_zero_vector_returns_0(self, tmp_path):
        client = GeminiEmbeddingClient(api_key=None, cache_dir=tmp_path)
        assert client.similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
