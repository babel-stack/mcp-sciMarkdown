# SciMarkdown

<p align="center">
  <strong>Conversor de documentos a Markdown con detección de fórmulas LaTeX, extracción intelixente de imaxes, filtrado de ruído e análise semántica con Gemini Embeddings.</strong>
</p>

<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Flag_of_Galicia.svg/20px-Flag_of_Galicia.svg.png" width="16" alt="Galicia"> <strong>Galego</strong> ·
  <a href="README.es.md">🇪🇸 Español</a> ·
  <a href="README.en.md">🇬🇧 English</a> ·
  <a href="README.bs.md">🇧🇦 Bosanski</a>
</p>

---

SciMarkdown é un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown) que amplía as súas capacidades de conversión con catro piares:

1. **Detección de fórmulas matemáticas e embebido LaTeX** en todos os formatos soportados
2. **Extracción, recorte e referenciado de imaxes** con vinculación de referencias textuais e índice de figuras
3. **Filtrado de ruído** — elimina cabeceiras, pés de páxina, números de páxina e imaxes decorativas; converte índices en hiperenlaces
4. **Análise semántica con Gemini Embeddings** (opcional) — clasificación de fórmulas, vinculación imaxe-texto por significado, clasificación de documentos e busca semántica (RAG)

---

## Características

### Detección de fórmulas matemáticas

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

**Saída (estilo GitHub):**
```markdown
Para todo $`x \in \mathbb{R}`$, a suma $`\sum_{i} x_{i} \leq \int f(x)dx`$ cúmprese.
```

### Extracción intelixente de imaxes

- Extrae imaxes embebidas de PDF, DOCX, PPTX, HTML, EPUB e Jupyter Notebooks
- Recorte automático de bordos brancos con marxes configurables
- As imaxes insértanse **na posición orixinal** do documento, ancoradas ao texto que as precede
- **Convención de nomes:** `{documento}_img{00001}.png` (5 díxitos)

### Filtrado de ruído

- **Texto repetido** — detecta cabeceiras/pés que se repiten na mesma posición en 3+ páxinas
- **Números de páxina** — detecta secuencias numéricas en bloques fronteira
- **Imaxes decorativas** — filtra imaxes pequenas (<30px), moi estreitas (ratio >8:1) ou repetidas
- **Índices (TOC)** — detecta táboas de contidos e convérteas en hiperenlaces markdown

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

### Servidor MCP con 12 ferramentas

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

# Instalar SciMarkdown (heurísticas, sen GPU, sen PyTorch)
pip install -e packages/scimarkdown
```

### Dependencias opcionais

```bash
# OCR de fórmulas con pix2tex (~500MB + PyTorch)
pip install -e "packages/scimarkdown[ocr]"

# OCR completo de artigos con Nougat (~3GB + PyTorch)
pip install -e "packages/scimarkdown[nougat]"

# LLM fallback (OpenAI/Anthropic)
pip install -e "packages/scimarkdown[llm]"

# Gemini Embeddings (análise semántica)
pip install -e "packages/scimarkdown[embeddings]"

# Todo
pip install -e "packages/scimarkdown[all]"
```

### Paso 4: Instalar MCP SDK (para o servidor MCP)

```bash
pip install "mcp[cli]>=1.0.0"
```

### Variables de entorno

| Variable | Necesaria para | Exemplo |
|----------|---------------|---------|
| `GEMINI_API_KEY` | Ferramentas de embeddings | `export GEMINI_API_KEY=AIza...` |
| `LLM_API_KEY` | LLM fallback | `export LLM_API_KEY=sk-...` |

### NixOS

```bash
# Atopar libstdc++
find /nix/store -name "libstdc++.so.6" 2>/dev/null | head -1

# Exportar (engadir a .bashrc/.zshrc)
export LD_LIBRARY_PATH=/nix/store/<hash>-gcc-<version>-lib/lib

# Se numpy 2.x falla con "X86_V2" en CPUs antigas:
pip install "numpy<2.0"
```

Inclúese un script lanzador compatible con NixOS: `run-scimarkdown-mcp.sh`

---

## Uso

### CLI

```bash
# Conversión básica (stdout)
scimarkdown document.pdf

# Saída a ficheiro
scimarkdown document.pdf -o document.md

# LaTeX estilo GitHub
scimarkdown paper.pdf --latex-style github

# Directorio de saída de imaxes personalizado
scimarkdown paper.pdf --output-dir ./images/

# Ficheiro de configuración personalizado
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

#### Uso directo de subcompoñentes

```python
# Detectar fórmulas en texto
from scimarkdown.math.detector import MathDetector
detector = MathDetector()
regions = detector.detect("The equation x² + y² = z² is famous.")
for r in regions:
    print(f"{r.original_text} → ${r.latex}$ (confianza: {r.confidence})")

# Extraer imaxes dun PDF
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
linked = linker.link("Como se mostra na Figura 1...", images)
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

# Vinculación semántica imaxe-texto (sen necesidade de "Figura X")
linker = SemanticLinker(client, threshold=0.60)
linked = linker.link(images, paragraphs)

# Busca semántica (RAG)
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

Engadir a `claude_desktop_config.json`:

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

NixOS — usar o lanzador incluído:

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
# Nivel usuario (dispoñible en todos os proxectos)
claude mcp add --scope user scimarkdown /path/to/mcp-sciMarkdown/run-scimarkdown-mcp.sh

# Nivel proxecto
claude mcp add scimarkdown scimarkdown-mcp
```

---

## Ferramentas MCP — Referencia completa

### Ferramentas de pipeline (conversión de extremo a extremo)

#### `convert_to_markdown`

Conversión básica vía MarkItDown. Sen enriquecemento.

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `uri` | string | Si | Ruta de ficheiro ou URL |

Devolve: `string` — Markdown simple

---

#### `convert_to_scimarkdown`

Conversión enriquecida con LaTeX, imaxes, filtrado de ruído e hiperenlaces TOC. Totalmente offline.

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `uri` | string | Si | Ruta de ficheiro ou URL |
| `config` | dict | Non | Sobreescribir `scimarkdown.yaml` |

Devolve: `string` — Markdown enriquecido

Exemplo de config:
```json
{"latex": {"style": "github"}, "images": {"dpi": 150}, "filters": {"enabled": true}}
```

---

#### `convert_to_scimarkdown_embeddings`

Conversión de máxima calidade con Gemini Embeddings. Require `GEMINI_API_KEY`.

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `uri` | string | Si | Ruta de ficheiro ou URL |
| `config` | dict | Non | Sobreescrituras de config |
| `embedding_options` | dict | Non | `classify_math`, `semantic_linking`, `classify_document` (bool) |

Devolve: `string` — Markdown enriquecido de máxima calidade

---

### Ferramentas granulares (offline, combinables)

Estas ferramentas pódense encadear: `detect_math` → `format_latex`, ou `extract_images` → `link_references` → `build_figure_index`.

#### `detect_math`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `text` | string | Si | Texto ou HTML a analizar |
| `methods` | list[string] | Non | `"unicode"`, `"mathml"`, `"mathjax"`, `"latex"` |

Devolve: `JSON string` — Array de `{original_text, latex, source_type, confidence, position, is_inline}`

#### `format_latex`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `formulas` | string (JSON) | Si | Saída de `detect_math` |
| `style` | string | Non | `"standard"` ou `"github"` |

Devolve: `JSON string` — Array de `{original_text, formatted}`

**Exemplo de encadeamento:**
```
1. detect_math(text="x² + y² = z²")  →  [{"latex": "x^{2}+y^{2}=z^{2}", ...}]
2. format_latex(formulas=↑, style="github")  →  [{"formatted": "$`x^{2}+y^{2}=z^{2}`$"}]
```

#### `extract_images`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `uri` | string | Si | Ruta do documento |
| `output_dir` | string | Non | Directorio de saída (por defecto: xunto ao documento) |
| `dpi` | int | Non | Resolución de rasterización (por defecto: 300) |
| `autocrop` | bool | Non | Recortar bordos brancos (por defecto: true) |

Devolve: `JSON string` — Array de `{file_path, width, height, position, original_format, context_text}`

Formatos soportados: PDF, DOCX, PPTX, HTML, EPUB, Jupyter Notebook.

#### `link_references`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `text` | string | Si | Texto do documento |
| `images` | string (JSON) | Si | Saída de `extract_images` |
| `patterns` | list[string] | Non | Patróns regex personalizados |

Devolve: `JSON string` — Array con `ordinal` e `reference_label` cubertos

#### `build_figure_index`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `images` | string (JSON) | Si | Saída de `link_references` |

Devolve: `string` — Táboa de índice de figuras en Markdown

**Exemplo completo de pipeline de imaxes:**
```
1. extract_images(uri="paper.pdf")          → imaxes extraídas
2. link_references(text=..., images=↑)      → imaxes con referencias
3. build_figure_index(images=↑)             → táboa markdown
```

#### `ocr_formula`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `image_path` | string | Si | Ruta á imaxe da fórmula |
| `engine` | string | Non | `"auto"`, `"pix2tex"`, `"nougat"` |

Devolve: `JSON string` — `{latex, confidence, engine_used}` ou `{error}`

---

### Ferramentas de embeddings (requiren `GEMINI_API_KEY`)

#### `analyze_document`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `uri` | string | Si | Ruta do documento |
| `analysis_type` | string | Non | `"full"`, `"structure"`, `"math"`, `"images"` |

Devolve: `JSON string` — `{document_type, math_density, math_count, word_count, formula_regions, classification_confidence}`

Tipos de documento: `academic_paper`, `technical_report`, `presentation`, `textbook`, `code_documentation`, `general_document`

#### `search_content`

Busca semántica dentro dun documento (RAG).

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `uri` | string | Si | Ruta do documento |
| `query` | string | Si | Consulta en linguaxe natural |
| `top_k` | int | Non | Número de resultados (por defecto: 5) |

Devolve: `JSON string` — Array de `{content, score, position, type}`

Exemplo:
```
search_content(uri="paper.pdf", query="ecuación de Schrödinger", top_k=3)
→ [
    {"content": "$H|\\psi\\rangle = E|\\psi\\rangle$", "score": 0.94, "type": "formula"},
    {"content": "A ecuación de Schrödinger independente do tempo...", "score": 0.87, "type": "text"}
  ]
```

#### `compare_sections`

| Parámetro | Tipo | Requirido | Descrición |
|-----------|------|-----------|------------|
| `uris` | string (JSON) | Si | Array de rutas de documentos |
| `granularity` | string | Non | `"paragraph"`, `"section"`, `"page"` |

Devolve: `JSON string` — `{document_count, total_sections, unique_topics}`

---

## Configuración

SciMarkdown busca `scimarkdown.yaml` no directorio actual. Todas as opcións teñen valores por defecto razoables.

```yaml
# ── Formato LaTeX ───────────────────────────────────────────
latex:
  style: "standard"              # "standard" ($...$) ou "github" ($`...`$)

# ── Imaxes ─────────────────────────────────────────────────
images:
  output_dir: "same"              # "same" = xunto ao documento fonte
  format: "png"
  dpi: 300
  margin_px: 10
  counter_digits: 5               # img00001
  autocrop_whitespace: true

# ── Detección de fórmulas ──────────────────────────────────
math:
  heuristic: true
  ocr_engine: "auto"              # "pix2tex", "nougat" ou "auto"
  confidence_threshold: 0.75

# ── LLM Fallback ──────────────────────────────────────────
llm:
  enabled: false
  provider: "openai"              # "openai" ou "anthropic"
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

# ── Filtros de ruído ─────────────────────────────────────
filters:
  enabled: true
  repeated_text: true             # Eliminar cabeceiras/pés repetidos
  page_numbers: true              # Eliminar números de páxina secuenciais
  decorative_images: true         # Eliminar imaxes pequenas/estreitas/repetidas
  min_repeat_pages: 3             # Páxinas que debe repetirse o texto para ser ruído
  max_header_length: 100          # Máx. caracteres para candidato a cabeceira
  min_image_size: 30              # Mín. px para conservar unha imaxe
  max_image_aspect_ratio: 8.0     # Ratio máximo antes de marcar como decorativa

# ── Referencias ─────────────────────────────────────────────
references:
  patterns:
    - 'Fig(?:ura|ure|\.)\s*(\d+)'
    - 'Tab(?:la|le|\.)\s*(\d+)'
    - 'Im(?:agen|age|g\.?)\s*(\d+)'
  languages: ["es", "en"]
  generate_index: true

# ── Rendemento ────────────────────────────────────────────
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

| Formato | Fórmulas | Imaxes | Filtro de ruído | Notas |
|---------|----------|--------|-----------------|-------|
| **PDF** | Unicode, OCR | Embebidas + vector | Cabeceiras, pés, números de páxina, TOC | Soporte completo |
| **DOCX** | OMML nativo | word/media/ | — | Mellor calidade de fórmulas |
| **PPTX** | OMML | ppt/media/ | — | |
| **HTML** | MathML, MathJax, KaTeX | `<img>`, base64 | — | |
| **EPUB** | MathML (vía HTML) | Imaxes do arquivo | — | Internamente HTML + ZIP |
| **Jupyter** | LaTeX nativo, MathML | Saídas de celdas | — | Paso directo de LaTeX |
| **XLSX** | Regex básico | — | — | Fórmulas de celdas |
| **Imaxes** | OCR (opcional) | O propio ficheiro | — | PNG, JPEG |
| **Audio** | — | — | — | Vía MarkItDown base |
| **CSV/JSON/XML** | — | — | — | Vía MarkItDown base |

---

## Arquitectura

```
Documento fonte
       │
       ▼
┌─────────────────────────┐
│  Fase 1: Extracción     │  MarkItDown (sen modificar)
│  → Markdown base        │  super().convert()
└─────────┬───────────────┘
          ▼
┌─────────────────────────────────────────────────┐
│  Fase 2: Enriquecemento                         │
│                                                  │
│  ┌────────────────────────────────────────┐      │
│  │ Capa 1: Heurísticas (OFFLINE)         │      │
│  │  MathDetector · ImageExtractor        │      │
│  │  ReferenceLinker · ImageCropper        │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Filtros de ruído (OFFLINE)            │      │
│  │  RepeatedText · PageNumbers           │      │
│  │  DecorativeImages · TocProcessor      │      │
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
│  → Imaxes inline        │  Posicionamento ancorado ao contexto
│  → Índice de figuras    │
│  → Hiperenlaces TOC     │
└─────────────────────────┘
```

### Estratexia de fork mínimo

- **0 liñas modificadas** no código fonte de MarkItDown
- `EnhancedMarkItDown` herda de `MarkItDown`, sobreescribe só `convert_stream()` e `convert_local()`
- O 100% do código de enriquecemento vive en `packages/scimarkdown/`
- Sincronización upstream cada 14 días vía GitHub Actions

---

## Degradación graceful

SciMarkdown nunca falla nunha conversión. Se o enriquecemento falla, sempre devolve o markdown base:

| Compoñente | Fallo | Comportamento |
|------------|-------|---------------|
| MathDetector | Falso positivo de regex | Marca con `<!-- sci:math:low-confidence -->` |
| MathOCR | Modelo non instalado | Usa só heurísticas |
| MathClassifier | API Gemini caída | Omite clasificación, mantén resultados heurísticos |
| SemanticLinker | API Gemini caída | Omite vinculación semántica, usa ReferenceLinker ordinal |
| NoiseFilter | Fallo ao parsear PDF | Omite filtrado, mantén todo o contido |
| TocProcessor | Non se detecta TOC | Sen cambios |
| ImageExtractor | Non se pode extraer | Omite imaxe, rexistra aviso |
| LLM Fallback | API caída/timeout | Omite LLM, continúa con resultados locais |
| Pipeline completo | Excepción inesperada | Devolve markdown base sen cambios |

---

## Desenvolvemento

### Executar tests

```bash
source .venv/bin/activate

# Todos os tests (409)
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

### Umbrais de calidade

| Métrica | Mínimo |
|---------|--------|
| Fórmulas LaTeX correctas | >= 95% |
| Imaxes extraídas | >= 95% |
| Referencias vinculadas | >= 95% |
| Tests Microsoft upstream | 100% |
| Cobertura de código | >= 85% |

---

## Sincronización upstream

SciMarkdown sincroniza con Microsoft MarkItDown cada 14 días:

1. GitHub Actions execútase os días 1 e 15 de cada mes
2. Sen conflitos + tests pasan → PR automático
3. Con conflitos → créase un issue con detalles

Sincronización manual:
```bash
python -m scimarkdown.sync.upstream --repo-dir .
```

---

## Versionado

```
SciMarkdown v{MAJOR}.{MINOR}.{PATCH}+mit{UPSTREAM_VERSION}
Exemplo: scimarkdown 0.1.0+mit0.1.1
```

---

## Custos de embeddings

| Operación | Custo/doc | 1000 docs/mes |
|-----------|-----------|---------------|
| Só conversión offline | $0 | $0 |
| + Clasificación matemática | ~$0.002 | ~$2 |
| + Vinculación semántica | ~$0.005 | ~$5 |
| + Clasificación de documento | ~$0.001 | ~$1 |
| + Indexación de contido (RAG) | ~$0.01 | ~$10 |
| **Todo activado** | **~$0.018** | **~$18** |

---

## Licenza

Este proxecto é un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown), licenciado baixo MIT License.

## Créditos

- **[Microsoft MarkItDown](https://github.com/microsoft/markitdown)** — Conversión base a Markdown
- **[Google Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)** — Análise semántica multimodal
- **[pix2tex](https://github.com/lukas-blecher/LaTeX-OCR)** — OCR de fórmulas (opcional)
- **[Nougat (Meta)](https://github.com/facebookresearch/nougat)** — OCR de artigos académicos (opcional)
