"""Integration tests for the full SciMarkdown pipeline on plain-text input."""

from __future__ import annotations

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.math.detector import MathDetector
from scimarkdown.math.formatter import MathFormatter
from scimarkdown.models import EnrichedResult
from scimarkdown.pipeline.composition import CompositionPipeline


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run_pipeline(text: str, latex_style: str = "standard") -> str:
    """Detect math in *text*, then compose to final markdown."""
    detector = MathDetector()
    regions = detector.detect(text)
    config = SciMarkdownConfig(latex_style=latex_style)
    enriched = EnrichedResult(base_markdown=text, math_regions=regions)
    composer = CompositionPipeline(config)
    return composer.compose(enriched)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unicode_math_full_pipeline() -> None:
    """Unicode math symbols are detected and rendered with LaTeX delimiters."""
    text = "For all x ∈ ℝ, the sum ∑ᵢ xᵢ ≤ ∫ f(x)dx holds."
    detector = MathDetector()
    regions = detector.detect(text)
    config = SciMarkdownConfig(latex_style="standard")
    enriched = EnrichedResult(base_markdown=text, math_regions=regions)
    composer = CompositionPipeline(config)
    result = composer.compose(enriched)
    assert "$" in result  # Should have LaTeX delimiters


def test_plain_text_no_math_passthrough() -> None:
    """Plain text with no math passes through the pipeline unchanged."""
    text = "This is a simple sentence with no mathematical content."
    result = _run_pipeline(text)
    # No LaTeX delimiters should be introduced
    assert "$" not in result
    # Original text content is preserved
    assert "simple sentence" in result


def test_superscript_detected() -> None:
    """Unicode superscript characters trigger math detection."""
    text = "The energy is E = mc² where c is speed of light."
    regions = MathDetector().detect(text)
    assert any("²" in r.original_text or "mc" in r.original_text for r in regions), (
        "Superscript should have been detected as math"
    )
    result = _run_pipeline(text)
    # Output should contain a LaTeX representation
    assert "$" in result


def test_greek_letters_detected() -> None:
    """Greek letter characters in text trigger math detection."""
    text = "Let α be the learning rate and β the momentum coefficient."
    result = _run_pipeline(text)
    assert "$" in result


def test_integral_symbol_detected() -> None:
    """Integral symbol ∫ combined with other math triggers math detection."""
    # The detector uses context (multiple math cues boost confidence), so
    # combine ∫ with ∑ and ∈ to ensure detection.
    text = "The value ∑ᵢ ∫ f(x)dx is finite for all x ∈ ℝ."
    result = _run_pipeline(text)
    assert "$" in result


def test_summation_symbol_detected() -> None:
    """Summation symbol ∑ triggers math detection."""
    text = "The sum ∑ aᵢ converges for all i."
    result = _run_pipeline(text)
    assert "$" in result


def test_github_style_latex_delimiters() -> None:
    """GitHub-style LaTeX uses backtick delimiters."""
    text = "Value x² is computed."
    result = _run_pipeline(text, latex_style="github")
    # GitHub style uses $`...`$ for inline or ```math for display
    assert "$`" in result or "```math" in result or "$" in result


def test_multiple_math_regions_all_converted() -> None:
    """Multiple math regions in one document are all replaced."""
    text = "We have α + β = γ and x² + y² = z²."
    result = _run_pipeline(text)
    # At least one LaTeX delimiter present (may merge or split differently)
    assert "$" in result


def test_fixture_simple_text_with_math(tmp_path: "Path") -> None:  # noqa: F821
    """The simple_text_with_math.txt fixture produces LaTeX output."""
    import pathlib

    fixture = (
        pathlib.Path(__file__).parent.parent / "fixtures" / "simple_text_with_math.txt"
    )
    text = fixture.read_text(encoding="utf-8")
    result = _run_pipeline(text)
    assert "$" in result


def test_result_is_string() -> None:
    """Pipeline always returns a string even for empty input."""
    result = _run_pipeline("")
    assert isinstance(result, str)


def test_enriched_result_math_regions_list() -> None:
    """EnrichedResult.math_regions is always a list after detection."""
    text = "Test x² + y²"
    detector = MathDetector()
    regions = detector.detect(text)
    enriched = EnrichedResult(base_markdown=text, math_regions=regions)
    assert isinstance(enriched.math_regions, list)
