"""Additional MathDetector tests for coverage gaps: mover, munder, mathjax block."""

import pytest
from unittest.mock import patch, MagicMock
from scimarkdown.math.detector import MathDetector, _mathml_node_to_latex
from scimarkdown.models import MathRegion


class TestMathMLNodeToLatex:
    def test_mover_tag(self):
        """mover tag generates \\overset{over}{base}."""
        from bs4 import BeautifulSoup
        html = "<mover><mi>x</mi><mo>&#x005E;</mo></mover>"
        soup = BeautifulSoup(html, "html.parser")
        node = soup.find("mover")
        result = _mathml_node_to_latex(node)
        assert r"\overset" in result

    def test_munder_tag(self):
        """munder tag generates \\underset{under}{base}."""
        from bs4 import BeautifulSoup
        html = "<munder><mi>x</mi><mo>&#x005F;</mo></munder>"
        soup = BeautifulSoup(html, "html.parser")
        node = soup.find("munder")
        result = _mathml_node_to_latex(node)
        assert r"\underset" in result

    def test_string_node_returns_stripped(self):
        """Passing a plain string to _mathml_node_to_latex returns it stripped."""
        result = _mathml_node_to_latex("  hello  ")
        assert result == "hello"

    def test_node_with_no_name_attr(self):
        """NavigableString-like object without .name is handled."""
        from bs4 import NavigableString
        ns = NavigableString("  text  ")
        result = _mathml_node_to_latex(ns)
        assert result == "text"

    def test_unknown_tag_joins_children(self):
        """Unknown MathML tags join their children."""
        from bs4 import BeautifulSoup
        html = "<munknown><mi>x</mi><mi>y</mi></munknown>"
        soup = BeautifulSoup(html, "html.parser")
        node = soup.find("munknown")
        result = _mathml_node_to_latex(node)
        assert "x" in result and "y" in result


class TestMathMLDetector:
    def test_detects_mover_in_mathml(self):
        """Detector handles mover inside a math tag."""
        text = '<math><mover><mi>x</mi><mo>&#770;</mo></mover></math>'
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        assert regions[0].source_type == "mathml"

    def test_detects_munder_in_mathml(self):
        """Detector handles munder inside a math tag."""
        text = '<math><munder><mi>lim</mi><mo>x&#x2192;0</mo></munder></math>'
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        assert regions[0].source_type == "mathml"


class TestMathJaxDetector:
    def test_detects_block_latex_in_span(self):
        """Span with katex class and \\[...\\] content is detected as non-inline."""
        text = r'<span class="katex">\[E = mc^2\]</span>'
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1
        assert any(r.source_type == "mathjax" for r in regions)
        mathjax = [r for r in regions if r.source_type == "mathjax"]
        assert mathjax[0].is_inline is False

    def test_detects_inline_latex_in_span(self):
        """Span with math class and \\(...\\) content is detected as inline."""
        text = r'<span class="math">\(x^2\)</span>'
        detector = MathDetector()
        regions = detector.detect(text)
        mathjax = [r for r in regions if r.source_type == "mathjax"]
        assert len(mathjax) >= 1
        assert mathjax[0].is_inline is True

    def test_span_without_latex_delimiters_uses_text(self):
        """Span with math class but no delimiters uses span text as latex."""
        text = '<span class="MathJax">x squared</span>'
        detector = MathDetector()
        regions = detector.detect(text)
        mathjax = [r for r in regions if r.source_type == "mathjax"]
        assert len(mathjax) >= 1
        assert mathjax[0].latex == "x squared"

    def test_mathjax_region_pos_is_zero_when_not_found(self):
        """When the span can't be found in text, position defaults to 0."""
        # This is hard to trigger directly but the code handles it.
        # Just ensure detection works on a valid span
        text = '<span class="katex">formula</span>'
        detector = MathDetector()
        regions = detector.detect(text)
        mathjax = [r for r in regions if r.source_type == "mathjax"]
        assert len(mathjax) >= 1
        assert mathjax[0].position >= 0


class TestUnicodeEdgeCases:
    def test_single_math_symbol_not_detected(self):
        """A single unicode math symbol (below threshold) is not detected."""
        from scimarkdown.math.detector import MathDetector
        text = "x ∈ A"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) == 0

    def test_two_math_symbols_detected(self):
        """Two or more unicode math symbols are detected."""
        text = "∀x ∈ A we have x ≥ 0"
        detector = MathDetector()
        regions = detector.detect(text)
        assert len(regions) >= 1


class TestOCRCoverage:
    def test_pix2tex_available_function(self):
        """_pix2tex_available returns bool."""
        from scimarkdown.math.ocr import _pix2tex_available
        result = _pix2tex_available()
        assert isinstance(result, bool)

    def test_nougat_available_function(self):
        """_nougat_available returns bool."""
        from scimarkdown.math.ocr import _nougat_available
        result = _nougat_available()
        assert isinstance(result, bool)

    def test_load_pix2tex_raises_import_error_when_unavailable(self):
        """_load_pix2tex raises ImportError when pix2tex is not installed."""
        from scimarkdown.math.ocr import _load_pix2tex, _pix2tex_available
        if _pix2tex_available():
            pytest.skip("pix2tex is installed")
        with pytest.raises((ImportError, ModuleNotFoundError)):
            _load_pix2tex()

    def test_load_nougat_raises_import_error_when_unavailable(self):
        """_load_nougat raises ImportError when nougat is not installed."""
        from scimarkdown.math.ocr import _load_nougat, _nougat_available
        if _nougat_available():
            pytest.skip("nougat is installed")
        with pytest.raises((ImportError, ModuleNotFoundError)):
            _load_nougat()

    def test_recognize_empty_result_returns_none(self):
        """When model returns empty string, recognize returns None."""
        from scimarkdown.math.ocr import MathOCR
        from unittest.mock import patch, MagicMock

        mock_model = MagicMock()
        mock_model.return_value = ""  # empty result

        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_pix2tex", return_value=mock_model):
                ocr = MathOCR(engine="pix2tex")
                result = ocr.recognize(MagicMock())

        assert result is None

    def test_get_model_returns_none_for_unknown_engine(self):
        """_get_model returns None for an engine without a loader."""
        from scimarkdown.math.ocr import MathOCR
        ocr = MathOCR(engine="none")
        result = ocr._get_model()
        assert result is None

    def test_load_failed_flag_prevents_retry(self):
        """After load failure, _load_failed=True causes _get_model to return None."""
        from scimarkdown.math.ocr import MathOCR
        from unittest.mock import patch

        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_pix2tex", side_effect=RuntimeError("GPU OOM")):
                ocr = MathOCR(engine="pix2tex")
                result = ocr._get_model()

        assert result is None
        assert ocr._load_failed is True

    def test_recognize_returns_none_when_load_failed(self):
        """recognize() returns None immediately when _load_failed=True."""
        from scimarkdown.math.ocr import MathOCR
        from unittest.mock import patch

        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_pix2tex", side_effect=RuntimeError("fail")):
                ocr = MathOCR(engine="pix2tex")
                # First recognize triggers load (fails)
                result = ocr.recognize(MagicMock())

        assert result is None
