"""MathClassifier — uses embeddings to confirm or discard heuristic math detections."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scimarkdown.embeddings.client import GeminiEmbeddingClient
    from scimarkdown.models import MathRegion

logger = logging.getLogger(__name__)

# Reference LaTeX formulas used as "anchor" embeddings.  These cover a broad
# range of mathematical expression styles so that any genuine formula will
# land close to at least one anchor in embedding space.
_REFERENCE_FORMULAS: list[str] = [
    r"E = mc^2",
    r"x^2 + y^2 = r^2",
    r"\frac{a}{b}",
    r"\sum_{i=0}^{n} x_i",
    r"\int_{a}^{b} f(x) \, dx",
    r"\lim_{x \to \infty} \frac{1}{x} = 0",
    r"\alpha + \beta = \gamma",
    r"\nabla^2 \phi = 0",
    r"\mathbf{F} = m\mathbf{a}",
    r"P(A|B) = \frac{P(B|A)P(A)}{P(B)}",
    r"\det(A) \neq 0",
    r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}",
    r"\sqrt{x^2 + y^2}",
    r"e^{i\pi} + 1 = 0",
    r"\forall x \in \mathbb{R}: x^2 \geq 0",
]

# Confidence above this value means the region is already reliable — skip API.
_HIGH_CONFIDENCE_PASSTHROUGH = 0.9


class MathClassifier:
    """Confirm or discard heuristic math detections using embedding similarity.

    Parameters
    ----------
    client:
        A :class:`~scimarkdown.embeddings.client.GeminiEmbeddingClient` instance.
    threshold:
        Cosine-similarity threshold; regions whose max similarity to the
        reference corpus exceeds this value are confirmed.
    """

    def __init__(self, client: "GeminiEmbeddingClient", threshold: float = 0.75) -> None:
        self._client = client
        self._threshold = threshold
        self._ref_embeddings: list[list[float]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, regions: list["MathRegion"]) -> list["MathRegion"]:
        """Classify *regions*, returning only those that pass the filter.

        * Regions with confidence >= 0.9 pass through untouched (no API call).
        * Other regions are embedded and compared to reference formulas.
          - max similarity >= threshold → confidence boosted to threshold,
            region kept.
          - max similarity < threshold → region discarded.
        """
        if not regions:
            return []

        kept: list["MathRegion"] = []
        needs_check: list["MathRegion"] = []

        for region in regions:
            if region.confidence >= _HIGH_CONFIDENCE_PASSTHROUGH:
                kept.append(region)
            else:
                needs_check.append(region)

        if not needs_check:
            return kept

        ref_embeddings = self._get_reference_embeddings()

        for region in needs_check:
            try:
                candidate_emb = self._client.embed_text(region.latex, task_type="SEMANTIC_SIMILARITY")
                max_sim = max(
                    self._client.similarity(candidate_emb, ref)
                    for ref in ref_embeddings
                )
                if max_sim >= self._threshold:
                    import copy
                    confirmed = copy.copy(region)
                    confirmed.confidence = max(region.confidence, self._threshold)
                    kept.append(confirmed)
                else:
                    logger.debug(
                        "MathClassifier discarded region %r (max_sim=%.3f < threshold=%.3f)",
                        region.latex[:50],
                        max_sim,
                        self._threshold,
                    )
            except Exception as exc:
                logger.warning("MathClassifier error for region %r: %s", region.latex[:50], exc)
                kept.append(region)  # keep on error to be conservative

        return kept

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_reference_embeddings(self) -> list[list[float]]:
        """Lazily embed reference formulas (cached per classifier instance)."""
        if self._ref_embeddings is None:
            self._ref_embeddings = []
            for formula in _REFERENCE_FORMULAS:
                try:
                    emb = self._client.embed_text(formula, task_type="SEMANTIC_SIMILARITY")
                    self._ref_embeddings.append(emb)
                except Exception as exc:
                    logger.debug("Could not embed reference formula %r: %s", formula, exc)
        return self._ref_embeddings
