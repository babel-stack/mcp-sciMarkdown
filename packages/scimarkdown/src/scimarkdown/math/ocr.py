"""MathOCR: Wrapper around pix2tex and Nougat OCR engines for LaTeX recognition."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_VALID_ENGINES = {"auto", "pix2tex", "nougat", "none"}
_DEFAULT_TIMEOUT = 60  # seconds


# ---------------------------------------------------------------------------
# OCRResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class OCRResult:
    """Result of an OCR recognition pass."""

    latex: str
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Availability probes (importable functions so tests can patch them)
# ---------------------------------------------------------------------------

def _pix2tex_available() -> bool:
    """Return True if pix2tex is importable."""
    try:
        import pix2tex  # noqa: F401
        return True
    except ImportError:
        return False


def _nougat_available() -> bool:
    """Return True if nougat is importable."""
    try:
        import nougat  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Lazy loader functions (patchable in tests)
# ---------------------------------------------------------------------------

def _load_pix2tex() -> Any:
    """Load and return a callable pix2tex model."""
    from pix2tex.cli import LatexOCR  # type: ignore[import]
    return LatexOCR()


def _load_nougat() -> Any:
    """Load and return a callable Nougat model."""
    from nougat import NougatModel  # type: ignore[import]
    model = NougatModel.from_pretrained()
    return model


# ---------------------------------------------------------------------------
# MathOCR
# ---------------------------------------------------------------------------

class MathOCR:
    """Wrap pix2tex or Nougat to recognize math formulas from images.

    Parameters
    ----------
    engine:
        ``"auto"``    — pick pix2tex if available, else nougat, else none.
        ``"pix2tex"`` — use pix2tex explicitly.
        ``"nougat"``  — use nougat explicitly.
        ``"none"``    — disable OCR (always returns None).
    timeout:
        Maximum seconds to wait for a recognition call.
    """

    def __init__(self, engine: str = "auto", timeout: float = _DEFAULT_TIMEOUT) -> None:
        if engine not in _VALID_ENGINES:
            raise ValueError(
                f"Unknown OCR engine {engine!r}. Valid values: {sorted(_VALID_ENGINES)}"
            )
        self.engine = engine
        self.timeout = timeout
        self._model: Optional[Any] = None
        self._resolved_engine: str = self._resolve_engine(engine)
        self._load_failed: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the resolved engine can be used."""
        e = self._resolved_engine
        if e == "none":
            return False
        if e == "pix2tex":
            return _pix2tex_available()
        if e == "nougat":
            return _nougat_available()
        return False  # pragma: no cover

    def recognize(self, image: Any) -> Optional[OCRResult]:
        """Recognize LaTeX from *image* (PIL.Image).

        Returns ``None`` on failure, unavailability, or engine "none".
        """
        if not self.is_available() or self._load_failed:
            return None

        model = self._get_model()
        if model is None:
            return None

        try:
            latex = model(image)
            if not latex:
                return None
            return OCRResult(latex=str(latex), confidence=0.9)
        except Exception as exc:
            logger.warning("MathOCR recognition failed: %s", exc)
            return None

    def unload(self) -> None:
        """Release the loaded model to free memory."""
        self._model = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_engine(self, engine: str) -> str:
        """For 'auto', select the best available engine at init time."""
        if engine != "auto":
            return engine
        if _pix2tex_available():
            return "pix2tex"
        if _nougat_available():
            return "nougat"
        return "none"

    def _get_model(self) -> Optional[Any]:
        """Lazy-load the model on first use."""
        if self._model is not None:
            return self._model

        loader: Optional[Callable[[], Any]] = None
        if self._resolved_engine == "pix2tex":
            loader = _load_pix2tex
        elif self._resolved_engine == "nougat":
            loader = _load_nougat

        if loader is None:
            return None

        try:
            self._model = loader()
            return self._model
        except Exception as exc:
            logger.warning("MathOCR failed to load engine %r: %s", self._resolved_engine, exc)
            self._load_failed = True
            return None
