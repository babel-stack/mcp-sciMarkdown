# SciMarkdown

<p align="center">
  <strong>Conversor de documentos a Markdown con detección de fórmulas LaTeX, extracción inteligente de imágenes, filtrado de ruido e análise semántica con Gemini Embeddings.</strong>
</p>

<p align="center">
  <a href="#-galego"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Flag_of_Galicia.svg/20px-Flag_of_Galicia.svg.png" width="16" alt="Galicia"> Galego</a> · <a href="#-español">🇪🇸 Español</a> · <a href="#-english">🇬🇧 English</a> · <a href="#-bosanski">🇧🇦 Bosanski</a>
</p>

---

<details open>
<summary><h2><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Flag_of_Galicia.svg/20px-Flag_of_Galicia.svg.png" width="16" alt="Galicia"> Galego</h2></summary>

SciMarkdown é un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown) que amplía as súas capacidades de conversión con catro piares:

1. **Detección de fórmulas matemáticas e embebido LaTeX** en todos os formatos soportados
2. **Extracción, recorte e referenciado de imaxes** con vinculación de referencias textuais e índice de figuras
3. **Filtrado de ruído** — elimina cabeceiras, pés de páxina, números de páxina e imaxes decorativas; converte índices en hiperenlaces
4. **Análise semántica con Gemini Embeddings** (opcional) — clasificación de fórmulas, vinculación imaxe-texto por significado, clasificación de documentos e busca semántica (RAG)

### Características

#### Detección de fórmulas matemáticas

SciMarkdown detecta e converte fórmulas matemáticas a LaTeX de forma automática usando múltiples estratexias por capas:

| Capa | Método | Formatos | Online | Calidade |
|------|--------|----------|--------|----------|
| 1 | **OMML nativo** | DOCX, PPTX | Non | Excelente |
| 1 | **MathML** | HTML, EPUB | Non | Moi boa |
| 1 | **MathJax/KaTeX** | HTML | Non | Moi boa |
| 1 | **Símbolos Unicode** | Todos (∑, ∫, ≤, ∈, ℝ...) | Non | Boa |
| 1 | **OCR de fórmulas** | PDF escaneados, imaxes | Non | Moi boa |
| 2 | **Gemini Embeddings** | Todos (confirma/descarta) | Si | Excelente |
| 3 | **LLM fallback** | Calquera formato | Si | Moi boa |

**Exemplo de entrada:**
```
Para todo x ∈ ℝ, a suma ∑ᵢ xᵢ ≤ ∫ f(x)dx cúmprese.
```

**Saída (estilo estándar):**
```markdown
Para todo $x \in \mathbb{R}$, a suma $\sum_{i} x_{i} \leq \int f(x)dx$ cúmprese.
```

#### Extracción intelixente de imaxes

- Extrae imaxes embebidas de PDF, DOCX, PPTX, HTML, EPUB e Jupyter Notebooks
- Recorte automático de bordos brancos con marxes configurables
- As imaxes insértanse **na posición orixinal** do documento, ancoradas ao texto que as precede
- **Convención de nomes:** `{documento}_img{00001}.png` (5 díxitos)

#### Filtrado de ruído

- **Texto repetido** — detecta cabeceiras/pés que se repiten na mesma posición en 3+ páxinas
- **Números de páxina** — detecta secuencias numéricas en bloques fronteira
- **Imaxes decorativas** — filtra imaxes pequenas (<30px), moi estreitas (ratio >8:1) ou repetidas
- **Índices (TOC)** — detecta táboas de contidos e convérteas en hiperenlaces markdown:

**Antes:**
```
Capítulo 1: Introdución ......... 15
Capítulo 2: Métodos ......... 30
```
**Despois:**
```markdown
- [Capítulo 1: Introdución](#capítulo-1-introdución)
- [Capítulo 2: Métodos](#capítulo-2-métodos)
```

#### Servidor MCP con 12 ferramentas

| # | Ferramenta | Nivel | Online |
|---|------------|-------|--------|
| 1 | `convert_to_markdown` | Pipeline | Non |
| 2 | `convert_to_scimarkdown` | Pipeline | Non |
| 3 | `convert_to_scimarkdown_embeddings` | Pipeline | Si |
| 4 | `detect_math` | Granular | Non |
| 5 | `format_latex` | Granular | Non |
| 6 | `extract_images` | Granular | Non |
| 7 | `link_references` | Granular | Non |
| 8 | `build_figure_index` | Granular | Non |
| 9 | `ocr_formula` | Granular | Non |
| 10 | `analyze_document` | Embeddings | Si |
| 11 | `search_content` | Embeddings | Si |
| 12 | `compare_sections` | Embeddings | Si |

</details>

---

<details>
<summary><h2>🇪🇸 Español</h2></summary>

SciMarkdown es un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown) que amplía sus capacidades de conversión con cuatro pilares:

1. **Detección de fórmulas matemáticas y embebido LaTeX** en todos los formatos soportados
2. **Extracción, recorte y referenciado de imágenes** con vinculación de referencias textuales e índice de figuras
3. **Filtrado de ruido** — elimina cabeceras, pies de página, números de página e imágenes decorativas; convierte índices en hiperenlaces
4. **Análisis semántico con Gemini Embeddings** (opcional) — clasificación de fórmulas, vinculación imagen-texto por significado, clasificación de documentos y búsqueda semántica (RAG)

### Características

#### Detección de fórmulas matemáticas

| Capa | Método | Formatos | Online | Calidad |
|------|--------|----------|--------|---------|
| 1 | **OMML nativo** | DOCX, PPTX | No | Excelente |
| 1 | **MathML** | HTML, EPUB | No | Muy buena |
| 1 | **MathJax/KaTeX** | HTML | No | Muy buena |
| 1 | **Símbolos Unicode** | Todos (∑, ∫, ≤, ∈, ℝ...) | No | Buena |
| 1 | **OCR de fórmulas** | PDF escaneados, imágenes | No | Muy buena |
| 2 | **Gemini Embeddings** | Todos (confirma/descarta) | Sí | Excelente |
| 3 | **LLM fallback** | Cualquier formato | Sí | Muy buena |

**Ejemplo de entrada:**
```
Para todo x ∈ ℝ, la suma ∑ᵢ xᵢ ≤ ∫ f(x)dx se cumple.
```

**Salida (estilo estándar):**
```markdown
Para todo $x \in \mathbb{R}$, la suma $\sum_{i} x_{i} \leq \int f(x)dx$ se cumple.
```

**Salida (estilo GitHub):**
```markdown
Para todo $`x \in \mathbb{R}`$, la suma $`\sum_{i} x_{i} \leq \int f(x)dx`$ se cumple.
```

#### Extracción inteligente de imágenes

- Extrae imágenes embebidas de PDF, DOCX, PPTX, HTML, EPUB y Jupyter Notebooks
- Recorte automático de bordes blancos con márgenes configurables
- Las imágenes se insertan **en la posición original** del documento, ancladas al texto que las precede
- **Convención de nombres:** `{documento}_img{00001}.png` (5 dígitos)

#### Filtrado de ruido

- **Texto repetido** — detecta cabeceras/pies que se repiten en la misma posición en 3+ páginas
- **Números de página** — detecta secuencias numéricas en bloques frontera
- **Imágenes decorativas** — filtra imágenes pequeñas (<30px), muy estrechas (ratio >8:1) o repetidas
- **Índices (TOC)** — detecta tablas de contenidos y las convierte en hiperenlaces markdown

#### Servidor MCP con 12 herramientas

| # | Herramienta | Nivel | Online |
|---|-------------|-------|--------|
| 1 | `convert_to_markdown` | Pipeline | No |
| 2 | `convert_to_scimarkdown` | Pipeline | No |
| 3 | `convert_to_scimarkdown_embeddings` | Pipeline | Sí |
| 4 | `detect_math` | Granular | No |
| 5 | `format_latex` | Granular | No |
| 6 | `extract_images` | Granular | No |
| 7 | `link_references` | Granular | No |
| 8 | `build_figure_index` | Granular | No |
| 9 | `ocr_formula` | Granular | No |
| 10 | `analyze_document` | Embeddings | Sí |
| 11 | `search_content` | Embeddings | Sí |
| 12 | `compare_sections` | Embeddings | Sí |

</details>

---

<details>
<summary><h2>🇬🇧 English</h2></summary>

SciMarkdown is a fork of [Microsoft MarkItDown](https://github.com/microsoft/markitdown) that extends its conversion capabilities with four pillars:

1. **Mathematical formula detection and LaTeX embedding** across all supported formats
2. **Image extraction, cropping, and referencing** with text reference linking and figure index
3. **Noise filtering** — removes headers, footers, page numbers, and decorative images; converts tables of contents into hyperlinks
4. **Semantic analysis with Gemini Embeddings** (optional) — formula classification, image-text linking by meaning, document classification, and semantic search (RAG)

### Features

#### Mathematical formula detection

| Layer | Method | Formats | Online | Quality |
|-------|--------|---------|--------|---------|
| 1 | **Native OMML** | DOCX, PPTX | No | Excellent |
| 1 | **MathML** | HTML, EPUB | No | Very good |
| 1 | **MathJax/KaTeX** | HTML | No | Very good |
| 1 | **Unicode symbols** | All (∑, ∫, ≤, ∈, ℝ...) | No | Good |
| 1 | **Formula OCR** | Scanned PDFs, images | No | Very good |
| 2 | **Gemini Embeddings** | All (confirm/discard) | Yes | Excellent |
| 3 | **LLM fallback** | Any format | Yes | Very good |

**Input example:**
```
For all x ∈ ℝ, the sum ∑ᵢ xᵢ ≤ ∫ f(x)dx holds.
```

**Output (standard style):**
```markdown
For all $x \in \mathbb{R}$, the sum $\sum_{i} x_{i} \leq \int f(x)dx$ holds.
```

#### Smart image extraction

- Extracts embedded images from PDF, DOCX, PPTX, HTML, EPUB, and Jupyter Notebooks
- Automatic white border cropping with configurable margins
- Images are inserted **at their original position** in the document, anchored to preceding text
- **Naming convention:** `{document}_img{00001}.png` (5 digits)

#### Noise filtering

- **Repeated text** — detects headers/footers repeated at the same position across 3+ pages
- **Page numbers** — detects sequential numbers in boundary blocks
- **Decorative images** — filters images smaller than 30px, extreme aspect ratio (>8:1), or repeated
- **Table of Contents** — detects TOC and converts entries to markdown hyperlinks

#### MCP Server with 12 tools

| # | Tool | Level | Online |
|---|------|-------|--------|
| 1 | `convert_to_markdown` | Pipeline | No |
| 2 | `convert_to_scimarkdown` | Pipeline | No |
| 3 | `convert_to_scimarkdown_embeddings` | Pipeline | Yes |
| 4 | `detect_math` | Granular | No |
| 5 | `format_latex` | Granular | No |
| 6 | `extract_images` | Granular | No |
| 7 | `link_references` | Granular | No |
| 8 | `build_figure_index` | Granular | No |
| 9 | `ocr_formula` | Granular | No |
| 10 | `analyze_document` | Embeddings | Yes |
| 11 | `search_content` | Embeddings | Yes |
| 12 | `compare_sections` | Embeddings | Yes |

</details>

---

<details>
<summary><h2>🇧🇦 Bosanski</h2></summary>

SciMarkdown je fork [Microsoft MarkItDown](https://github.com/microsoft/markitdown) koji proširuje mogućnosti konverzije sa četiri stuba:

1. **Detekcija matematičkih formula i LaTeX ugradnja** u svim podržanim formatima
2. **Ekstrakcija, obrezivanje i referenciranje slika** sa povezivanjem tekstualnih referenci i indeksom slika
3. **Filtriranje šuma** — uklanja zaglavlja, podnožja, brojeve stranica i dekorativne slike; pretvara sadržaje u hiperveze
4. **Semantička analiza sa Gemini Embeddings** (opcionalno) — klasifikacija formula, povezivanje slika i teksta po značenju, klasifikacija dokumenata i semantičko pretraživanje (RAG)

### Karakteristike

#### Detekcija matematičkih formula

| Sloj | Metod | Formati | Online | Kvalitet |
|------|-------|---------|--------|----------|
| 1 | **Nativni OMML** | DOCX, PPTX | Ne | Odličan |
| 1 | **MathML** | HTML, EPUB | Ne | Vrlo dobar |
| 1 | **MathJax/KaTeX** | HTML | Ne | Vrlo dobar |
| 1 | **Unicode simboli** | Svi (∑, ∫, ≤, ∈, ℝ...) | Ne | Dobar |
| 1 | **OCR formula** | Skenirani PDF, slike | Ne | Vrlo dobar |
| 2 | **Gemini Embeddings** | Svi (potvrđuje/odbacuje) | Da | Odličan |
| 3 | **LLM fallback** | Bilo koji format | Da | Vrlo dobar |

**Primjer ulaza:**
```
Za sve x ∈ ℝ, zbir ∑ᵢ xᵢ ≤ ∫ f(x)dx važi.
```

**Izlaz (standardni stil):**
```markdown
Za sve $x \in \mathbb{R}$, zbir $\sum_{i} x_{i} \leq \int f(x)dx$ važi.
```

#### Pametna ekstrakcija slika

- Ekstrahuje ugrađene slike iz PDF, DOCX, PPTX, HTML, EPUB i Jupyter Notebooks
- Automatsko obrezivanje bijelih rubova sa podesivim marginama
- Slike se ubacuju **na originalnu poziciju** u dokumentu, usidrene na prethodni tekst
- **Konvencija imenovanja:** `{dokument}_img{00001}.png` (5 cifara)

#### Filtriranje šuma

- **Ponovljeni tekst** — detektuje zaglavlja/podnožja koja se ponavljaju na istoj poziciji na 3+ stranica
- **Brojevi stranica** — detektuje sekvencijalne brojeve u graničnim blokovima
- **Dekorativne slike** — filtrira slike manje od 30px, ekstremnog omjera (>8:1) ili ponovljene
- **Sadržaj (TOC)** — detektuje tabele sadržaja i pretvara ih u markdown hiperveze:

**Prije:**
```
Poglavlje 1: Uvod ......... 15
Poglavlje 2: Metode ......... 30
```
**Poslije:**
```markdown
- [Poglavlje 1: Uvod](#poglavlje-1-uvod)
- [Poglavlje 2: Metode](#poglavlje-2-metode)
```

#### MCP Server sa 12 alata

| # | Alat | Nivo | Online |
|---|------|------|--------|
| 1 | `convert_to_markdown` | Pipeline | Ne |
| 2 | `convert_to_scimarkdown` | Pipeline | Ne |
| 3 | `convert_to_scimarkdown_embeddings` | Pipeline | Da |
| 4 | `detect_math` | Granularni | Ne |
| 5 | `format_latex` | Granularni | Ne |
| 6 | `extract_images` | Granularni | Ne |
| 7 | `link_references` | Granularni | Ne |
| 8 | `build_figure_index` | Granularni | Ne |
| 9 | `ocr_formula` | Granularni | Ne |
| 10 | `analyze_document` | Embeddings | Da |
| 11 | `search_content` | Embeddings | Da |
| 12 | `compare_sections` | Embeddings | Da |

</details>

---

## Installation

### Prerequisites

- Python >= 3.10
- Git

### Step 1: Clone

```bash
git clone https://github.com/babel-stack/mcp-sciMarkdown.git
cd mcp-sciMarkdown
```

### Step 2: Virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install base dependencies

```bash
# Install MarkItDown (local fork)
pip install -e packages/markitdown[all]

# Install SciMarkdown (heuristics, no GPU, no PyTorch)
pip install -e packages/scimarkdown
```

### Optional dependencies

```bash
# Formula OCR with pix2tex (~500MB + PyTorch)
pip install -e "packages/scimarkdown[ocr]"

# Full paper OCR with Nougat (~3GB + PyTorch)
pip install -e "packages/scimarkdown[nougat]"

# LLM fallback (OpenAI/Anthropic)
pip install -e "packages/scimarkdown[llm]"

# Gemini Embeddings (semantic analysis)
pip install -e "packages/scimarkdown[embeddings]"

# Everything
pip install -e "packages/scimarkdown[all]"
```

### Step 4: Install MCP SDK (for MCP server)

```bash
pip install "mcp[cli]>=1.0.0"
```

### Environment variables

| Variable | Required for | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Embeddings tools | `export GEMINI_API_KEY=AIza...` |
| `LLM_API_KEY` | LLM fallback | `export LLM_API_KEY=sk-...` |

### NixOS

```bash
# Find libstdc++
find /nix/store -name "libstdc++.so.6" 2>/dev/null | head -1

# Export (add to .bashrc/.zshrc)
export LD_LIBRARY_PATH=/nix/store/<hash>-gcc-<version>-lib/lib

# If numpy 2.x fails with "X86_V2" on older CPUs:
pip install "numpy<2.0"
```

A NixOS-compatible launcher script is included: `run-scimarkdown-mcp.sh`

---

## Usage

### CLI

```bash
# Basic conversion (stdout)
scimarkdown document.pdf

# Output to file
scimarkdown document.pdf -o document.md

# GitHub-flavored LaTeX
scimarkdown paper.pdf --latex-style github

# Custom image output directory
scimarkdown paper.pdf --output-dir ./images/

# Custom config file
scimarkdown paper.pdf -c my_config.yaml
```

### Python API

```python
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig

# Default configuration
converter = EnhancedMarkItDown()
result = converter.convert("document.pdf")
print(result.markdown)

# Custom configuration
config = SciMarkdownConfig(
    latex_style="github",
    images_dpi=150,
    references_generate_index=True,
    filters_enabled=True,
)
converter = EnhancedMarkItDown(sci_config=config)
result = converter.convert("paper.docx")
```

#### Direct subcomponent usage

```python
# Detect formulas in text
from scimarkdown.math.detector import MathDetector
detector = MathDetector()
regions = detector.detect("The equation x² + y² = z² is famous.")
for r in regions:
    print(f"{r.original_text} → ${r.latex}$ (confidence: {r.confidence})")

# Extract images from a PDF
from scimarkdown.images.extractor import ImageExtractor
from scimarkdown.config import SciMarkdownConfig
from pathlib import Path

extractor = ImageExtractor(
    config=SciMarkdownConfig(),
    document_name="paper",
    output_dir=Path("./images"),
)
with open("paper.pdf", "rb") as f:
    images = extractor.extract_from_pdf(f)
    for img in images:
        print(f"Extracted: {img.file_path} ({img.width}x{img.height})")

# Link references
from scimarkdown.images.reference_linker import ReferenceLinker
linker = ReferenceLinker(SciMarkdownConfig())
linked = linker.link("As shown in Figure 1...", images)
```

#### Gemini Embeddings usage

```python
from scimarkdown.embeddings.client import GeminiEmbeddingClient
from scimarkdown.embeddings.math_classifier import MathClassifier
from scimarkdown.embeddings.semantic_linker import SemanticLinker
from scimarkdown.embeddings.content_indexer import ContentIndexer

# Create client
client = GeminiEmbeddingClient(api_key="your-api-key")

# Classify formula candidates
classifier = MathClassifier(client, threshold=0.75)
confirmed = classifier.classify(detected_regions)

# Semantic image-text linking (no "Figure X" needed)
linker = SemanticLinker(client, threshold=0.60)
linked = linker.link(images, paragraphs)

# Semantic search (RAG)
indexer = ContentIndexer(client)
index = indexer.index(markdown_text)
results = indexer.search(index, "Schrödinger equation", top_k=5)
```

### MCP Server

#### STDIO mode (Claude Desktop, Claude Code, Cursor...)

```bash
scimarkdown-mcp
```

#### HTTP mode (web integration)

```bash
scimarkdown-mcp --http --port 3001
```

#### Claude Desktop configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scimarkdown": {
      "command": "scimarkdown-mcp",
      "args": [],
      "env": {
        "GEMINI_API_KEY": "your-api-key"
      }
    }
  }
}
```

NixOS — use the included launcher:

```json
{
  "mcpServers": {
    "scimarkdown": {
      "command": "/path/to/mcp-sciMarkdown/run-scimarkdown-mcp.sh",
      "env": {
        "GEMINI_API_KEY": "your-api-key"
      }
    }
  }
}
```

#### Claude Code configuration

```bash
# User-level (available in all projects)
claude mcp add --scope user scimarkdown /path/to/mcp-sciMarkdown/run-scimarkdown-mcp.sh

# Project-level
claude mcp add scimarkdown scimarkdown-mcp
```

---

## MCP Tools — Complete Reference

### Pipeline tools (end-to-end conversion)

#### `convert_to_markdown`

Basic conversion via MarkItDown. No enrichment.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | string | Yes | File path or URL |

Returns: `string` — Plain markdown

---

#### `convert_to_scimarkdown`

Enriched conversion with LaTeX, images, noise filtering, and TOC hyperlinks. Fully offline.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | string | Yes | File path or URL |
| `config` | dict | No | Override `scimarkdown.yaml` |

Returns: `string` — Enriched markdown

Config example:
```json
{"latex": {"style": "github"}, "images": {"dpi": 150}, "filters": {"enabled": true}}
```

---

#### `convert_to_scimarkdown_embeddings`

Maximum quality conversion with Gemini Embeddings. Requires `GEMINI_API_KEY`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | string | Yes | File path or URL |
| `config` | dict | No | Config overrides |
| `embedding_options` | dict | No | `classify_math`, `semantic_linking`, `classify_document` (bool) |

Returns: `string` — Highest quality enriched markdown

---

### Granular tools (offline, composable)

These tools can be chained: `detect_math` → `format_latex`, or `extract_images` → `link_references` → `build_figure_index`.

#### `detect_math`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Text or HTML to analyze |
| `methods` | list[string] | No | `"unicode"`, `"mathml"`, `"mathjax"`, `"latex"` |

Returns: `JSON string` — Array of `{original_text, latex, source_type, confidence, position, is_inline}`

#### `format_latex`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `formulas` | string (JSON) | Yes | Output of `detect_math` |
| `style` | string | No | `"standard"` or `"github"` |

Returns: `JSON string` — Array of `{original_text, formatted}`

**Chaining example:**
```
1. detect_math(text="x² + y² = z²")  →  [{"latex": "x^{2}+y^{2}=z^{2}", ...}]
2. format_latex(formulas=↑, style="github")  →  [{"formatted": "$`x^{2}+y^{2}=z^{2}`$"}]
```

#### `extract_images`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | string | Yes | Document path |
| `output_dir` | string | No | Output directory (default: same as document) |
| `dpi` | int | No | Rasterization resolution (default: 300) |
| `autocrop` | bool | No | Crop white borders (default: true) |

Returns: `JSON string` — Array of `{file_path, width, height, position, original_format, context_text}`

Supported formats: PDF, DOCX, PPTX, HTML, EPUB, Jupyter Notebook.

#### `link_references`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Document text |
| `images` | string (JSON) | Yes | Output of `extract_images` |
| `patterns` | list[string] | No | Custom regex patterns |

Returns: `JSON string` — Array with `ordinal` and `reference_label` populated

#### `build_figure_index`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `images` | string (JSON) | Yes | Output of `link_references` |

Returns: `string` — Markdown figure index table

**Full image pipeline example:**
```
1. extract_images(uri="paper.pdf")          → extracted images
2. link_references(text=..., images=↑)      → images with references
3. build_figure_index(images=↑)             → markdown table
```

#### `ocr_formula`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image_path` | string | Yes | Path to formula image |
| `engine` | string | No | `"auto"`, `"pix2tex"`, `"nougat"` |

Returns: `JSON string` — `{latex, confidence, engine_used}` or `{error}`

---

### Embedding tools (require `GEMINI_API_KEY`)

#### `analyze_document`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | string | Yes | Document path |
| `analysis_type` | string | No | `"full"`, `"structure"`, `"math"`, `"images"` |

Returns: `JSON string` — `{document_type, math_density, math_count, word_count, formula_regions, classification_confidence}`

Document types: `academic_paper`, `technical_report`, `presentation`, `textbook`, `code_documentation`, `general_document`

#### `search_content`

Semantic search within a document (RAG).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uri` | string | Yes | Document path |
| `query` | string | Yes | Natural language query |
| `top_k` | int | No | Number of results (default: 5) |

Returns: `JSON string` — Array of `{content, score, position, type}`

Example:
```
search_content(uri="paper.pdf", query="Schrödinger equation", top_k=3)
→ [
    {"content": "$H|\\psi\\rangle = E|\\psi\\rangle$", "score": 0.94, "type": "formula"},
    {"content": "The time-independent Schrödinger equation...", "score": 0.87, "type": "text"}
  ]
```

#### `compare_sections`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `uris` | string (JSON) | Yes | Array of document paths |
| `granularity` | string | No | `"paragraph"`, `"section"`, `"page"` |

Returns: `JSON string` — `{document_count, total_sections, unique_topics}`

---

## Configuration

SciMarkdown looks for `scimarkdown.yaml` in the current directory. All options have sensible defaults.

```yaml
# ── LaTeX format ───────────────────────────────────────────
latex:
  style: "standard"              # "standard" ($...$) or "github" ($`...`$)

# ── Images ─────────────────────────────────────────────────
images:
  output_dir: "same"              # "same" = next to source document
  format: "png"
  dpi: 300
  margin_px: 10
  counter_digits: 5               # img00001
  autocrop_whitespace: true

# ── Formula detection ──────────────────────────────────────
math:
  heuristic: true
  ocr_engine: "auto"              # "pix2tex", "nougat", or "auto"
  confidence_threshold: 0.75

# ── LLM Fallback ──────────────────────────────────────────
llm:
  enabled: false
  provider: "openai"              # "openai" or "anthropic"
  model: "gpt-4o"
  api_key_env: "LLM_API_KEY"

# ── Gemini Embeddings ─────────────────────────────────────
embeddings:
  enabled: false
  model: "gemini-embedding-2-preview"
  api_key_env: "GEMINI_API_KEY"
  dimensions: 768
  classify_math: true
  semantic_linking: true
  classify_document: true
  content_indexing: false
  cache_enabled: true
  math_similarity_threshold: 0.75
  image_link_threshold: 0.60

# ── Noise filters ─────────────────────────────────────────
filters:
  enabled: true
  repeated_text: true             # Remove repeated headers/footers
  page_numbers: true              # Remove sequential page numbers
  decorative_images: true         # Remove small/narrow/repeated images
  min_repeat_pages: 3             # Pages text must repeat to be noise
  max_header_length: 100          # Max chars for header candidate
  min_image_size: 30              # Min px to keep an image
  max_image_aspect_ratio: 8.0     # Max ratio before flagging as decorative

# ── References ─────────────────────────────────────────────
references:
  patterns:
    - 'Fig(?:ura|ure|\.)\s*(\d+)'
    - 'Tab(?:la|le|\.)\s*(\d+)'
    - 'Im(?:agen|age|g\.?)\s*(\d+)'
  languages: ["es", "en"]
  generate_index: true

# ── Performance ────────────────────────────────────────────
performance:
  total_timeout_seconds: 1800
  max_images: 10000
  max_image_file_size_mb: 50

# ── Upstream sync ──────────────────────────────────────────
sync:
  remote: "https://github.com/microsoft/markitdown.git"
  check_interval_days: 14
```

---

## Supported formats

| Format | Formulas | Images | Noise filter | Notes |
|--------|----------|--------|--------------|-------|
| **PDF** | Unicode, OCR | Embedded + vector | Headers, footers, page numbers, TOC | Full support |
| **DOCX** | Native OMML | word/media/ | — | Best formula quality |
| **PPTX** | OMML | ppt/media/ | — | |
| **HTML** | MathML, MathJax, KaTeX | `<img>`, base64 | — | |
| **EPUB** | MathML (via HTML) | Archive images | — | Internally HTML + ZIP |
| **Jupyter** | Native LaTeX, MathML | Cell outputs | — | LaTeX passthrough |
| **XLSX** | Basic regex | — | — | Cell formulas |
| **Images** | OCR (optional) | The file itself | — | PNG, JPEG |
| **Audio** | — | — | — | Via base MarkItDown |
| **CSV/JSON/XML** | — | — | — | Via base MarkItDown |

---

## Architecture

```
Source document
       │
       ▼
┌─────────────────────────┐
│  Phase 1: Extraction    │  MarkItDown (unmodified)
│  → Base markdown        │  super().convert()
└─────────┬───────────────┘
          ▼
┌─────────────────────────────────────────────────┐
│  Phase 2: Enrichment                            │
│                                                  │
│  ┌────────────────────────────────────────┐      │
│  │ Layer 1: Heuristics (OFFLINE)         │      │
│  │  MathDetector · ImageExtractor        │      │
│  │  ReferenceLinker · ImageCropper        │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Noise Filters (OFFLINE)               │      │
│  │  RepeatedText · PageNumbers           │      │
│  │  DecorativeImages · TocProcessor      │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Layer 2: Embeddings (ONLINE, optional) │      │
│  │  MathClassifier · SemanticLinker      │      │
│  │  DocumentClassifier                    │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Layer 3: LLM Fallback (ONLINE, opt.)  │      │
│  │  OpenAI / Anthropic                    │      │
│  └────────────────────────────────────────┘      │
└─────────────────────┬────────────────────────────┘
                      ▼
┌─────────────────────────┐
│  Phase 3: Composition   │
│  → Markdown + LaTeX     │  MathFormatter · IndexBuilder
│  → Inline images        │  Context-anchored positioning
│  → Figure index         │
│  → TOC hyperlinks       │
└─────────────────────────┘
```

### Minimal fork strategy

- **0 lines modified** in MarkItDown source code
- `EnhancedMarkItDown` inherits from `MarkItDown`, overrides only `convert_stream()` and `convert_local()`
- 100% of enrichment code lives in `packages/scimarkdown/`
- Upstream sync every 14 days via GitHub Actions

---

## Graceful degradation

SciMarkdown never crashes on a conversion. If enrichment fails, it always returns the base markdown:

| Component | Failure | Behavior |
|-----------|---------|----------|
| MathDetector | Regex false positive | Marks with `<!-- sci:math:low-confidence -->` |
| MathOCR | Model not installed | Uses heuristics only |
| MathClassifier | Gemini API down | Skips classification, keeps heuristic results |
| SemanticLinker | Gemini API down | Skips semantic linking, uses ordinal ReferenceLinker |
| NoiseFilter | PDF parsing fails | Skips filtering, keeps all content |
| TocProcessor | No TOC detected | No changes |
| ImageExtractor | Cannot extract | Skips image, logs warning |
| LLM Fallback | API down/timeout | Skips LLM, continues with local results |
| Full pipeline | Unexpected exception | Returns base markdown unchanged |

---

## Development

### Run tests

```bash
source .venv/bin/activate

# All tests (409)
python -m pytest tests/ -v --ignore=tests/upstream

# By module
python -m pytest tests/unit/math/ -v
python -m pytest tests/unit/images/ -v
python -m pytest tests/unit/filters/ -v
python -m pytest tests/unit/embeddings/ -v
python -m pytest tests/unit/mcp/ -v
python -m pytest tests/unit/pipeline/ -v
python -m pytest tests/integration/ -v

# With coverage
python -m pytest tests/ --cov=scimarkdown --cov-report=html --ignore=tests/upstream
```

### Quality thresholds

| Metric | Minimum |
|--------|---------|
| LaTeX formulas correct | >= 95% |
| Images extracted | >= 95% |
| References linked | >= 95% |
| Upstream Microsoft tests | 100% |
| Code coverage | >= 85% |

---

## Upstream sync

SciMarkdown syncs with Microsoft MarkItDown every 14 days:

1. GitHub Actions runs on the 1st and 15th of each month
2. No conflicts + tests pass → automatic PR
3. Conflicts → issue created with details

Manual sync:
```bash
python -m scimarkdown.sync.upstream --repo-dir .
```

---

## Versioning

```
SciMarkdown v{MAJOR}.{MINOR}.{PATCH}+mit{UPSTREAM_VERSION}
Example: scimarkdown 0.1.0+mit0.1.1
```

---

## Embedding costs

| Operation | Cost/doc | 1000 docs/month |
|-----------|----------|-----------------|
| Offline conversion only | $0 | $0 |
| + Math classification | ~$0.002 | ~$2 |
| + Semantic linking | ~$0.005 | ~$5 |
| + Document classification | ~$0.001 | ~$1 |
| + Content indexing (RAG) | ~$0.01 | ~$10 |
| **All enabled** | **~$0.018** | **~$18** |

---

## License

This project is a fork of [Microsoft MarkItDown](https://github.com/microsoft/markitdown), licensed under MIT License.

## Credits

- **[Microsoft MarkItDown](https://github.com/microsoft/markitdown)** — Base Markdown conversion
- **[Google Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)** — Multimodal semantic analysis
- **[pix2tex](https://github.com/lukas-blecher/LaTeX-OCR)** — Formula OCR (optional)
- **[Nougat (Meta)](https://github.com/facebookresearch/nougat)** — Academic paper OCR (optional)
