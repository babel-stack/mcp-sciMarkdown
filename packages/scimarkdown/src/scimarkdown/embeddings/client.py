"""Gemini Embedding API client with caching and cosine similarity."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

from scimarkdown.embeddings.cache import EmbeddingCache

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-embedding-2-preview"


def _create_genai_client(api_key: str):
    """Create a google-genai client.  Separated for easy mocking in tests."""
    import google.genai as genai  # lazy import — package may not be installed
    return genai.Client(api_key=api_key)


class GeminiEmbeddingClient:
    """Client for the Gemini Embedding API with transparent caching.

    Parameters
    ----------
    api_key:
        Gemini API key.  If ``None`` the client is considered unavailable.
    cache_dir:
        Directory for the file-based :class:`EmbeddingCache`.
    model:
        Gemini embedding model name.
    """

    def __init__(
        self,
        api_key: Optional[str],
        cache_dir: Path,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._cache = EmbeddingCache(cache_dir=cache_dir)
        self._client = None

        if api_key:
            try:
                self._client = _create_genai_client(api_key)
            except Exception as exc:
                logger.warning("Could not create Gemini client: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the client was initialised with a valid API key."""
        return self._client is not None

    def embed_text(self, text: str, task_type: str = "SEMANTIC_SIMILARITY") -> list[float]:
        """Return an embedding vector for *text*.

        Results are cached by (task_type, sha256(text)) so repeated calls
        with identical inputs do not hit the API.
        """
        cache_key = self._cache.content_hash(f"{task_type}:{text}")
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        result = self._client.models.embed_content(
            model=self._model,
            contents=text,
            config={"task_type": task_type},
        )
        embedding: list[float] = list(result.embeddings[0].values)
        self._cache.put(cache_key, embedding)
        return embedding

    def embed_image(self, image_bytes: bytes, mime_type: str = "image/png") -> list[float]:
        """Return a multimodal embedding vector for *image_bytes*."""
        # Build an inline blob for the Gemini SDK
        try:
            from google.genai import types as genai_types  # lazy import
            blob = genai_types.Blob(mime_type=mime_type, data=image_bytes)
        except ImportError:
            # Fallback: pass raw bytes — SDK will handle it
            blob = image_bytes  # type: ignore[assignment]

        result = self._client.models.embed_content(
            model=self._model,
            contents=blob,
        )
        return list(result.embeddings[0].values)

    def embed_batch(self, texts: list[str], task_type: str = "SEMANTIC_SIMILARITY") -> list[list[float]]:
        """Return embeddings for a batch of *texts* in a single API call.

        Empty inputs are returned as-is without hitting the API.
        """
        if not texts:
            return []

        result = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config={"task_type": task_type},
        )
        return [list(e.values) for e in result.embeddings]

    @staticmethod
    def similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Cosine similarity between two vectors, in [-1, 1]."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
