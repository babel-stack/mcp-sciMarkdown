"""Tests for ReferenceLinker — ordinal matching, repeated refs, edge cases."""

import pytest
from scimarkdown.config import SciMarkdownConfig
from scimarkdown.images import ReferenceLinker
from scimarkdown.models import ImageRef


def _make_image(position: int = 0) -> ImageRef:
    return ImageRef(position=position, file_path=f"/tmp/img{position}.png", original_format="png")


def _make_linker() -> ReferenceLinker:
    return ReferenceLinker(config=SciMarkdownConfig())


class TestExactOrdinalMatch:
    def test_three_figures_matched_in_order(self):
        """'Figure 1 ... Figure 2 ... Figure 3' assigns ordinals 1, 2, 3."""
        linker = _make_linker()
        images = [_make_image(0), _make_image(1), _make_image(2)]
        text = "See Figure 1 for the intro. Figure 2 shows the results. Figure 3 concludes."
        result = linker.link(text, images)
        assert result[0].ordinal == 1
        assert result[1].ordinal == 2
        assert result[2].ordinal == 3

    def test_reference_label_contains_match_text(self):
        linker = _make_linker()
        images = [_make_image()]
        text = "As shown in Figure 1."
        result = linker.link(text, images)
        assert result[0].reference_label is not None
        assert "1" in result[0].reference_label

    def test_ordinal_two_skips_image_zero(self):
        """Ordinal 2 maps to images[1], leaving images[0] unmatched."""
        linker = _make_linker()
        images = [_make_image(0), _make_image(1)]
        text = "Figure 2 is interesting."
        result = linker.link(text, images)
        assert result[0].reference_label is None
        assert result[1].ordinal == 2


class TestSpanishPatterns:
    def test_figura_detected(self):
        """'Figura 1' should be matched by the default patterns."""
        linker = _make_linker()
        images = [_make_image()]
        text = "Como se muestra en la Figura 1."
        result = linker.link(text, images)
        assert result[0].ordinal == 1

    def test_figura_label_set(self):
        linker = _make_linker()
        images = [_make_image()]
        text = "Ver Figura 1 para detalles."
        result = linker.link(text, images)
        assert result[0].reference_label is not None


class TestRepeatedReferences:
    def test_repeated_reference_same_image(self):
        """'Figure 1' appearing twice should point to images[0] both times."""
        linker = _make_linker()
        images = [_make_image(0), _make_image(1)]
        text = "Figure 1 is great. See also Figure 1 for comparison."
        result = linker.link(text, images)
        # Only one unique ordinal seen → images[0] is matched, images[1] is not
        assert result[0].ordinal == 1
        assert result[1].reference_label is None

    def test_repeated_and_unique(self):
        linker = _make_linker()
        images = [_make_image(0), _make_image(1)]
        text = "Figure 1 introduced it. Figure 2 extends it. Figure 1 revisited."
        result = linker.link(text, images)
        assert result[0].ordinal == 1
        assert result[1].ordinal == 2


class TestNoReferences:
    def test_no_references_images_unchanged(self):
        """Text with no figure references → all images left with None labels."""
        linker = _make_linker()
        images = [_make_image(0), _make_image(1)]
        text = "This document has no figure citations at all."
        result = linker.link(text, images)
        for img in result:
            assert img.reference_label is None
            assert img.ordinal is None

    def test_empty_images_list(self):
        linker = _make_linker()
        text = "Figure 1 is referenced here."
        result = linker.link(text, [])
        assert result == []


class TestFigAbbreviation:
    def test_fig_dot_detected(self):
        """'Fig. 1' should be matched by the default patterns."""
        linker = _make_linker()
        images = [_make_image()]
        text = "As shown in Fig. 1 above."
        result = linker.link(text, images)
        assert result[0].ordinal == 1

    def test_figure_full_word_detected(self):
        """'Figure 1' (full word) should be matched."""
        linker = _make_linker()
        images = [_make_image()]
        text = "See Figure 1 for details."
        result = linker.link(text, images)
        assert result[0].ordinal == 1
