"""Embeddings module for SciMarkdown — semantic enrichment via vector embeddings."""

from scimarkdown.embeddings.cache import EmbeddingCache
from scimarkdown.embeddings.client import GeminiEmbeddingClient, _create_genai_client
from scimarkdown.embeddings.math_classifier import MathClassifier
from scimarkdown.embeddings.semantic_linker import SemanticLinker
from scimarkdown.embeddings.document_classifier import DocumentClassifier, CATEGORIES
from scimarkdown.embeddings.content_indexer import ContentIndexer, ContentIndex

__all__ = [
    "EmbeddingCache",
    "GeminiEmbeddingClient",
    "_create_genai_client",
    "MathClassifier",
    "SemanticLinker",
    "DocumentClassifier",
    "CATEGORIES",
    "ContentIndexer",
    "ContentIndex",
]
