"""Tests for enrichment pipeline coverage gaps."""

import io
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.pipeline.enrichment import EnrichmentPipeline, _create_embedding_client
from scimarkdown.models import EnrichedResult, MathRegion, ImageRef


# -------------------------------------------------------------------------
# _create_embedding_client
# -------------------------------------------------------------------------

class TestCreateEmbeddingClient:
    def test_returns_none_when_embeddings_disabled(self):
        config = SciMarkdownConfig(embeddings_enabled=False)
        result = _create_embedding_client(config)
        assert result is None

    def test_returns_none_when_no_api_key(self):
        config = SciMarkdownConfig(
            embeddings_enabled=True,
            embeddings_api_key_env="NONEXISTENT_KEY_XYZ123",
        )
        with patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != "NONEXISTENT_KEY_XYZ123"}, clear=True):
            result = _create_embedding_client(config)
        assert result is None

    def test_returns_client_when_key_present(self, tmp_path):
        config = SciMarkdownConfig(
            embeddings_enabled=True,
            embeddings_api_key_env="TEST_GEMINI_KEY",
            embeddings_cache_dir=str(tmp_path),
        )
        mock_client = MagicMock()
        with patch.dict(os.environ, {"TEST_GEMINI_KEY": "fake-key"}):
            with patch("scimarkdown.embeddings.client.GeminiEmbeddingClient", return_value=mock_client):
                result = _create_embedding_client(config)
        assert result is mock_client

    def test_returns_none_when_client_creation_fails(self, tmp_path):
        config = SciMarkdownConfig(
            embeddings_enabled=True,
            embeddings_api_key_env="TEST_GEMINI_KEY",
            embeddings_cache_dir=str(tmp_path),
        )
        with patch.dict(os.environ, {"TEST_GEMINI_KEY": "fake-key"}):
            with patch("scimarkdown.embeddings.client.GeminiEmbeddingClient", side_effect=Exception("import error")):
                result = _create_embedding_client(config)
        assert result is None


# -------------------------------------------------------------------------
# EnrichmentPipeline.enrich — various paths
# -------------------------------------------------------------------------

class TestEnrichmentPipelineEnrich:
    def _make_pipeline(self, **kwargs) -> EnrichmentPipeline:
        config = SciMarkdownConfig(**kwargs)
        return EnrichmentPipeline(config)

    def test_enrich_basic(self, tmp_path):
        """Basic enrichment with no math or images."""
        pipeline = self._make_pipeline(math_heuristic=False, filters_enabled=False)
        stream = io.BytesIO(b"Hello world")
        result = pipeline.enrich(
            base_markdown="Hello world",
            source_stream=stream,
            file_extension=".txt",
            document_name="test",
            output_dir=tmp_path,
        )
        assert isinstance(result, EnrichedResult)
        assert result.base_markdown == "Hello world"

    def test_enrich_with_math_detection(self, tmp_path):
        """Math heuristic is applied when enabled."""
        pipeline = self._make_pipeline(math_heuristic=True, filters_enabled=False)
        stream = io.BytesIO(b"")
        result = pipeline.enrich(
            base_markdown=r"The formula \(x^2 + y^2\) is important.",
            source_stream=stream,
            file_extension=".txt",
            document_name="test",
            output_dir=tmp_path,
        )
        assert isinstance(result, EnrichedResult)

    def test_enrich_with_llm_fallback(self, tmp_path):
        """LLM fallback is applied to low-confidence math regions."""
        pipeline = self._make_pipeline(
            math_heuristic=True,
            llm_enabled=True,
            llm_api_key_env="TEST_LLM_KEY",
            math_confidence_threshold=0.99,  # everything is "low confidence"
            filters_enabled=False,
        )

        with patch("scimarkdown.llm.fallback._call_openai") as mock_call:
            mock_call.return_value = r"x^{2}"
            with patch.dict(os.environ, {"TEST_LLM_KEY": "fake-key"}):
                stream = io.BytesIO(b"")
                result = pipeline.enrich(
                    base_markdown=r"The formula \(x^2\) here.",
                    source_stream=stream,
                    file_extension=".txt",
                    document_name="test",
                    output_dir=tmp_path,
                )
        assert isinstance(result, EnrichedResult)

    def test_enrich_with_embeddings_math_classifier(self, tmp_path):
        """Embeddings path: math classifier is applied when client available."""
        config = SciMarkdownConfig(
            math_heuristic=True,
            embeddings_enabled=True,
            embeddings_classify_math=True,
            embeddings_api_key_env="GEMINI_API_KEY",
            embeddings_cache_dir=str(tmp_path),
            filters_enabled=False,
        )
        pipeline = EnrichmentPipeline(config)

        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.9

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            with patch("scimarkdown.embeddings.client.GeminiEmbeddingClient", return_value=mock_client):
                stream = io.BytesIO(b"")
                result = pipeline.enrich(
                    base_markdown=r"The formula \(E = mc^2\) here.",
                    source_stream=stream,
                    file_extension=".txt",
                    document_name="test",
                    output_dir=tmp_path,
                )
        assert isinstance(result, EnrichedResult)

    def test_enrich_with_filters_pdf(self, tmp_path):
        """Filters are applied to PDF streams."""
        fitz = pytest.importorskip("fitz", reason="PyMuPDF required")

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 50), "Header")
        page.insert_text((72, 300), "Body text content")
        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        doc.close()
        pdf_bytes.seek(0)

        pipeline = self._make_pipeline(
            math_heuristic=False,
            filters_enabled=True,
        )
        result = pipeline.enrich(
            base_markdown="Header\n\nBody text content",
            source_stream=pdf_bytes,
            file_extension=".pdf",
            document_name="test",
            output_dir=tmp_path,
        )
        assert isinstance(result, EnrichedResult)

    def test_enrich_with_image_extraction(self, tmp_path):
        """Images are extracted for supported formats (EPUB)."""
        import zipfile
        from PIL import Image
        import io as _io

        img = Image.new("RGB", (50, 50), "green")
        img_buf = _io.BytesIO()
        img.save(img_buf, format="PNG")
        img_bytes = img_buf.getvalue()

        epub_path = tmp_path / "test.epub"
        with zipfile.ZipFile(epub_path, "w") as zf:
            zf.writestr("OEBPS/img.png", img_bytes)

        pipeline = self._make_pipeline(
            math_heuristic=False,
            filters_enabled=False,
        )
        with open(epub_path, "rb") as f:
            result = pipeline.enrich(
                base_markdown="Some text",
                source_stream=f,
                file_extension=".epub",
                document_name="test",
                output_dir=tmp_path,
            )
        assert isinstance(result, EnrichedResult)

    def test_enrich_with_semantic_linking(self, tmp_path):
        """Semantic linker is applied when embeddings are enabled."""
        from PIL import Image
        import io as _io

        # Create a real image file
        img_path = tmp_path / "img.png"
        Image.new("RGB", (20, 20)).save(str(img_path))

        config = SciMarkdownConfig(
            math_heuristic=False,
            embeddings_enabled=True,
            embeddings_semantic_linking=True,
            embeddings_api_key_env="GEMINI_API_KEY",
            embeddings_cache_dir=str(tmp_path),
            filters_enabled=False,
        )
        pipeline = EnrichmentPipeline(config)

        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2]
        mock_client.embed_image.return_value = [0.1, 0.2]
        mock_client.similarity.return_value = 0.9

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            with patch("scimarkdown.embeddings.client.GeminiEmbeddingClient", return_value=mock_client):
                stream = io.BytesIO(b"")
                result = pipeline.enrich(
                    base_markdown="Some relevant text\n\nAnother paragraph.",
                    source_stream=stream,
                    file_extension=".txt",
                    document_name="test",
                    output_dir=tmp_path,
                )
        assert isinstance(result, EnrichedResult)

    def test_enrich_math_detection_failure_graceful(self, tmp_path):
        """Math detection failure is caught and enrichment continues."""
        pipeline = self._make_pipeline(math_heuristic=True, filters_enabled=False)

        with patch("scimarkdown.math.detector.MathDetector.detect", side_effect=Exception("detector error")):
            stream = io.BytesIO(b"")
            result = pipeline.enrich(
                base_markdown=r"\(x^2\)",
                source_stream=stream,
                file_extension=".txt",
                document_name="test",
                output_dir=tmp_path,
            )
        assert isinstance(result, EnrichedResult)
        assert result.math_regions == []


# -------------------------------------------------------------------------
# CompositionPipeline — edge cases
# -------------------------------------------------------------------------

class TestCompositionPipelineEdges:
    def test_compose_with_images_and_figure_index(self, tmp_path):
        """Figure index is appended when references_generate_index=True."""
        from scimarkdown.pipeline.composition import CompositionPipeline
        from scimarkdown.models import ImageRef

        img_path = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(str(img_path))

        config = SciMarkdownConfig(references_generate_index=True)
        pipeline = CompositionPipeline(config)

        enriched = EnrichedResult(
            base_markdown="Some markdown content.",
            math_regions=[],
            images=[
                ImageRef(
                    position=0,
                    file_path=str(img_path),
                    original_format="png",
                    width=10,
                    height=10,
                    reference_label="Figure 1",
                    ordinal=1,
                )
            ],
        )
        result = pipeline.compose(enriched)
        assert isinstance(result, str)
        assert "Figure Index" in result or "Figure 1" in result

    def test_compose_image_fallback_all_same_position(self, tmp_path):
        """When all images have same position (pos_range=0), proportional fallback handles it."""
        from scimarkdown.pipeline.composition import CompositionPipeline
        from scimarkdown.models import ImageRef

        img_path = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(str(img_path))

        config = SciMarkdownConfig(references_generate_index=False)
        pipeline = CompositionPipeline(config)

        enriched = EnrichedResult(
            base_markdown="Para 1\n\nPara 2\n\nPara 3",
            math_regions=[],
            images=[
                ImageRef(
                    position=5,  # all at same position
                    file_path=str(img_path),
                    original_format="png",
                    width=10,
                    height=10,
                ),
                ImageRef(
                    position=5,
                    file_path=str(img_path),
                    original_format="png",
                    width=10,
                    height=10,
                ),
            ],
        )
        result = pipeline.compose(enriched)
        assert isinstance(result, str)
