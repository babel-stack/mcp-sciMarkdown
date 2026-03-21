"""Tests for MathClassifier."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from scimarkdown.embeddings.math_classifier import MathClassifier
from scimarkdown.models import MathRegion


def _make_region(latex: str, confidence: float, source_type: str = "heuristic") -> MathRegion:
    return MathRegion(
        position=0,
        original_text=latex,
        latex=latex,
        source_type=source_type,
        confidence=confidence,
    )


def _make_client(similarity_value: float = 0.8):
    """Mock client returning a fixed similarity."""
    mock = MagicMock()
    mock.embed_text.return_value = [0.1, 0.2, 0.3]
    mock.similarity.return_value = similarity_value
    return mock


class TestPassthrough:
    def test_high_confidence_region_passes_without_api_call(self, tmp_path):
        client = _make_client()
        classifier = MathClassifier(client=client, threshold=0.75)
        region = _make_region(r"x^2 + y^2 = r^2", confidence=0.95)
        results = classifier.classify([region])
        assert len(results) == 1
        client.embed_text.assert_not_called()

    def test_high_confidence_region_confidence_unchanged(self, tmp_path):
        client = _make_client()
        classifier = MathClassifier(client=client, threshold=0.75)
        region = _make_region(r"\frac{a}{b}", confidence=0.92)
        results = classifier.classify([region])
        assert results[0].confidence == 0.92


class TestConfirm:
    def test_low_confidence_confirmed_when_similarity_above_threshold(self):
        client = _make_client(similarity_value=0.85)
        classifier = MathClassifier(client=client, threshold=0.75)
        region = _make_region(r"E = mc^2", confidence=0.5)
        results = classifier.classify([region])
        assert len(results) == 1
        assert results[0].confidence > 0.5  # boosted

    def test_confirmed_region_confidence_boosted_to_threshold_or_above(self):
        client = _make_client(similarity_value=0.85)
        classifier = MathClassifier(client=client, threshold=0.75)
        region = _make_region(r"\sum_{i=0}^{n} x_i", confidence=0.4)
        results = classifier.classify([region])
        assert results[0].confidence >= 0.75


class TestDiscard:
    def test_low_confidence_discarded_when_similarity_below_threshold(self):
        client = _make_client(similarity_value=0.3)
        classifier = MathClassifier(client=client, threshold=0.75)
        region = _make_region(r"not really math", confidence=0.4)
        results = classifier.classify([region])
        assert len(results) == 0


class TestEdgeCases:
    def test_empty_list_returns_empty(self):
        client = _make_client()
        classifier = MathClassifier(client=client, threshold=0.75)
        assert classifier.classify([]) == []

    def test_multiple_regions_processed_correctly(self):
        client = MagicMock()
        client.embed_text.return_value = [0.1, 0.2, 0.3]
        # similarity returns 0.85 for first candidate's comparisons, 0.2 for second
        call_count = [0]
        def side_effect_similarity(a, b):
            # Reference embeddings are fetched first (15 calls per candidate).
            # We use the candidate's call index (tracked separately).
            # The easiest: return high sim for the first region's candidate call,
            # low for the second.
            call_count[0] += 1
            # Calls 1-15: references for region 1 -> high sim
            if call_count[0] <= 15:
                return 0.85
            # Calls 16-30: references for region 2 -> low sim
            return 0.2
        client.similarity.side_effect = side_effect_similarity
        classifier = MathClassifier(client=client, threshold=0.75)
        regions = [
            _make_region(r"x^2", confidence=0.5),
            _make_region(r"not math at all blah", confidence=0.3),
        ]
        results = classifier.classify(regions)
        # First region confirmed, second discarded
        assert len(results) == 1
