"""DocumentClassifier — classify documents and optimize pipeline config."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scimarkdown.embeddings.client import GeminiEmbeddingClient
    from scimarkdown.config import SciMarkdownConfig

logger = logging.getLogger(__name__)

# Ordered list of category names (order is significant for test predictability).
CATEGORIES: list[str] = [
    "academic_paper",
    "technical_report",
    "presentation",
    "textbook",
    "code_documentation",
    "general_document",
]

# Description strings used as embedding anchors for each category.
_CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "academic_paper": (
        "A peer-reviewed scientific article with abstract, introduction, methodology, "
        "results and references sections. Contains mathematical equations, figures, "
        "and citations."
    ),
    "technical_report": (
        "A technical report documenting engineering or research findings. Includes "
        "tables, diagrams, specifications, and structured sections."
    ),
    "presentation": (
        "A slide-based presentation with bullet points, titles, and visual elements. "
        "Content is concise with minimal prose."
    ),
    "textbook": (
        "An educational textbook with chapters, definitions, examples, exercises, "
        "and pedagogical explanations. Covers a subject systematically."
    ),
    "code_documentation": (
        "Software documentation, API reference, or developer guide. Contains code "
        "snippets, function signatures, and technical descriptions."
    ),
    "general_document": (
        "A general-purpose document such as a letter, report, or article that does "
        "not fit into a more specific category."
    ),
}

# Maximum number of characters from the document to use for classification.
_MAX_CHARS = 2000


class DocumentClassifier:
    """Classify a document into one of six categories using embeddings.

    Parameters
    ----------
    client:
        A :class:`~scimarkdown.embeddings.client.GeminiEmbeddingClient`.
    """

    def __init__(self, client: "GeminiEmbeddingClient") -> None:
        self._client = client
        # Lazily computed category description embeddings.
        self._desc_embeddings: dict[str, list[float]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, text: str) -> tuple[str, float]:
        """Classify *text* and return ``(category, confidence)``.

        Uses only the first :data:`_MAX_CHARS` characters of *text*.
        Confidence is the normalised cosine similarity of the winning category.
        """
        snippet = text[:_MAX_CHARS]
        doc_emb = self._client.embed_text(snippet, task_type="SEMANTIC_SIMILARITY")

        desc_embeddings = self._get_description_embeddings()

        best_cat = "general_document"
        best_sim = -1.0
        for cat in CATEGORIES:
            desc_emb = desc_embeddings.get(cat)
            if desc_emb is None:
                continue
            sim = self._client.similarity(doc_emb, desc_emb)
            if sim > best_sim:
                best_sim = sim
                best_cat = cat

        # Normalise to [0, 1] — cosine similarity is in [-1, 1].
        confidence = max(0.0, min(1.0, (best_sim + 1.0) / 2.0))
        return best_cat, confidence

    def optimize_config(self, category: str, config: "SciMarkdownConfig") -> "SciMarkdownConfig":
        """Return a copy of *config* optimised for *category*.

        The original config is never mutated.
        """
        result = copy.deepcopy(config)
        if category == "academic_paper":
            result.math_heuristic = True
            result.references_generate_index = True
        elif category == "technical_report":
            result.references_generate_index = True
            result.images_autocrop_whitespace = True
        elif category == "presentation":
            result.images_dpi = max(result.images_dpi, 150)
            result.math_heuristic = False
        elif category == "textbook":
            result.math_heuristic = True
            result.references_generate_index = True
        elif category == "code_documentation":
            result.math_heuristic = False
        elif category == "general_document":
            pass  # use defaults
        else:
            logger.debug("DocumentClassifier: unknown category %r — config unchanged.", category)
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_description_embeddings(self) -> dict[str, list[float]]:
        """Lazily embed category descriptions."""
        if self._desc_embeddings is None:
            self._desc_embeddings = {}
            for cat, desc in _CATEGORY_DESCRIPTIONS.items():
                try:
                    emb = self._client.embed_text(desc, task_type="SEMANTIC_SIMILARITY")
                    self._desc_embeddings[cat] = emb
                except Exception as exc:
                    logger.debug("DocumentClassifier: could not embed category %r: %s", cat, exc)
        return self._desc_embeddings
