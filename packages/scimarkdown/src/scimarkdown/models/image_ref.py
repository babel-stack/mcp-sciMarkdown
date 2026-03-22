from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageRef:
    position: int
    file_path: str
    original_format: str
    width: int = 0
    height: int = 0
    caption: Optional[str] = None
    reference_label: Optional[str] = None
    ordinal: Optional[int] = None
    context_text: Optional[str] = None  # Text immediately above/before the image in source
