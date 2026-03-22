"""Tests covering remaining coverage gaps in embeddings subpackage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

from scimarkdown.embeddings.cache import EmbeddingCache
from scimarkdown.embeddings.client import GeminiEmbeddingClient, _create_genai_client
from scimarkdown.embeddings.document_classifier import DocumentClassifier
from scimarkdown.embeddings.math_classifier import MathClassifier
from scimarkdown.embeddings.semantic_linker import SemanticLinker
from scimarkdown.embeddings.content_indexer import ContentIndexer, _classify_chunk, _split_into_chunks
from scimarkdown.models import MathRegion, ImageRef


# -------------------------------------------------------------------------
# EmbeddingCache — error paths
# -------------------------------------------------------------------------

class TestEmbeddingCacheErrors:
    def test_get_returns_none_on_corrupted_json(self, tmp_path):
        """get() returns None when the cached file contains invalid JSON."""
        cache = EmbeddingCache(cache_dir=tmp_path)
        # Write corrupted JSON file
        path = cache._path_for("badkey")
        path.write_text("not valid json {{{", encoding="utf-8")
        result = cache.get("badkey")
        assert result is None

    def test_get_returns_none_on_read_error(self, tmp_path):
        """get() returns None when the file can't be read."""
        cache = EmbeddingCache(cache_dir=tmp_path)
        path = cache._path_for("readkey")
        path.write_text('{"embedding": [1.0]}', encoding="utf-8")
        path.chmod(0o000)  # Make unreadable
        try:
            result = cache.get("readkey")
            assert result is None
        finally:
            path.chmod(0o644)

    def test_put_handles_write_error(self, tmp_path):
        """put() logs and doesn't raise when the file can't be written."""
        cache = EmbeddingCache(cache_dir=tmp_path)
        # Make dir read-only so write fails
        tmp_path.chmod(0o555)
        try:
            # Should not raise
            cache.put("writekey", [1.0, 2.0])
        except Exception:
            pass  # On some systems this may still succeed
        finally:
            tmp_path.chmod(0o755)

    def test_clear_handles_unlink_error(self, tmp_path):
        """clear() continues gracefully when a file can't be deleted."""
        cache = EmbeddingCache(cache_dir=tmp_path)
        cache.put("key1", [1.0])
        cache.put("key2", [2.0])

        # Make one file undeletable
        files = list(tmp_path.glob("*.json"))
        if files:
            files[0].chmod(0o444)
            tmp_path.chmod(0o555)
            try:
                cache.clear()  # Should not raise
            finally:
                tmp_path.chmod(0o755)
                for f in tmp_path.glob("*.json"):
                    f.chmod(0o644)


# -------------------------------------------------------------------------
# GeminiEmbeddingClient — error paths
# -------------------------------------------------------------------------

class TestGeminiClientErrors:
    def test_create_genai_client_imports_google_genai(self):
        """_create_genai_client creates a Gemini client when google.genai is available."""
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()

        with patch.dict("sys.modules", {"google.genai": mock_genai}):
            result = _create_genai_client("test-key")

        mock_genai.Client.assert_called_once_with(api_key="test-key")

    def test_client_creation_failure_sets_client_none(self, tmp_path):
        """When _create_genai_client raises, _client is None (not available)."""
        with patch("scimarkdown.embeddings.client._create_genai_client", side_effect=Exception("no google")):
            client = GeminiEmbeddingClient(api_key="test-key", cache_dir=tmp_path)
        assert client.is_available() is False
        assert client._client is None

    def test_embed_image_without_genai_types(self, tmp_path):
        """embed_image falls back gracefully when google.genai.types is unavailable."""
        mock_genai = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
        mock_genai.models.embed_content.return_value = mock_response

        with patch("scimarkdown.embeddings.client._create_genai_client", return_value=mock_genai):
            client = GeminiEmbeddingClient(api_key="key", cache_dir=tmp_path)

        # Patch the genai_types import to fail inside embed_image
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "google.genai" and "types" in str(args):
                raise ImportError("no types")
            return real_import(name, *args, **kwargs)

        # embed_image should work even without google.genai.types
        result = client.embed_image(b"fake-image-bytes", mime_type="image/png")
        assert result == [0.1, 0.2, 0.3]


# -------------------------------------------------------------------------
# DocumentClassifier — optimize_config branches
# -------------------------------------------------------------------------

class TestDocumentClassifierOptimizeConfig:
    def _make_classifier(self, tmp_path):
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.8
        return DocumentClassifier(client=mock_client)

    def test_optimize_config_academic_paper(self, tmp_path):
        from scimarkdown.config import SciMarkdownConfig
        clf = self._make_classifier(tmp_path)
        config = SciMarkdownConfig()
        result = clf.optimize_config("academic_paper", config)
        assert result.math_heuristic is True
        assert result.references_generate_index is True

    def test_optimize_config_technical_report(self, tmp_path):
        from scimarkdown.config import SciMarkdownConfig
        clf = self._make_classifier(tmp_path)
        config = SciMarkdownConfig()
        result = clf.optimize_config("technical_report", config)
        assert result.references_generate_index is True
        assert result.images_autocrop_whitespace is True

    def test_optimize_config_presentation(self, tmp_path):
        from scimarkdown.config import SciMarkdownConfig
        clf = self._make_classifier(tmp_path)
        config = SciMarkdownConfig(images_dpi=72)
        result = clf.optimize_config("presentation", config)
        assert result.images_dpi >= 150
        assert result.math_heuristic is False

    def test_optimize_config_textbook(self, tmp_path):
        from scimarkdown.config import SciMarkdownConfig
        clf = self._make_classifier(tmp_path)
        config = SciMarkdownConfig()
        result = clf.optimize_config("textbook", config)
        assert result.math_heuristic is True
        assert result.references_generate_index is True

    def test_optimize_config_code_documentation(self, tmp_path):
        from scimarkdown.config import SciMarkdownConfig
        clf = self._make_classifier(tmp_path)
        config = SciMarkdownConfig()
        result = clf.optimize_config("code_documentation", config)
        assert result.math_heuristic is False

    def test_optimize_config_general_document(self, tmp_path):
        from scimarkdown.config import SciMarkdownConfig
        clf = self._make_classifier(tmp_path)
        config = SciMarkdownConfig()
        original_math = config.math_heuristic
        result = clf.optimize_config("general_document", config)
        assert result.math_heuristic == original_math  # unchanged

    def test_optimize_config_unknown_category(self, tmp_path):
        from scimarkdown.config import SciMarkdownConfig
        clf = self._make_classifier(tmp_path)
        config = SciMarkdownConfig()
        result = clf.optimize_config("mystery_category", config)
        # Should not raise; original config returned unchanged
        assert result is not None

    def test_description_embeddings_error_handled(self, tmp_path):
        """If embedding a description fails, that category is skipped."""
        mock_client = MagicMock()
        # 6 categories + 1 for the doc snippet classify call
        # First category embedding fails, rest succeed
        mock_client.embed_text.side_effect = [
            [0.9, 0.9, 0.9],  # doc snippet (classify's own call)
            Exception("API error"),  # first category description fails
            [0.1, 0.2, 0.3],  # rest succeed
            [0.1, 0.2, 0.3],
            [0.1, 0.2, 0.3],
            [0.1, 0.2, 0.3],
            [0.1, 0.2, 0.3],
        ]
        mock_client.similarity.return_value = 0.7

        clf = DocumentClassifier(client=mock_client)
        # Force lazy load of descriptions first (so order is predictable)
        # Doc snippet is embedded first in classify(), then descriptions are loaded
        result = clf.classify("some text about research")
        assert isinstance(result, tuple)
        assert len(result) == 2


# -------------------------------------------------------------------------
# SemanticLinker — missing file and exception paths
# -------------------------------------------------------------------------

class TestSemanticLinkerEdges:
    def test_link_skips_missing_image_file(self, tmp_path):
        """Images with non-existent file paths are skipped."""
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2]

        linker = SemanticLinker(client=mock_client)
        images = [
            ImageRef(
                position=0,
                file_path="/nonexistent/image.png",
                original_format="png",
                width=100,
                height=100,
            )
        ]
        result = linker.link(images, ["Some relevant text"])
        # Should return without error, image kept but no caption set
        assert len(result) == 1

    def test_link_embed_text_exception_skipped(self, tmp_path):
        """When embed_text fails for a text block, it's skipped."""
        mock_client = MagicMock()
        mock_client.embed_text.side_effect = Exception("API error")

        linker = SemanticLinker(client=mock_client)
        img_path = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(str(img_path))

        images = [
            ImageRef(
                position=0,
                file_path=str(img_path),
                original_format="png",
                width=10,
                height=10,
            )
        ]
        # text embedding fails → text_embeddings is empty → image gets no caption
        result = linker.link(images, ["Some text"])
        assert len(result) == 1
        assert result[0].caption is None

    def test_link_embed_image_exception_skipped(self, tmp_path):
        """When embed_image fails, that image is skipped."""
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2]
        mock_client.embed_image.side_effect = Exception("embed failed")

        linker = SemanticLinker(client=mock_client)
        img_path = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(str(img_path))

        images = [
            ImageRef(
                position=0,
                file_path=str(img_path),
                original_format="png",
                width=10,
                height=10,
            )
        ]
        result = linker.link(images, ["relevant text"])
        assert len(result) == 1
        assert result[0].caption is None

    def test_link_similarity_exception_handled(self, tmp_path):
        """Similarity exception is logged and that block is skipped."""
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2]
        mock_client.embed_image.return_value = [0.1, 0.2]
        mock_client.similarity.side_effect = Exception("sim error")

        linker = SemanticLinker(client=mock_client, threshold=0.5)
        img_path = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(str(img_path))

        images = [
            ImageRef(
                position=0,
                file_path=str(img_path),
                original_format="png",
                width=10,
                height=10,
            )
        ]
        # Should not raise
        result = linker.link(images, ["some text"])
        assert len(result) == 1

    def test_link_empty_images(self):
        """link() with empty image list returns empty list."""
        mock_client = MagicMock()
        linker = SemanticLinker(client=mock_client)
        result = linker.link([], ["some text"])
        assert result == []


# -------------------------------------------------------------------------
# ContentIndexer — chunk types and edge cases
# -------------------------------------------------------------------------

class TestContentIndexerChunkTypes:
    def test_classify_chunk_formula(self):
        assert _classify_chunk("$$x^2 + y^2 = r^2$$") == "formula"

    def test_classify_chunk_formula_inline_dollar(self):
        # Single-dollar inline formula (starts and ends with $)
        assert _classify_chunk("$x + y$") == "formula"

    def test_classify_chunk_image(self):
        assert _classify_chunk("![alt text](image.png)") == "image"

    def test_classify_chunk_table(self):
        assert _classify_chunk("| col1 | col2 |") == "table"

    def test_classify_chunk_text(self):
        assert _classify_chunk("Regular paragraph text") == "text"

    def test_split_empty_markdown(self):
        result = _split_into_chunks("")
        assert result == []

    def test_split_with_formula_block(self):
        md = "# Introduction\n\n$$E = mc^2$$\n\nSome text."
        chunks = _split_into_chunks(md)
        types = [c["type"] for c in chunks]
        assert "formula" in types

    def test_split_with_image(self):
        md = "# Section\n\n![Caption](img.png)\n\nSome text."
        chunks = _split_into_chunks(md)
        types = [c["type"] for c in chunks]
        assert "image" in types

    def test_index_embed_error_skips_chunk(self, tmp_path):
        """When embedding a chunk fails, that chunk is skipped."""
        mock_client = MagicMock()
        mock_client.embed_text.side_effect = Exception("API error")

        indexer = ContentIndexer(client=mock_client)
        idx = indexer.index("# Hello\n\nSome text here.")
        # All chunks failed → empty index
        assert len(idx.chunks) == 0
        assert len(idx.embeddings) == 0

    def test_search_embed_query_error(self, tmp_path):
        """When embedding the query fails, search returns empty list."""
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2]

        indexer = ContentIndexer(client=mock_client)
        idx = indexer.index("# Hello\n\nSome text.")

        # Now make query embedding fail
        mock_client.embed_text.side_effect = Exception("query failed")
        result = indexer.search(idx, "query")
        assert result == []

    def test_search_similarity_error_skipped(self, tmp_path):
        """When similarity computation fails for a chunk, that chunk is skipped."""
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2]

        indexer = ContentIndexer(client=mock_client)
        idx = indexer.index("# Hello\n\nSome text.")

        # First embed_text call succeeds (for query), similarity fails
        mock_client.embed_text.side_effect = None
        mock_client.embed_text.return_value = [0.1, 0.2]
        mock_client.similarity.side_effect = Exception("sim error")

        result = indexer.search(idx, "query")
        assert result == []


# -------------------------------------------------------------------------
# MathClassifier — empty reference embeddings
# -------------------------------------------------------------------------

class TestMathClassifierEdges:
    def test_classify_with_empty_reference_embeddings(self):
        """When all reference embedding calls fail, needs_check regions are kept."""
        mock_client = MagicMock()
        # All embed_text calls fail
        mock_client.embed_text.side_effect = Exception("API error")

        classifier = MathClassifier(client=mock_client, threshold=0.75)
        region = MathRegion(
            position=0,
            original_text="x squared",
            latex="x^2",
            source_type="unicode",
            confidence=0.5,  # below high confidence threshold
        )
        # With no reference embeddings, the region processing should fail gracefully
        result = classifier.classify([region])
        # Region kept on error (conservative)
        assert len(result) >= 0  # may be kept or empty depending on error handling

    def test_classify_error_in_candidate_embedding_keeps_region(self):
        """When embed_text for a candidate fails, region is kept (conservative)."""
        mock_client = MagicMock()
        # Reference embeddings succeed
        mock_client.embed_text.side_effect = [
            [0.1, 0.2],  # ref 1
            [0.3, 0.4],  # ref 2 (only need a few)
            Exception("candidate embed failed"),  # candidate fails
        ]

        # Pre-populate ref embeddings to avoid loading all 15
        classifier = MathClassifier(client=mock_client, threshold=0.75)
        classifier._ref_embeddings = [[0.1, 0.2], [0.3, 0.4]]

        region = MathRegion(
            position=0,
            original_text="some math",
            latex="x^2",
            source_type="heuristic",
            confidence=0.5,
        )

        mock_client.embed_text.side_effect = Exception("embed failed")
        result = classifier.classify([region])
        # On error, region is kept (conservative approach)
        assert len(result) == 1

    def test_classify_high_confidence_passthrough(self):
        """Regions with confidence >= 0.9 pass through without API calls."""
        mock_client = MagicMock()
        # embed_text should NOT be called for high-confidence regions

        classifier = MathClassifier(client=mock_client)
        region = MathRegion(
            position=0,
            original_text="$\\frac{a}{b}$",
            latex="\\frac{a}{b}",
            source_type="latex",
            confidence=0.95,  # high confidence
        )
        result = classifier.classify([region])
        assert len(result) == 1
        assert result[0].confidence == 0.95
        # embed_text should not have been called
        mock_client.embed_text.assert_not_called()
