"""Image extractor for PDF, DOCX, and PPTX documents."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import IO, Optional

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import ImageRef


class ImageExtractor:
    """Extracts embedded images from PDF, DOCX, and PPTX documents."""

    def __init__(
        self,
        config: SciMarkdownConfig,
        document_name: str,
        output_dir: Path,
    ) -> None:
        self.config = config
        self.document_name = self._sanitize_name(document_name)
        self.output_dir = output_dir
        self._counter: int = 0
        self._total_bytes: int = 0

    # ------------------------------------------------------------------
    # Naming helpers
    # ------------------------------------------------------------------

    def _sanitize_name(self, name: str) -> str:
        """Remove extension and replace non-alphanumeric characters with underscores."""
        # Strip extension
        stem = Path(name).stem
        # Replace non-alphanumeric chars with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9]", "_", stem)
        return sanitized

    def _make_filename(self, number: int, ext: str = "png") -> str:
        """Return ``{doc_name}_img{NNNNN}.{ext}`` with zero-padded counter.

        Uses at least 5 digits; if ``number`` > 99999 the width grows to fit.
        """
        width = max(5, len(str(number)))
        padded = str(number).zfill(width)
        return f"{self.document_name}_img{padded}.{ext}"

    def _next_filename(self, ext: str = "png") -> str:
        """Increment counter and return the next filename."""
        self._counter += 1
        return self._make_filename(self._counter, ext)

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def _save_image(self, img: "PIL.Image.Image", filename: str) -> Optional[str]:  # noqa: F821
        """Save *img* to ``output_dir/filename``.

        Respects ``performance_max_image_file_size_mb`` and
        ``performance_max_total_images_size_mb`` from config.

        Returns the absolute file path as a string, or ``None`` if skipped.
        """
        from PIL import Image  # noqa: F401 — ensure PIL available

        max_file_mb = self.config.performance_max_image_file_size_mb
        max_total_mb = self.config.performance_max_total_images_size_mb

        # Determine format from filename extension
        ext = Path(filename).suffix.lstrip(".").upper()
        if ext == "JPG":
            ext = "JPEG"

        # Estimate size in memory first
        buf = io.BytesIO()
        img.save(buf, format=ext)
        size_bytes = buf.tell()

        if size_bytes > max_file_mb * 1024 * 1024:
            return None

        if self._total_bytes + size_bytes > max_total_mb * 1024 * 1024:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        dest = self.output_dir / filename
        buf.seek(0)
        dest.write_bytes(buf.read())

        self._total_bytes += size_bytes
        return str(dest)

    # ------------------------------------------------------------------
    # Extractors
    # ------------------------------------------------------------------

    def extract_from_pdf(self, stream: IO[bytes]) -> list[ImageRef]:
        """Extract embedded images from a PDF byte stream using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError("PyMuPDF (fitz) is required for PDF extraction") from exc

        results: list[ImageRef] = []
        data = stream.read()
        doc = fitz.open(stream="data", filetype="pdf")  # type: ignore[attr-defined]

        try:
            for page_num, page in enumerate(doc):
                for img_index, img_info in enumerate(page.get_images(full=True)):
                    xref = img_info[0]
                    position = page_num * 1000 + img_index

                    try:
                        base_image = doc.extract_image(xref)
                    except Exception:
                        continue

                    raw_bytes: bytes = base_image["image"]
                    ext: str = base_image.get("ext", "png").lower()

                    from PIL import Image

                    try:
                        pil_img = Image.open(io.BytesIO(raw_bytes))
                        pil_img.load()
                    except Exception:
                        continue

                    filename = self._next_filename(ext)
                    saved_path = self._save_image(pil_img, filename)
                    if saved_path is None:
                        self._counter -= 1
                        continue

                    results.append(
                        ImageRef(
                            position=position,
                            file_path=saved_path,
                            original_format=ext,
                            width=pil_img.width,
                            height=pil_img.height,
                        )
                    )
        finally:
            doc.close()

        return results

    def extract_from_docx(self, stream: IO[bytes]) -> list[ImageRef]:
        """Extract embedded images from a DOCX byte stream (word/media/)."""
        return self._extract_from_zip(stream, prefix="word/media/")

    def extract_from_pptx(self, stream: IO[bytes]) -> list[ImageRef]:
        """Extract embedded images from a PPTX byte stream (ppt/media/)."""
        return self._extract_from_zip(stream, prefix="ppt/media/")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_from_zip(
        self, stream: IO[bytes], prefix: str
    ) -> list[ImageRef]:
        """Generic ZIP-based image extraction for DOCX/PPTX."""
        from PIL import Image

        results: list[ImageRef] = []

        with zipfile.ZipFile(stream) as zf:
            media_names = sorted(
                name for name in zf.namelist() if name.startswith(prefix)
            )

            for idx, member_name in enumerate(media_names):
                raw = zf.read(member_name)
                ext = Path(member_name).suffix.lstrip(".").lower()

                try:
                    pil_img = Image.open(io.BytesIO(raw))
                    pil_img.load()
                except Exception:
                    continue

                filename = self._next_filename(ext or "png")
                saved_path = self._save_image(pil_img, filename)
                if saved_path is None:
                    self._counter -= 1
                    continue

                results.append(
                    ImageRef(
                        position=idx,
                        file_path=saved_path,
                        original_format=ext or "png",
                        width=pil_img.width,
                        height=pil_img.height,
                    )
                )

        return results
