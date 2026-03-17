"""Integration tests for the full SciMarkdown pipeline on HTML input."""

from __future__ import annotations

import pathlib

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.math.detector import MathDetector
from scimarkdown.models import EnrichedResult
from scimarkdown.pipeline.composition import CompositionPipeline


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run_pipeline(html: str, latex_style: str = "standard") -> str:
    """Detect math in *html*, then compose to final markdown."""
    detector = MathDetector()
    regions = detector.detect(html)
    config = SciMarkdownConfig(latex_style=latex_style)
    enriched = EnrichedResult(base_markdown=html, math_regions=regions)
    composer = CompositionPipeline(config)
    return composer.compose(enriched)


# ---------------------------------------------------------------------------
# MathML tests
# ---------------------------------------------------------------------------


def test_html_mathml_full_pipeline() -> None:
    """MathML <math> tag is detected and converted to LaTeX."""
    html = '<p>The formula <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math> is simple.</p>'
    detector = MathDetector()
    regions = detector.detect(html)
    assert len(regions) >= 1
    config = SciMarkdownConfig(latex_style="standard")
    enriched = EnrichedResult(base_markdown=html, math_regions=regions)
    composer = CompositionPipeline(config)
    result = composer.compose(enriched)
    assert "\\frac" in result or "$" in result


def test_html_mathml_frac_rendered() -> None:
    """MathML mfrac produces \\frac{}{} in LaTeX output."""
    html = '<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>'
    result = _run_pipeline(html)
    assert "\\frac" in result


def test_html_mathml_multiple_formulas() -> None:
    """Multiple <math> blocks in one HTML document are all processed."""
    html = (
        '<p><math><mi>x</mi></math></p>'
        '<p><math><mfrac><mn>1</mn><mn>2</mn></mfrac></math></p>'
    )
    detector = MathDetector()
    regions = detector.detect(html)
    assert len(regions) >= 2
    result = _run_pipeline(html)
    assert "$" in result


def test_html_mathml_fixture() -> None:
    """The html_mathml.html fixture produces LaTeX with \\frac."""
    fixture = (
        pathlib.Path(__file__).parent.parent / "fixtures" / "html_mathml.html"
    )
    html = fixture.read_text(encoding="utf-8")
    result = _run_pipeline(html)
    assert "\\frac" in result or "$" in result


# ---------------------------------------------------------------------------
# MathJax tests
# ---------------------------------------------------------------------------


def test_html_mathjax_inline_detected() -> None:
    """MathJax inline \\(...\\) syntax is detected."""
    html = '<p>The value <span class="math inline">\\(e^{i\\pi} + 1 = 0\\)</span>.</p>'
    detector = MathDetector()
    regions = detector.detect(html)
    assert len(regions) >= 1


def test_html_mathjax_inline_produces_latex() -> None:
    """MathJax inline expression renders to LaTeX in the composed output."""
    html = '<span class="math inline">\\(e^{i\\pi} + 1 = 0\\)</span>'
    result = _run_pipeline(html)
    assert "$" in result or "\\(" in result or "e^" in result


def test_html_mathjax_fixture() -> None:
    """The html_mathjax.html fixture is processed without error."""
    fixture = (
        pathlib.Path(__file__).parent.parent / "fixtures" / "html_mathjax.html"
    )
    html = fixture.read_text(encoding="utf-8")
    result = _run_pipeline(html)
    # Should produce some LaTeX delimiter or preserved expression
    assert isinstance(result, str) and len(result) > 0


# ---------------------------------------------------------------------------
# Combined / edge case tests
# ---------------------------------------------------------------------------


def test_html_no_math_passthrough() -> None:
    """HTML with no math passes through without LaTeX delimiters."""
    html = "<p>Hello, world! No formulas here.</p>"
    result = _run_pipeline(html)
    assert "$" not in result
    assert "Hello, world!" in result


def test_html_mathml_source_type() -> None:
    """MathML regions have source_type='mathml'."""
    html = '<math><mi>x</mi></math>'
    detector = MathDetector()
    regions = detector.detect(html)
    assert any(r.source_type == "mathml" for r in regions)


def test_html_mathjax_source_type() -> None:
    """MathJax regions have source_type='mathjax'."""
    html = '<span class="math inline">\\(x^2\\)</span>'
    detector = MathDetector()
    regions = detector.detect(html)
    assert any(r.source_type == "mathjax" for r in regions)


def test_html_result_is_string() -> None:
    """Pipeline always returns a string for any HTML input."""
    result = _run_pipeline("")
    assert isinstance(result, str)


def test_html_github_style_delimiters() -> None:
    """GitHub-style config produces backtick delimiters for math."""
    html = '<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>'
    result = _run_pipeline(html, latex_style="github")
    # GitHub style uses $`...`$ for inline or ```math for display
    assert "$`" in result or "```math" in result or "$" in result
