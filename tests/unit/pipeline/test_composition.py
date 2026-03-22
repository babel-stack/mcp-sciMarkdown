"""Tests for CompositionPipeline (Phase 3)."""

from __future__ import annotations

import pytest

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import EnrichedResult, ImageRef, MathRegion
from scimarkdown.pipeline import CompositionPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline(**kwargs) -> CompositionPipeline:
    config = SciMarkdownConfig(**kwargs)
    return CompositionPipeline(config)


def _enriched(
    markdown: str = "",
    images: list[ImageRef] | None = None,
    math_regions: list[MathRegion] | None = None,
) -> EnrichedResult:
    return EnrichedResult(
        base_markdown=markdown,
        images=images or [],
        math_regions=math_regions or [],
    )


def _image(
    position: int = 0,
    file_path: str = "/out/img.png",
    original_format: str = "png",
    caption: str | None = None,
    reference_label: str | None = None,
) -> ImageRef:
    return ImageRef(
        position=position,
        file_path=file_path,
        original_format=original_format,
        caption=caption,
        reference_label=reference_label,
    )


def _math_region(
    position: int,
    original_text: str,
    latex: str,
    is_inline: bool = True,
    source_type: str = "unicode",
    confidence: float = 0.9,
) -> MathRegion:
    return MathRegion(
        position=position,
        original_text=original_text,
        latex=latex,
        source_type=source_type,
        confidence=confidence,
        is_inline=is_inline,
    )


# ---------------------------------------------------------------------------
# test_composition_no_enrichment
# ---------------------------------------------------------------------------

class TestCompositionNoEnrichment:
    """No math/images → output equals input."""

    def test_empty_markdown_returns_empty(self):
        pipeline = _make_pipeline()
        result = pipeline.compose(_enriched(""))
        assert result == ""

    def test_plain_markdown_returned_unchanged(self):
        pipeline = _make_pipeline()
        md = "# Hello\n\nThis is a paragraph.\n"
        result = pipeline.compose(_enriched(md))
        assert result == md

    def test_no_math_no_images_identity(self):
        pipeline = _make_pipeline()
        md = "Some text without math or images."
        result = pipeline.compose(_enriched(md))
        assert result == md


# ---------------------------------------------------------------------------
# test_composition_with_images
# ---------------------------------------------------------------------------

class TestCompositionWithImages:
    """Image refs → markdown image links + index."""

    def test_single_image_appended(self):
        pipeline = _make_pipeline(references_generate_index=False)
        img = _image(position=0, file_path="/out/fig1.png")
        result = pipeline.compose(_enriched("Some text.", images=[img]))
        assert "![](/out/fig1.png)" in result

    def test_image_with_caption_and_label(self):
        pipeline = _make_pipeline(references_generate_index=False)
        img = _image(
            position=0,
            file_path="/out/fig1.png",
            caption="My caption",
            reference_label="Figure 1",
        )
        result = pipeline.compose(_enriched("Text.", images=[img]))
        assert "![Figure 1: My caption](/out/fig1.png)" in result

    def test_image_with_only_label(self):
        pipeline = _make_pipeline(references_generate_index=False)
        img = _image(position=0, file_path="/out/fig1.png", reference_label="Fig. 1")
        result = pipeline.compose(_enriched("Text.", images=[img]))
        assert "![Fig. 1](/out/fig1.png)" in result

    def test_image_with_only_caption(self):
        pipeline = _make_pipeline(references_generate_index=False)
        img = _image(position=0, file_path="/out/fig1.png", caption="A diagram")
        result = pipeline.compose(_enriched("Text.", images=[img]))
        assert "![A diagram](/out/fig1.png)" in result

    def test_images_sorted_by_position(self):
        pipeline = _make_pipeline(references_generate_index=False)
        img_b = _image(position=100, file_path="/out/img_b.png")
        img_a = _image(position=10, file_path="/out/img_a.png")
        result = pipeline.compose(_enriched("Text.", images=[img_b, img_a]))
        pos_a = result.index("img_a.png")
        pos_b = result.index("img_b.png")
        assert pos_a < pos_b

    def test_image_inserted_by_context_text(self):
        """Images with context_text should appear right after the matching paragraph."""
        pipeline = _make_pipeline(references_generate_index=False)
        md = "# Introduction\n\nFirst paragraph about physics.\n\n# Methods\n\nSecond paragraph about chemistry.\n\n# Results\n\nThird paragraph about biology."
        img = ImageRef(
            position=0, file_path="chem.png", original_format="png",
            context_text="Second paragraph about chemistry.",
        )
        result = pipeline.compose(_enriched(md, images=[img]))

        # Image should appear after "chemistry" paragraph, before "Results"
        pos_img = result.index("chem.png")
        pos_chemistry = result.index("about chemistry")
        pos_results = result.index("# Results")
        assert pos_img > pos_chemistry, "Image should be after the chemistry paragraph"
        assert pos_img < pos_results, "Image should be before Results section"

    def test_image_context_text_fallback_to_proportional(self):
        """If context_text doesn't match, falls back to proportional positioning."""
        pipeline = _make_pipeline(references_generate_index=False)
        md = "# Intro\n\nParagraph one.\n\n# End\n\nParagraph two."
        img = ImageRef(
            position=2000, file_path="late.png", original_format="png",
            context_text="This text does not exist in the markdown.",
        )
        result = pipeline.compose(_enriched(md, images=[img]))
        # Should still appear somewhere (proportional fallback)
        assert "late.png" in result

    def test_image_without_context_uses_position(self):
        """Images without context_text use proportional positioning."""
        pipeline = _make_pipeline(references_generate_index=False)
        md = "# Introduction\n\nFirst paragraph.\n\n# Methods\n\nSecond paragraph.\n\n# Results\n\nThird paragraph."
        img_early = _image(position=0, file_path="early.png")
        img_late = _image(position=2000, file_path="late.png")
        result = pipeline.compose(_enriched(md, images=[img_early, img_late]))
        pos_early = result.index("early.png")
        pos_late = result.index("late.png")
        assert pos_early < pos_late

    def test_single_paragraph_image_inline(self):
        """With a single paragraph, image should be right after it."""
        pipeline = _make_pipeline(references_generate_index=False)
        md = "Only one paragraph here."
        img = _image(position=0, file_path="fig.png")
        result = pipeline.compose(_enriched(md, images=[img]))
        assert "Only one paragraph here." in result
        assert "fig.png" in result

    def test_figure_index_appended_when_enabled(self):
        pipeline = _make_pipeline(references_generate_index=True)
        img = _image(
            position=0,
            file_path="/out/fig1.png",
            reference_label="Figure 1",
            caption="Overview",
        )
        result = pipeline.compose(_enriched("Text.", images=[img]))
        assert "## Figure Index" in result
        assert "Figure 1" in result

    def test_figure_index_contains_file_column(self):
        pipeline = _make_pipeline(references_generate_index=True)
        img = _image(position=0, file_path="/out/fig1.png")
        result = pipeline.compose(_enriched("Text.", images=[img]))
        assert "fig1.png" in result


# ---------------------------------------------------------------------------
# test_composition_with_math_standard
# ---------------------------------------------------------------------------

class TestCompositionWithMathStandard:
    """Unicode regions → $LaTeX$ (standard style)."""

    def test_unicode_symbol_replaced_standard(self):
        pipeline = _make_pipeline(latex_style="standard")
        original = "α + β"
        md = f"The formula {original} is key."
        pos = md.index(original)
        region = _math_region(
            position=pos,
            original_text=original,
            latex=r"\alpha + \beta",
            is_inline=True,
        )
        result = pipeline.compose(_enriched(md, math_regions=[region]))
        assert r"$\alpha + \beta$" in result
        assert original not in result

    def test_block_math_standard(self):
        pipeline = _make_pipeline(latex_style="standard")
        original = "∑ xᵢ"
        md = f"Display: {original}"
        pos = md.index(original)
        region = _math_region(
            position=pos,
            original_text=original,
            latex=r"\sum x_{i}",
            is_inline=False,
        )
        result = pipeline.compose(_enriched(md, math_regions=[region]))
        assert r"$$\sum x_{i}$$" in result

    def test_multiple_math_regions_replaced(self):
        pipeline = _make_pipeline(latex_style="standard")
        md = "Let α = 1 and β = 2."
        # Two separate single-symbol regions
        r1 = _math_region(position=4, original_text="α", latex=r"\alpha")
        r2 = _math_region(position=13, original_text="β", latex=r"\beta")
        result = pipeline.compose(_enriched(md, math_regions=[r1, r2]))
        assert r"$\alpha$" in result
        assert r"$\beta$" in result


# ---------------------------------------------------------------------------
# test_composition_with_math_github
# ---------------------------------------------------------------------------

class TestCompositionWithMathGithub:
    """Unicode regions → $`LaTeX`$ (GitHub style)."""

    def test_inline_math_github_style(self):
        pipeline = _make_pipeline(latex_style="github")
        original = "α"
        md = f"Value {original} here."
        pos = md.index(original)
        region = _math_region(
            position=pos,
            original_text=original,
            latex=r"\alpha",
            is_inline=True,
        )
        result = pipeline.compose(_enriched(md, math_regions=[region]))
        assert r"$`\alpha`$" in result

    def test_block_math_github_style(self):
        pipeline = _make_pipeline(latex_style="github")
        original = "∑ n"
        md = f"Formula: {original}."
        pos = md.index(original)
        region = _math_region(
            position=pos,
            original_text=original,
            latex=r"\sum n",
            is_inline=False,
        )
        result = pipeline.compose(_enriched(md, math_regions=[region]))
        assert "```math" in result
        assert r"\sum n" in result


# ---------------------------------------------------------------------------
# test_composition_no_index_when_disabled
# ---------------------------------------------------------------------------

class TestCompositionNoIndexWhenDisabled:
    """references_generate_index=False → no ## Figure Index appended."""

    def test_no_index_when_disabled(self):
        pipeline = _make_pipeline(references_generate_index=False)
        img = _image(position=0, file_path="/out/fig1.png", reference_label="Figure 1")
        result = pipeline.compose(_enriched("Text.", images=[img]))
        assert "## Figure Index" not in result

    def test_image_links_still_present_when_index_disabled(self):
        pipeline = _make_pipeline(references_generate_index=False)
        img = _image(position=0, file_path="/out/fig1.png")
        result = pipeline.compose(_enriched("Text.", images=[img]))
        assert "fig1.png" in result

    def test_no_index_on_empty_images(self):
        pipeline = _make_pipeline(references_generate_index=True)
        result = pipeline.compose(_enriched("Text."))
        assert "## Figure Index" not in result
