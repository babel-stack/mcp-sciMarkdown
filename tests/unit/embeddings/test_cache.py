"""Tests for EmbeddingCache."""

import pytest
from scimarkdown.embeddings.cache import EmbeddingCache


class TestContentHash:
    def test_returns_hex_string(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        h = cache.content_hash("hello world")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex = 64 chars

    def test_same_input_same_hash(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        assert cache.content_hash("test") == cache.content_hash("test")

    def test_different_input_different_hash(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        assert cache.content_hash("abc") != cache.content_hash("def")


class TestGetPut:
    def test_get_returns_none_when_missing(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        assert cache.get("nonexistent_key") is None

    def test_put_and_get_returns_embedding(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        embedding = [0.1, 0.2, 0.3]
        cache.put("mykey", embedding)
        result = cache.get("mykey")
        assert result == embedding

    def test_put_overwrites_existing(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        cache.put("key", [1.0, 2.0])
        cache.put("key", [3.0, 4.0])
        assert cache.get("key") == [3.0, 4.0]

    def test_persists_across_instances(self, tmp_path):
        cache1 = EmbeddingCache(cache_dir=tmp_path)
        cache1.put("persistent_key", [0.5, 0.6])
        cache2 = EmbeddingCache(cache_dir=tmp_path)
        assert cache2.get("persistent_key") == [0.5, 0.6]


class TestClear:
    def test_clear_removes_all_entries(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        cache.put("k1", [1.0])
        cache.put("k2", [2.0])
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_clear_on_empty_cache_is_safe(self, tmp_path):
        cache = EmbeddingCache(cache_dir=tmp_path)
        cache.clear()  # should not raise
