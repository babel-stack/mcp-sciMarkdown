"""Math detector: Unicode symbols, MathML, MathJax/KaTeX, and existing LaTeX delimiters."""

from __future__ import annotations

import re
from typing import List

from bs4 import BeautifulSoup, Tag

from scimarkdown.models import MathRegion


# ---------------------------------------------------------------------------
# Unicode → LaTeX mapping tables
# ---------------------------------------------------------------------------

UNICODE_TO_LATEX: dict[str, str] = {
    # Logic / set theory
    "∀": r"\forall",
    "∃": r"\exists",
    "∈": r"\in",
    "∉": r"\notin",
    "∅": r"\emptyset",
    "∩": r"\cap",
    "∪": r"\cup",
    "⊂": r"\subset",
    "⊃": r"\supset",
    "⊆": r"\subseteq",
    "⊇": r"\supseteq",
    # Arithmetic / algebra
    "±": r"\pm",
    "∓": r"\mp",
    "×": r"\times",
    "÷": r"\div",
    "⋅": r"\cdot",
    "·": r"\cdot",
    "√": r"\sqrt",
    "∝": r"\propto",
    # Calculus
    "∑": r"\sum",
    "∏": r"\prod",
    "∫": r"\int",
    "∂": r"\partial",
    "∇": r"\nabla",
    "∆": r"\Delta",
    # Relations
    "≤": r"\leq",
    "≥": r"\geq",
    "≠": r"\neq",
    "≈": r"\approx",
    "≡": r"\equiv",
    "≪": r"\ll",
    "≫": r"\gg",
    "∼": r"\sim",
    "≃": r"\simeq",
    "≅": r"\cong",
    # Arrows
    "→": r"\rightarrow",
    "←": r"\leftarrow",
    "↔": r"\leftrightarrow",
    "⇒": r"\Rightarrow",
    "⇐": r"\Leftarrow",
    "⇔": r"\Leftrightarrow",
    "↦": r"\mapsto",
    # Misc
    "∞": r"\infty",
    "∴": r"\therefore",
    "∵": r"\because",
    "⊥": r"\perp",
    "∥": r"\parallel",
    "∠": r"\angle",
    "°": r"^{\circ}",
    # Greek lowercase
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\varepsilon",
    "ζ": r"\zeta",
    "η": r"\eta",
    "θ": r"\theta",
    "ι": r"\iota",
    "κ": r"\kappa",
    "λ": r"\lambda",
    "μ": r"\mu",
    "ν": r"\nu",
    "ξ": r"\xi",
    "π": r"\pi",
    "ρ": r"\rho",
    "σ": r"\sigma",
    "τ": r"\tau",
    "υ": r"\upsilon",
    "φ": r"\phi",
    "χ": r"\chi",
    "ψ": r"\psi",
    "ω": r"\omega",
    # Greek uppercase
    "Γ": r"\Gamma",
    "Δ": r"\Delta",
    "Θ": r"\Theta",
    "Λ": r"\Lambda",
    "Ξ": r"\Xi",
    "Π": r"\Pi",
    "Σ": r"\Sigma",
    "Υ": r"\Upsilon",
    "Φ": r"\Phi",
    "Ψ": r"\Psi",
    "Ω": r"\Omega",
    # Blackboard bold
    "ℝ": r"\mathbb{R}",
    "ℤ": r"\mathbb{Z}",
    "ℕ": r"\mathbb{N}",
    "ℚ": r"\mathbb{Q}",
    "ℂ": r"\mathbb{C}",
    "𝔽": r"\mathbb{F}",
    # Superscript digits & letters (Unicode superscript chars)
    "⁰": "^{0}",
    "¹": "^{1}",
    "²": "^{2}",
    "³": "^{3}",
    "⁴": "^{4}",
    "⁵": "^{5}",
    "⁶": "^{6}",
    "⁷": "^{7}",
    "⁸": "^{8}",
    "⁹": "^{9}",
    "ⁿ": "^{n}",
    "ⁱ": "^{i}",
    # Subscript digits & letters
    "₀": "_{0}",
    "₁": "_{1}",
    "₂": "_{2}",
    "₃": "_{3}",
    "₄": "_{4}",
    "₅": "_{5}",
    "₆": "_{6}",
    "₇": "_{7}",
    "₈": "_{8}",
    "₉": "_{9}",
    "ₙ": "_{n}",
    "ᵢ": "_{i}",
    "ⱼ": "_{j}",
    "ₖ": "_{k}",
}

# Characters that are "pure" math symbols (non-super/sub) used for counting
_MATH_SYMBOL_CHARS: frozenset[str] = frozenset(
    c
    for c in UNICODE_TO_LATEX
    if not (c in "⁰¹²³⁴⁵⁶⁷⁸⁹ⁿⁱ₀₁₂₃₄₅₆₇₈₉ₙᵢⱼₖ")
)

# Super/subscript chars
_SUPERSCRIPT_CHARS: frozenset[str] = frozenset("⁰¹²³⁴⁵⁶⁷⁸⁹ⁿⁱ")
_SUBSCRIPT_CHARS: frozenset[str] = frozenset("₀₁₂₃₄₅₆₇₈₉ₙᵢⱼₖ")
_SUPER_SUB_CHARS: frozenset[str] = _SUPERSCRIPT_CHARS | _SUBSCRIPT_CHARS


def _count_math_symbols(text: str) -> int:
    """Count non-super/sub Unicode math symbols in *text*."""
    return sum(1 for ch in text if ch in _MATH_SYMBOL_CHARS)


def _count_super_sub(text: str) -> int:
    return sum(1 for ch in text if ch in _SUPER_SUB_CHARS)


def _unicode_line_to_latex(text: str) -> str:
    """Replace every known Unicode math character with its LaTeX equivalent."""
    result: list[str] = []
    for ch in text:
        result.append(UNICODE_TO_LATEX.get(ch, ch))
    return "".join(result)


# ---------------------------------------------------------------------------
# MathML → LaTeX helpers
# ---------------------------------------------------------------------------

def _mathml_node_to_latex(node) -> str:
    """Recursively convert a BeautifulSoup MathML node to LaTeX."""
    if isinstance(node, str):
        return node.strip()

    if not hasattr(node, "name") or node.name is None:
        return node.get_text(strip=True) if hasattr(node, "get_text") else str(node).strip()

    tag = node.name.lower()
    children = [c for c in node.children]
    child_latex = [_mathml_node_to_latex(c) for c in children]
    child_latex = [s for s in child_latex if s]  # remove empty

    if tag == "math":
        return " ".join(child_latex)
    elif tag in ("mn", "mi", "mo", "mtext"):
        return "".join(child_latex)
    elif tag == "mrow":
        return " ".join(child_latex)
    elif tag == "mfrac":
        num = child_latex[0] if len(child_latex) > 0 else ""
        den = child_latex[1] if len(child_latex) > 1 else ""
        return rf"\frac{{{num}}}{{{den}}}"
    elif tag == "msup":
        base = child_latex[0] if len(child_latex) > 0 else ""
        exp = child_latex[1] if len(child_latex) > 1 else ""
        return rf"{base}^{{{exp}}}"
    elif tag == "msub":
        base = child_latex[0] if len(child_latex) > 0 else ""
        sub = child_latex[1] if len(child_latex) > 1 else ""
        return rf"{base}_{{{sub}}}"
    elif tag == "msqrt":
        inner = " ".join(child_latex)
        return rf"\sqrt{{{inner}}}"
    elif tag == "msubsup":
        base = child_latex[0] if len(child_latex) > 0 else ""
        sub = child_latex[1] if len(child_latex) > 1 else ""
        exp = child_latex[2] if len(child_latex) > 2 else ""
        return rf"{base}_{{{sub}}}^{{{exp}}}"
    elif tag == "mover":
        base = child_latex[0] if len(child_latex) > 0 else ""
        over = child_latex[1] if len(child_latex) > 1 else ""
        return rf"\overset{{{over}}}{{{base}}}"
    elif tag == "munder":
        base = child_latex[0] if len(child_latex) > 0 else ""
        under = child_latex[1] if len(child_latex) > 1 else ""
        return rf"\underset{{{under}}}{{{base}}}"
    else:
        return " ".join(child_latex)


# ---------------------------------------------------------------------------
# MathDetector
# ---------------------------------------------------------------------------

_LATEX_INLINE_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_LATEX_BLOCK_RE = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)

# MathJax/KaTeX: spans with class containing "math", "katex", "MathJax"
_MATHJAX_SPAN_CLASS_RE = re.compile(r"math|katex|MathJax", re.IGNORECASE)

# Detect LaTeX inside span content: \(...\) or \[...\]
_LATEX_INNER_INLINE_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_LATEX_INNER_BLOCK_RE = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)


class MathDetector:
    """Detect math regions in text or HTML using multiple strategies."""

    def detect(self, text: str) -> List[MathRegion]:
        """Return all detected MathRegion objects from *text*."""
        mathml_regions = self._detect_mathml(text)
        mathjax_regions = self._detect_mathjax(text)

        # Collect ranges already covered by MathML and MathJax to avoid duplicates
        covered_ranges: list[tuple[int, int]] = []
        for r in mathml_regions + mathjax_regions:
            end = r.position + len(r.original_text)
            covered_ranges.append((r.position, end))

        def _is_covered(pos: int, length: int) -> bool:
            end = pos + length
            for start_c, end_c in covered_ranges:
                # Consider covered if position overlaps with any existing range
                if not (end <= start_c or pos >= end_c):
                    return True
            return False

        latex_regions = [
            r for r in self._detect_latex_delimiters(text)
            if not _is_covered(r.position, len(r.original_text))
        ]
        unicode_regions = self._detect_unicode(text)

        regions: list[MathRegion] = (
            mathml_regions + mathjax_regions + latex_regions + unicode_regions
        )

        # Deduplicate by position (keep highest-priority / first seen)
        seen_positions: set[int] = set()
        unique: list[MathRegion] = []
        for r in regions:
            if r.position not in seen_positions:
                seen_positions.add(r.position)
                unique.append(r)

        return unique

    # ------------------------------------------------------------------
    # Strategy 1: MathML
    # ------------------------------------------------------------------

    def _detect_mathml(self, text: str) -> list[MathRegion]:
        regions: list[MathRegion] = []
        soup = BeautifulSoup(text, "html.parser")
        math_tags = soup.find_all("math")
        for tag in math_tags:
            original = str(tag)
            pos = text.find(original)
            if pos == -1:
                pos = 0
            latex = _mathml_node_to_latex(tag)
            regions.append(
                MathRegion(
                    position=pos,
                    original_text=original,
                    latex=latex,
                    source_type="mathml",
                    confidence=0.95,
                    is_inline=True,
                )
            )
        return regions

    # ------------------------------------------------------------------
    # Strategy 2: MathJax / KaTeX spans
    # ------------------------------------------------------------------

    def _detect_mathjax(self, text: str) -> list[MathRegion]:
        regions: list[MathRegion] = []
        soup = BeautifulSoup(text, "html.parser")
        spans = soup.find_all("span")
        for span in spans:
            classes = span.get("class", [])
            classes_str = " ".join(classes) if isinstance(classes, list) else str(classes)
            if not _MATHJAX_SPAN_CLASS_RE.search(classes_str):
                continue
            original = str(span)
            pos = text.find(original)
            if pos == -1:
                pos = 0
            span_text = span.get_text()
            # Try to extract LaTeX from delimiters inside the span text
            m_inline = _LATEX_INNER_INLINE_RE.search(span_text)
            m_block = _LATEX_INNER_BLOCK_RE.search(span_text)
            if m_inline:
                latex = m_inline.group(1).strip()
                is_inline = True
            elif m_block:
                latex = m_block.group(1).strip()
                is_inline = False
            else:
                latex = span_text.strip()
                is_inline = True
            regions.append(
                MathRegion(
                    position=pos,
                    original_text=original,
                    latex=latex,
                    source_type="mathjax",
                    confidence=0.9,
                    is_inline=is_inline,
                )
            )
        return regions

    # ------------------------------------------------------------------
    # Strategy 3: Existing LaTeX delimiters
    # ------------------------------------------------------------------

    def _detect_latex_delimiters(self, text: str) -> list[MathRegion]:
        regions: list[MathRegion] = []
        for m in _LATEX_INLINE_RE.finditer(text):
            regions.append(
                MathRegion(
                    position=m.start(),
                    original_text=m.group(0),
                    latex=m.group(1).strip(),
                    source_type="latex",
                    confidence=1.0,
                    is_inline=True,
                )
            )
        for m in _LATEX_BLOCK_RE.finditer(text):
            regions.append(
                MathRegion(
                    position=m.start(),
                    original_text=m.group(0),
                    latex=m.group(1).strip(),
                    source_type="latex",
                    confidence=1.0,
                    is_inline=False,
                )
            )
        return regions

    # ------------------------------------------------------------------
    # Strategy 4: Unicode math symbols
    # ------------------------------------------------------------------

    def _detect_unicode(self, text: str) -> list[MathRegion]:
        """Detect lines (or segments) containing 2+ math Unicode symbols."""
        regions: list[MathRegion] = []
        offset = 0
        for line in text.splitlines(keepends=True):
            sym_count = _count_math_symbols(line)
            sup_sub_count = _count_super_sub(line)
            total = sym_count + sup_sub_count

            if sym_count >= 2 or (sym_count >= 1 and sup_sub_count >= 1):
                # Confidence scales with number of symbols
                if total >= 5:
                    confidence = 0.95
                elif total >= 3:
                    confidence = 0.8
                else:
                    confidence = 0.6

                latex = _unicode_line_to_latex(line.rstrip())
                regions.append(
                    MathRegion(
                        position=offset,
                        original_text=line.rstrip(),
                        latex=latex,
                        source_type="unicode",
                        confidence=confidence,
                        is_inline=True,
                    )
                )
            elif sup_sub_count >= 1 and sym_count == 0:
                # Super/subscript with at least 1 char: detect as single token
                # only if there's a superscript/subscript that forms a plausible math expression
                # Look for patterns like "x²" or "H₂" (letter followed by super/sub)
                for m in re.finditer(
                    r"[A-Za-z0-9][⁰¹²³⁴⁵⁶⁷⁸⁹ⁿⁱ₀₁₂₃₄₅₆₇₈₉ₙᵢⱼₖ]+", line
                ):
                    seg = m.group(0)
                    latex = _unicode_line_to_latex(seg)
                    regions.append(
                        MathRegion(
                            position=offset + m.start(),
                            original_text=seg,
                            latex=latex,
                            source_type="unicode",
                            confidence=0.7,
                            is_inline=True,
                        )
                    )
            offset += len(line)
        return regions
