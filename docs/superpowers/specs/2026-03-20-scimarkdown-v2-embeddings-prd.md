# SciMarkdown v2 — PRD con Gemini Embeddings

**Fecha:** 2026-03-20
**Estado:** Propuesta
**Versión anterior:** SciMarkdown v0.1.0 (heurístico + LLM fallback)

---

## 1. Pregunta estratégica: ¿Merece la pena mantener SciMarkdown?

### Qué hace SciMarkdown hoy (v0.1)

1. Convierte documentos (PDF, DOCX, PPTX, HTML, EPUB, Jupyter) a Markdown
2. Detecta fórmulas matemáticas por heurísticas (Unicode, MathML, regex) y las convierte a LaTeX
3. Extrae imágenes, las recorta y las guarda con naming convention
4. Vincula referencias textuales ("Figura 1") a imágenes por ordinal
5. Genera índice de figuras
6. LLM fallback opcional para fórmulas ambiguas
7. Todo esto via MCP server, CLI, o Python API

### Qué aportarían los Gemini Embeddings

Los embeddings NO reemplazan ninguna de estas funciones. **Los embeddings no convierten, no extraen, no formatean.** Lo que hacen es:

- **Clasificar** — ¿esto es una fórmula o texto normal?
- **Vincular** — ¿esta imagen corresponde a este párrafo?
- **Buscar** — ¿qué secciones del documento hablan de X?

### Veredicto

| | Sin embeddings | Con embeddings |
|---|---|---|
| **Conversión de formatos** | Funciona | Igual (embeddings no convierten) |
| **Detección de fórmulas** | Buena (heurísticas) | Excelente (clasificación semántica) |
| **Extracción de imágenes** | Funciona | Igual (embeddings no extraen bytes) |
| **Vinculación imagen-texto** | Frágil (solo "Figura X") | Robusta (similitud semántica) |
| **Funciona offline** | Sí | No (requiere API) |
| **Coste por documento** | 0 | ~$0.001-0.01 |
| **Latencia** | <5s | +2-5s por llamada API |

**Conclusión: SciMarkdown v0.1 es la base necesaria. Los embeddings son una capa de mejora, no un reemplazo.** Sin la conversión de formatos, extracción de imágenes, y formateo LaTeX, los embeddings no sirven de nada. Sin los embeddings, SciMarkdown funciona bien pero con limitaciones en detección y vinculación.

**Recomendación: mantener SciMarkdown como está + añadir capa de embeddings opcional.**

---

## 2. Arquitectura v2

```
Documento original
       │
       ▼
┌─────────────────────┐
│  Fase 1: Extracción │  MarkItDown (sin cambios)
└─────────┬───────────┘
          ▼
┌─────────────────────────────────────────┐
│  Fase 2: Enriquecimiento               │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ Capa 1: Heurísticas (OFFLINE)  │    │  ← v0.1 actual
│  │ • MathDetector (regex, Unicode) │    │
│  │ • ImageExtractor               │    │
│  │ • ReferenceLinker (ordinal)     │    │
│  └───────────────┬─────────────────┘    │
│                  ▼                      │
│  ┌─────────────────────────────────┐    │
│  │ Capa 2: Embeddings (ONLINE)    │    │  ← NUEVO v2
│  │ • MathClassifier (confirma/    │    │
│  │   descarta detecciones)         │    │
│  │ • SemanticLinker (vincula      │    │
│  │   imágenes por contenido)       │    │
│  │ • DocumentClassifier (optimiza │    │
│  │   pipeline según tipo)          │    │
│  └───────────────┬─────────────────┘    │
│                  ▼                      │
│  ┌─────────────────────────────────┐    │
│  │ Capa 3: LLM Fallback (ONLINE) │    │  ← v0.1 actual
│  │ • Fórmulas no reconocidas      │    │
│  └─────────────────────────────────┘    │
└─────────────────────┬───────────────────┘
                      ▼
┌─────────────────────────┐
│  Fase 3: Composición    │  (sin cambios)
└─────────────────────────┘
```

**Principio de diseño:** Cada capa refina el resultado de la anterior. Si una capa no está disponible (offline, sin API key), se salta y la siguiente trabaja con lo que hay.

---

## 3. Tools MCP — Catálogo completo v2

### 3.1 Tools existentes (v0.1, sin cambios)

#### `convert_to_markdown`

Conversión básica via MarkItDown original. Sin enriquecimiento.

```
Entrada:
  uri: string (requerido)        — "file:///path/to/doc.pdf" o URL

Salida:
  string                         — Markdown plano

Ejemplo de llamada:
  convert_to_markdown(uri="file:///home/user/paper.pdf")
```

#### `convert_to_scimarkdown`

Conversión enriquecida con LaTeX e imágenes. Pipeline completo.

```
Entrada:
  uri: string (requerido)        — "file:///path/to/doc.pdf" o URL
  config: dict (opcional)        — Overrides de scimarkdown.yaml

Salida:
  string                         — Markdown con $LaTeX$, enlaces a imágenes, índice

Ejemplo de llamada:
  convert_to_scimarkdown(
    uri="file:///home/user/paper.pdf",
    config={"latex": {"style": "github"}, "images": {"dpi": 150}}
  )
```

### 3.2 Tools granulares offline (v2 — subcomponentes expuestos)

Cada subcomponente del pipeline, accesible individualmente para control granular.

#### `detect_math`

Detecta fórmulas matemáticas en texto sin convertir el documento completo.

```
Entrada:
  text: string (requerido)       — Texto o HTML a analizar
  methods: list[string] (opc)    — ["unicode", "mathml", "mathjax", "latex"]
                                    (default: todos)

Salida:
  list[dict] con:
    original_text: string        — Texto original detectado
    latex: string                — Conversión a LaTeX
    source_type: string          — "unicode" | "mathml" | "mathjax" | "latex"
    confidence: float            — 0.0-1.0
    position: int                — Offset en el texto
    is_inline: bool              — Inline o block

Ejemplo:
  detect_math(text="Para todo x ∈ ℝ, ∑ᵢ xᵢ ≤ ∫ f(x)dx")
  → [{"latex": "x \\in \\mathbb{R}", "confidence": 0.85, ...}]
```

#### `format_latex`

Formatea fórmulas detectadas al estilo LaTeX deseado.

```
Entrada:
  formulas: list[dict] (req)     — Output de detect_math
  style: string (opcional)       — "standard" | "github" (default: "standard")

Salida:
  list[dict] con:
    original_text: string
    formatted: string            — "$x^{2}$" o "$`x^{2}`$"

Ejemplo:
  format_latex(
    formulas=[{"latex": "x^{2}", "is_inline": true}],
    style="github"
  )
  → [{"formatted": "$`x^{2}`$"}]
```

#### `extract_images`

Extrae imágenes de un documento sin hacer la conversión a markdown.

```
Entrada:
  uri: string (requerido)        — Documento fuente
  output_dir: string (opcional)  — Directorio de salida (default: junto al documento)
  dpi: int (opcional)            — Resolución rasterización (default: 300)
  autocrop: bool (opcional)      — Recortar bordes blancos (default: true)

Salida:
  list[dict] con:
    file_path: string            — Ruta de la imagen guardada
    width: int
    height: int
    position: int                — Posición ordinal en el documento
    original_format: string

Ejemplo:
  extract_images(uri="file:///paper.pdf", dpi=150)
  → [{"file_path": "paper_img00001.png", "width": 800, ...}]
```

#### `link_references`

Vincula referencias textuales ("Figura X") a imágenes extraídas.

```
Entrada:
  text: string (requerido)       — Texto del documento
  images: list[dict] (requerido) — Output de extract_images
  patterns: list[string] (opc)   — Regex patterns (default: config)

Salida:
  list[dict] con:
    file_path: string
    ordinal: int | null
    reference_label: string | null  — "Figura 1", "Table 2"...
    caption: string | null

Ejemplo:
  link_references(
    text="Como se ve en la Figura 1...",
    images=[{"file_path": "doc_img00001.png", "position": 0}]
  )
  → [{"file_path": "doc_img00001.png", "ordinal": 1, "reference_label": "Figura 1"}]
```

#### `build_figure_index`

Genera un índice de figuras en markdown.

```
Entrada:
  images: list[dict] (requerido) — Output de link_references o extract_images

Salida:
  string                         — Tabla markdown con índice de figuras

Ejemplo:
  build_figure_index(images=[...])
  → "## Figure Index\n| # | Figure | Description | File |\n..."
```

#### `ocr_formula`

Reconoce una fórmula en una imagen via pix2tex o Nougat (requiere [ocr]).

```
Entrada:
  image_path: string (requerido) — Ruta a imagen de fórmula
  engine: string (opcional)      — "auto" | "pix2tex" | "nougat" (default: "auto")

Salida:
  dict con:
    latex: string                — Fórmula reconocida
    confidence: float
    engine_used: string

Ejemplo:
  ocr_formula(image_path="/tmp/equation.png")
  → {"latex": "E = mc^{2}", "confidence": 0.92, "engine_used": "pix2tex"}
```

### 3.3 Tools online — embeddings (v2 — requieren API Gemini)

#### `convert_to_scimarkdown_embeddings`

Conversión con pipeline completo + embeddings para máxima calidad.

```
Entrada:
  uri: string (requerido)        — "file:///path/to/doc.pdf" o URL
  config: dict (opcional)        — Overrides de scimarkdown.yaml
  embedding_options: dict (opc)  — Opciones de embeddings

Salida:
  string                         — Markdown enriquecido con mayor precisión

Ejemplo de llamada:
  convert_to_scimarkdown_embeddings(
    uri="file:///home/user/paper.pdf",
    config={"latex": {"style": "standard"}},
    embedding_options={
      "classify_math": true,
      "semantic_linking": true,
      "classify_document": true
    }
  )
```

#### `analyze_document`

Clasifica un documento y devuelve metadatos semánticos sin convertir.

```
Entrada:
  uri: string (requerido)        — Documento a analizar
  analysis_type: string (opc)    — "full" | "structure" | "math" | "images"
                                    (default: "full")

Salida:
  dict con:
    document_type: string        — "academic_paper", "technical_report", "presentation"...
    language: string             — "es", "en", "fr"...
    math_density: float          — 0.0-1.0, proporción de contenido matemático
    image_count: int             — Imágenes detectadas
    sections: list[dict]         — Secciones con embeddings de resumen
    formula_regions: list[dict]  — Regiones de fórmulas con confianza

Ejemplo de llamada:
  analyze_document(
    uri="file:///home/user/paper.pdf",
    analysis_type="full"
  )

Ejemplo de respuesta:
  {
    "document_type": "academic_paper",
    "language": "en",
    "math_density": 0.35,
    "image_count": 8,
    "sections": [
      {"title": "Introduction", "topic": "quantum computing basics"},
      {"title": "Methods", "topic": "variational quantum eigensolver"}
    ],
    "formula_regions": [
      {"text": "H|ψ⟩ = E|ψ⟩", "confidence": 0.97, "type": "equation"}
    ]
  }
```

#### `search_content`

Búsqueda semántica dentro de un documento ya convertido.

```
Entrada:
  uri: string (requerido)        — Documento (se convierte si no está en caché)
  query: string (requerido)      — Consulta en lenguaje natural
  top_k: int (opcional)          — Número de resultados (default: 5)
  include_images: bool (opc)     — Buscar también en imágenes (default: true)

Salida:
  list[dict] con:
    content: string              — Fragmento de markdown relevante
    score: float                 — Similitud (0.0-1.0)
    position: int                — Posición en el documento
    type: string                 — "text" | "formula" | "image" | "table"

Ejemplo de llamada:
  search_content(
    uri="file:///home/user/paper.pdf",
    query="ecuación de Schrödinger",
    top_k=3
  )

Ejemplo de respuesta:
  [
    {"content": "$H|\\psi\\rangle = E|\\psi\\rangle$", "score": 0.94, "type": "formula"},
    {"content": "The time-independent Schrödinger equation...", "score": 0.87, "type": "text"},
    {"content": "![Fig 3](paper_img00003.png)", "score": 0.72, "type": "image"}
  ]
```

#### `compare_sections`

Compara semánticamente secciones de uno o más documentos.

```
Entrada:
  uris: list[string] (requerido) — 1 o más documentos
  granularity: string (opcional)  — "paragraph" | "section" | "page" (default: "section")

Salida:
  dict con:
    similarity_matrix: list[list[float]]  — Matriz de similitud entre secciones
    clusters: list[dict]                  — Agrupaciones temáticas
    unique_topics: list[string]           — Temas únicos encontrados

Ejemplo de llamada:
  compare_sections(
    uris=["file:///paper1.pdf", "file:///paper2.pdf"],
    granularity="section"
  )
```

### 3.4 Resumen de tools

#### Pipeline completo (conversión end-to-end)

| Tool | Online | Coste | Caso de uso |
|------|--------|-------|-------------|
| `convert_to_markdown` | No | 0 | Conversión básica MarkItDown |
| `convert_to_scimarkdown` | No* | 0* | Conversión con LaTeX e imágenes |
| `convert_to_scimarkdown_embeddings` | Sí | ~$0.01/doc | Máxima calidad (+ embeddings Gemini) |

#### Control granular (subcomponentes offline)

| Tool | Online | Coste | Caso de uso |
|------|--------|-------|-------------|
| `detect_math` | No | 0 | Detectar fórmulas en texto |
| `format_latex` | No | 0 | Formatear fórmulas a LaTeX |
| `extract_images` | No | 0 | Extraer imágenes de un documento |
| `link_references` | No | 0 | Vincular "Figura X" a imágenes |
| `build_figure_index` | No | 0 | Generar índice de figuras |
| `ocr_formula` | No | 0 | OCR de fórmula en imagen (pix2tex/Nougat) |

#### Análisis semántico (requieren API Gemini)

| Tool | Online | Coste | Caso de uso |
|------|--------|-------|-------------|
| `analyze_document` | Sí | ~$0.005/doc | Pre-análisis semántico |
| `search_content` | Sí | ~$0.002/query | Búsqueda semántica (RAG) |
| `compare_sections` | Sí | ~$0.01/doc | Comparar documentos |

**Total: 12 tools MCP** (3 pipeline + 6 granulares + 3 semánticas)

*Sin coste excepto si LLM fallback está activado.

---

## 4. Componentes nuevos del paquete

```
packages/scimarkdown/src/scimarkdown/
├── embeddings/                    ← NUEVO
│   ├── __init__.py
│   ├── client.py                  ← Cliente Gemini Embeddings API
│   ├── math_classifier.py         ← Clasificación de fórmulas por embedding
│   ├── semantic_linker.py         ← Vinculación imagen-texto semántica
│   ├── document_classifier.py     ← Clasificación de tipo de documento
│   ├── content_indexer.py         ← Indexación de secciones para búsqueda
│   └── cache.py                   ← Caché local de embeddings
```

### 4.1 `client.py` — Cliente Gemini Embeddings

```python
class GeminiEmbeddingClient:
    """Cliente para la API de Gemini Embeddings."""

    def __init__(self, api_key: str, model: str = "gemini-embedding-2-preview"):
        ...

    def embed_text(self, text: str, task_type: str = "SEMANTIC_SIMILARITY") -> list[float]:
        """Genera embedding de texto. Devuelve vector de dimensión configurable."""
        ...

    def embed_image(self, image: PIL.Image) -> list[float]:
        """Genera embedding de imagen (modelo multimodal)."""
        ...

    def embed_batch(self, items: list[str], task_type: str) -> list[list[float]]:
        """Genera embeddings en batch (más eficiente)."""
        ...

    def similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Similitud coseno entre dos vectores."""
        ...
```

### 4.2 `math_classifier.py` — Clasificación de fórmulas

Flujo: heurística detecta candidatos → embedding los clasifica → se eliminan falsos positivos.

```python
class MathClassifier:
    """Usa embeddings para confirmar/descartar detecciones heurísticas."""

    # Embeddings de referencia pre-calculados
    _MATH_REFERENCES = [
        "x^2 + y^2 = z^2",
        "\\int_0^\\infty e^{-x} dx = 1",
        "\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}",
        # ... 50+ fórmulas de referencia
    ]

    def classify(self, candidates: list[MathRegion]) -> list[MathRegion]:
        """Filtra candidatos: confirma fórmulas reales, descarta falsos positivos."""
        # 1. Genera embeddings de cada candidato (task_type=CLASSIFICATION)
        # 2. Compara con embeddings de referencia
        # 3. Si similitud > threshold → confirmar (confidence ↑)
        # 4. Si similitud < threshold → descartar o bajar confidence
        ...
```

### 4.3 `semantic_linker.py` — Vinculación semántica

El componente de mayor impacto. Vincula imágenes a texto por significado, no por "Figura X".

```python
class SemanticLinker:
    """Vincula imágenes a texto por similitud semántica multimodal."""

    def link(self, images: list[ImageRef], text_blocks: list[str]) -> list[ImageRef]:
        """
        1. Genera embedding de cada imagen (embed_image)
        2. Genera embedding de cada párrafo/sección (embed_text, task_type=SEMANTIC_SIMILARITY)
        3. Calcula matriz de similitud imagen×texto
        4. Asigna cada imagen al bloque de texto más similar
        5. Genera caption automático si no existe
        """
        ...
```

### 4.4 `document_classifier.py` — Clasificación de documento

```python
class DocumentClassifier:
    """Clasifica el tipo de documento para optimizar el pipeline."""

    CATEGORIES = [
        "academic_paper",        # → Nougat + detección agresiva de fórmulas
        "technical_report",      # → Priorizar tablas y diagramas
        "presentation",          # → Priorizar imágenes
        "textbook",              # → Fórmulas + definiciones
        "code_documentation",    # → Priorizar bloques de código
        "general_document",      # → Pipeline estándar
    ]

    def classify(self, text: str) -> tuple[str, float]:
        """Devuelve (categoría, confianza)."""
        # task_type=CLASSIFICATION
        ...

    def optimize_config(self, category: str, config: SciMarkdownConfig) -> SciMarkdownConfig:
        """Ajusta la configuración según el tipo de documento."""
        ...
```

### 4.5 `content_indexer.py` — Indexación para búsqueda

```python
class ContentIndexer:
    """Indexa contenido convertido para búsqueda semántica."""

    def index(self, markdown: str, images: list[ImageRef]) -> "ContentIndex":
        """
        1. Divide markdown en chunks (por sección/párrafo)
        2. Genera embeddings de cada chunk (task_type=RETRIEVAL_DOCUMENT)
        3. Genera embeddings de cada imagen
        4. Almacena en índice local
        """
        ...

    def search(self, index: "ContentIndex", query: str, top_k: int = 5) -> list[dict]:
        """
        1. Genera embedding de la query (task_type=RETRIEVAL_QUERY)
        2. Busca los chunks más similares
        3. Devuelve fragmentos ordenados por relevancia
        """
        ...
```

### 4.6 `cache.py` — Caché de embeddings

```python
class EmbeddingCache:
    """Caché local para evitar llamadas redundantes a la API."""

    def __init__(self, cache_dir: Path = Path(".scimarkdown_cache")):
        ...

    def get(self, content_hash: str) -> Optional[list[float]]:
        ...

    def put(self, content_hash: str, embedding: list[float]) -> None:
        ...
```

---

## 5. Configuración v2

Extensión de `scimarkdown.yaml`:

```yaml
# === Sección nueva: Embeddings ===
embeddings:
  enabled: false                    # Activar capa de embeddings
  provider: "gemini"                # Por ahora solo Gemini
  model: "gemini-embedding-2-preview"
  api_key_env: "GEMINI_API_KEY"     # Variable de entorno
  dimensions: 768                   # 128-3072 (768 = buen balance)

  # Funcionalidades individuales
  classify_math: true               # Confirmar/descartar fórmulas
  semantic_linking: true            # Vincular imágenes por contenido
  classify_document: true           # Clasificar tipo de documento
  content_indexing: false           # Indexar para búsqueda (más costoso)

  # Caché
  cache_enabled: true
  cache_dir: ".scimarkdown_cache"
  cache_ttl_days: 30

  # Umbrales
  math_similarity_threshold: 0.75   # Mínimo para confirmar fórmula
  image_link_threshold: 0.60        # Mínimo para vincular imagen-texto

  # Límites
  max_embeddings_per_document: 500  # Control de costes
  batch_size: 100                   # Embeddings por request
```

---

## 6. Ventajas e inconvenientes

### Mantener v0.1 como está (sin embeddings)

| Ventaja | Inconveniente |
|---------|---------------|
| Funciona 100% offline | Detección de fórmulas limitada a patrones |
| Coste cero | Vinculación imagen-texto solo por "Figura X" |
| Latencia baja (<5s) | No puede clasificar tipo de documento |
| Sin dependencias externas | No ofrece búsqueda semántica |
| Privacidad total (datos no salen) | Falsos positivos en detección de fórmulas |
| Simple de mantener | No puede vincular imágenes sin referencia explícita |

### Añadir embeddings (v2)

| Ventaja | Inconveniente |
|---------|---------------|
| Detección de fórmulas ~95%→99% | Requiere API key (Gemini) |
| Vinculación semántica de imágenes | Coste por documento (~$0.01) |
| Clasificación automática de documentos | Latencia extra (+2-5s) |
| Búsqueda semántica en output | Datos enviados a Google |
| Pre-filtro inteligente para OCR | Complejidad del código aumenta |
| Captions automáticos de imágenes | Dependencia de servicio externo |
| Comparación entre documentos | Caché necesaria para eficiencia |

### Mantener ambos (recomendado)

| Escenario | Qué se usa |
|-----------|------------|
| Laptop sin internet | v0.1 (heurísticas offline) |
| Servidor con API key | v2 (heurísticas + embeddings) |
| Documento confidencial | v0.1 (datos no salen del equipo) |
| Paper científico complejo | v2 (máxima calidad) |
| Procesamiento batch de 1000 docs | v0.1 (coste cero) |
| Documento con imágenes sin "Figura X" | v2 (vinculación semántica) |

---

## 7. Flujo de decisión del pipeline

```
¿embeddings.enabled?
    │
    ├── NO → Pipeline v0.1 completo (offline)
    │        convert_to_scimarkdown()
    │
    └── SÍ → ¿classify_document?
              │
              ├── SÍ → DocumentClassifier → optimiza config
              │
              └── Pipeline v0.1 (heurísticas)
                    │
                    ▼
                  ¿classify_math?
                    │
                    ├── SÍ → MathClassifier confirma/descarta candidatos
                    │
                    └── ¿semantic_linking?
                          │
                          ├── SÍ → SemanticLinker vincula imágenes
                          │        (reemplaza o complementa ReferenceLinker)
                          │
                          └── ¿content_indexing?
                                │
                                ├── SÍ → ContentIndexer genera índice
                                │
                                └── Composición final (Fase 3)
```

---

## 8. Roadmap de implementación

| Fase | Qué | Dependencias | Esfuerzo |
|------|-----|-------------|----------|
| **v0.1** (HECHO) | Pipeline heurístico completo | Ninguna | Completado |
| **v2.0** | Cliente Gemini + caché | API key Gemini | 2 tareas |
| **v2.1** | MathClassifier | v2.0 | 2 tareas |
| **v2.2** | SemanticLinker | v2.0 | 3 tareas |
| **v2.3** | DocumentClassifier | v2.0 | 2 tareas |
| **v2.4** | ContentIndexer + search_content tool | v2.0 | 3 tareas |
| **v2.5** | analyze_document + compare_sections tools | v2.4 | 2 tareas |
| **v2.6** | convert_to_scimarkdown_embeddings tool | v2.1-v2.3 | 1 tarea |

**Estimación total: ~15 tareas adicionales sobre v0.1.**

---

## 9. Costes estimados

Basado en precios de Gemini API (marzo 2026):

| Operación | Embeddings/doc | Coste/doc | 1000 docs/mes |
|-----------|---------------|-----------|---------------|
| Solo conversión (v0.1) | 0 | $0 | $0 |
| + Clasificación math | ~20 | ~$0.002 | ~$2 |
| + Semantic linking | ~50 | ~$0.005 | ~$5 |
| + Document classification | ~5 | ~$0.001 | ~$1 |
| + Content indexing | ~100 | ~$0.01 | ~$10 |
| **Todo activado** | **~175** | **~$0.018** | **~$18** |

---

## 10. Conclusión

**¿Merece la pena mantener SciMarkdown?** Absolutamente sí. Los embeddings son un potenciador, no un sustituto. La conversión de formatos, extracción de imágenes, y formateo LaTeX son trabajo que los embeddings no pueden hacer.

**¿Merece la pena añadir embeddings?** Sí, como capa opcional. El mayor impacto está en:
1. **SemanticLinker** — elimina la dependencia frágil de "Figura X"
2. **MathClassifier** — reduce falsos positivos del detector heurístico
3. **search_content** — habilita RAG sobre documentos convertidos

**Modelo de negocio:** SciMarkdown offline es gratuito y útil. SciMarkdown con embeddings es premium y excelente. Ambos coexisten.
