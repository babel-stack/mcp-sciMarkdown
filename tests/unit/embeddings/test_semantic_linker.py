"""Tests for SemanticLinker."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from scimarkdown.embeddings.semantic_linker import SemanticLinker
from scimarkdown.models import ImageRef


def _make_image(file_path: str, position: int = 0) -> ImageRef:
    return ImageRef(
        position=position,
        file_path=file_path,
        original_format="png",
        width=100,
        height=100,
    )


def _make_client(image_emb=None, text_emb=None, similarity_value=0.8):
    client = MagicMock()
    client.embed_image.return_value = image_emb or [0.1, 0.2, 0.3]
    client.embed_text.return_value = text_emb or [0.1, 0.2, 0.3]
    client.similarity.return_value = similarity_value
    return client


class TestSemanticLinker:
    def test_links_image_to_text_when_similarity_above_threshold(self, tmp_path):
        img_path = tmp_path / "figure1.png"
        img_path.write_bytes(b"\x89PNG fake")

        client = _make_client(similarity_value=0.9)
        linker = SemanticLinker(client=client, threshold=0.60)
        image = _make_image(str(img_path))
        text_blocks = ["This figure shows the correlation between x and y."]
        results = linker.link([image], text_blocks)
        assert len(results) == 1
        assert results[0].caption is not None
        assert "correlation" in results[0].caption

    def test_does_not_link_when_similarity_below_threshold(self, tmp_path):
        img_path = tmp_path / "figure2.png"
        img_path.write_bytes(b"\x89PNG fake")

        client = _make_client(similarity_value=0.3)
        linker = SemanticLinker(client=client, threshold=0.60)
        image = _make_image(str(img_path))
        text_blocks = ["Some unrelated text."]
        results = linker.link([image], text_blocks)
        assert results[0].caption is None

    def test_skips_nonexistent_image_file(self, tmp_path, caplog):
        import logging
        client = _make_client()
        linker = SemanticLinker(client=client, threshold=0.60)
        image = _make_image("/nonexistent/path/figure.png")
        with caplog.at_level(logging.WARNING):
            results = linker.link([image], ["Some text."])
        assert results[0].caption is None
        client.embed_image.assert_not_called()

    def test_caption_truncated_to_100_chars(self, tmp_path):
        img_path = tmp_path / "figure3.png"
        img_path.write_bytes(b"\x89PNG fake")

        client = _make_client(similarity_value=0.9)
        linker = SemanticLinker(client=client, threshold=0.60)
        image = _make_image(str(img_path))
        long_text = "A" * 200
        results = linker.link([image], [long_text])
        assert results[0].caption is not None
        assert len(results[0].caption) <= 100

    def test_empty_images_returns_empty(self, tmp_path):
        client = _make_client()
        linker = SemanticLinker(client=client, threshold=0.60)
        results = linker.link([], ["some text"])
        assert results == []

    def test_empty_text_blocks_leaves_captions_unchanged(self, tmp_path):
        img_path = tmp_path / "figure4.png"
        img_path.write_bytes(b"\x89PNG fake")

        client = _make_client()
        linker = SemanticLinker(client=client, threshold=0.60)
        image = _make_image(str(img_path))
        results = linker.link([image], [])
        assert results[0].caption is None

    def test_picks_best_matching_text_block(self, tmp_path):
        img_path = tmp_path / "figure5.png"
        img_path.write_bytes(b"\x89PNG fake")

        client = MagicMock()
        client.embed_image.return_value = [1.0, 0.0]
        # First text block has lower similarity, second higher
        client.embed_text.side_effect = [[0.5, 0.5], [0.9, 0.1]]
        client.similarity.side_effect = [0.65, 0.92]

        linker = SemanticLinker(client=client, threshold=0.60)
        image = _make_image(str(img_path))
        text_blocks = ["Less relevant text.", "Highly relevant figure description."]
        results = linker.link([image], text_blocks)
        assert results[0].caption == "Highly relevant figure description."
