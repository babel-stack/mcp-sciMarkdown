"""EnhancedMarkItDown: subclass that adds formula detection and image extraction."""

import io
import logging
from pathlib import Path
from typing import Optional, BinaryIO, Any

from markitdown import MarkItDown, DocumentConverterResult
from markitdown._stream_info import StreamInfo

from .config import SciMarkdownConfig, load_config
from .pipeline import EnrichmentPipeline, CompositionPipeline

logger = logging.getLogger(__name__)


class EnhancedMarkItDown(MarkItDown):
    """Extends MarkItDown with LaTeX formula detection and image extraction.

    Dual-pass architecture:
    - Pass 1: super().convert*() for base markdown
    - Pass 2: Re-parse source for structured data (EnrichmentPipeline)
    - Merge: Compose enriched markdown (CompositionPipeline)
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
        self._enrichment = EnrichmentPipeline(self.sci_config)
        self._composition = CompositionPipeline(self.sci_config)

    def convert_stream(self, stream, *, stream_info=None, file_extension=None, **kwargs):
        """Convert a byte stream with dual-pass enrichment.

        Pass 1 produces the base markdown via the parent class.
        Pass 2 enriches and composes the final markdown.
        On any error in Pass 2, the base result is returned unchanged.
        """
        if not stream.seekable():
            stream = io.BytesIO(stream.read())

        stream.seek(0)
        base_result = super().convert_stream(
            stream, stream_info=stream_info, file_extension=file_extension, **kwargs
        )

        stream.seek(0)
        try:
            document_name = "document"
            if file_extension:
                document_name = f"document{file_extension}"

            output_dir = self.output_dir
            if self.sci_config.images_output_dir != "same":
                output_dir = Path(self.sci_config.images_output_dir)

            ext = file_extension or ""
            enriched = self._enrichment.enrich(
                base_markdown=base_result.markdown or "",
                source_stream=stream,
                file_extension=ext,
                document_name=document_name,
                output_dir=output_dir,
            )

            final_markdown = self._composition.compose(enriched)

            return DocumentConverterResult(
                title=base_result.title,
                markdown=final_markdown,
            )
        except Exception as e:
            logger.error(f"Enrichment failed, returning base result: {e}", exc_info=True)
            return base_result
