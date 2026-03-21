"""ContentIndexer — semantic search index for Markdown documents (RAG)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scimarkdown.embeddings.client import GeminiEmbeddingClient

logger = logging.getLogger(__name__)

# Regex patterns for chunk classification.
_HEADING_RE = re.compile(r"^#{1,6}\s+.+", re.MULTILINE)
_FORMULA_BLOCK_RE = re.compile(r"\$\$.+?\$\$", re.DOTALL)
_FORMULA_INLINE_RE = re.compile(r"\$[^$\n]+\$")
_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")
_TABLE_ROW_RE = re.compile(r"^\|.+\|", re.MULTILINE)


@dataclass
class ContentIndex:
    """Result of indexing a Markdown document.

    Attributes
    ----------
    chunks:
        List of dicts, each with keys ``text`` and ``type``.
    embeddings:
        Parallel list of embedding vectors (one per chunk).
    """

    chunks: list[dict] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)


class ContentIndexer:
    """Split Markdown into typed chunks and index them with embeddings.

    Parameters
    ----------
    client:
        A :class:`~scimarkdown.embeddings.client.GeminiEmbeddingClient`.
    """

    def __init__(self, client: "GeminiEmbeddingClient") -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self, markdown: str) -> ContentIndex:
        """Split *markdown* into chunks, embed each, return a :class:`ContentIndex`."""
        chunks = _split_into_chunks(markdown)
        if not chunks:
            return ContentIndex()

        embeddings: list[list[float]] = []
        kept_chunks: list[dict] = []
        for chunk in chunks:
            try:
                emb = self._client.embed_text(chunk["text"], task_type="RETRIEVAL_DOCUMENT")
                embeddings.append(emb)
                kept_chunks.append(chunk)
            except Exception as exc:
                logger.debug("ContentIndexer: could not embed chunk: %s", exc)

        return ContentIndex(chunks=kept_chunks, embeddings=embeddings)

    def search(
        self,
        index: ContentIndex,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Search *index* for chunks most relevant to *query*.

        Returns up to *top_k* dicts with keys ``text``, ``type``, and
        ``similarity``, sorted by descending similarity.
        """
        if not index.chunks:
            return []

        try:
            query_emb = self._client.embed_text(query, task_type="RETRIEVAL_QUERY")
        except Exception as exc:
            logger.warning("ContentIndexer: could not embed query: %s", exc)
            return []

        scored: list[dict] = []
        for chunk, chunk_emb in zip(index.chunks, index.embeddings):
            try:
                sim = self._client.similarity(query_emb, chunk_emb)
                scored.append({**chunk, "similarity": sim})
            except Exception as exc:
                logger.debug("ContentIndexer: similarity error: %s", exc)

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]


# ------------------------------------------------------------------
# Chunk splitting helpers
# ------------------------------------------------------------------

def _classify_chunk(text: str) -> str:
    """Return the chunk type for *text*."""
    stripped = text.strip()
    if _HEADING_RE.match(stripped):
        return "heading"
    if _FORMULA_BLOCK_RE.search(stripped) or (
        stripped.startswith("$") and stripped.endswith("$")
    ):
        return "formula"
    if _IMAGE_RE.search(stripped):
        return "image"
    if _TABLE_ROW_RE.search(stripped):
        return "table"
    return "text"


def _split_into_chunks(markdown: str) -> list[dict]:
    """Split *markdown* into chunks at heading boundaries."""
    if not markdown.strip():
        return []

    # Split on headers (##, ###, etc.)
    heading_pattern = re.compile(r"(?=^#{1,6}\s)", re.MULTILINE)
    parts = heading_pattern.split(markdown)

    chunks: list[dict] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # A part may span multiple paragraphs — split on blank lines
        paragraphs = re.split(r"\n\s*\n", part)
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            chunk_type = _classify_chunk(para)
            chunks.append({"text": para, "type": chunk_type})

    return chunks
