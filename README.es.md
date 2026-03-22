# SciMarkdown

<p align="center">
  <strong>Conversor de documentos a Markdown con detección de fórmulas LaTeX, extracción inteligente de imágenes, filtrado de ruido y análisis semántico con Gemini Embeddings.</strong>
</p>

<p align="center">
  <a href="README.md"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Flag_of_Galicia.svg/20px-Flag_of_Galicia.svg.png" width="16" alt="Galicia"> Galego</a> ·
  🇪🇸 <strong>Español</strong> ·
  <a href="README.en.md">🇬🇧 English</a> ·
  <a href="README.bs.md">🇧🇦 Bosanski</a>
</p>

---

SciMarkdown es un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown) que amplía sus capacidades de conversión con cuatro pilares:

1. **Detección de fórmulas matemáticas y embebido LaTeX** en todos los formatos soportados
2. **Extracción, recorte y referenciado de imágenes** con vinculación de referencias textuales e índice de figuras
3. **Filtrado de ruido** — elimina cabeceras, pies de página, números de página e imágenes decorativas; convierte índices en hiperenlaces
4. **Análisis semántico con Gemini Embeddings** (opcional) — clasificación de fórmulas, vinculación imagen-texto por significado, clasificación de documentos y búsqueda semántica (RAG)

---

## Características

### Detección de fórmulas matemáticas

SciMarkdown detecta y convierte fórmulas matemáticas a LaTeX de forma automática usando múltiples estrategias por capas:

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

### Extracción inteligente de imágenes

- Extrae imágenes embebidas de PDF, DOCX, PPTX, HTML, EPUB y Jupyter Notebooks
- Recorte automático de bordes blancos con márgenes configurables
- Las imágenes se insertan **en la posición original** del documento, ancladas al texto que las precede
- **Convención de nombres:** `{documento}_img{00001}.png` (5 dígitos)
- **Rutas relativas:** Las rutas de imagen en el markdown son nombres de fichero relativos (no rutas absolutas), lo que hace el markdown portable

### Filtrado de ruido

- **Texto repetido** — detecta cabeceras/pies que se repiten en la misma posición en 3+ páginas
- **Números de página** — detecta secuencias numéricas en bloques frontera
- **Imágenes decorativas** — filtra imágenes pequeñas (<30px), muy estrechas (ratio >8:1) o repetidas
- **Índices (TOC)** — detecta tablas de contenidos y las convierte en hiperenlaces markdown
- **HeadingDetector** — detecta patrones de capítulo/sección ("Capítulo N.", "N.N. Título") y los convierte en encabezados markdown (#, ##, ###)
- **TextCleaner** — elimina artefactos de codificación CID de los PDF, convierte rutas absolutas de imágenes en nombres de fichero relativos, fusiona saltos de línea intra-párrafo del PDF preservando estructuras clave-valor
- **Eliminación de párrafos repetidos** — elimina párrafos que aparecen 3+ veces en el documento (cabeceras/pies que escapan a la detección por página)

**Antes:**
```
Capítulo 1: Introducción ......... 15
Capítulo 2: Métodos ......... 30
```
**Después:**
```markdown
- [Capítulo 1: Introducción](#capítulo-1-introducción)
- [Capítulo 2: Métodos](#capítulo-2-métodos)
```

### Servidor MCP con 12 herramientas

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

---

## Instalación

### Requisitos previos

- Python >= 3.10
- Git

### Paso 1: Clonar

```bash
git clone https://github.com/babel-stack/mcp-sciMarkdown.git
cd mcp-sciMarkdown
```

### Paso 2: Entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalar dependencias base

```bash
# Instalar MarkItDown (fork local)
pip install -e packages/markitdown[all]

# Instalar SciMarkdown (heurísticas, sin GPU, sin PyTorch)
pip install -e packages/scimarkdown
```

### Dependencias opcionales

```bash
# OCR de fórmulas con pix2tex (~500MB + PyTorch)
pip install -e "packages/scimarkdown[ocr]"

# OCR completo de artículos con Nougat (~3GB + PyTorch)
pip install -e "packages/scimarkdown[nougat]"

# LLM fallback (OpenAI/Anthropic)
pip install -e "packages/scimarkdown[llm]"

# Gemini Embeddings (análisis semántico)
pip install -e "packages/scimarkdown[embeddings]"

# Todo
pip install -e "packages/scimarkdown[all]"
```

### Paso 4: Instalar MCP SDK (para el servidor MCP)

```bash
pip install "mcp[cli]>=1.0.0"
```

### Variables de entorno

| Variable | Necesaria para | Ejemplo |
|----------|---------------|---------|
| `GEMINI_API_KEY` | Herramientas de embeddings | `export GEMINI_API_KEY=AIza...` |
| `LLM_API_KEY` | LLM fallback | `export LLM_API_KEY=sk-...` |

### NixOS

```bash
# Encontrar libstdc++
find /nix/store -name "libstdc++.so.6" 2>/dev/null | head -1

# Exportar (añadir a .bashrc/.zshrc)
export LD_LIBRARY_PATH=/nix/store/<hash>-gcc-<version>-lib/lib

# Si numpy 2.x falla con "X86_V2" en CPUs antiguas:
pip install "numpy<2.0"
```

Se incluye un script lanzador compatible con NixOS: `run-scimarkdown-mcp.sh`

---

## Uso

### CLI

```bash
# Conversión básica (stdout)
scimarkdown document.pdf

# Salida a fichero
scimarkdown document.pdf -o document.md

# LaTeX estilo GitHub
scimarkdown paper.pdf --latex-style github

# Directorio de salida de imágenes personalizado
scimarkdown paper.pdf --output-dir ./images/

# Fichero de configuración personalizado
scimarkdown paper.pdf -c my_config.yaml
```

### API Python

```python
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig

# Configuración por defecto
converter = EnhancedMarkItDown()
result = converter.convert("document.pdf")
print(result.markdown)

# Configuración personalizada
config = SciMarkdownConfig(
    latex_style="github",
    images_dpi=150,
    references_generate_index=True,
    filters_enabled=True,
)
converter = EnhancedMarkItDown(sci_config=config)
result = converter.convert("paper.docx")
```

#### Uso directo de subcomponentes

```python
# Detectar fórmulas en texto
from scimarkdown.math.detector import MathDetector
detector = MathDetector()
regions = detector.detect("The equation x² + y² = z² is famous.")
for r in regions:
    print(f"{r.original_text} → ${r.latex}$ (confianza: {r.confidence})")

# Extraer imágenes de un PDF
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
        print(f"Extraída: {img.file_path} ({img.width}x{img.height})")

# Vincular referencias
from scimarkdown.images.reference_linker import ReferenceLinker
linker = ReferenceLinker(SciMarkdownConfig())
linked = linker.link("Como se muestra en la Figura 1...", images)
```

#### Uso de Gemini Embeddings

```python
from scimarkdown.embeddings.client import GeminiEmbeddingClient
from scimarkdown.embeddings.math_classifier import MathClassifier
from scimarkdown.embeddings.semantic_linker import SemanticLinker
from scimarkdown.embeddings.content_indexer import ContentIndexer

# Crear cliente
client = GeminiEmbeddingClient(api_key="your-api-key")

# Clasificar candidatos a fórmula
classifier = MathClassifier(client, threshold=0.75)
confirmed = classifier.classify(detected_regions)

# Vinculación semántica imagen-texto (sin necesidad de "Figura X")
linker = SemanticLinker(client, threshold=0.60)
linked = linker.link(images, paragraphs)

# Búsqueda semántica (RAG)
indexer = ContentIndexer(client)
index = indexer.index(markdown_text)
results = indexer.search(index, "ecuación de Schrödinger", top_k=5)
```

### Servidor MCP

#### Modo STDIO (Claude Desktop, Claude Code, Cursor...)

```bash
scimarkdown-mcp
```

#### Modo HTTP (integración web)

```bash
scimarkdown-mcp --http --port 3001
```

#### Configuración en Claude Desktop

Añadir a `claude_desktop_config.json`:

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

NixOS — usar el lanzador incluido:

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

#### Configuración en Claude Code

```bash
# Nivel usuario (disponible en todos los proyectos)
claude mcp add --scope user scimarkdown /path/to/mcp-sciMarkdown/run-scimarkdown-mcp.sh

# Nivel proyecto
claude mcp add scimarkdown scimarkdown-mcp
```

---

## Herramientas MCP — Referencia completa

### Herramientas de pipeline (conversión de extremo a extremo)

#### `convert_to_markdown`

Conversión básica vía MarkItDown. Sin enriquecimiento.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta de fichero o URL |

Devuelve: `string` — Markdown simple

---

#### `convert_to_scimarkdown`

Conversión enriquecida con LaTeX, imágenes, filtrado de ruido e hiperenlaces TOC. Totalmente offline.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta de fichero o URL |
| `config` | dict | No | Sobreescribir `scimarkdown.yaml` |

Devuelve: `string` — Markdown enriquecido

Ejemplo de config:
```json
{"latex": {"style": "github"}, "images": {"dpi": 150}, "filters": {"enabled": true}}
```

---

#### `convert_to_scimarkdown_embeddings`

Conversión de máxima calidad con Gemini Embeddings. Requiere `GEMINI_API_KEY`.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta de fichero o URL |
| `config` | dict | No | Sobreescrituras de config |
| `embedding_options` | dict | No | `classify_math`, `semantic_linking`, `classify_document` (bool) |

Devuelve: `string` — Markdown enriquecido de máxima calidad

---

### Herramientas granulares (offline, combinables)

Estas herramientas se pueden encadenar: `detect_math` → `format_latex`, o `extract_images` → `link_references` → `build_figure_index`.

#### `detect_math`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `text` | string | Sí | Texto o HTML a analizar |
| `methods` | list[string] | No | `"unicode"`, `"mathml"`, `"mathjax"`, `"latex"` |

Devuelve: `JSON string` — Array de `{original_text, latex, source_type, confidence, position, is_inline}`

#### `format_latex`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `formulas` | string (JSON) | Sí | Salida de `detect_math` |
| `style` | string | No | `"standard"` o `"github"` |

Devuelve: `JSON string` — Array de `{original_text, formatted}`

**Ejemplo de encadenamiento:**
```
1. detect_math(text="x² + y² = z²")  →  [{"latex": "x^{2}+y^{2}=z^{2}", ...}]
2. format_latex(formulas=↑, style="github")  →  [{"formatted": "$`x^{2}+y^{2}=z^{2}`$"}]
```

#### `extract_images`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta del documento |
| `output_dir` | string | No | Directorio de salida (por defecto: junto al documento) |
| `dpi` | int | No | Resolución de rasterización (por defecto: 300) |
| `autocrop` | bool | No | Recortar bordes blancos (por defecto: true) |

Devuelve: `JSON string` — Array de `{file_path, width, height, position, original_format, context_text}`

Formatos soportados: PDF, DOCX, PPTX, HTML, EPUB, Jupyter Notebook.

#### `link_references`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `text` | string | Sí | Texto del documento |
| `images` | string (JSON) | Sí | Salida de `extract_images` |
| `patterns` | list[string] | No | Patrones regex personalizados |

Devuelve: `JSON string` — Array con `ordinal` y `reference_label` rellenos

#### `build_figure_index`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `images` | string (JSON) | Sí | Salida de `link_references` |

Devuelve: `string` — Tabla de índice de figuras en Markdown

**Ejemplo completo de pipeline de imágenes:**
```
1. extract_images(uri="paper.pdf")          → imágenes extraídas
2. link_references(text=..., images=↑)      → imágenes con referencias
3. build_figure_index(images=↑)             → tabla markdown
```

#### `ocr_formula`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `image_path` | string | Sí | Ruta a la imagen de la fórmula |
| `engine` | string | No | `"auto"`, `"pix2tex"`, `"nougat"` |

Devuelve: `JSON string` — `{latex, confidence, engine_used}` o `{error}`

---

### Herramientas de embeddings (requieren `GEMINI_API_KEY`)

#### `analyze_document`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta del documento |
| `analysis_type` | string | No | `"full"`, `"structure"`, `"math"`, `"images"` |

Devuelve: `JSON string` — `{document_type, math_density, math_count, word_count, formula_regions, classification_confidence}`

Tipos de documento: `academic_paper`, `technical_report`, `presentation`, `textbook`, `code_documentation`, `general_document`

#### `search_content`

Búsqueda semántica dentro de un documento (RAG).

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta del documento |
| `query` | string | Sí | Consulta en lenguaje natural |
| `top_k` | int | No | Número de resultados (por defecto: 5) |

Devuelve: `JSON string` — Array de `{content, score, position, type}`

Ejemplo:
```
search_content(uri="paper.pdf", query="ecuación de Schrödinger", top_k=3)
→ [
    {"content": "$H|\\psi\\rangle = E|\\psi\\rangle$", "score": 0.94, "type": "formula"},
    {"content": "La ecuación de Schrödinger independiente del tiempo...", "score": 0.87, "type": "text"}
  ]
```

#### `compare_sections`

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uris` | string (JSON) | Sí | Array de rutas de documentos |
| `granularity` | string | No | `"paragraph"`, `"section"`, `"page"` |

Devuelve: `JSON string` — `{document_count, total_sections, unique_topics}`

---

## Configuración

SciMarkdown busca `scimarkdown.yaml` en el directorio actual. Todas las opciones tienen valores por defecto razonables.

```yaml
# ── Formato LaTeX ───────────────────────────────────────────
latex:
  style: "standard"              # "standard" ($...$) o "github" ($`...`$)

# ── Imágenes ─────────────────────────────────────────────────
images:
  output_dir: "same"              # "same" = junto al documento fuente
  format: "png"
  dpi: 300
  margin_px: 10
  counter_digits: 5               # img00001
  autocrop_whitespace: true

# ── Detección de fórmulas ──────────────────────────────────
math:
  heuristic: true
  ocr_engine: "auto"              # "pix2tex", "nougat" o "auto"
  confidence_threshold: 0.75

# ── LLM Fallback ──────────────────────────────────────────
llm:
  enabled: false
  provider: "openai"              # "openai" o "anthropic"
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

# ── Filtros de ruido ─────────────────────────────────────
filters:
  enabled: true
  repeated_text: true             # Eliminar cabeceras/pies repetidos
  page_numbers: true              # Eliminar números de página secuenciales
  decorative_images: true         # Eliminar imágenes pequeñas/estrechas/repetidas
  min_repeat_pages: 3             # Páginas que debe repetirse el texto para ser ruido
  max_header_length: 100          # Máx. caracteres para candidato a cabecera
  min_image_size: 30              # Mín. px para conservar una imagen
  max_image_aspect_ratio: 8.0     # Ratio máximo antes de marcar como decorativa
  # (Estos son automáticos, sin configuración necesaria:)
  # heading_detection: automático
  # cid_cleaning: automático
  # path_normalization: automático
  # line_break_merging: automático (preserva estructuras clave-valor)
  # repeated_paragraph_removal: mín. 3 ocurrencias

# ── Referencias ─────────────────────────────────────────────
references:
  patterns:
    - 'Fig(?:ura|ure|\.)\s*(\d+)'
    - 'Tab(?:la|le|\.)\s*(\d+)'
    - 'Im(?:agen|age|g\.?)\s*(\d+)'
  languages: ["es", "en"]
  generate_index: true

# ── Rendimiento ────────────────────────────────────────────
performance:
  total_timeout_seconds: 1800
  max_images: 10000
  max_image_file_size_mb: 50

# ── Sincronización upstream ──────────────────────────────
sync:
  remote: "https://github.com/microsoft/markitdown.git"
  check_interval_days: 14
```

---

## Formatos soportados

| Formato | Fórmulas | Imágenes | Filtro de ruido | Notas |
|---------|----------|----------|-----------------|-------|
| **PDF** | Unicode, OCR | Embebidas + vector | Cabeceras, pies, números de página, TOC | Soporte completo |
| **DOCX** | OMML nativo | word/media/ | — | Mejor calidad de fórmulas |
| **PPTX** | OMML | ppt/media/ | — | |
| **HTML** | MathML, MathJax, KaTeX | `<img>`, base64 | — | |
| **EPUB** | MathML (vía HTML) | Imágenes del archivo | — | Internamente HTML + ZIP |
| **Jupyter** | LaTeX nativo, MathML | Salidas de celdas | — | Paso directo de LaTeX |
| **XLSX** | Regex básico | — | — | Fórmulas de celdas |
| **Imágenes** | OCR (opcional) | El propio fichero | — | PNG, JPEG |
| **Audio** | — | — | — | Vía MarkItDown base |
| **CSV/JSON/XML** | — | — | — | Vía MarkItDown base |

---

## Arquitectura

```
Documento fuente
       │
       ▼
┌─────────────────────────┐
│  Fase 1: Extracción     │  MarkItDown (sin modificar)
│  → Markdown base        │  super().convert()
└─────────┬───────────────┘
          ▼
┌─────────────────────────────────────────────────┐
│  Fase 2: Enriquecimiento                        │
│                                                  │
│  ┌────────────────────────────────────────┐      │
│  │ Capa 1: Heurísticas (OFFLINE)         │      │
│  │  MathDetector · ImageExtractor        │      │
│  │  ReferenceLinker · ImageCropper        │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Filtros de ruido (OFFLINE)            │      │
│  │  RepeatedText · PageNumbers           │      │
│  │  DecorativeImages · TocProcessor      │      │
│  │  HeadingDetector · TextCleaner        │      │
│  │  RepeatedParagraphs                    │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Capa 2: Embeddings (ONLINE, opcional) │      │
│  │  MathClassifier · SemanticLinker      │      │
│  │  DocumentClassifier                    │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Capa 3: LLM Fallback (ONLINE, opc.)  │      │
│  │  OpenAI / Anthropic                    │      │
│  └────────────────────────────────────────┘      │
└─────────────────────┬────────────────────────────┘
                      ▼
┌─────────────────────────┐
│  Fase 3: Composición    │
│  → Markdown + LaTeX     │  MathFormatter · IndexBuilder
│  → Imágenes inline      │  Posicionamiento anclado al contexto
│  → Índice de figuras    │
│  → Hiperenlaces TOC     │
└─────────────────────────┘
```

### Estructura del proyecto

```
packages/scimarkdown/
│       ├── filters/
│       │   ├── noise_filter.py         ← Orquestrador + eliminación de párrafos repetidos
│       │   ├── repeated_text.py        ← Detección de cabecera/pie por posición de página
│       │   ├── page_numbers.py         ← Detección de números de página secuenciales
│       │   ├── decorative_images.py    ← Filtro de imágenes pequeñas/estrechas/repetidas
│       │   ├── toc_processor.py        ← Conversión TOC → hiperenlaces
│       │   ├── heading_detector.py     ← Capítulo/sección → encabezados markdown
│       │   └── text_cleaner.py         ← Eliminación CID, normalización de rutas, fusión de líneas
```

### Estrategia de fork mínimo

- **0 líneas modificadas** en el código fuente de MarkItDown
- `EnhancedMarkItDown` hereda de `MarkItDown`, sobreescribe solo `convert_stream()` y `convert_local()`
- El 100% del código de enriquecimiento vive en `packages/scimarkdown/`
- Sincronización upstream cada 14 días vía GitHub Actions

---

## Degradación graceful

SciMarkdown nunca falla en una conversión. Si el enriquecimiento falla, siempre devuelve el markdown base:

| Componente | Fallo | Comportamiento |
|------------|-------|----------------|
| MathDetector | Falso positivo de regex | Marca con `<!-- sci:math:low-confidence -->` |
| MathOCR | Modelo no instalado | Usa solo heurísticas |
| MathClassifier | API Gemini caída | Omite clasificación, mantiene resultados heurísticos |
| SemanticLinker | API Gemini caída | Omite vinculación semántica, usa ReferenceLinker ordinal |
| NoiseFilter | Fallo al parsear PDF | Omite filtrado, mantiene todo el contenido |
| TocProcessor | No se detecta TOC | Sin cambios |
| HeadingDetector | Ningún patrón coincide | Texto sin cambios |
| TextCleaner | El procesamiento falla | Texto sin cambios |
| RepeatedParagraphs | La detección falla | Se mantienen todos los párrafos |
| ImageExtractor | No se puede extraer | Omite imagen, registra aviso |
| LLM Fallback | API caída/timeout | Omite LLM, continúa con resultados locales |
| Pipeline completo | Excepción inesperada | Devuelve markdown base sin cambios |

---

## Desarrollo

### Ejecutar tests

```bash
source .venv/bin/activate

# Todos los tests (790)
python -m pytest tests/ -v --ignore=tests/upstream

# Por módulo
python -m pytest tests/unit/math/ -v
python -m pytest tests/unit/images/ -v
python -m pytest tests/unit/filters/ -v
python -m pytest tests/unit/embeddings/ -v
python -m pytest tests/unit/mcp/ -v
python -m pytest tests/unit/pipeline/ -v
python -m pytest tests/integration/ -v

# Con cobertura
python -m pytest tests/ --cov=scimarkdown --cov-report=html --ignore=tests/upstream
```

### Umbrales de calidad

| Métrica | Mínimo |
|---------|--------|
| Fórmulas LaTeX correctas | >= 95% |
| Imágenes extraídas | >= 95% |
| Referencias vinculadas | >= 95% |
| Tests Microsoft upstream | 100% |
| Cobertura de código | >= 85% |

---

## Sincronización upstream

SciMarkdown sincroniza con Microsoft MarkItDown cada 14 días:

1. GitHub Actions se ejecuta los días 1 y 15 de cada mes
2. Sin conflictos + tests pasan → PR automático
3. Con conflictos → se crea un issue con detalles

Sincronización manual:
```bash
python -m scimarkdown.sync.upstream --repo-dir .
```

---

## Versionado

```
SciMarkdown v{MAJOR}.{MINOR}.{PATCH}+mit{UPSTREAM_VERSION}
Ejemplo: scimarkdown 0.1.0+mit0.1.1
```

---

## Costes de embeddings

| Operación | Coste/doc | 1000 docs/mes |
|-----------|-----------|---------------|
| Solo conversión offline | $0 | $0 |
| + Clasificación matemática | ~$0.002 | ~$2 |
| + Vinculación semántica | ~$0.005 | ~$5 |
| + Clasificación de documento | ~$0.001 | ~$1 |
| + Indexación de contenido (RAG) | ~$0.01 | ~$10 |
| **Todo activado** | **~$0.018** | **~$18** |

---

## Licencia

Este proyecto es un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown), licenciado bajo MIT License.

## Créditos

- **[Microsoft MarkItDown](https://github.com/microsoft/markitdown)** — Conversión base a Markdown
- **[Google Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)** — Análisis semántico multimodal
- **[pix2tex](https://github.com/lukas-blecher/LaTeX-OCR)** — OCR de fórmulas (opcional)
- **[Nougat (Meta)](https://github.com/facebookresearch/nougat)** — OCR de artículos académicos (opcional)
