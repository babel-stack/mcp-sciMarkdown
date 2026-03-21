"""SemanticLinker — links images to text blocks via multimodal embedding similarity."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scimarkdown.embeddings.client import GeminiEmbeddingClient
    from scimarkdown.models import ImageRef

logger = logging.getLogger(__name__)

_CAPTION_MAX_LEN = 100


class SemanticLinker:
    """Link images to the most semantically relevant text block.

    For each image the linker:

    1. Reads the image file from disk and obtains its multimodal embedding.
    2. Embeds each text block.
    3. Picks the text block with the highest cosine similarity.
    4. If that similarity exceeds *threshold*, sets ``image.caption`` to a
       truncated version of the matching text block.

    Images whose file does not exist on disk are skipped with a warning.

    Parameters
    ----------
    client:
        A :class:`~scimarkdown.embeddings.client.GeminiEmbeddingClient`.
    threshold:
        Minimum cosine similarity required to assign a caption.
    """

    def __init__(self, client: "GeminiEmbeddingClient", threshold: float = 0.60) -> None:
        self._client = client
        self._threshold = threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def link(
        self,
        images: list["ImageRef"],
        text_blocks: list[str],
    ) -> list["ImageRef"]:
        """Set captions on *images* where a matching text block is found.

        Returns the (potentially modified) list.  The list is mutated
        in-place; a reference to the same list is also returned for
        convenience.
        """
        if not images:
            return images

        # Pre-embed all non-empty text blocks once.
        text_embeddings: list[tuple[str, list[float]]] = []
        for block in text_blocks:
            if not block.strip():
                continue
            try:
                emb = self._client.embed_text(block, task_type="SEMANTIC_SIMILARITY")
                text_embeddings.append((block, emb))
            except Exception as exc:
                logger.debug("SemanticLinker: could not embed text block: %s", exc)

        for image in images:
            img_path = Path(image.file_path)
            if not img_path.exists():
                logger.warning(
                    "SemanticLinker: image file not found, skipping: %s", img_path
                )
                continue

            if not text_embeddings:
                continue

            try:
                img_bytes = img_path.read_bytes()
                suffix = img_path.suffix.lower().lstrip(".")
                mime_type = _mime_for(suffix)
                img_emb = self._client.embed_image(img_bytes, mime_type=mime_type)
            except Exception as exc:
                logger.warning(
                    "SemanticLinker: could not embed image %s: %s", img_path, exc
                )
                continue

            # Find best matching text block.
            best_sim = -1.0
            best_text = ""
            for block, text_emb in text_embeddings:
                try:
                    sim = self._client.similarity(img_emb, text_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_text = block
                except Exception as exc:
                    logger.debug("SemanticLinker: similarity error: %s", exc)

            if best_sim >= self._threshold:
                image.caption = best_text[:_CAPTION_MAX_LEN]
                logger.debug(
                    "SemanticLinker: linked image %s to text (sim=%.3f)",
                    img_path.name,
                    best_sim,
                )

        return images


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _mime_for(suffix: str) -> str:
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
    }.get(suffix, "image/png")
