"""MCP server for SciMarkdown with two conversion tools."""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from markitdown import MarkItDown
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig
from scimarkdown.math.detector import MathDetector
from scimarkdown.math.formatter import MathFormatter
from scimarkdown.math.ocr import MathOCR
from scimarkdown.images.extractor import ImageExtractor
from scimarkdown.images.reference_linker import ReferenceLinker
from scimarkdown.images.index_builder import IndexBuilder
from scimarkdown.models import MathRegion, ImageRef
from scimarkdown.mcp.serializers import math_region_to_dict, image_ref_to_dict


def _get_embedding_client():
    """Return a GeminiEmbeddingClient if GEMINI_API_KEY is set, else None."""
    import os
    from pathlib import Path
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from scimarkdown.embeddings.client import GeminiEmbeddingClient
        return GeminiEmbeddingClient(api_key=api_key, cache_dir=Path(".scimarkdown_cache"))
    except Exception:
        return None


def create_mcp_server() -> FastMCP:
    """Create and return a configured FastMCP server instance."""
    mcp = FastMCP("scimarkdown")

    @mcp.tool()
    def convert_to_markdown(uri: str) -> str:
        """Convert a file or URL to plain Markdown using base MarkItDown.

        Args:
            uri: File path or URL to convert.

        Returns:
            Markdown text of the converted document.
        """
        converter = MarkItDown()
        result = converter.convert(uri)
        return result.markdown or ""

    @mcp.tool()
    def convert_to_scimarkdown(uri: str, config: Optional[dict] = None) -> str:
        """Convert a file or URL to enriched SciMarkdown with LaTeX and image support.

        Args:
            uri: File path or URL to convert.
            config: Optional configuration overrides as a dict.
                    Supports the same keys as scimarkdown.yaml (nested dicts).

        Returns:
            Enriched Markdown text with LaTeX formulas and image references.
        """
        sci_config = SciMarkdownConfig()
        if config:
            sci_config = sci_config.with_overrides(config)

        converter = EnhancedMarkItDown(sci_config=sci_config)
        result = converter.convert(uri)
        return result.markdown or ""

    @mcp.tool()
    def detect_math(text: str, methods: Optional[list] = None) -> str:
        """Detect math regions in text using MathDetector.

        Args:
            text: Input text (plain text or HTML) to scan for math.
            methods: Optional list of source_type values to filter by
                     (e.g. ["latex", "unicode", "mathml", "mathjax"]).
                     If None or empty, all detected regions are returned.

        Returns:
            JSON array of math region dicts, each with keys:
            position, original_text, latex, source_type, confidence, is_inline.
        """
        detector = MathDetector()
        regions = detector.detect(text)
        if methods:
            regions = [r for r in regions if r.source_type in methods]
        return json.dumps([math_region_to_dict(r) for r in regions])

    @mcp.tool()
    def format_latex(formulas: str, style: str = "standard") -> str:
        """Format LaTeX formula dicts into Markdown-embeddable strings.

        Args:
            formulas: JSON array of dicts, each containing at least
                      "latex" (str) and "is_inline" (bool).
                      "original_text" is included in the output if present.
            style: Formatting style — "standard" ($...$) or "github" ($`...`$).

        Returns:
            JSON array of dicts with keys "original_text" and "formatted".
        """
        formula_list = json.loads(formulas)
        formatter = MathFormatter(style=style)
        results = []
        for item in formula_list:
            region = MathRegion(
                position=item.get("position", 0),
                original_text=item.get("original_text", item.get("latex", "")),
                latex=item["latex"],
                source_type=item.get("source_type", "latex"),
                confidence=item.get("confidence", 1.0),
                is_inline=item.get("is_inline", True),
            )
            formatted = formatter.format(region)
            results.append({
                "original_text": region.original_text,
                "formatted": formatted,
            })
        return json.dumps(results)

    @mcp.tool()
    def extract_images(
        uri: str,
        output_dir: Optional[str] = None,
        dpi: int = 300,
        autocrop: bool = True,
    ) -> str:
        """Extract embedded images from a document file.

        Supports PDF, DOCX, PPTX, HTML, EPUB, and Jupyter (.ipynb) files.

        Args:
            uri: Path to the document file.
            output_dir: Directory to save extracted images.
                        Defaults to a sibling directory next to the file.
            dpi: Resolution for PDF rasterisation (default 300).
            autocrop: Whether to auto-crop whitespace from extracted images.

        Returns:
            JSON array of image ref dicts with keys:
            position, file_path, original_format, width, height,
            caption, reference_label, ordinal.
        """
        from pathlib import Path

        file_path = Path(uri)
        ext = file_path.suffix.lower().lstrip(".")

        if output_dir is None:
            out = file_path.parent / (file_path.stem + "_images")
        else:
            out = Path(output_dir)

        config = SciMarkdownConfig(
            images_dpi=dpi,
            images_autocrop_whitespace=autocrop,
        )
        extractor = ImageExtractor(
            config=config,
            document_name=file_path.name,
            output_dir=out,
        )

        with open(uri, "rb") as stream:
            if ext == "pdf":
                image_refs = extractor.extract_from_pdf(stream)
            elif ext == "docx":
                image_refs = extractor.extract_from_docx(stream)
            elif ext == "pptx":
                image_refs = extractor.extract_from_pptx(stream)
            elif ext in ("html", "htm"):
                image_refs = extractor.extract_from_html(stream)
            elif ext == "epub":
                image_refs = extractor.extract_from_epub(stream)
            elif ext == "ipynb":
                image_refs = extractor.extract_from_jupyter(stream)
            else:
                raise ValueError(f"Unsupported file format: {ext!r}")

        return json.dumps([image_ref_to_dict(r) for r in image_refs])

    @mcp.tool()
    def link_references(
        text: str,
        images: str,
        patterns: Optional[list] = None,
    ) -> str:
        """Link figure references in text to extracted ImageRef objects.

        Args:
            text: Document text to scan for figure references.
            images: JSON array of image ref dicts (as returned by extract_images).
            patterns: Optional list of regex patterns (each with a capture group
                      for the ordinal) to override the default reference patterns.

        Returns:
            JSON array of updated image ref dicts with reference_label and
            ordinal fields populated where matches were found.
        """
        image_list = json.loads(images)
        image_refs = [
            ImageRef(
                position=d["position"],
                file_path=d["file_path"],
                original_format=d["original_format"],
                width=d.get("width", 0),
                height=d.get("height", 0),
                caption=d.get("caption"),
                reference_label=d.get("reference_label"),
                ordinal=d.get("ordinal"),
            )
            for d in image_list
        ]

        config = SciMarkdownConfig()
        if patterns:
            config.references_patterns = patterns

        linker = ReferenceLinker(config=config)
        updated = linker.link(text, image_refs)
        return json.dumps([image_ref_to_dict(r) for r in updated])

    @mcp.tool()
    def build_figure_index(images: str) -> str:
        """Build a Markdown figure-index table from image ref dicts.

        Args:
            images: JSON array of image ref dicts (as returned by extract_images
                    or link_references).

        Returns:
            Markdown string with a ## Figure Index table, or empty string
            if the images list is empty.
        """
        image_list = json.loads(images)
        image_refs = [
            ImageRef(
                position=d["position"],
                file_path=d["file_path"],
                original_format=d["original_format"],
                width=d.get("width", 0),
                height=d.get("height", 0),
                caption=d.get("caption"),
                reference_label=d.get("reference_label"),
                ordinal=d.get("ordinal"),
            )
            for d in image_list
        ]

        builder = IndexBuilder()
        return builder.build(image_refs)

    @mcp.tool()
    def ocr_formula(image_path: str, engine: str = "auto") -> str:
        """Recognize a LaTeX formula from an image using OCR.

        Args:
            image_path: Path to an image file (PNG, JPEG, etc.) containing
                        a rendered math formula.
            engine: OCR engine to use — "auto", "pix2tex", "nougat", or "none".
                    "auto" picks the best available engine.

        Returns:
            JSON object with one of:
            - {"latex": ..., "confidence": ..., "engine_used": ...} on success.
            - {"error": ...} if the engine is unavailable or recognition fails.
        """
        from PIL import Image

        ocr = MathOCR(engine=engine)
        if not ocr.is_available():
            return json.dumps({
                "error": f"OCR engine {engine!r} is not available. "
                         "Install pix2tex or nougat to enable formula OCR."
            })

        img = Image.open(image_path)
        result = ocr.recognize(img)
        if result is None:
            return json.dumps({"error": "OCR recognition failed"})

        return json.dumps({
            "latex": result.latex,
            "confidence": result.confidence,
            "engine_used": ocr._resolved_engine,
        })

    @mcp.tool()
    def convert_to_scimarkdown_embeddings(
        uri: str,
        config: Optional[dict] = None,
        embedding_options: Optional[dict] = None,
    ) -> str:
        """Convert a file to enriched SciMarkdown with embeddings-based enhancements.

        Enables the full embeddings pipeline (math classification, semantic
        image-text linking) on top of standard SciMarkdown conversion.

        Args:
            uri: File path or URL to convert.
            config: Optional SciMarkdown config overrides (nested dicts).
            embedding_options: Optional embeddings section overrides, e.g.
                               {"classify_math": True, "semantic_linking": True}.

        Returns:
            Enriched Markdown text.
        """
        sci_config = SciMarkdownConfig()
        if config:
            sci_config = sci_config.with_overrides(config)
        # Force-enable embeddings
        sci_config.embeddings_enabled = True
        if embedding_options:
            sci_config = sci_config.with_overrides({"embeddings": embedding_options})

        converter = EnhancedMarkItDown(sci_config=sci_config)
        result = converter.convert(uri)
        return result.markdown or ""

    @mcp.tool()
    def analyze_document(uri: str, analysis_type: Optional[str] = None) -> str:
        """Analyze a document for math regions and document type.

        Converts the document, detects math regions, and optionally classifies
        the document type using embeddings.

        Args:
            uri: File path or URL to analyze.
            analysis_type: Optional analysis type — "full" (includes document
                           classification via embeddings) or None for basic.

        Returns:
            JSON object with keys:
            - "document": {"uri": ..., "type": ...}
            - "math_regions": list of math region dicts
            - "document_category": (str, if analysis_type="full" and client available)
            - "category_confidence": (float, if analysis_type="full" and client available)
        """
        from pathlib import Path as _Path

        file_path = _Path(uri)
        detector = MathDetector()

        # Convert to markdown first
        converter = MarkItDown()
        result = converter.convert(uri)
        markdown = result.markdown or ""

        math_regions = detector.detect(markdown)

        output: dict = {
            "document": {
                "uri": uri,
                "name": file_path.name,
                "extension": file_path.suffix,
            },
            "math_regions": [math_region_to_dict(r) for r in math_regions],
        }

        if analysis_type == "full":
            client = _get_embedding_client()
            if client is not None:
                try:
                    from scimarkdown.embeddings.document_classifier import DocumentClassifier
                    clf = DocumentClassifier(client=client)
                    category, confidence = clf.classify(markdown)
                    output["document_category"] = category
                    output["category_confidence"] = confidence
                except Exception:
                    pass

        return json.dumps(output)

    @mcp.tool()
    def search_content(uri: str, query: str, top_k: int = 5) -> str:
        """Semantically search a document for the most relevant sections.

        Converts the document, builds a semantic index using embeddings, and
        returns the top-k most relevant chunks for the query.

        Args:
            uri: File path or URL to search.
            query: Natural language search query.
            top_k: Number of results to return (default 5).

        Returns:
            JSON array of result dicts with keys: text, type, similarity.
            Returns an empty array if embeddings are unavailable.
        """
        client = _get_embedding_client()
        if client is None:
            return json.dumps([])

        try:
            converter = MarkItDown()
            result = converter.convert(uri)
            markdown = result.markdown or ""

            from scimarkdown.embeddings.content_indexer import ContentIndexer
            indexer = ContentIndexer(client=client)
            idx = indexer.index(markdown)
            results = indexer.search(idx, query, top_k=top_k)
            return json.dumps(results)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    @mcp.tool()
    def compare_sections(uris_json: str, granularity: Optional[str] = None) -> str:
        """Compare sections across multiple documents using semantic similarity.

        Converts each document, builds a content index, and returns a comparison
        report showing common topics and similarity scores between documents.

        Args:
            uris_json: JSON array of file paths or URLs to compare.
            granularity: Comparison granularity — "heading" to compare only
                         headings, or None for all chunk types.

        Returns:
            JSON object with:
            - "documents": list of {"uri": ..., "chunk_count": ...}
            - "topics": list of {"text": ..., "type": ..., "similarity": ...,
                                 "found_in": [uri, ...]}
        """
        uris: list[str] = json.loads(uris_json)
        client = _get_embedding_client()

        doc_infos: list[dict] = []
        all_chunks: list[dict] = []  # enriched with source uri

        for uri in uris:
            try:
                converter = MarkItDown()
                result = converter.convert(uri)
                markdown = result.markdown or ""

                if client is not None:
                    from scimarkdown.embeddings.content_indexer import ContentIndexer
                    indexer = ContentIndexer(client=client)
                    idx = indexer.index(markdown)
                    chunks = idx.chunks
                    embeddings = idx.embeddings
                else:
                    chunks = []
                    embeddings = []

                if granularity == "heading":
                    filtered = [
                        (c, e) for c, e in zip(chunks, embeddings)
                        if c.get("type") == "heading"
                    ]
                    chunks = [c for c, _ in filtered]
                    embeddings = [e for _, e in filtered]

                doc_infos.append({"uri": uri, "chunk_count": len(chunks)})
                for chunk, emb in zip(chunks, embeddings):
                    all_chunks.append({**chunk, "uri": uri, "_emb": emb})
            except Exception as exc:
                doc_infos.append({"uri": uri, "error": str(exc)})

        # Find common topics: chunks from different documents with high similarity
        topics: list[dict] = []
        if client is not None and len(all_chunks) > 1:
            seen = set()
            for i, chunk_a in enumerate(all_chunks):
                if i in seen:
                    continue
                best_sim = -1.0
                best_j = -1
                for j, chunk_b in enumerate(all_chunks):
                    if i == j or chunk_a["uri"] == chunk_b["uri"]:
                        continue
                    sim = client.similarity(chunk_a["_emb"], chunk_b["_emb"])
                    if sim > best_sim:
                        best_sim = sim
                        best_j = j
                if best_j >= 0 and best_sim > 0.5:
                    seen.add(best_j)
                    topics.append({
                        "text": chunk_a["text"],
                        "type": chunk_a["type"],
                        "similarity": best_sim,
                        "found_in": [chunk_a["uri"], all_chunks[best_j]["uri"]],
                    })

        return json.dumps({
            "documents": doc_infos,
            "topics": topics,
        })

    return mcp
