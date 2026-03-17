from dataclasses import dataclass


@dataclass
class TextBlock:
    position: int
    content: str
    block_type: str = "paragraph"
