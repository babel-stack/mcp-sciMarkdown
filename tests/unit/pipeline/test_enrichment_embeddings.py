"""Tests for embeddings integration in the enrichment pipeline."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.pipeline.enrichment import EnrichmentPipeline, _create_embedding_client
from scimarkdown.models import MathRegion, ImageRef


def _make_config(enabled=True, classify_math=True, semantic_linking=True):
    return SciMarkdownConfig(
        embeddings_enabled=enabled,
        embeddings_classify_math=classify_math,
        embeddings_semantic_linking=semantic_linking,
        embeddings_api_key_env="GEMINI_API_KEY",
    )


def _make_mock_embedding_client():
    client = MagicMock()
    client.is_available.return_value = True
    return client


class TestCreateEmbeddingClient:
    def test_returns_none_when_disabled(self):
        config = SciMarkdownConfig(embeddings_enabled=False)
        result = _create_embedding_client(config)
        assert result is None

    def test_returns_none_when_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        config = SciMarkdownConfig(embeddings_enabled=True, embeddings_api_key_env="GEMINI_API_KEY")
        result = _create_embedding_client(config)
        assert result is None

    def test_returns_client_when_api_key_present(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        config = SciMarkdownConfig(
            embeddings_enabled=True,
            embeddings_api_key_env="GEMINI_API_KEY",
            embeddings_cache_dir=str(tmp_path),
        )
        mock_client = _make_mock_embedding_client()
        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=MagicMock()):
            result = _create_embedding_client(config)
        assert result is not None


class TestEnrichWithEmbeddings:
    def _run_enrich(self, config, mock_client):
        """Run enrich() with a mocked embedding client."""
        pipeline = EnrichmentPipeline(config=config)
        source = io.BytesIO(b"fake content")
        # Use LaTeX delimiters that MathDetector can detect
        markdown = r"# Test" + "\n\n" + r"The formula \(x^2 + y^2\) is important."
        with patch("scimarkdown.pipeline.enrichment._create_embedding_client", return_value=mock_client):
            return pipeline.enrich(
                base_markdown=markdown,
                source_stream=source,
                file_extension=".txt",
                document_name="test.txt",
                output_dir=Path("/tmp"),
            )

    def test_enrich_runs_without_embedding_client(self):
        config = SciMarkdownConfig(embeddings_enabled=False)
        result = self._run_enrich(config, None)
        assert result is not None

    def test_math_classifier_called_when_classify_math_enabled(self):
        config = _make_config(classify_math=True, semantic_linking=False)
        mock_client = _make_mock_embedding_client()
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = []
        mock_cls = MagicMock(return_value=mock_classifier)
        with patch("scimarkdown.embeddings.math_classifier.MathClassifier", mock_cls):
            self._run_enrich(config, mock_client)
        mock_classifier.classify.assert_called_once()

    def test_math_classifier_not_called_when_disabled(self):
        config = _make_config(classify_math=False, semantic_linking=False)
        mock_client = _make_mock_embedding_client()
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = []
        mock_cls = MagicMock(return_value=mock_classifier)
        with patch("scimarkdown.embeddings.math_classifier.MathClassifier", mock_cls):
            self._run_enrich(config, mock_client)
        mock_classifier.classify.assert_not_called()

    def test_semantic_linker_called_when_enabled(self):
        config = _make_config(classify_math=False, semantic_linking=True)
        mock_client = _make_mock_embedding_client()
        mock_linker = MagicMock()
        mock_linker.link.return_value = []
        mock_cls = MagicMock(return_value=mock_linker)
        with patch("scimarkdown.embeddings.semantic_linker.SemanticLinker", mock_cls):
            self._run_enrich(config, mock_client)
        mock_linker.link.assert_called_once()

    def test_semantic_linker_not_called_when_disabled(self):
        config = _make_config(classify_math=False, semantic_linking=False)
        mock_client = _make_mock_embedding_client()
        mock_linker = MagicMock()
        mock_linker.link.return_value = []
        mock_cls = MagicMock(return_value=mock_linker)
        with patch("scimarkdown.embeddings.semantic_linker.SemanticLinker", mock_cls):
            self._run_enrich(config, mock_client)
        mock_linker.link.assert_not_called()

    def test_graceful_degradation_on_classifier_error(self):
        config = _make_config(classify_math=True, semantic_linking=False)
        mock_client = _make_mock_embedding_client()
        mock_classifier = MagicMock()
        mock_classifier.classify.side_effect = RuntimeError("API down")
        mock_cls = MagicMock(return_value=mock_classifier)
        with patch("scimarkdown.embeddings.math_classifier.MathClassifier", mock_cls):
            # Should not raise
            result = self._run_enrich(config, mock_client)
        assert result is not None
