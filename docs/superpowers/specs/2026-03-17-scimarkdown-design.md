# SciMarkdown - Design Specification

**Date:** 2026-03-17
**Status:** Approved
**Base project:** Microsoft MarkItDown (fork)

---

## 1. Overview

SciMarkdown is a fork of Microsoft MarkItDown that extends its document-to-markdown conversion with two key capabilities:

1. **Mathematical formula detection and LaTeX embedding** across all supported formats (PDF, DOCX, PPTX, HTML, EPUB, images, Jupyter, XLSX)
2. **Image extraction, cropping, and referencing** with positional awareness, text reference linking, and a figure index

### Goals

- Maintain quality and reliability as top priority
- Minimize fork surface (~50 lines modified in upstream code) to ease upstream synchronization
- Keep all enhancement logic in a separate `scimarkdown` package
- Provide a clear upgrade path if Microsoft adds middleware/hooks

---

## 2. Architecture

### Pipeline (3 phases)

```
Document
    |
    v
+-------------------------+
|  Phase 1: Extraction    |  (Existing MarkItDown converters + extensions)
|  - Raw text             |
|  - Embedded images      |
|  - Graphic regions      |
|  - Positional metadata  |
+-----------+-------------+
            v
+-----------------------------+
|  Phase 2: Enrichment        |
|  +---------------------+    |
|  | MathDetector        |    |  Detects formulas in text (regex, MathML, Unicode)
|  | MathOCR             |    |  Recognizes formulas in images (pix2tex / Nougat)
|  | ImageExtractor      |    |  Extracts, crops, and saves images
|  | ReferenceLinker     |    |  Links images to their textual references
|  | LLMFallback         |    |  Fallback for ambiguous cases
|  +---------------------+    |
+-----------+-----------------+
            v
+-----------------------------+
|  Phase 3: Composition       |
|  - Markdown with LaTeX      |
|  - Image links              |
|  - Figure index             |
|  - Configurable format      |
+-----------------------------+
```

### Fork strategy

**Modified in upstream code (~50 lines):**

| File | Change |
|---|---|
| `_markitdown.py` | Add hooks for pipeline phases via subclass override |
| `_base_converter.py` | Extend `DocumentConverterResult` with optional `enrichment_data` field |

**NOT modified:**
- No existing converter is touched
- All existing tests must continue to pass

**Enhancement code lives in `scimarkdown/` package:**

`EnhancedMarkItDown` subclasses `MarkItDown`, overrides only `convert()` to inject phases 2 and 3. 95% of code is in the separate package with zero merge conflict risk.

### Intermediate data model

`EnrichedResult` transports data between phases:

- `text_blocks`: list of text blocks with ordinal position
- `images`: list of extracted images with position, saved path, and text reference
- `math_regions`: detected math regions (text or image) with resulting LaTeX
- `metadata`: title, author, etc.

---

## 3. Package structure

```
scimarkdown/
+-- packages/
|   +-- markitdown/              <- Fork of Microsoft (minimal changes ~50 lines)
|   +-- markitdown-mcp/          <- Fork of MCP server (adds 2nd tool)
|   +-- scimarkdown/             <- Our enrichment package
|       +-- __init__.py
|       +-- _enhanced_markitdown.py   <- Subclass of MarkItDown
|       +-- config.py                 <- Configuration (LaTeX format, paths, LLM)
|       +--
|       +-- pipeline/
|       |   +-- enrichment.py         <- Phase 2 orchestrator
|       |   +-- composition.py        <- Phase 3 orchestrator
|       +--
|       +-- math/
|       |   +-- detector.py           <- Heuristic detection in text
|       |   |                            (regex Unicode, MathML, scientific patterns)
|       |   +-- ocr.py               <- Formula recognition in images
|       |   |                            (pix2tex for isolated, Nougat for full pages)
|       |   +-- formatter.py          <- Configurable LaTeX formatter
|       |                                ($...$ / $$...$$ vs GitHub-flavored)
|       +--
|       +-- images/
|       |   +-- extractor.py          <- Extracts embedded images (per format)
|       |   +-- cropper.py            <- Rasterizes and crops graphic regions
|       |   +-- reference_linker.py   <- Links "Figure X" in text to image
|       |   +-- index_builder.py      <- Generates figure index
|       +--
|       +-- models/
|       |   +-- enriched_result.py    <- EnrichedResult dataclass
|       |   +-- text_block.py         <- Text block with position
|       |   +-- math_region.py        <- Detected math region
|       |   +-- image_ref.py          <- Image reference with metadata
|       +--
|       +-- llm/
|       |   +-- fallback.py           <- Generic LLM client (OpenAI/Claude)
|       +--
|       +-- sync/
|           +-- upstream.py           <- Upstream sync script
```

---

## 4. Mathematical formula detection by format

### Detection methods per format

| Format | Detection method | Tool | Expected quality |
|---|---|---|---|
| **DOCX** | Native OMML in XML | Existing MarkItDown omml.py | Excellent |
| **PPTX** | OMML in slides XML | Same OMML module adapted | Excellent |
| **HTML** | MathML tags, KaTeX/MathJax class attributes, `<math>` elements | BeautifulSoup + regex | Very good |
| **PDF (text)** | Unicode math patterns (sum, integral, sqrt, leq, in...), layout heuristics (superscripts, fractions) | Regex + pdfplumber character positions | Good |
| **PDF (formula as image)** | Detection of text-free regions with equation layout | pix2tex for isolated formulas | Very good |
| **PDF (full papers)** | Academic document detected by structure | Nougat (processes full page) | Excellent |
| **Scanned images** | OCR + math region detection | pix2tex / Nougat | Good-Very good |
| **EPUB** | Internally HTML - same path as HTML | BeautifulSoup | Very good |
| **Jupyter Notebooks** | Markdown cells already contain LaTeX, output cells may have MathML | Passthrough + parsing | Excellent |
| **XLSX** | Cell formulas as text, rare equations | Basic regex | Acceptable |
| **LLM fallback** | Any ambiguous or unrecognized case | OpenAI/Claude with specialized prompt | Very good |

### Decision flow for a content block

```
Is native OMML?       --yes--> omml.py (existing)
    | no
Is MathML/KaTeX?      --yes--> MathML parser -> LaTeX
    | no
Contains Unicode math? --yes--> Regex + mapping -> LaTeX
    | no
Is formula image?      --yes--> pix2tex -> LaTeX
    | no
Is paper page?         --yes--> Nougat -> LaTeX
    | no
LLM available?         --yes--> LLM fallback -> LaTeX
    | no
    v
Leave as plain text
```

---

## 5. Image extraction, cropping, and referencing

### Extraction by format

| Format | Method | Library |
|---|---|---|
| **PDF** | Embedded images + rasterization of vector regions | PyMuPDF (fitz) |
| **DOCX** | Image relationships in XML (`word/media/`) | python-docx + zipfile |
| **PPTX** | Images in slides (`ppt/media/`) | python-pptx |
| **HTML/EPUB** | `<img>`, `<figure>` tags, CSS `background-image` | BeautifulSoup + requests |
| **Jupyter** | Cell outputs with `image/png`, `image/svg` | Decode base64 from JSON |
| **Images** | The file itself is the image | Pillow |

### Naming convention

```
{document_name}_img{NNNNN}.{ext}

Example: paper_relativity_img00001.png
         paper_relativity_img00002.jpg
         paper_relativity_img00003.png
```

- 5-digit counter (supports up to 99999 images per document)
- Original extension preserved when possible (png, jpg); SVG and vectors rasterized to PNG
- Rasterization resolution configurable (default 300 DPI)

### Smart cropping

**For directly embedded images:**
- Extracted as-is from the document

**For graphic regions (vector figures, composite charts in PDF):**
1. PyMuPDF detects the bounding box of the graphic region
2. Region rasterized with configurable margin (default 10px)
3. Auto-crop white borders with Pillow
4. Saved as PNG

### Text reference linking

`ReferenceLinker` searches for patterns in text:
- `Figura X`, `Figure X`, `Fig. X`, `Fig X`
- `Tabla X`, `Table X`, `Tab. X`
- `Grafico X`, `Graph X`, `Chart X`
- `Imagen X`, `Image X`, `Img. X`
- Configurable patterns via regex for other languages

When a reference is found, it links to the positionally closest image with the same ordinal number.

### Markdown output

Inline where the image appears:
```markdown
![Figura 1: Diagrama de flujo del sistema](paper_relativity_img00001.png)
```

Figure index at the end of the document:
```markdown
## Figure Index

| # | Figure | Description | File |
|---|--------|-------------|------|
| 1 | Figura 1 | Diagrama de flujo del sistema | [img00001](paper_relativity_img00001.png) |
| 2 | Figura 2 | Resultados experimentales | [img00002](paper_relativity_img00002.png) |
```

---

## 6. Configuration

### Configuration file `scimarkdown.yaml`

```yaml
# LaTeX format
latex:
  style: "standard"          # "standard" ($...$, $$...$$) or "github" ($`...`$, ```math)

# Images
images:
  output_dir: "same"          # "same" = next to original document
  format: "png"               # output format for rasterized images
  dpi: 300                    # resolution for vector rasterization
  margin_px: 10               # margin when cropping regions
  counter_digits: 5           # counter digits (img00001)
  autocrop_whitespace: true   # auto-crop white borders

# Formula detection
math:
  heuristic: true             # regex/Unicode detection
  ocr_engine: "pix2tex"       # "pix2tex", "nougat", or "auto" (chooses by context)
  nougat_model: "0.1.0-base"  # Nougat model
  confidence_threshold: 0.75  # minimum threshold to accept OCR without LLM

# LLM Fallback
llm:
  enabled: false              # enable LLM fallback
  provider: "openai"          # "openai" or "anthropic"
  model: "gpt-4o"             # model to use
  api_key_env: "LLM_API_KEY"  # environment variable with API key

# References
references:
  patterns:                   # reference patterns (regex)
    - 'Fig(?:ura|ure|\.)\s*(\d+)'
    - 'Tab(?:la|le|\.)\s*(\d+)'
    - 'Gr[aA]f(?:ico|h)\s*(\d+)'
    - 'Im(?:agen|age|g\.?)\s*(\d+)'
    - 'Chart\s*(\d+)'
  languages: ["es", "en"]    # detection languages
  generate_index: true        # generate figure index at end

# Upstream sync
sync:
  remote: "https://github.com/microsoft/markitdown.git"
  branch: "main"
  check_interval_days: 14     # every 2 weeks
```

### MCP Server (2 tools)

```
convert_to_markdown(uri: str, config: Optional[dict]) -> str
  -> Full enriched conversion (formulas + images)

convert_to_markdown_simple(uri: str) -> str
  -> Original MarkItDown conversion (compatibility)
```

---

## 7. Upstream synchronization and evolution

### Sync process (every 14 days, configurable)

**Automated script `sync/upstream.py`:**

1. `git fetch upstream` (microsoft/markitdown)
2. Compare commits - any new changes?
   - No -> log "up to date", end
   - Yes -> continue
3. Generate changelog of upstream changes (new converters, fixes, breaking changes)
4. `git merge upstream/main --no-commit`
   - No conflicts -> auto-merge OK
   - Conflicts -> mark conflicting files, notify
5. Run tests
   - Microsoft tests pass + SciMarkdown tests pass -> commit merge
   - Tests fail -> revert merge, create issue with details
6. Generate sync report `sync_report_YYYY-MM-DD`

### CI/CD for synchronization

```yaml
# GitHub Action: .github/workflows/upstream-sync.yml
# Runs every 14 days or manually
# 1. Executes sync/upstream.py
# 2. If changes without conflicts and tests pass -> creates automatic PR
# 3. If conflicts -> creates issue with details
# 4. Notifies team
```

### Evolution roadmap

| Phase | Scope | Trigger |
|---|---|---|
| **Watch** | Review upstream changelog every 14 days | Automatic (script/CI) |
| **Adopt** | Integrate new Microsoft converters | New converter detected |
| **Enhance** | Add enrichment to new converter | Manual after adoption |
| **Deprecate** | If Microsoft adds native hooks/middleware, migrate to plugin | Breaking change upstream |

### Versioning

```
SciMarkdown v{MAJOR}.{MINOR}.{PATCH}+mit{UPSTREAM_VERSION}

Example: scimarkdown 1.2.0+mit0.1.1
```

This always shows which MarkItDown version SciMarkdown is built on.

---

## 8. Dependencies

### Required dependencies

| Package | Use |
|---|---|
| `markitdown[all]` | Base (local fork) |
| `Pillow>=9.0.0` | Cropping, autocrop, rasterization |
| `PyMuPDF>=1.24.0` | PDF image extraction, region rasterization |
| `python-docx` | Access to DOCX embedded images |
| `pix2tex>=0.1.1` | Isolated formula OCR |
| `PyYAML` | Read `scimarkdown.yaml` |

### Optional dependencies

| Package | Use | Install group |
|---|---|---|
| `nougat-ocr` | Full academic paper OCR (~3GB model) | `[nougat]` |
| `openai>=1.0.0` | LLM fallback (OpenAI) | `[llm]` |
| `anthropic` | LLM fallback (Claude) | `[llm]` |
| `torch` | Required by Nougat and pix2tex | Implicit with OCR |

### Installation groups

```bash
# Minimum: heuristics + pix2tex (lightweight)
pip install scimarkdown

# With Nougat for academic papers (~3GB additional)
pip install scimarkdown[nougat]

# With LLM fallback
pip install scimarkdown[llm]

# Everything
pip install scimarkdown[all]
```

### System requirements

- Python >= 3.10
- `exiftool` (optional, for image EXIF metadata)
- GPU recommended for Nougat (works on CPU but slow)
- ~500MB disk for pix2tex, ~3GB for Nougat

---

## 9. Testing

### Test structure

```
tests/
+-- unit/
|   +-- math/
|   |   +-- test_detector.py         <- Regex patterns, Unicode, MathML
|   |   +-- test_ocr.py              <- Mock pix2tex/Nougat, verify LaTeX output
|   |   +-- test_formatter.py        <- Standard vs GitHub-flavored
|   +-- images/
|   |   +-- test_extractor.py        <- Extraction per format
|   |   +-- test_cropper.py          <- Cropping, autocrop, margins
|   |   +-- test_reference_linker.py <- Fig/Table -> image linking
|   |   +-- test_index_builder.py    <- Figure index generation
|   +-- pipeline/
|       +-- test_enrichment.py       <- Phase 2 orchestration
|       +-- test_composition.py      <- Phase 3 assembly
|
+-- integration/
|   +-- test_pdf_full.py             <- PDF with formulas + images -> markdown
|   +-- test_docx_full.py            <- Full DOCX
|   +-- test_pptx_full.py            <- Full PPTX
|   +-- test_html_full.py            <- HTML with MathML/KaTeX
|   +-- test_epub_full.py            <- Full EPUB
|   +-- test_mcp_tools.py            <- Both MCP server tools
|
+-- fixtures/                        <- Test documents
|   +-- pdf_with_formulas.pdf
|   +-- pdf_scanned_paper.pdf
|   +-- docx_mixed_content.docx
|   +-- pptx_with_equations.pptx
|   +-- html_mathjax.html
|   +-- html_mathml.html
|   +-- expected/                    <- Expected markdown (golden files)
|       +-- pdf_with_formulas.md
|       +-- ...
|
+-- upstream/
|   +-- test_microsoft_suite.py      <- Re-run original MarkItDown tests
|                                       to verify no regression
|
+-- conftest.py                      <- Shared fixtures, skip if no GPU/model
```

### Quality thresholds

| Metric | Minimum threshold |
|---|---|
| Correct LaTeX formulas (vs golden file) | >= 95% |
| Images extracted (vs total in document) | >= 95% |
| References correctly linked | >= 95% |
| Upstream Microsoft tests | 100% pass |
| SciMarkdown code coverage | >= 85% |

### CI pipeline

```
Push/PR -> lint + format -> unit tests -> integration tests (no GPU)
                                           -> GPU integration tests (main only)
                                           -> upstream sync check (scheduled only)
```

---

## 10. MCP Server changes

The forked MCP server (`markitdown-mcp`) is extended to expose 2 tools:

### Tool 1: `convert_to_markdown` (enhanced)

```python
@mcp.tool()
async def convert_to_markdown(uri: str, config: Optional[dict] = None) -> str:
    """Convert a document to markdown with LaTeX formulas and image extraction."""
    # Uses EnhancedMarkItDown with full pipeline
    # config overrides scimarkdown.yaml values
```

### Tool 2: `convert_to_markdown_simple` (compatibility)

```python
@mcp.tool()
async def convert_to_markdown_simple(uri: str) -> str:
    """Convert a document to markdown (original MarkItDown behavior)."""
    # Uses base MarkItDown, no enrichment
```

Both tools support the same URI schemes: `http://`, `https://`, `file:`, `data:`.
