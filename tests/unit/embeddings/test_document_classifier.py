"""Tests for DocumentClassifier."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from scimarkdown.embeddings.document_classifier import DocumentClassifier, CATEGORIES
from scimarkdown.config import SciMarkdownConfig


def _make_client(similarities: dict[str, float] | None = None):
    """Mock client with controllable per-category similarities."""
    client = MagicMock()
    client.embed_text.return_value = [0.1, 0.2, 0.3]
    if similarities:
        # Map category name to similarity value; default to 0.5
        default = 0.5
        sim_values = [similarities.get(cat, default) for cat in CATEGORIES]
        client.similarity.side_effect = sim_values
    else:
        client.similarity.return_value = 0.5
    return client


class TestClassify:
    def test_returns_category_and_confidence(self):
        client = _make_client({"academic_paper": 0.9, "technical_report": 0.6})
        classifier = DocumentClassifier(client=client)
        category, confidence = classifier.classify("Some academic text about quantum mechanics.")
        assert category == "academic_paper"
        assert 0.0 <= confidence <= 1.0

    def test_category_with_highest_similarity_wins(self):
        client = _make_client({
            "academic_paper": 0.3,
            "technical_report": 0.3,
            "presentation": 0.3,
            "textbook": 0.95,
            "code_documentation": 0.3,
            "general_document": 0.3,
        })
        classifier = DocumentClassifier(client=client)
        category, _ = classifier.classify("Chapter 1: Introduction to algebra.")
        assert category == "textbook"

    def test_uses_first_2000_chars(self):
        client = _make_client()
        classifier = DocumentClassifier(client=client)
        long_text = "x" * 5000
        classifier.classify(long_text)
        call_args = client.embed_text.call_args_list[0]
        embedded_text = call_args[0][0]
        assert len(embedded_text) <= 2000

    def test_all_6_categories_available(self):
        assert len(CATEGORIES) == 6
        assert "academic_paper" in CATEGORIES
        assert "technical_report" in CATEGORIES
        assert "presentation" in CATEGORIES
        assert "textbook" in CATEGORIES
        assert "code_documentation" in CATEGORIES
        assert "general_document" in CATEGORIES


class TestOptimizeConfig:
    def test_returns_scimarkdown_config(self):
        client = _make_client()
        classifier = DocumentClassifier(client=client)
        config = SciMarkdownConfig()
        result = classifier.optimize_config("academic_paper", config)
        assert isinstance(result, SciMarkdownConfig)

    def test_academic_paper_enables_math_heuristic(self):
        client = _make_client()
        classifier = DocumentClassifier(client=client)
        config = SciMarkdownConfig(math_heuristic=False)
        result = classifier.optimize_config("academic_paper", config)
        assert result.math_heuristic is True

    def test_presentation_adjusts_image_settings(self):
        client = _make_client()
        classifier = DocumentClassifier(client=client)
        config = SciMarkdownConfig()
        result = classifier.optimize_config("presentation", config)
        assert isinstance(result, SciMarkdownConfig)

    def test_unknown_category_returns_config_unchanged(self):
        client = _make_client()
        classifier = DocumentClassifier(client=client)
        config = SciMarkdownConfig()
        result = classifier.optimize_config("unknown_category", config)
        assert result.math_heuristic == config.math_heuristic

    def test_original_config_not_mutated(self):
        client = _make_client()
        classifier = DocumentClassifier(client=client)
        config = SciMarkdownConfig(math_heuristic=False)
        classifier.optimize_config("academic_paper", config)
        assert config.math_heuristic is False  # original unchanged
