"""Image extractor for PDF, DOCX, PPTX, HTML, EPUB, and Jupyter documents."""

from __future__ import annotations

import io
import logging
import re
import zipfile
from pathlib import Path
from typing import IO, Optional

from scimarkdown.config import SciMarkdownConfig
from scimarkdown.models import ImageRef

logger = logging.getLogger(__name__)


class ImageExtractor:
    """Extracts embedded images from PDF, DOCX, PPTX, HTML, EPUB, and Jupyter documents."""

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

    def _next_filename(self, ext: str = "png") -> Optional[str]:
        """Increment counter and return the next filename, or None if limit reached."""
        if self._counter >= self.config.performance_max_images:
            logger.warning("Max images limit (%d) reached, skipping.", self.config.performance_max_images)
            return None
        self._counter += 1
        return self._make_filename(self._counter, ext)

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def _save_image(self, img: "PIL.Image.Image", filename: str) -> Optional[str]:  # noqa: F821
        """Save *img* to ``output_dir/filename``.

        Applies auto-cropping if enabled, then respects
        ``performance_max_image_file_size_mb`` and
        ``performance_max_total_images_size_mb`` from config.

        Returns the absolute file path as a string, or ``None`` if skipped.
        """
        from PIL import Image  # noqa: F401 — ensure PIL available
        from .cropper import ImageCropper

        # Apply auto-cropping if enabled
        if self.config.images_autocrop_whitespace:
            cropper = ImageCropper(
                margin=self.config.images_margin_px,
                autocrop=True,
            )
            img = cropper.crop(img)

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
        return filename  # Return filename only, not absolute path

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
        doc = fitz.open(stream=data, filetype="pdf")  # type: ignore[attr-defined]

        try:
            for page_num, page in enumerate(doc):
                # Get text blocks with positions for context matching
                text_blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
                # Sort by y position (top to bottom)
                text_only = sorted(
                    [(b[1], b[4].strip()) for b in text_blocks if b[6] == 0 and b[4].strip()],
                    key=lambda t: t[0],
                )

                for img_index, img_info in enumerate(page.get_images(full=True)):
                    xref = img_info[0]
                    position = page_num * 1000 + img_index

                    try:
                        base_image = doc.extract_image(xref)
                    except Exception:
                        continue

                    # Find image bounding box on page for context matching
                    context_text = None
                    try:
                        img_rects = page.get_image_rects(xref)
                        if img_rects:
                            img_y = img_rects[0].y0  # Top edge of image
                            # Find the text block closest above the image
                            for text_y, text_content in reversed(text_only):
                                if text_y < img_y and text_content:
                                    # Take last 100 chars to use as anchor
                                    context_text = text_content[-100:].strip()
                                    break
                    except Exception:  # pragma: no cover
                        pass

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
                            context_text=context_text,
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

    def extract_from_html(self, stream: IO[bytes]) -> list[ImageRef]:
        """Extract images from an HTML byte stream.

        Finds ``<img>`` tags with base64 data URIs (``data:image/...;base64,...``),
        decodes them, opens via PIL, and saves to ``output_dir``.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:  # pragma: no cover
            raise ImportError("beautifulsoup4 is required for HTML extraction") from exc

        from PIL import Image

        results: list[ImageRef] = []
        html_bytes = stream.read()
        soup = BeautifulSoup(html_bytes, "html.parser")

        for idx, img_tag in enumerate(soup.find_all("img")):
            src = img_tag.get("src", "")
            if not src.startswith("data:image/"):
                continue

            # Capture text context: find preceding text in the DOM
            context_text = None
            prev = img_tag.find_previous(string=True)
            while prev and not prev.strip():
                prev = prev.find_previous(string=True)
            if prev and prev.strip():
                context_text = prev.strip()[-100:]

            try:
                # data:image/png;base64,<data>
                header, b64data = src.split(",", 1)
                # derive extension from mime type
                mime_part = header.split(";")[0]  # e.g. "data:image/png"
                ext = mime_part.split("/")[-1].lower()  # e.g. "png"
                if ext == "jpeg":
                    ext = "jpg"

                raw_bytes = __import__("base64").b64decode(b64data)
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
                    position=idx,
                    file_path=saved_path,
                    original_format=ext,
                    width=pil_img.width,
                    height=pil_img.height,
                    context_text=context_text,
                )
            )

        return results

    def extract_from_epub(self, stream: IO[bytes]) -> list[ImageRef]:
        """Extract images from an EPUB byte stream (ZIP archive).

        Finds PNG/JPG/GIF image files in the archive, skipping ``META-INF/``,
        opens them with PIL, and saves to ``output_dir``.
        """
        from PIL import Image

        _IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        results: list[ImageRef] = []

        with zipfile.ZipFile(stream) as zf:
            image_names = sorted(
                name
                for name in zf.namelist()
                if not name.startswith("META-INF/")
                and Path(name).suffix.lower() in _IMAGE_EXTENSIONS
            )

            for idx, member_name in enumerate(image_names):
                raw = zf.read(member_name)
                ext = Path(member_name).suffix.lstrip(".").lower()
                if ext == "jpeg":
                    ext = "jpg"

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

    def extract_from_jupyter(self, stream: IO[bytes]) -> list[ImageRef]:
        """Extract images from a Jupyter notebook byte stream.

        Iterates cells → outputs → data, finds ``image/png`` or ``image/jpeg``
        mime keys, decodes base64 data, and saves to ``output_dir``.
        """
        import base64
        import json

        from PIL import Image

        results: list[ImageRef] = []
        notebook = json.loads(stream.read())
        cells = notebook.get("cells", [])
        counter = 0

        for cell in cells:
            outputs = cell.get("outputs", [])
            for output in outputs:
                data = output.get("data", {})
                for mime_type in ("image/png", "image/jpeg"):
                    b64_data = data.get(mime_type)
                    if b64_data is None:
                        continue

                    # Notebook data may be a list of lines or a single string
                    if isinstance(b64_data, list):
                        b64_data = "".join(b64_data)

                    ext = mime_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"

                    try:
                        raw_bytes = base64.b64decode(b64_data)
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
                            position=counter,
                            file_path=saved_path,
                            original_format=ext,
                            width=pil_img.width,
                            height=pil_img.height,
                        )
                    )
                    counter += 1

        return results

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
