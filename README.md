# SciMarkdown

**Conversor de documentos a Markdown con detección de fórmulas LaTeX, extracción inteligente de imágenes y análisis semántico con Gemini Embeddings.**

SciMarkdown es un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown) que amplía sus capacidades de conversión con tres pilares:

1. **Detección de fórmulas matemáticas y embebido LaTeX** en todos los formatos soportados
2. **Extracción, recorte y referenciado de imágenes** con vinculación de referencias textuales e índice de figuras
3. **Análisis semántico con Gemini Embeddings** (opcional) — clasificación de fórmulas, vinculación imagen-texto por significado, clasificación de documentos, y búsqueda semántica (RAG)

---

## Tabla de contenidos

- [Características](#características)
- [Instalación](#instalación)
- [Uso](#uso)
  - [CLI](#cli)
  - [Python API](#python-api)
  - [Servidor MCP](#servidor-mcp)
- [Herramientas MCP — Catálogo completo](#herramientas-mcp--catálogo-completo)
  - [Pipeline de conversión](#1-pipeline-de-conversión-3-tools)
  - [Control granular offline](#2-control-granular-offline-6-tools)
  - [Análisis con embeddings](#3-análisis-con-embeddings-3-tools)
- [Configuración](#configuración)
- [Formatos soportados](#formatos-soportados)
- [Arquitectura](#arquitectura)
- [Degradación elegante](#degradación-elegante)
- [Desarrollo](#desarrollo)
- [Sincronización con upstream](#sincronización-con-upstream)

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
- Rasterización de gráficos vectoriales a PNG (300 DPI por defecto)
- **Naming convention:** `{documento}_img{00001}.png` (5 dígitos, ordenación alfabética = orden en documento)
- Las imágenes se guardan junto al documento original

### Vinculación de referencias

SciMarkdown detecta automáticamente referencias en el texto como "Figura 1", "Fig. 2", "Table 3", "Imagen 4" (en español e inglés) y las vincula a las imágenes extraídas. Genera un **índice de figuras** al final del documento:

```markdown
## Figure Index

| # | Figure | Description | File |
|---|--------|-------------|------|
| 1 | Figura 1 | Diagrama de arquitectura | doc_img00001.png |
| 2 | Figura 2 | Resultados experimentales | doc_img00002.png |
```

### Análisis semántico con Gemini Embeddings (opcional)

Cuando se configura una API key de Gemini, SciMarkdown activa capacidades avanzadas:

- **MathClassifier** — Confirma o descarta detecciones heurísticas de fórmulas comparando contra embeddings de referencia
- **SemanticLinker** — Vincula imágenes a texto por similitud semántica multimodal, sin necesitar "Figura X"
- **DocumentClassifier** — Clasifica el tipo de documento (paper académico, informe técnico, presentación...) y optimiza el pipeline
- **ContentIndexer** — Indexa el contenido convertido para búsqueda semántica (RAG)

---

## Instalación

### Requisitos previos

- Python >= 3.10
- Git

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/babel-stack/mcp-sciMarkdown.git
cd mcp-sciMarkdown
```

### Paso 2: Crear entorno virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalar dependencias base

```bash
# Instalar MarkItDown (fork local)
pip install -e packages/markitdown[all]

# Instalar SciMarkdown (heurísticas, sin GPU ni PyTorch)
pip install -e packages/scimarkdown
```

### Dependencias opcionales

```bash
# OCR de fórmulas con pix2tex (~500MB + PyTorch)
pip install -e "packages/scimarkdown[ocr]"

# OCR de papers completos con Nougat (~3GB + PyTorch)
pip install -e "packages/scimarkdown[nougat]"

# LLM fallback (OpenAI/Anthropic)
pip install -e "packages/scimarkdown[llm]"

# Gemini Embeddings (análisis semántico)
pip install -e "packages/scimarkdown[embeddings]"

# Todo incluido
pip install -e "packages/scimarkdown[all]"
```

### Paso 4 (opcional): Instalar MCP SDK

```bash
pip install "mcp[cli]>=1.0.0"
```

### Variables de entorno

| Variable | Necesaria para | Ejemplo |
|----------|---------------|---------|
| `GEMINI_API_KEY` | Embeddings (tools con `_embeddings`, `analyze_document`, `search_content`, `compare_sections`) | `export GEMINI_API_KEY=AIza...` |
| `LLM_API_KEY` | LLM fallback | `export LLM_API_KEY=sk-...` |

### NixOS

En NixOS, numpy puede necesitar `libstdc++` del nix store:

```bash
# Encontrar libstdc++
find /nix/store -name "libstdc++.so.6" 2>/dev/null | head -1

# Exportar (añadir a tu .bashrc o .zshrc)
export LD_LIBRARY_PATH=/nix/store/<hash>-gcc-<version>-lib/lib

# Si numpy 2.x falla con "X86_V2" en CPUs antiguas:
pip install "numpy<2.0"
```

Se incluye un script launcher compatible con NixOS: `run-scimarkdown-mcp.sh`

---

## Uso

### CLI

```bash
# Conversión básica (salida a stdout)
scimarkdown documento.pdf

# Especificar fichero de salida
scimarkdown documento.pdf -o documento.md

# Estilo LaTeX GitHub-flavored
scimarkdown paper.pdf --latex-style github

# Directorio personalizado para imágenes extraídas
scimarkdown paper.pdf --output-dir ./imagenes/

# Fichero de configuración personalizado
scimarkdown paper.pdf -c mi_config.yaml
```

### Python API

```python
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig

# Conversión con valores por defecto
converter = EnhancedMarkItDown()
result = converter.convert("documento.pdf")
print(result.markdown)

# Configuración personalizada
config = SciMarkdownConfig(
    latex_style="github",
    images_dpi=150,
    references_generate_index=True,
)
converter = EnhancedMarkItDown(sci_config=config)
result = converter.convert("paper.docx")
```

#### Uso directo de subcomponentes

```python
# Detectar fórmulas en texto
from scimarkdown.math.detector import MathDetector
detector = MathDetector()
regions = detector.detect("La ecuación x² + y² = z² es famosa.")
for r in regions:
    print(f"{r.original_text} → ${r.latex}$ (confianza: {r.confidence})")

# Extraer imágenes de un PDF
from scimarkdown.images.extractor import ImageExtractor
from scimarkdown.config import SciMarkdownConfig
from pathlib import Path

extractor = ImageExtractor(
    config=SciMarkdownConfig(),
    document_name="paper",
    output_dir=Path("./imagenes"),
)
with open("paper.pdf", "rb") as f:
    images = extractor.extract_from_pdf(f)
    for img in images:
        print(f"Extraída: {img.file_path} ({img.width}x{img.height})")

# Vincular referencias
from scimarkdown.images.reference_linker import ReferenceLinker
linker = ReferenceLinker(SciMarkdownConfig())
linked = linker.link("Como muestra la Figura 1...", images)
```

#### Uso con Gemini Embeddings

```python
from scimarkdown.embeddings.client import GeminiEmbeddingClient
from scimarkdown.embeddings.math_classifier import MathClassifier
from scimarkdown.embeddings.semantic_linker import SemanticLinker
from scimarkdown.embeddings.document_classifier import DocumentClassifier
from scimarkdown.embeddings.content_indexer import ContentIndexer

# Crear cliente
client = GeminiEmbeddingClient(api_key="tu-api-key")

# Clasificar fórmulas
classifier = MathClassifier(client, threshold=0.75)
confirmed = classifier.classify(detected_regions)

# Vincular imágenes por semántica
linker = SemanticLinker(client, threshold=0.60)
linked = linker.link(images, paragraphs)

# Clasificar tipo de documento
doc_classifier = DocumentClassifier(client)
doc_type, confidence = doc_classifier.classify(text)

# Búsqueda semántica (RAG)
indexer = ContentIndexer(client)
index = indexer.index(markdown_text)
results = indexer.search(index, "ecuación de Schrödinger", top_k=5)
```

### Servidor MCP

#### Modo STDIO (para Claude Desktop, Claude Code, Cursor, etc.)

```bash
scimarkdown-mcp
```

#### Modo HTTP (para integración web)

```bash
scimarkdown-mcp --http --port 3001
```

#### Configuración en Claude Desktop

Añade a tu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scimarkdown": {
      "command": "scimarkdown-mcp",
      "args": [],
      "env": {
        "GEMINI_API_KEY": "tu-api-key-aquí"
      }
    }
  }
}
```

En NixOS, usa el launcher incluido:

```json
{
  "mcpServers": {
    "scimarkdown": {
      "command": "/ruta/a/mcp-sciMarkdown/run-scimarkdown-mcp.sh",
      "env": {
        "GEMINI_API_KEY": "tu-api-key-aquí"
      }
    }
  }
}
```

#### Configuración en Claude Code

```bash
# Añadir a nivel de usuario (disponible en todos los proyectos)
claude mcp add --scope user scimarkdown /ruta/a/mcp-sciMarkdown/run-scimarkdown-mcp.sh

# O a nivel de proyecto
claude mcp add scimarkdown scimarkdown-mcp
```

---

## Herramientas MCP — Catálogo completo

SciMarkdown expone **12 herramientas MCP** organizadas en tres niveles.

### 1. Pipeline de conversión (3 tools)

Conversión end-to-end de documentos completos.

#### `convert_to_markdown`

Conversión básica via MarkItDown original. Sin enriquecimiento.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta o URL del documento |

```
Retorna: string — Markdown plano
```

#### `convert_to_scimarkdown`

Conversión enriquecida con LaTeX e imágenes. Pipeline offline completo.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta o URL del documento |
| `config` | dict | No | Overrides de `scimarkdown.yaml` |

```
Retorna: string — Markdown con $LaTeX$, enlaces a imágenes, índice de figuras
```

Ejemplo de `config`:
```json
{"latex": {"style": "github"}, "images": {"dpi": 150}}
```

#### `convert_to_scimarkdown_embeddings`

Conversión con pipeline completo + Gemini Embeddings para máxima calidad. Requiere `GEMINI_API_KEY`.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta o URL del documento |
| `config` | dict | No | Overrides de configuración |
| `embedding_options` | dict | No | Opciones de embeddings |

Opciones de `embedding_options`:

| Clave | Tipo | Defecto | Descripción |
|-------|------|---------|-------------|
| `classify_math` | bool | true | Confirmar/descartar fórmulas con embeddings |
| `semantic_linking` | bool | true | Vincular imágenes a texto por semántica |
| `classify_document` | bool | true | Clasificar tipo de documento |

```
Retorna: string — Markdown enriquecido con máxima precisión
```

### 2. Control granular offline (6 tools)

Cada subcomponente del pipeline accesible individualmente. No requieren API key. Permiten encadenar operaciones: `detect_math` → `format_latex`, o `extract_images` → `link_references` → `build_figure_index`.

#### `detect_math`

Detecta fórmulas matemáticas en texto o HTML.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `text` | string | Sí | Texto o HTML a analizar |
| `methods` | list[string] | No | Métodos: `"unicode"`, `"mathml"`, `"mathjax"`, `"latex"`. Default: todos |

```
Retorna: JSON string — array de objetos con:
  original_text, latex, source_type, confidence, position, is_inline
```

#### `format_latex`

Formatea fórmulas detectadas al estilo LaTeX deseado.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `formulas` | string (JSON) | Sí | Array de fórmulas (output de `detect_math`) |
| `style` | string | No | `"standard"` ($...$) o `"github"` ($\`...\`$). Default: `"standard"` |

```
Retorna: JSON string — array de objetos con: original_text, formatted
```

**Ejemplo de encadenamiento:**
```
1. detect_math(text="x² + y² = z²")
   → [{"latex": "x^{2} + y^{2} = z^{2}", ...}]

2. format_latex(formulas=<resultado anterior>, style="github")
   → [{"formatted": "$`x^{2} + y^{2} = z^{2}`$"}]
```

#### `extract_images`

Extrae imágenes de un documento y las guarda en disco.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta al documento |
| `output_dir` | string | No | Directorio de salida. Default: junto al documento |
| `dpi` | int | No | Resolución para vectoriales. Default: 300 |
| `autocrop` | bool | No | Recortar bordes blancos. Default: true |

```
Retorna: JSON string — array de objetos con:
  file_path, width, height, position, original_format, ordinal, reference_label, caption
```

Formatos soportados: PDF, DOCX, PPTX, HTML, EPUB, Jupyter Notebook.

#### `link_references`

Vincula referencias textuales ("Figura 1", "Table 2") a imágenes extraídas.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `text` | string | Sí | Texto del documento |
| `images` | string (JSON) | Sí | Array de imágenes (output de `extract_images`) |
| `patterns` | list[string] | No | Regex patterns personalizados |

```
Retorna: JSON string — array de imágenes con ordinal y reference_label actualizados
```

#### `build_figure_index`

Genera un índice de figuras en formato markdown.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `images` | string (JSON) | Sí | Array de imágenes (output de `link_references`) |

```
Retorna: string — Tabla markdown con índice de figuras, o "" si vacío
```

**Ejemplo de encadenamiento completo:**
```
1. extract_images(uri="paper.pdf")        → imágenes extraídas
2. link_references(text=..., images=...)  → imágenes con referencias
3. build_figure_index(images=...)         → tabla markdown
```

#### `ocr_formula`

Reconoce una fórmula matemática en una imagen via OCR. Requiere `[ocr]` (pix2tex).

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `image_path` | string | Sí | Ruta a la imagen de la fórmula |
| `engine` | string | No | `"auto"`, `"pix2tex"`, `"nougat"`. Default: `"auto"` |

```
Retorna: JSON string — {latex, confidence, engine_used} o {error}
```

### 3. Análisis con embeddings (3 tools)

Funcionalidades avanzadas que requieren `GEMINI_API_KEY`.

#### `analyze_document`

Analiza un documento y devuelve metadatos semánticos sin convertir.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta al documento |
| `analysis_type` | string | No | `"full"`, `"structure"`, `"math"`, `"images"`. Default: `"full"` |

```
Retorna: JSON string con:
  document_type      — "academic_paper", "technical_report", "presentation",
                       "textbook", "code_documentation", "general_document"
  math_density       — 0.0-1.0, proporción de contenido matemático
  math_count         — Número de fórmulas detectadas
  word_count         — Palabras totales
  formula_regions    — Array de regiones de fórmulas con confianza
  classification_confidence — Confianza de la clasificación (si embeddings disponibles)
```

#### `search_content`

Búsqueda semántica dentro de un documento (RAG).

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uri` | string | Sí | Ruta al documento |
| `query` | string | Sí | Consulta en lenguaje natural |
| `top_k` | int | No | Número de resultados. Default: 5 |

```
Retorna: JSON string — array de objetos con:
  content    — Fragmento de markdown relevante
  score      — Similitud (0.0-1.0)
  position   — Posición en el documento
  type       — "text", "heading", "formula", "image", "table"
```

Ejemplo:
```
search_content(uri="paper.pdf", query="ecuación de Schrödinger", top_k=3)
→ [
    {"content": "$H|\\psi\\rangle = E|\\psi\\rangle$", "score": 0.94, "type": "formula"},
    {"content": "The time-independent Schrödinger equation...", "score": 0.87, "type": "text"},
  ]
```

#### `compare_sections`

Compara semánticamente secciones entre uno o más documentos.

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `uris` | string (JSON) | Sí | Array de rutas a documentos |
| `granularity` | string | No | `"paragraph"`, `"section"`, `"page"`. Default: `"section"` |

```
Retorna: JSON string con:
  document_count   — Número de documentos comparados
  total_sections   — Secciones totales encontradas
  unique_topics    — Temas únicos identificados
```

### Resumen de tools

| # | Tool | Nivel | Online | Coste |
|---|------|-------|--------|-------|
| 1 | `convert_to_markdown` | Pipeline | No | 0 |
| 2 | `convert_to_scimarkdown` | Pipeline | No | 0 |
| 3 | `convert_to_scimarkdown_embeddings` | Pipeline | Sí | ~$0.01/doc |
| 4 | `detect_math` | Granular | No | 0 |
| 5 | `format_latex` | Granular | No | 0 |
| 6 | `extract_images` | Granular | No | 0 |
| 7 | `link_references` | Granular | No | 0 |
| 8 | `build_figure_index` | Granular | No | 0 |
| 9 | `ocr_formula` | Granular | No | 0 |
| 10 | `analyze_document` | Embeddings | Sí | ~$0.005/doc |
| 11 | `search_content` | Embeddings | Sí | ~$0.002/query |
| 12 | `compare_sections` | Embeddings | Sí | ~$0.01/doc |

---

## Configuración

SciMarkdown busca un fichero `scimarkdown.yaml` en el directorio actual. Todas las opciones tienen valores por defecto sensatos — no es necesario crear el fichero para usar SciMarkdown.

```yaml
# ── Formato LaTeX ──────────────────────────────────────────
latex:
  style: "standard"          # "standard" ($...$) o "github" ($`...`$)

# ── Imágenes ───────────────────────────────────────────────
images:
  output_dir: "same"          # "same" = junto al documento original
  format: "png"               # formato de rasterización
  dpi: 300                    # resolución para gráficos vectoriales
  margin_px: 10               # margen al recortar regiones
  counter_digits: 5           # dígitos del contador (img00001)
  autocrop_whitespace: true   # recortar bordes blancos automáticamente

# ── Detección de fórmulas ──────────────────────────────────
math:
  heuristic: true             # detección por regex/Unicode
  ocr_engine: "auto"          # "pix2tex", "nougat" o "auto"
  nougat_model: "0.1.0-base"  # modelo de Nougat
  confidence_threshold: 0.75  # umbral para aceptar OCR sin LLM

# ── LLM Fallback ──────────────────────────────────────────
llm:
  enabled: false              # activar fallback LLM
  provider: "openai"          # "openai" o "anthropic"
  model: "gpt-4o"             # modelo a usar
  api_key_env: "LLM_API_KEY"  # variable de entorno con la API key

# ── Gemini Embeddings (NUEVO v2) ──────────────────────────
embeddings:
  enabled: false              # activar capa de embeddings
  provider: "gemini"          # proveedor (por ahora solo Gemini)
  model: "gemini-embedding-2-preview"
  api_key_env: "GEMINI_API_KEY"
  dimensions: 768             # 128-3072 (768 = buen balance calidad/coste)
  classify_math: true         # confirmar/descartar fórmulas con embeddings
  semantic_linking: true      # vincular imágenes a texto por semántica
  classify_document: true     # clasificar tipo de documento
  content_indexing: false     # indexar para búsqueda semántica (más costoso)
  cache_enabled: true         # caché local de embeddings
  cache_dir: ".scimarkdown_cache"
  cache_ttl_days: 30
  math_similarity_threshold: 0.75   # umbral para confirmar fórmula
  image_link_threshold: 0.60        # umbral para vincular imagen-texto
  max_embeddings_per_document: 500   # control de costes
  batch_size: 100                    # embeddings por request

# ── Referencias ────────────────────────────────────────────
references:
  patterns:                   # patrones regex para detectar referencias
    - 'Fig(?:ura|ure|\.)\s*(\d+)'
    - 'Tab(?:la|le|\.)\s*(\d+)'
    - 'Gr[aA]f(?:ico|h)\s*(\d+)'
    - 'Im(?:agen|age|g\.?)\s*(\d+)'
    - 'Chart\s*(\d+)'
  languages: ["es", "en"]
  generate_index: true        # generar índice de figuras al final

# ── Rendimiento ────────────────────────────────────────────
performance:
  total_timeout_seconds: 1800
  max_images: 10000
  max_image_file_size_mb: 50
  max_total_images_size_mb: 500
  ocr_timeout_seconds: 30
  nougat_timeout_seconds: 120
  llm_timeout_seconds: 60
  unload_models_after_conversion: false

# ── Sincronización con upstream ────────────────────────────
sync:
  remote: "https://github.com/microsoft/markitdown.git"
  branch: "main"
  check_interval_days: 14
```

---

## Formatos soportados

| Formato | Fórmulas | Imágenes | Notas |
|---------|----------|----------|-------|
| **PDF** | Unicode, OCR | Embebidas + vectoriales | Nougat para papers completos |
| **DOCX** | OMML nativo | word/media/ | Mejor calidad de fórmulas |
| **PPTX** | OMML | ppt/media/ | |
| **HTML** | MathML, MathJax, KaTeX | `<img>` tags, base64 | |
| **EPUB** | MathML (vía HTML) | Imágenes del archivo | Internamente HTML + ZIP |
| **Jupyter** | LaTeX nativo, MathML | Outputs de celdas | Passthrough de LaTeX existente |
| **XLSX** | Regex básico | N/A | Fórmulas de celdas |
| **Imágenes** | OCR (opcional) | El propio fichero | PNG, JPEG |
| **Audio** | N/A | N/A | Vía MarkItDown base |
| **CSV/JSON/XML** | N/A | N/A | Vía MarkItDown base |
| **ZIP** | Recursivo | Recursivo | Vía MarkItDown base |

---

## Arquitectura

SciMarkdown usa una arquitectura de **pipeline de 3 fases con 3 capas de enriquecimiento**:

```
Documento original
       │
       ▼
┌─────────────────────────┐
│  Fase 1: Extracción     │  MarkItDown (sin modificar)
│  → Markdown base        │  super().convert()
└─────────┬───────────────┘
          ▼
┌─────────────────────────────────────────────────┐
│  Fase 2: Enriquecimiento                       │
│                                                 │
│  ┌───────────────────────────────────────┐      │
│  │ Capa 1: Heurísticas (OFFLINE)        │      │
│  │  MathDetector · ImageExtractor       │      │
│  │  ReferenceLinker · ImageCropper       │      │
│  └──────────────────┬────────────────────┘      │
│                     ▼                           │
│  ┌───────────────────────────────────────┐      │
│  │ Capa 2: Embeddings (ONLINE, opcional) │      │
│  │  MathClassifier · SemanticLinker     │      │
│  │  DocumentClassifier                   │      │
│  └──────────────────┬────────────────────┘      │
│                     ▼                           │
│  ┌───────────────────────────────────────┐      │
│  │ Capa 3: LLM Fallback (ONLINE, opc.)  │      │
│  │  OpenAI / Anthropic                   │      │
│  └───────────────────────────────────────┘      │
└─────────────────────┬───────────────────────────┘
                      ▼
┌─────────────────────────┐
│  Fase 3: Composición    │
│  → Markdown + LaTeX     │  MathFormatter · IndexBuilder
│  → Imágenes enlazadas   │
│  → Índice de figuras    │
└─────────────────────────┘
```

**Principio de diseño:** Cada capa refina el resultado de la anterior. Si una capa no está disponible (offline, sin API key, modelo no instalado), se salta y la siguiente trabaja con lo que hay.

### Estrategia de fork mínimo

- **0 líneas modificadas** en el código de MarkItDown
- `EnhancedMarkItDown` hereda de `MarkItDown` y override solo `convert_stream()` y `convert_local()`
- El 100% del código de enriquecimiento vive en `packages/scimarkdown/`
- Sincronización con upstream cada 14 días vía GitHub Actions

### Estructura del proyecto

```
mcp-sciMarkdown/
├── packages/
│   ├── markitdown/                ← Fork de Microsoft (sin cambios)
│   ├── markitdown-mcp/            ← Fork del MCP server original
│   └── scimarkdown/               ← Paquete de enriquecimiento
│       └── src/scimarkdown/
│           ├── math/
│           │   ├── detector.py        ← Detección heurística (Unicode, MathML, MathJax)
│           │   ├── formatter.py       ← Formato LaTeX ($...$ vs $`...`$)
│           │   └── ocr.py             ← Wrapper pix2tex / Nougat
│           ├── images/
│           │   ├── extractor.py       ← Extracción (PDF, DOCX, PPTX, HTML, EPUB, Jupyter)
│           │   ├── cropper.py         ← Recorte automático de bordes
│           │   ├── reference_linker.py← Vinculación "Figura X" → imagen
│           │   └── index_builder.py   ← Generación de índice de figuras
│           ├── embeddings/            ← NUEVO v2
│           │   ├── client.py          ← Cliente Gemini Embeddings API
│           │   ├── cache.py           ← Caché local de embeddings
│           │   ├── math_classifier.py ← Clasificación de fórmulas por embedding
│           │   ├── semantic_linker.py ← Vinculación imagen-texto semántica
│           │   ├── document_classifier.py ← Clasificación de tipo de documento
│           │   └── content_indexer.py ← Indexación y búsqueda semántica (RAG)
│           ├── pipeline/
│           │   ├── enrichment.py      ← Orquestador Fase 2 (3 capas)
│           │   └── composition.py     ← Orquestador Fase 3
│           ├── llm/
│           │   └── fallback.py        ← Cliente LLM (OpenAI/Anthropic)
│           ├── mcp/
│           │   ├── server.py          ← Servidor MCP con 12 tools
│           │   ├── serializers.py     ← Serialización de dataclasses a JSON
│           │   └── __main__.py        ← CLI del MCP
│           ├── sync/
│           │   └── upstream.py        ← Script de sincronización
│           ├── models/                ← Dataclasses (EnrichedResult, MathRegion, ImageRef...)
│           ├── config.py              ← Sistema de configuración YAML
│           ├── _enhanced_markitdown.py← Subclase principal
│           └── __main__.py            ← CLI de SciMarkdown
├── tests/                         ← 350 tests
│   ├── unit/
│   │   ├── math/                  ← Tests de detección y formato
│   │   ├── images/                ← Tests de extracción y vinculación
│   │   ├── pipeline/              ← Tests de orquestación
│   │   ├── mcp/                   ← Tests de herramientas MCP
│   │   └── embeddings/            ← Tests de embeddings (mocked)
│   ├── integration/               ← Tests de pipeline completo
│   ├── upstream/                  ← Tests de regresión del upstream
│   └── fixtures/                  ← Documentos de prueba
├── .github/workflows/
│   └── upstream-sync.yml          ← Sincronización automática cada 14 días
├── scimarkdown.yaml               ← Configuración por defecto
├── run-scimarkdown-mcp.sh         ← Launcher NixOS
└── docs/superpowers/
    ├── specs/                     ← Especificaciones de diseño
    └── plans/                     ← Planes de implementación
```

---

## Degradación elegante

SciMarkdown nunca falla en una conversión. Si el enriquecimiento falla, siempre devuelve el markdown base:

| Componente | Fallo | Comportamiento |
|------------|-------|----------------|
| MathDetector | Regex false positive | Marca con `<!-- sci:math:low-confidence -->` |
| MathOCR | Modelo no instalado | Usa solo heurísticas. Log warning. |
| MathClassifier | API Gemini caída | Salta clasificación, mantiene resultados heurísticos. |
| SemanticLinker | API Gemini caída | Salta linking semántico, usa ReferenceLinker ordinal. |
| ImageExtractor | No puede extraer | Skip imagen. Log warning. |
| LLM Fallback | API caída/timeout | Skip LLM. Continúa con resultados locales. |
| Pipeline completo | Excepción inesperada | Devuelve markdown base sin enriquecer. Log traceback. |

---

## Desarrollo

### Ejecutar tests

```bash
source .venv/bin/activate

# Todos los tests (350)
python -m pytest tests/ -v --ignore=tests/upstream

# Solo tests unitarios
python -m pytest tests/unit/ -v

# Por módulo
python -m pytest tests/unit/math/ -v
python -m pytest tests/unit/images/ -v
python -m pytest tests/unit/embeddings/ -v
python -m pytest tests/unit/mcp/ -v
python -m pytest tests/unit/pipeline/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Con cobertura
python -m pytest tests/ --cov=scimarkdown --cov-report=html --ignore=tests/upstream
```

### Umbrales de calidad

| Métrica | Umbral mínimo |
|---------|---------------|
| Fórmulas LaTeX correctas | >= 95% |
| Imágenes extraídas | >= 95% |
| Referencias vinculadas | >= 95% |
| Tests upstream Microsoft | 100% |
| Cobertura de código | >= 85% |

### Añadir soporte para un nuevo formato

1. Añadir método `extract_from_<formato>(stream)` en `images/extractor.py`
2. Añadir la extensión al mapping `_IMAGE_FORMATS` en `pipeline/enrichment.py`
3. Escribir tests en `tests/unit/images/`
4. Añadir test de integración en `tests/integration/`

---

## Sincronización con upstream

SciMarkdown se sincroniza con el repositorio original de Microsoft MarkItDown cada 14 días:

1. **Automático:** GitHub Actions ejecuta el script cada 1 y 15 de cada mes
2. Si no hay conflictos y los tests pasan → PR automática
3. Si hay conflictos → se crea un issue con los detalles

Para sincronizar manualmente:

```bash
python -m scimarkdown.sync.upstream --repo-dir .
```

---

## Versionado

```
SciMarkdown v{MAJOR}.{MINOR}.{PATCH}+mit{UPSTREAM_VERSION}

Ejemplo: scimarkdown 0.1.0+mit0.1.1
```

El sufijo `+mit` indica sobre qué versión de MarkItDown está construido.

---

## Costes estimados (embeddings)

| Operación | Coste/doc | 1000 docs/mes |
|-----------|-----------|---------------|
| Solo conversión offline | $0 | $0 |
| + Clasificación math (embeddings) | ~$0.002 | ~$2 |
| + Semantic linking (embeddings) | ~$0.005 | ~$5 |
| + Document classification | ~$0.001 | ~$1 |
| + Content indexing (RAG) | ~$0.01 | ~$10 |
| **Todo activado** | **~$0.018** | **~$18** |

---

## Licencia

Este proyecto es un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown), licenciado bajo MIT License.

---

## Créditos

- **[Microsoft MarkItDown](https://github.com/microsoft/markitdown)** — Proyecto base de conversión a Markdown
- **[Google Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)** — Análisis semántico multimodal
- **[pix2tex](https://github.com/lukas-blecher/LaTeX-OCR)** — OCR de fórmulas matemáticas (opcional)
- **[Nougat (Meta)](https://github.com/facebookresearch/nougat)** — OCR de papers académicos (opcional)
