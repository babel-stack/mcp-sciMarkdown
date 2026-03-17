# SciMarkdown

**Conversor de documentos a Markdown con detección de fórmulas LaTeX y extracción inteligente de imágenes.**

SciMarkdown es un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown) que amplía sus capacidades de conversión con dos funcionalidades clave:

1. **Detección de fórmulas matemáticas y embebido LaTeX** en todos los formatos soportados (PDF, DOCX, PPTX, HTML, EPUB, imágenes, Jupyter Notebooks, XLSX)
2. **Extracción, recorte y referenciado de imágenes** con conciencia posicional, vinculación de referencias textuales e índice de figuras

---

## Características

### Detección de fórmulas matemáticas

SciMarkdown detecta y convierte fórmulas matemáticas a LaTeX de forma automática usando múltiples estrategias:

| Método | Formatos | Calidad |
|--------|----------|---------|
| **OMML nativo** | DOCX, PPTX | Excelente |
| **MathML** | HTML, EPUB | Muy buena |
| **MathJax/KaTeX** | HTML | Muy buena |
| **Símbolos Unicode** | Todos (∑, ∫, ≤, ∈, ℝ...) | Buena |
| **OCR de fórmulas** (opcional) | PDF escaneados, imágenes | Muy buena |
| **LLM fallback** (opcional) | Cualquier formato | Muy buena |

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
| 1 | Figura 1 | Diagrama de arquitectura | [img00001](doc_img00001.png) |
| 2 | Figura 2 | Resultados experimentales | [img00002](doc_img00002.png) |
```

### Servidor MCP (Model Context Protocol)

SciMarkdown incluye un servidor MCP que expone dos herramientas:

| Herramienta | Descripción |
|-------------|-------------|
| `convert_to_markdown` | Conversión original de MarkItDown (compatibilidad) |
| `convert_to_scimarkdown` | Conversión enriquecida con fórmulas LaTeX e imágenes |

---

## Instalación

### Requisitos previos

- Python >= 3.10
- Git

### Instalación básica (heurísticas, sin GPU ni PyTorch)

```bash
git clone https://github.com/<tu-usuario>/scimarkdown.git
cd scimarkdown

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# Instalar MarkItDown (fork local)
pip install -e packages/markitdown[all]

# Instalar SciMarkdown
pip install -e packages/scimarkdown
```

### Instalación con OCR de fórmulas (requiere PyTorch)

```bash
# Con pix2tex (~500MB + PyTorch) para fórmulas aisladas
pip install -e "packages/scimarkdown[ocr]"

# Con Nougat (~3GB + PyTorch) para papers académicos completos
pip install -e "packages/scimarkdown[nougat]"
```

### Instalación con LLM fallback

```bash
# Para usar OpenAI o Anthropic como fallback
pip install -e "packages/scimarkdown[llm]"
```

### Instalación completa

```bash
pip install -e "packages/scimarkdown[all]"
```

### NixOS

En NixOS, numpy puede necesitar `libstdc++` del nix store. Localiza la librería y expórtala:

```bash
# Encontrar libstdc++
find /nix/store -name "libstdc++.so.6" 2>/dev/null | head -1

# Exportar antes de usar
export LD_LIBRARY_PATH=/nix/store/<hash>-gcc-<version>-lib/lib

# Si numpy 2.x falla con "X86_V2", instalar numpy 1.x:
pip install "numpy<2.0"
```

---

## Uso

### CLI

```bash
# Conversión básica (salida a stdout)
scimarkdown documento.pdf

# Especificar fichero de salida
scimarkdown documento.pdf -o documento.md

# Estilo LaTeX GitHub
scimarkdown paper.pdf --latex-style github

# Directorio personalizado para imágenes
scimarkdown paper.pdf --output-dir ./imagenes/

# Fichero de configuración personalizado
scimarkdown paper.pdf -c mi_config.yaml
```

### Python API

```python
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig

# Configuración por defecto
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

### Servidor MCP

#### Modo STDIO (para integración con Claude, Cursor, etc.)

```bash
scimarkdown-mcp
```

#### Modo HTTP (para integración web)

```bash
scimarkdown-mcp --http --port 3001
```

#### Configuración en Claude Desktop

Añade esto a tu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scimarkdown": {
      "command": "scimarkdown-mcp",
      "args": []
    }
  }
}
```

En NixOS, usa un wrapper:

```json
{
  "mcpServers": {
    "scimarkdown": {
      "command": "/bin/sh",
      "args": ["-c", "LD_LIBRARY_PATH=/nix/store/<hash>-gcc-<version>-lib/lib scimarkdown-mcp"]
    }
  }
}
```

#### Configuración en Claude Code

```bash
claude mcp add scimarkdown scimarkdown-mcp
```

#### Herramientas MCP disponibles

**`convert_to_markdown(uri)`**

Conversión estándar de MarkItDown (sin enriquecimiento). Compatibilidad total con el MCP original.

```
uri: "file:///ruta/al/documento.pdf"
```

**`convert_to_scimarkdown(uri, config?)`**

Conversión enriquecida con detección de fórmulas LaTeX y extracción de imágenes.

```
uri: "file:///ruta/al/paper.pdf"
config: {"latex": {"style": "github"}, "images": {"dpi": 150}}
```

Parámetros de `config` opcionales (sobrescriben `scimarkdown.yaml`):

| Sección | Clave | Valores | Defecto |
|---------|-------|---------|---------|
| `latex.style` | Estilo LaTeX | `"standard"`, `"github"` | `"standard"` |
| `images.dpi` | Resolución rasterización | Entero | `300` |
| `images.output_dir` | Directorio de imágenes | Ruta o `"same"` | `"same"` |
| `math.heuristic` | Detección heurística | `true`, `false` | `true` |
| `math.ocr_engine` | Motor OCR | `"auto"`, `"pix2tex"`, `"nougat"` | `"auto"` |
| `references.generate_index` | Índice de figuras | `true`, `false` | `true` |

---

## Configuración

SciMarkdown busca un fichero `scimarkdown.yaml` en el directorio actual. Todas las opciones tienen valores por defecto sensatos.

```yaml
# Formato LaTeX
latex:
  style: "standard"          # "standard" ($...$) o "github" ($`...`$)

# Imágenes
images:
  output_dir: "same"          # "same" = junto al documento original
  format: "png"               # formato de rasterización
  dpi: 300                    # resolución para gráficos vectoriales
  margin_px: 10               # margen al recortar regiones
  counter_digits: 5           # dígitos del contador (img00001)
  autocrop_whitespace: true   # recortar bordes blancos

# Detección de fórmulas
math:
  heuristic: true             # detección por regex/Unicode
  ocr_engine: "auto"          # "pix2tex", "nougat" o "auto"
  nougat_model: "0.1.0-base"  # modelo de Nougat
  confidence_threshold: 0.75  # umbral para aceptar OCR sin LLM

# LLM Fallback (desactivado por defecto)
llm:
  enabled: false
  provider: "openai"          # "openai" o "anthropic"
  model: "gpt-4o"
  api_key_env: "LLM_API_KEY"  # variable de entorno con la API key

# Referencias
references:
  patterns:                   # patrones regex para detectar referencias
    - 'Fig(?:ura|ure|\.)\s*(\d+)'
    - 'Tab(?:la|le|\.)\s*(\d+)'
    - 'Gr[aA]f(?:ico|h)\s*(\d+)'
    - 'Im(?:agen|age|g\.?)\s*(\d+)'
    - 'Chart\s*(\d+)'
  languages: ["es", "en"]
  generate_index: true        # generar índice de figuras al final

# Rendimiento
performance:
  total_timeout_seconds: 1800 # 30 min máximo por conversión
  max_images: 10000
  max_image_file_size_mb: 50
  max_total_images_size_mb: 500
  ocr_timeout_seconds: 30
  nougat_timeout_seconds: 120
  llm_timeout_seconds: 60
  unload_models_after_conversion: false

# Sincronización con upstream
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
| **EPUB** | MathML (vía HTML) | Imágenes del archivo | Internamente es HTML + ZIP |
| **Jupyter** | LaTeX nativo, MathML | Outputs de celdas | Passthrough de LaTeX existente |
| **XLSX** | Regex básico | N/A | Fórmulas de celdas |
| **Imágenes** | OCR (opcional) | El propio fichero | PNG, JPEG |
| **Audio** | N/A | N/A | Via MarkItDown base |
| **CSV/JSON/XML** | N/A | N/A | Via MarkItDown base |
| **ZIP** | Recursivo | Recursivo | Via MarkItDown base |

---

## Arquitectura

SciMarkdown usa una arquitectura de **pipeline de 3 fases** con un **fork mínimo** de MarkItDown:

```
Documento original
       │
       ▼
┌─────────────────────┐
│  Fase 1: Extracción │  MarkItDown (sin modificar)
│  → Markdown base    │  super().convert()
└─────────┬───────────┘
          ▼
┌─────────────────────────┐
│  Fase 2: Enriquecimiento│  SciMarkdown (paquete separado)
│  • MathDetector         │  Re-parsea el documento original
│  • ImageExtractor       │
│  • ReferenceLinker      │
│  • LLM Fallback         │
└─────────┬───────────────┘
          ▼
┌─────────────────────────┐
│  Fase 3: Composición    │  SciMarkdown
│  → Markdown + LaTeX     │  Fusiona markdown base + datos estructurados
│  → Imágenes enlazadas   │
│  → Índice de figuras    │
└─────────────────────────┘
```

### Estrategia de fork mínimo

- **0 líneas modificadas** en el código de MarkItDown (el upstream `convert_stream()` ya hace los streams seekable)
- `EnhancedMarkItDown` hereda de `MarkItDown` y override solo `convert_stream()`
- El 100% del código de enriquecimiento vive en `packages/scimarkdown/`
- Sincronización con upstream cada 14 días vía GitHub Actions

### Estructura del proyecto

```
scimarkdown/
├── packages/
│   ├── markitdown/              ← Fork de Microsoft (sin cambios)
│   ├── markitdown-mcp/          ← Fork del MCP server original
│   └── scimarkdown/             ← Paquete de enriquecimiento
│       └── src/scimarkdown/
│           ├── math/
│           │   ├── detector.py      ← Detección heurística (Unicode, MathML, MathJax)
│           │   ├── formatter.py     ← Formato LaTeX ($...$ vs $`...`$)
│           │   └── ocr.py           ← Wrapper pix2tex / Nougat
│           ├── images/
│           │   ├── extractor.py     ← Extracción por formato (PDF, DOCX, PPTX, HTML, EPUB, Jupyter)
│           │   ├── cropper.py       ← Recorte automático de bordes
│           │   ├── reference_linker.py ← Vinculación Figura X → imagen
│           │   └── index_builder.py ← Generación de índice de figuras
│           ├── pipeline/
│           │   ├── enrichment.py    ← Orquestador Fase 2
│           │   └── composition.py   ← Orquestador Fase 3
│           ├── llm/
│           │   └── fallback.py      ← Cliente LLM (OpenAI/Anthropic)
│           ├── mcp/
│           │   ├── server.py        ← Servidor MCP con 2 tools
│           │   └── __main__.py      ← CLI del MCP
│           ├── sync/
│           │   └── upstream.py      ← Script de sincronización
│           ├── models/              ← Dataclasses (EnrichedResult, MathRegion, ImageRef...)
│           ├── config.py            ← Sistema de configuración YAML
│           ├── _enhanced_markitdown.py ← Subclase principal
│           └── __main__.py          ← CLI de SciMarkdown
├── tests/
│   ├── unit/                    ← 200+ tests unitarios
│   │   ├── math/                ← Tests de detección y formato
│   │   ├── images/              ← Tests de extracción y vinculación
│   │   └── pipeline/            ← Tests de orquestación
│   ├── integration/             ← Tests de pipeline completo
│   ├── upstream/                ← Tests de regresión del upstream
│   └── fixtures/                ← Documentos de prueba
├── .github/
│   └── workflows/
│       └── upstream-sync.yml    ← Sincronización automática cada 14 días
├── scimarkdown.yaml             ← Configuración por defecto
└── docs/superpowers/
    ├── specs/                   ← Especificación de diseño
    └── plans/                   ← Plan de implementación
```

---

## Versionado

```
SciMarkdown v{MAJOR}.{MINOR}.{PATCH}+mit{UPSTREAM_VERSION}

Ejemplo: scimarkdown 0.1.0+mit0.1.1
```

El sufijo `+mit` indica sobre qué versión de MarkItDown está construido.

---

## Sincronización con upstream

SciMarkdown se sincroniza con el repositorio original de Microsoft MarkItDown cada 14 días:

1. **Automático:** GitHub Actions ejecuta el script de sincronización cada 1 y 15 de cada mes
2. Si no hay conflictos y los tests pasan → PR automática
3. Si hay conflictos → se crea un issue con los detalles

Para sincronizar manualmente:

```bash
python -m scimarkdown.sync.upstream --repo-dir .
```

---

## Desarrollo

### Ejecutar tests

```bash
# Activar entorno virtual
source .venv/bin/activate

# Todos los tests
python -m pytest tests/ -v

# Solo tests unitarios
python -m pytest tests/unit/ -v

# Solo un módulo
python -m pytest tests/unit/math/ -v

# Con cobertura
python -m pytest tests/ --cov=scimarkdown --cov-report=html
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
3. Escribir tests en `tests/unit/images/test_extractor_formats.py`
4. Añadir test de integración en `tests/integration/`

---

## Degradación elegante

SciMarkdown nunca falla en una conversión. Si el enriquecimiento falla, siempre devuelve el markdown base de MarkItDown:

| Componente | Fallo | Comportamiento |
|------------|-------|----------------|
| MathDetector | Regex false positive | Marca con `<!-- sci:math:low-confidence -->` |
| MathOCR | Modelo no instalado | Usa solo heurísticas. Log warning. |
| ImageExtractor | No puede extraer | Skip imagen. Log warning. |
| LLM Fallback | API caída/timeout | Skip LLM. Continúa con resultados locales. |
| Pipeline completo | Excepción inesperada | Devuelve markdown base sin enriquecer. Log traceback. |

---

## Licencia

Este proyecto es un fork de [Microsoft MarkItDown](https://github.com/microsoft/markitdown), licenciado bajo MIT License.

---

## Créditos

- **[Microsoft MarkItDown](https://github.com/microsoft/markitdown)** — Proyecto base de conversión a Markdown
- **[pix2tex](https://github.com/lukas-blecher/LaTeX-OCR)** — OCR de fórmulas matemáticas (opcional)
- **[Nougat (Meta)](https://github.com/facebookresearch/nougat)** — OCR de papers académicos (opcional)
