"""Tests for MathFormatter — standard and GitHub-flavored LaTeX output."""

import pytest
from scimarkdown.math import MathFormatter
from scimarkdown.models import MathRegion


def _make_region(
    latex: str,
    *,
    is_inline: bool = True,
    confidence: float = 1.0,
    source_type: str = "latex",
) -> MathRegion:
    return MathRegion(
        position=0,
        original_text=latex,
        latex=latex,
        source_type=source_type,
        confidence=confidence,
        is_inline=is_inline,
    )


class TestStandardStyle:
    def test_inline_standard(self):
        formatter = MathFormatter(style="standard")
        region = _make_region("x^2 + 1 = 0", is_inline=True)
        result = formatter.format(region)
        assert result == "$x^2 + 1 = 0$"

    def test_block_standard(self):
        formatter = MathFormatter(style="standard")
        region = _make_region(r"E = mc^2", is_inline=False)
        result = formatter.format(region)
        assert result == "$$E = mc^2$$"

    def test_inline_standard_frac(self):
        formatter = MathFormatter(style="standard")
        region = _make_region(r"\frac{1}{2}", is_inline=True)
        result = formatter.format(region)
        assert result == r"$\frac{1}{2}$"

    def test_block_standard_sum(self):
        formatter = MathFormatter(style="standard")
        region = _make_region(r"\sum_{i=0}^{n} x_i", is_inline=False)
        result = formatter.format(region)
        assert result == r"$$\sum_{i=0}^{n} x_i$$"


class TestGitHubStyle:
    def test_inline_github(self):
        formatter = MathFormatter(style="github")
        region = _make_region("x + y", is_inline=True)
        result = formatter.format(region)
        assert result == "$`x + y`$"

    def test_block_github(self):
        formatter = MathFormatter(style="github")
        region = _make_region(r"E = mc^2", is_inline=False)
        result = formatter.format(region)
        assert result == "```math\nE = mc^2\n```"

    def test_inline_github_complex(self):
        formatter = MathFormatter(style="github")
        region = _make_region(r"\alpha + \beta", is_inline=True)
        result = formatter.format(region)
        assert result == r"$`\alpha + \beta`$"

    def test_block_github_multiline_preserved(self):
        formatter = MathFormatter(style="github")
        region = _make_region(r"\int_a^b f(x)\,dx", is_inline=False)
        result = formatter.format(region)
        assert result.startswith("```math\n")
        assert result.endswith("\n```")
        assert r"\int_a^b f(x)\,dx" in result


class TestLowConfidenceMarker:
    def test_low_confidence_inline_standard(self):
        formatter = MathFormatter(style="standard")
        region = _make_region("x ≤ y", confidence=0.6, source_type="unicode")
        result = formatter.format(region)
        assert result.startswith("<!-- sci:math:low-confidence -->")
        assert "$x ≤ y$" in result

    def test_low_confidence_block_standard(self):
        formatter = MathFormatter(style="standard")
        region = _make_region("x = y", confidence=0.65, is_inline=False, source_type="unicode")
        result = formatter.format(region)
        assert result.startswith("<!-- sci:math:low-confidence -->")
        assert "$$x = y$$" in result

    def test_low_confidence_github(self):
        formatter = MathFormatter(style="github")
        region = _make_region("x", confidence=0.5, source_type="unicode")
        result = formatter.format(region)
        assert result.startswith("<!-- sci:math:low-confidence -->")
        assert "$`x`$" in result

    def test_threshold_exactly_07_not_low(self):
        formatter = MathFormatter(style="standard")
        region = _make_region("x", confidence=0.7)
        result = formatter.format(region)
        assert not result.startswith("<!-- sci:math:low-confidence -->")

    def test_threshold_below_07_is_low(self):
        formatter = MathFormatter(style="standard")
        region = _make_region("x", confidence=0.699)
        result = formatter.format(region)
        assert result.startswith("<!-- sci:math:low-confidence -->")

    def test_high_confidence_no_marker(self):
        formatter = MathFormatter(style="standard")
        region = _make_region("x^2", confidence=0.95, source_type="mathjax")
        result = formatter.format(region)
        assert "<!-- sci:math:low-confidence -->" not in result


class TestFormatterInitialization:
    def test_default_style_is_standard(self):
        formatter = MathFormatter()
        region = _make_region("x")
        result = formatter.format(region)
        assert result == "$x$"

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError):
            MathFormatter(style="unknown_style")

    def test_format_list(self):
        formatter = MathFormatter(style="standard")
        regions = [
            _make_region("x", is_inline=True),
            _make_region("y = z", is_inline=False),
        ]
        results = formatter.format_all(regions)
        assert len(results) == 2
        assert results[0] == "$x$"
        assert results[1] == "$$y = z$$"
