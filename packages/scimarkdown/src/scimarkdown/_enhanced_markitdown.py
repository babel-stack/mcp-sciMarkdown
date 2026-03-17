"""EnhancedMarkItDown: subclass that adds formula detection and image extraction."""

import io
import logging
from pathlib import Path
from typing import Optional, BinaryIO, Any

from markitdown import MarkItDown, DocumentConverterResult
from markitdown._stream_info import StreamInfo

from .config import SciMarkdownConfig, load_config

logger = logging.getLogger(__name__)


class EnhancedMarkItDown(MarkItDown):
    """Extends MarkItDown with LaTeX formula detection and image extraction.

    Dual-pass architecture:
    - Pass 1: super().convert*() for base markdown
    - Pass 2: Re-parse source for structured data
    - Merge: Compose enriched markdown
    """

    def __init__(
        self,
        sci_config: Optional[SciMarkdownConfig] = None,
        output_dir: Optional[Path] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.sci_config = sci_config or load_config()
        self.output_dir = output_dir or Path(".")

    # Phase 2 and 3 will be added in Task 14.
    # For now, this is a passthrough skeleton.
