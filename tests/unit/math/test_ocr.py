"""Tests for MathOCR — wrapper around pix2tex/Nougat engines."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from scimarkdown.math import MathOCR
from scimarkdown.math.ocr import OCRResult


class TestOCRResult:
    def test_ocr_result_fields(self):
        result = OCRResult(latex=r"\frac{1}{2}", confidence=0.88)
        assert result.latex == r"\frac{1}{2}"
        assert result.confidence == pytest.approx(0.88)

    def test_ocr_result_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(OCRResult)


class TestMathOCRInit:
    def test_default_engine_is_auto(self):
        ocr = MathOCR()
        assert ocr.engine == "auto"

    def test_explicit_none_engine(self):
        ocr = MathOCR(engine="none")
        assert ocr.engine == "none"

    def test_explicit_pix2tex_engine(self):
        ocr = MathOCR(engine="pix2tex")
        assert ocr.engine == "pix2tex"

    def test_explicit_nougat_engine(self):
        ocr = MathOCR(engine="nougat")
        assert ocr.engine == "nougat"

    def test_invalid_engine_raises(self):
        with pytest.raises(ValueError):
            MathOCR(engine="unknown_engine")

    def test_timeout_config(self):
        ocr = MathOCR(timeout=30)
        assert ocr.timeout == 30

    def test_default_timeout(self):
        ocr = MathOCR()
        assert isinstance(ocr.timeout, (int, float))
        assert ocr.timeout > 0


class TestNoneEngine:
    def test_none_engine_not_available(self):
        ocr = MathOCR(engine="none")
        assert ocr.is_available() is False

    def test_none_engine_recognize_returns_none(self):
        ocr = MathOCR(engine="none")
        fake_image = MagicMock()
        result = ocr.recognize(fake_image)
        assert result is None

    def test_none_engine_unload_is_noop(self):
        ocr = MathOCR(engine="none")
        ocr.unload()  # Should not raise


class TestAutoSelection:
    def test_auto_falls_back_to_none_when_nothing_available(self):
        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=False):
            with patch("scimarkdown.math.ocr._nougat_available", return_value=False):
                ocr = MathOCR(engine="auto")
                assert ocr.is_available() is False

    def test_auto_selects_pix2tex_when_available(self):
        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._nougat_available", return_value=False):
                ocr = MathOCR(engine="auto")
                assert ocr.is_available() is True
                assert ocr._resolved_engine == "pix2tex"

    def test_auto_selects_nougat_when_only_nougat_available(self):
        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=False):
            with patch("scimarkdown.math.ocr._nougat_available", return_value=True):
                ocr = MathOCR(engine="auto")
                assert ocr.is_available() is True
                assert ocr._resolved_engine == "nougat"


class TestPix2texEngine:
    def test_pix2tex_not_available_when_not_installed(self):
        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=False):
            ocr = MathOCR(engine="pix2tex")
            assert ocr.is_available() is False

    def test_pix2tex_recognize_uses_mock(self):
        mock_model = MagicMock()
        mock_model.return_value = r"\frac{a}{b}"

        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_pix2tex", return_value=mock_model):
                ocr = MathOCR(engine="pix2tex")
                fake_image = MagicMock()
                fake_image.size = (100, 50)
                result = ocr.recognize(fake_image)
                assert result is not None
                assert isinstance(result, OCRResult)
                assert result.latex == r"\frac{a}{b}"

    def test_pix2tex_recognize_returns_none_when_unavailable(self):
        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=False):
            ocr = MathOCR(engine="pix2tex")
            fake_image = MagicMock()
            result = ocr.recognize(fake_image)
            assert result is None

    def test_pix2tex_unload_clears_model(self):
        mock_model = MagicMock()
        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_pix2tex", return_value=mock_model):
                ocr = MathOCR(engine="pix2tex")
                ocr._model = mock_model
                ocr.unload()
                assert ocr._model is None


class TestNougatEngine:
    def test_nougat_not_available_when_not_installed(self):
        with patch("scimarkdown.math.ocr._nougat_available", return_value=False):
            ocr = MathOCR(engine="nougat")
            assert ocr.is_available() is False

    def test_nougat_recognize_uses_mock(self):
        mock_model = MagicMock()
        mock_model.return_value = r"\int_0^1 f(x)\,dx"

        with patch("scimarkdown.math.ocr._nougat_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_nougat", return_value=mock_model):
                ocr = MathOCR(engine="nougat")
                fake_image = MagicMock()
                result = ocr.recognize(fake_image)
                assert result is not None
                assert isinstance(result, OCRResult)
                assert result.latex == r"\int_0^1 f(x)\,dx"

    def test_nougat_recognize_returns_none_when_unavailable(self):
        with patch("scimarkdown.math.ocr._nougat_available", return_value=False):
            ocr = MathOCR(engine="nougat")
            fake_image = MagicMock()
            result = ocr.recognize(fake_image)
            assert result is None

    def test_nougat_unload_clears_model(self):
        mock_model = MagicMock()
        with patch("scimarkdown.math.ocr._nougat_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_nougat", return_value=mock_model):
                ocr = MathOCR(engine="nougat")
                ocr._model = mock_model
                ocr.unload()
                assert ocr._model is None


class TestGracefulFallback:
    def test_recognize_exception_returns_none(self):
        mock_model = MagicMock()
        mock_model.side_effect = RuntimeError("GPU OOM")

        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_pix2tex", return_value=mock_model):
                ocr = MathOCR(engine="pix2tex")
                fake_image = MagicMock()
                result = ocr.recognize(fake_image)
                assert result is None

    def test_load_exception_makes_unavailable(self):
        with patch("scimarkdown.math.ocr._pix2tex_available", return_value=True):
            with patch("scimarkdown.math.ocr._load_pix2tex", side_effect=ImportError("no pix2tex")):
                ocr = MathOCR(engine="pix2tex")
                # Calling is_available triggers lazy loading — if load fails,
                # the engine degrades gracefully
                result = ocr.recognize(MagicMock())
                assert result is None

    def test_timeout_config_accepted(self):
        ocr = MathOCR(engine="none", timeout=5)
        assert ocr.timeout == 5
