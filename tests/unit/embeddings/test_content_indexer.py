"""Tests for ContentIndexer."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from scimarkdown.embeddings.content_indexer import ContentIndexer, ContentIndex


SAMPLE_MARKDOWN = """# Introduction

This is the introduction section with some text about scientific methods.

## Methods

We used regression analysis to evaluate the dataset.

## Formula

$$E = mc^2$$

## Results

The results show a significant improvement.
"""


def _make_client(embedding_fn=None):
    client = MagicMock()
    if embedding_fn:
        client.embed_text.side_effect = embedding_fn
    else:
        # Each call returns a slightly different embedding so similarity varies
        call_count = [0]
        def default_emb(text, **kwargs):
            call_count[0] += 1
            return [float(call_count[0]) * 0.1, 0.0, 0.0]
        client.embed_text.side_effect = default_emb
    return client


class TestIndex:
    def test_returns_content_index(self):
        client = _make_client()
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        assert isinstance(idx, ContentIndex)

    def test_chunks_are_created(self):
        client = _make_client()
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        assert len(idx.chunks) > 0

    def test_embeddings_match_chunks(self):
        client = _make_client()
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        assert len(idx.chunks) == len(idx.embeddings)

    def test_chunks_have_required_keys(self):
        client = _make_client()
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        for chunk in idx.chunks:
            assert "text" in chunk
            assert "type" in chunk

    def test_chunk_types_are_valid(self):
        client = _make_client()
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        valid_types = {"text", "heading", "formula", "image", "table"}
        for chunk in idx.chunks:
            assert chunk["type"] in valid_types

    def test_headings_detected(self):
        client = _make_client()
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        types = [c["type"] for c in idx.chunks]
        assert "heading" in types

    def test_empty_markdown_returns_empty_index(self):
        client = _make_client()
        indexer = ContentIndexer(client=client)
        idx = indexer.index("")
        assert len(idx.chunks) == 0
        assert len(idx.embeddings) == 0


class TestSearch:
    def test_returns_list_of_dicts(self):
        client = MagicMock()
        client.embed_text.return_value = [1.0, 0.0, 0.0]
        client.similarity.return_value = 0.8
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        results = indexer.search(idx, "quantum physics", top_k=2)
        assert isinstance(results, list)

    def test_top_k_limits_results(self):
        client = MagicMock()
        client.embed_text.return_value = [1.0, 0.0, 0.0]
        client.similarity.return_value = 0.8
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        results = indexer.search(idx, "some query", top_k=2)
        assert len(results) <= 2

    def test_results_have_required_keys(self):
        client = MagicMock()
        client.embed_text.return_value = [1.0, 0.0, 0.0]
        client.similarity.return_value = 0.8
        indexer = ContentIndexer(client=client)
        idx = indexer.index(SAMPLE_MARKDOWN)
        results = indexer.search(idx, "methods", top_k=3)
        for r in results:
            assert "text" in r
            assert "type" in r
            assert "similarity" in r

    def test_search_on_empty_index_returns_empty(self):
        client = MagicMock()
        client.embed_text.return_value = [1.0, 0.0, 0.0]
        indexer = ContentIndexer(client=client)
        idx = indexer.index("")
        results = indexer.search(idx, "anything", top_k=5)
        assert results == []
