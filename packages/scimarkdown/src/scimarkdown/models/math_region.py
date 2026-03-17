from dataclasses import dataclass


@dataclass
class MathRegion:
    position: int
    original_text: str
    latex: str
    source_type: str  # "omml", "mathml", "unicode", "mathjax", "latex", "ocr", "llm"
    confidence: float = 1.0
    is_inline: bool = True
