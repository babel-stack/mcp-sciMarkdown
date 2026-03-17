from dataclasses import dataclass, field
from typing import Any, Optional
from .text_block import TextBlock
from .math_region import MathRegion
from .image_ref import ImageRef


@dataclass
class EnrichedResult:
    base_markdown: str
    title: Optional[str] = None
    text_blocks: list[TextBlock] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    math_regions: list[MathRegion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
