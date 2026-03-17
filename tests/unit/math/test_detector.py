"""Tests for MathDetector — Unicode, MathML, MathJax/KaTeX detection."""

import pytest
from scimarkdown.math import MathDetector
from scimarkdown.models import MathRegion


class TestUnicodeSuperscripts:
    def test_superscript_digits_detected(self):
        text = "E = mc²"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 1
        assert "^{2}" in regions[0].latex
        assert regions[0].source_type == "unicode"

    def test_superscript_n_detected(self):
        text = "x⁰ + xⁿ"
        detector = MathDetector()
        regions = detector.detect(text)
        assert any("^{n}" in r.latex or "^{0}" in r.latex for r in regions)

    def test_subscript_detected(self):
        text = "H₂O is water"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 1
        assert "_{2}" in regions[0].latex

    def test_mixed_super_subscript(self):
        text = "xᵢ² is common"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1


class TestUnicodeMathSymbols:
    def test_two_symbols_detected(self):
        text = "∀x ∈ ℝ there exists a solution"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        assert regions[0].source_type == "unicode"

    def test_single_symbol_no_detection(self):
        # Only 1 math symbol — below threshold of 2
        text = "x ∈ A"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 0

    def test_sum_integral_symbols(self):
        text = "∑ᵢ ∫ f(x) dx"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        latex = regions[0].latex
        assert "\\sum" in latex or "\\int" in latex

    def test_inequality_symbols(self):
        text = "a ≤ b ≥ c ≠ d"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1

    def test_infinity_symbol(self):
        text = "lim x→∞ equals ∞"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        assert "\\infty" in regions[0].latex

    def test_greek_letters(self):
        text = "α + β = γ"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        latex = regions[0].latex
        assert "\\alpha" in latex

    def test_blackboard_bold(self):
        text = "x ∈ ℝ, n ∈ ℤ"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        latex = regions[0].latex
        assert "\\mathbb{R}" in latex or "\\mathbb{Z}" in latex

    def test_confidence_scales_with_symbol_count(self):
        text_few = "a ≤ b"   # 1 symbol — no detection
        text_many = "∀x ∈ ℝ: x² ≥ 0"
        detector = MathDetector()
        regions_few = detector.detect(text_few)
        regions_many = detector.detect(text_many)
        assert len(regions_few) == 0
        assert len(regions_many) >= 1
        assert regions_many[0].confidence >= 0.6


class TestMathMLParsing:
    def test_simple_mathml(self):
        html = "<math><mn>2</mn><mo>+</mo><mn>3</mn></math>"
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert regions[0].source_type == "mathml"
        assert regions[0].confidence == pytest.approx(0.95)

    def test_mfrac_conversion(self):
        html = "<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>"
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert "\\frac" in regions[0].latex

    def test_msup_conversion(self):
        html = "<math><msup><mi>x</mi><mn>2</mn></msup></math>"
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert "^" in regions[0].latex

    def test_msub_conversion(self):
        html = "<math><msub><mi>x</mi><mi>i</mi></msub></math>"
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert "_" in regions[0].latex

    def test_msqrt_conversion(self):
        html = "<math><msqrt><mn>2</mn></msqrt></math>"
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert "\\sqrt" in regions[0].latex

    def test_position_is_character_offset(self):
        html = "Some text <math><mn>1</mn></math> more text"
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert regions[0].position == html.index("<math>")

    def test_mathml_in_html_context(self):
        html = "<p>Formula: <math><mi>x</mi><mo>+</mo><mi>y</mi></math></p>"
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert regions[0].source_type == "mathml"


class TestMathJaxKaTeX:
    def test_inline_mathjax(self):
        html = r'<span class="math-tex">\(x^2 + y^2 = z^2\)</span>'
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert regions[0].source_type == "mathjax"
        assert "x^2" in regions[0].latex
        assert regions[0].confidence == pytest.approx(0.9)

    def test_display_mathjax(self):
        html = r'<span class="math">\[E = mc^2\]</span>'
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert regions[0].source_type == "mathjax"
        assert "E = mc^2" in regions[0].latex

    def test_katex_span(self):
        html = r'<span class="katex">\(f(x) = \int_{-\infty}^{\infty}\)</span>'
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert regions[0].source_type == "mathjax"

    def test_position_of_mathjax(self):
        html = r'text <span class="math-tex">\(a+b\)</span> end'
        detector = MathDetector()
        regions = detector.detect(html)
        assert len(regions) == 1
        assert regions[0].position == html.index('<span')


class TestExistingLatexDelimiters:
    def test_inline_latex_passthrough(self):
        text = r"The equation \(x^2 + 1 = 0\) has no real solutions."
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 1
        assert regions[0].source_type == "latex"
        assert regions[0].confidence == pytest.approx(1.0)
        assert "x^2 + 1 = 0" in regions[0].latex

    def test_block_latex_passthrough(self):
        text = r"Consider \[E = mc^2\] as the equation."
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 1
        assert regions[0].source_type == "latex"
        assert "E = mc^2" in regions[0].latex

    def test_position_of_latex(self):
        text = r"abc \(x\) def"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 1
        assert regions[0].position == text.index(r"\(")


class TestNoFalsePositives:
    def test_plain_english_text(self):
        text = "This is a plain English sentence with no math."
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 0

    def test_numbers_alone(self):
        text = "There are 42 items in 3 categories."
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 0

    def test_punctuation_not_math(self):
        text = "Hello, world! How are you?"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 0

    def test_url_not_math(self):
        text = "Visit https://example.com/path?foo=bar for more info."
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 0

    def test_single_greek_no_detect(self):
        # A single Greek letter by itself should not trigger detection
        text = "See section α for details"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 0


class TestMathRegionFields:
    def test_returns_math_region_instances(self):
        text = r"\(x + y\)"
        detector = MathDetector()
        regions = detector.detect(text)
        assert all(isinstance(r, MathRegion) for r in regions)

    def test_original_text_preserved(self):
        text = r"\(x^2\)"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 1
        assert regions[0].original_text == r"\(x^2\)"

    def test_is_inline_for_inline_latex(self):
        text = r"\(x\)"
        detector = MathDetector()
        regions = detector.detect(text)
        assert regions[0].is_inline is True

    def test_is_inline_false_for_block_latex(self):
        text = r"\[x = y\]"
        detector = MathDetector()
        regions = detector.detect(text)
        assert regions[0].is_inline is False
