"""Tests for MCP serializers: math_region_to_dict and image_ref_to_dict."""

import pytest

from scimarkdown.models import ImageRef, MathRegion
from scimarkdown.mcp.serializers import image_ref_to_dict, math_region_to_dict


class TestMathRegionToDict:
    def test_all_fields_present(self):
        region = MathRegion(
            position=5,
            original_text=r"\(x^2\)",
            latex=r"x^2",
            source_type="latex",
            confidence=1.0,
            is_inline=True,
        )
        result = math_region_to_dict(region)
        assert result["position"] == 5
        assert result["original_text"] == r"\(x^2\)"
        assert result["latex"] == r"x^2"
        assert result["source_type"] == "latex"
        assert result["confidence"] == 1.0
        assert result["is_inline"] is True

    def test_returns_dict(self):
        region = MathRegion(
            position=0, original_text="α", latex=r"\alpha", source_type="unicode"
        )
        result = math_region_to_dict(region)
        assert isinstance(result, dict)

    def test_default_values(self):
        region = MathRegion(
            position=0, original_text="α", latex=r"\alpha", source_type="unicode"
        )
        result = math_region_to_dict(region)
        assert result["confidence"] == 1.0
        assert result["is_inline"] is True

    def test_block_formula(self):
        region = MathRegion(
            position=10,
            original_text=r"\[E = mc^2\]",
            latex=r"E = mc^2",
            source_type="latex",
            confidence=1.0,
            is_inline=False,
        )
        result = math_region_to_dict(region)
        assert result["is_inline"] is False

    def test_low_confidence(self):
        region = MathRegion(
            position=0,
            original_text="x ∑ y",
            latex=r"x \sum y",
            source_type="unicode",
            confidence=0.6,
            is_inline=True,
        )
        result = math_region_to_dict(region)
        assert result["confidence"] == 0.6


class TestImageRefToDict:
    def test_all_fields_present(self):
        ref = ImageRef(
            position=0,
            file_path="/tmp/doc_img00001.png",
            original_format="png",
            width=640,
            height=480,
            caption="Test figure",
            reference_label="Figure 1",
            ordinal=1,
        )
        result = image_ref_to_dict(ref)
        assert result["position"] == 0
        assert result["file_path"] == "/tmp/doc_img00001.png"
        assert result["original_format"] == "png"
        assert result["width"] == 640
        assert result["height"] == 480
        assert result["caption"] == "Test figure"
        assert result["reference_label"] == "Figure 1"
        assert result["ordinal"] == 1

    def test_returns_dict(self):
        ref = ImageRef(position=0, file_path="/tmp/img.png", original_format="png")
        result = image_ref_to_dict(ref)
        assert isinstance(result, dict)

    def test_optional_fields_none(self):
        ref = ImageRef(position=0, file_path="/tmp/img.png", original_format="png")
        result = image_ref_to_dict(ref)
        assert result["caption"] is None
        assert result["reference_label"] is None
        assert result["ordinal"] is None

    def test_default_dimensions(self):
        ref = ImageRef(position=0, file_path="/tmp/img.png", original_format="png")
        result = image_ref_to_dict(ref)
        assert result["width"] == 0
        assert result["height"] == 0
