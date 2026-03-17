"""Math formatter: render MathRegion objects as LaTeX-delimited strings."""

from __future__ import annotations

from typing import List, Sequence

from scimarkdown.models import MathRegion

_VALID_STYLES = {"standard", "github"}
_LOW_CONFIDENCE_MARKER = "<!-- sci:math:low-confidence -->"
_LOW_CONFIDENCE_THRESHOLD = 0.7


class MathFormatter:
    """Format MathRegion objects into Markdown-embeddable LaTeX strings.

    Parameters
    ----------
    style:
        ``"standard"`` — ``$...$`` / ``$$...$$``
        ``"github"``   — `` $`...`$ `` / ```` ```math\\n...\\n``` ````
    """

    def __init__(self, style: str = "standard") -> None:
        if style not in _VALID_STYLES:
            raise ValueError(
                f"Unknown math style {style!r}. Valid values: {sorted(_VALID_STYLES)}"
            )
        self.style = style

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(self, region: MathRegion) -> str:
        """Return the formatted string for a single MathRegion."""
        body = self._render_body(region)
        if region.confidence < _LOW_CONFIDENCE_THRESHOLD:
            return f"{_LOW_CONFIDENCE_MARKER} {body}"
        return body

    def format_all(self, regions: Sequence[MathRegion]) -> List[str]:
        """Return a list of formatted strings, one per region."""
        return [self.format(r) for r in regions]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _render_body(self, region: MathRegion) -> str:
        latex = region.latex
        if self.style == "standard":
            if region.is_inline:
                return f"${latex}$"
            else:
                return f"$${latex}$$"
        else:  # github
            if region.is_inline:
                return f"$`{latex}`$"
            else:
                return f"```math\n{latex}\n```"
