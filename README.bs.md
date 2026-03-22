# SciMarkdown

<p align="center">
  <strong>Konverter dokumenata u Markdown sa detekcijom LaTeX formula, pametnom ekstrakcijom slika, filtriranjem šuma i semantičkom analizom sa Gemini Embeddings.</strong>
</p>

<p align="center">
  <a href="README.md"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Flag_of_Galicia.svg/20px-Flag_of_Galicia.svg.png" width="16" alt="Galicia"> Galego</a> ·
  <a href="README.es.md">🇪🇸 Español</a> ·
  <a href="README.en.md">🇬🇧 English</a> ·
  🇧🇦 <strong>Bosanski</strong>
</p>

---

SciMarkdown je fork [Microsoft MarkItDown](https://github.com/microsoft/markitdown) koji proširuje mogućnosti konverzije sa četiri stuba:

1. **Detekcija matematičkih formula i LaTeX ugradnja** u svim podržanim formatima
2. **Ekstrakcija, obrezivanje i referenciranje slika** sa povezivanjem tekstualnih referenci i indeksom slika
3. **Filtriranje šuma** — uklanja zaglavlja, podnožja, brojeve stranica i dekorativne slike; pretvara sadržaje u hiperveze
4. **Semantička analiza sa Gemini Embeddings** (opcionalno) — klasifikacija formula, povezivanje slika i teksta po značenju, klasifikacija dokumenata i semantičko pretraživanje (RAG)

---

## Karakteristike

### Detekcija matematičkih formula

SciMarkdown automatski detektuje i konvertuje matematičke formule u LaTeX koristeći više slojevitih strategija:

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

**Izlaz (GitHub stil):**
```markdown
Za sve $`x \in \mathbb{R}`$, zbir $`\sum_{i} x_{i} \leq \int f(x)dx`$ važi.
```

### Pametna ekstrakcija slika

- Ekstrahuje ugrađene slike iz PDF, DOCX, PPTX, HTML, EPUB i Jupyter Notebooks
- Automatsko obrezivanje bijelih rubova sa podesivim marginama
- Slike se ubacuju **na originalnu poziciju** u dokumentu, usidrene na prethodni tekst
- **Konvencija imenovanja:** `{dokument}_img{00001}.png` (5 cifara)
- **Relativne putanje:** Putanje slika u markdownu su relativni nazivi fajlova (ne apsolutne putanje), što čini markdown prenosivim

### Filtriranje šuma

- **Ponovljeni tekst** — detektuje zaglavlja/podnožja koja se ponavljaju na istoj poziciji na 3+ stranica
- **Brojevi stranica** — detektuje sekvencijalne brojeve u graničnim blokovima
- **Dekorativne slike** — filtrira slike manje od 30px, ekstremnog omjera (>8:1) ili ponovljene
- **Sadržaj (TOC)** — detektuje tabele sadržaja i pretvara ih u markdown hiperveze
- **HeadingDetector** — detektuje obrasce poglavlja/sekcija ("Capítulo N.", "N.N. Naslov") i pretvara ih u markdown naslove (#, ##, ###)
- **TextCleaner** — uklanja CID artefakte kodiranja iz PDF-ova, pretvara apsolutne putanje slika u relativne nazive fajlova, spaja intra-paragrafske PDF prijelome redova uz očuvanje struktura ključ-vrijednost
- **Uklanjanje ponovljenih paragrafa** — uklanja paragrafe koji se pojavljuju 3+ puta u dokumentu (zaglavlja/podnožja koja prođu kroz detekciju na nivou stranice)

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

### MCP Server sa 12 alata

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

---

## Instalacija

### Preduvjeti

- Python >= 3.10
- Git

### Korak 1: Kloniranje

```bash
git clone https://github.com/babel-stack/mcp-sciMarkdown.git
cd mcp-sciMarkdown
```

### Korak 2: Virtualno okruženje

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Korak 3: Instalacija osnovnih zavisnosti

```bash
# Instalirati MarkItDown (lokalni fork)
pip install -e packages/markitdown[all]

# Instalirati SciMarkdown (heuristike, bez GPU-a, bez PyTorcha)
pip install -e packages/scimarkdown
```

### Opcionalne zavisnosti

```bash
# OCR formula sa pix2tex (~500MB + PyTorch)
pip install -e "packages/scimarkdown[ocr]"

# Potpuni OCR radova sa Nougat (~3GB + PyTorch)
pip install -e "packages/scimarkdown[nougat]"

# LLM fallback (OpenAI/Anthropic)
pip install -e "packages/scimarkdown[llm]"

# Gemini Embeddings (semantička analiza)
pip install -e "packages/scimarkdown[embeddings]"

# Sve
pip install -e "packages/scimarkdown[all]"
```

### Korak 4: Instalacija MCP SDK (za MCP server)

```bash
pip install "mcp[cli]>=1.0.0"
```

### Varijable okoline

| Varijabla | Potrebna za | Primjer |
|-----------|------------|---------|
| `GEMINI_API_KEY` | Embeddings alate | `export GEMINI_API_KEY=AIza...` |
| `LLM_API_KEY` | LLM fallback | `export LLM_API_KEY=sk-...` |

### NixOS

```bash
# Pronaći libstdc++
find /nix/store -name "libstdc++.so.6" 2>/dev/null | head -1

# Exportovati (dodati u .bashrc/.zshrc)
export LD_LIBRARY_PATH=/nix/store/<hash>-gcc-<version>-lib/lib

# Ako numpy 2.x ne radi sa "X86_V2" na starijim CPU-ima:
pip install "numpy<2.0"
```

Uključena je skripta za pokretanje kompatibilna sa NixOS: `run-scimarkdown-mcp.sh`

---

## Korištenje

### CLI

```bash
# Osnovna konverzija (stdout)
scimarkdown document.pdf

# Izlaz u fajl
scimarkdown document.pdf -o document.md

# LaTeX GitHub stila
scimarkdown paper.pdf --latex-style github

# Prilagođeni direktorij izlaza slika
scimarkdown paper.pdf --output-dir ./images/

# Prilagođeni konfiguracijski fajl
scimarkdown paper.pdf -c my_config.yaml
```

### Python API

```python
from scimarkdown._enhanced_markitdown import EnhancedMarkItDown
from scimarkdown.config import SciMarkdownConfig

# Zadana konfiguracija
converter = EnhancedMarkItDown()
result = converter.convert("document.pdf")
print(result.markdown)

# Prilagođena konfiguracija
config = SciMarkdownConfig(
    latex_style="github",
    images_dpi=150,
    references_generate_index=True,
    filters_enabled=True,
)
converter = EnhancedMarkItDown(sci_config=config)
result = converter.convert("paper.docx")
```

#### Direktno korištenje podkomponenti

```python
# Detektovati formule u tekstu
from scimarkdown.math.detector import MathDetector
detector = MathDetector()
regions = detector.detect("The equation x² + y² = z² is famous.")
for r in regions:
    print(f"{r.original_text} → ${r.latex}$ (pouzdanost: {r.confidence})")

# Ekstrahirati slike iz PDF-a
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
        print(f"Ekstrahirano: {img.file_path} ({img.width}x{img.height})")

# Povezati reference
from scimarkdown.images.reference_linker import ReferenceLinker
linker = ReferenceLinker(SciMarkdownConfig())
linked = linker.link("Kao što je prikazano na Slici 1...", images)
```

#### Korištenje Gemini Embeddings

```python
from scimarkdown.embeddings.client import GeminiEmbeddingClient
from scimarkdown.embeddings.math_classifier import MathClassifier
from scimarkdown.embeddings.semantic_linker import SemanticLinker
from scimarkdown.embeddings.content_indexer import ContentIndexer

# Kreirati klijenta
client = GeminiEmbeddingClient(api_key="your-api-key")

# Klasificirati kandidate za formule
classifier = MathClassifier(client, threshold=0.75)
confirmed = classifier.classify(detected_regions)

# Semantičko povezivanje slika i teksta (bez potrebe za "Slika X")
linker = SemanticLinker(client, threshold=0.60)
linked = linker.link(images, paragraphs)

# Semantičko pretraživanje (RAG)
indexer = ContentIndexer(client)
index = indexer.index(markdown_text)
results = indexer.search(index, "Schrödingerova jednadžba", top_k=5)
```

### MCP Server

#### STDIO način (Claude Desktop, Claude Code, Cursor...)

```bash
scimarkdown-mcp
```

#### HTTP način (web integracija)

```bash
scimarkdown-mcp --http --port 3001
```

#### Konfiguracija Claude Desktop

Dodati u `claude_desktop_config.json`:

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

NixOS — koristiti uključenu skriptu:

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

#### Konfiguracija Claude Code

```bash
# Na nivou korisnika (dostupno u svim projektima)
claude mcp add --scope user scimarkdown /path/to/mcp-sciMarkdown/run-scimarkdown-mcp.sh

# Na nivou projekta
claude mcp add scimarkdown scimarkdown-mcp
```

---

## MCP Alati — Kompletna referenca

### Pipeline alati (konverzija od početka do kraja)

#### `convert_to_markdown`

Osnovna konverzija putem MarkItDown. Bez obogaćivanja.

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `uri` | string | Da | Putanja fajla ili URL |

Vraća: `string` — Čisti markdown

---

#### `convert_to_scimarkdown`

Obogaćena konverzija sa LaTeX-om, slikama, filtriranjem šuma i TOC hipervezama. Potpuno offline.

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `uri` | string | Da | Putanja fajla ili URL |
| `config` | dict | Ne | Pregaziti `scimarkdown.yaml` |

Vraća: `string` — Obogaćeni markdown

Primjer konfiguracije:
```json
{"latex": {"style": "github"}, "images": {"dpi": 150}, "filters": {"enabled": true}}
```

---

#### `convert_to_scimarkdown_embeddings`

Konverzija maksimalnog kvaliteta sa Gemini Embeddings. Zahtijeva `GEMINI_API_KEY`.

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `uri` | string | Da | Putanja fajla ili URL |
| `config` | dict | Ne | Pregazivanja konfiguracije |
| `embedding_options` | dict | Ne | `classify_math`, `semantic_linking`, `classify_document` (bool) |

Vraća: `string` — Obogaćeni markdown najvećeg kvaliteta

---

### Granularni alati (offline, kombinabilni)

Ovi alati se mogu ulančavati: `detect_math` → `format_latex`, ili `extract_images` → `link_references` → `build_figure_index`.

#### `detect_math`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `text` | string | Da | Tekst ili HTML za analizu |
| `methods` | list[string] | Ne | `"unicode"`, `"mathml"`, `"mathjax"`, `"latex"` |

Vraća: `JSON string` — Niz `{original_text, latex, source_type, confidence, position, is_inline}`

#### `format_latex`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `formulas` | string (JSON) | Da | Izlaz `detect_math` |
| `style` | string | Ne | `"standard"` ili `"github"` |

Vraća: `JSON string` — Niz `{original_text, formatted}`

**Primjer ulančavanja:**
```
1. detect_math(text="x² + y² = z²")  →  [{"latex": "x^{2}+y^{2}=z^{2}", ...}]
2. format_latex(formulas=↑, style="github")  →  [{"formatted": "$`x^{2}+y^{2}=z^{2}`$"}]
```

#### `extract_images`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `uri` | string | Da | Putanja dokumenta |
| `output_dir` | string | Ne | Izlazni direktorij (zadano: uz dokument) |
| `dpi` | int | Ne | Rezolucija rasterizacije (zadano: 300) |
| `autocrop` | bool | Ne | Obrezati bijele rubove (zadano: true) |

Vraća: `JSON string` — Niz `{file_path, width, height, position, original_format, context_text}`

Podržani formati: PDF, DOCX, PPTX, HTML, EPUB, Jupyter Notebook.

#### `link_references`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `text` | string | Da | Tekst dokumenta |
| `images` | string (JSON) | Da | Izlaz `extract_images` |
| `patterns` | list[string] | Ne | Prilagođeni regex uzorci |

Vraća: `JSON string` — Niz sa popunjenim `ordinal` i `reference_label`

#### `build_figure_index`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `images` | string (JSON) | Da | Izlaz `link_references` |

Vraća: `string` — Markdown tabela indeksa slika

**Kompletan primjer pipeline-a slika:**
```
1. extract_images(uri="paper.pdf")          → ekstrahirane slike
2. link_references(text=..., images=↑)      → slike sa referencama
3. build_figure_index(images=↑)             → markdown tabela
```

#### `ocr_formula`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `image_path` | string | Da | Putanja do slike formule |
| `engine` | string | Ne | `"auto"`, `"pix2tex"`, `"nougat"` |

Vraća: `JSON string` — `{latex, confidence, engine_used}` ili `{error}`

---

### Embeddings alati (zahtijevaju `GEMINI_API_KEY`)

#### `analyze_document`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `uri` | string | Da | Putanja dokumenta |
| `analysis_type` | string | Ne | `"full"`, `"structure"`, `"math"`, `"images"` |

Vraća: `JSON string` — `{document_type, math_density, math_count, word_count, formula_regions, classification_confidence}`

Tipovi dokumenata: `academic_paper`, `technical_report`, `presentation`, `textbook`, `code_documentation`, `general_document`

#### `search_content`

Semantičko pretraživanje unutar dokumenta (RAG).

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `uri` | string | Da | Putanja dokumenta |
| `query` | string | Da | Upit na prirodnom jeziku |
| `top_k` | int | Ne | Broj rezultata (zadano: 5) |

Vraća: `JSON string` — Niz `{content, score, position, type}`

Primjer:
```
search_content(uri="paper.pdf", query="Schrödingerova jednadžba", top_k=3)
→ [
    {"content": "$H|\\psi\\rangle = E|\\psi\\rangle$", "score": 0.94, "type": "formula"},
    {"content": "Vremenski neovisna Schrödingerova jednadžba...", "score": 0.87, "type": "text"}
  ]
```

#### `compare_sections`

| Parametar | Tip | Obavezno | Opis |
|-----------|-----|----------|------|
| `uris` | string (JSON) | Da | Niz putanja dokumenata |
| `granularity` | string | Ne | `"paragraph"`, `"section"`, `"page"` |

Vraća: `JSON string` — `{document_count, total_sections, unique_topics}`

---

## Konfiguracija

SciMarkdown traži `scimarkdown.yaml` u trenutnom direktoriju. Sve opcije imaju razumne zadane vrijednosti.

```yaml
# ── LaTeX format ───────────────────────────────────────────
latex:
  style: "standard"              # "standard" ($...$) ili "github" ($`...`$)

# ── Slike ──────────────────────────────────────────────────
images:
  output_dir: "same"              # "same" = uz izvorni dokument
  format: "png"
  dpi: 300
  margin_px: 10
  counter_digits: 5               # img00001
  autocrop_whitespace: true

# ── Detekcija formula ──────────────────────────────────────
math:
  heuristic: true
  ocr_engine: "auto"              # "pix2tex", "nougat" ili "auto"
  confidence_threshold: 0.75

# ── LLM Fallback ──────────────────────────────────────────
llm:
  enabled: false
  provider: "openai"              # "openai" ili "anthropic"
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

# ── Filteri šuma ──────────────────────────────────────────
filters:
  enabled: true
  repeated_text: true             # Ukloniti ponovljena zaglavlja/podnožja
  page_numbers: true              # Ukloniti sekvencijalne brojeve stranica
  decorative_images: true         # Ukloniti male/uske/ponovljene slike
  min_repeat_pages: 3             # Stranice koje tekst mora ponavljati da bi bio šum
  max_header_length: 100          # Maks. znakova za kandidata zaglavlja
  min_image_size: 30              # Min. px za čuvanje slike
  max_image_aspect_ratio: 8.0     # Maksimalni omjer prije označavanja kao dekorativne
  # (Ovo je automatsko, nije potrebna konfiguracija:)
  # heading_detection: automatski
  # cid_cleaning: automatski
  # path_normalization: automatski
  # line_break_merging: automatski (čuva strukture ključ-vrijednost)
  # repeated_paragraph_removal: min. 3 pojave

# ── Reference ──────────────────────────────────────────────
references:
  patterns:
    - 'Fig(?:ura|ure|\.)\s*(\d+)'
    - 'Tab(?:la|le|\.)\s*(\d+)'
    - 'Im(?:agen|age|g\.?)\s*(\d+)'
  languages: ["es", "en"]
  generate_index: true

# ── Performanse ────────────────────────────────────────────
performance:
  total_timeout_seconds: 1800
  max_images: 10000
  max_image_file_size_mb: 50

# ── Upstream sinhronizacija ────────────────────────────────
sync:
  remote: "https://github.com/microsoft/markitdown.git"
  check_interval_days: 14
```

---

## Podržani formati

| Format | Formule | Slike | Filter šuma | Napomene |
|--------|---------|-------|-------------|----------|
| **PDF** | Unicode, OCR | Ugrađene + vektorske | Zaglavlja, podnožja, brojevi stranica, TOC | Potpuna podrška |
| **DOCX** | Nativni OMML | word/media/ | — | Najbolji kvalitet formula |
| **PPTX** | OMML | ppt/media/ | — | |
| **HTML** | MathML, MathJax, KaTeX | `<img>`, base64 | — | |
| **EPUB** | MathML (putem HTML) | Slike arhive | — | Interno HTML + ZIP |
| **Jupyter** | Nativni LaTeX, MathML | Izlazi ćelija | — | LaTeX prolaz |
| **XLSX** | Osnovni regex | — | — | Formule ćelija |
| **Slike** | OCR (opcionalno) | Sam fajl | — | PNG, JPEG |
| **Audio** | — | — | — | Putem baznog MarkItDown |
| **CSV/JSON/XML** | — | — | — | Putem baznog MarkItDown |

---

## Arhitektura

```
Izvorni dokument
       │
       ▼
┌─────────────────────────┐
│  Faza 1: Ekstrakcija    │  MarkItDown (nemodifikovani)
│  → Bazni markdown       │  super().convert()
└─────────┬───────────────┘
          ▼
┌─────────────────────────────────────────────────┐
│  Faza 2: Obogaćivanje                           │
│                                                  │
│  ┌────────────────────────────────────────┐      │
│  │ Sloj 1: Heuristike (OFFLINE)          │      │
│  │  MathDetector · ImageExtractor        │      │
│  │  ReferenceLinker · ImageCropper        │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Filteri šuma (OFFLINE)                │      │
│  │  RepeatedText · PageNumbers           │      │
│  │  DecorativeImages · TocProcessor      │      │
│  │  HeadingDetector · TextCleaner        │      │
│  │  RepeatedParagraphs                    │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Sloj 2: Embeddings (ONLINE, opcion.)  │      │
│  │  MathClassifier · SemanticLinker      │      │
│  │  DocumentClassifier                    │      │
│  └──────────────────┬─────────────────────┘      │
│                     ▼                            │
│  ┌────────────────────────────────────────┐      │
│  │ Sloj 3: LLM Fallback (ONLINE, opc.)  │      │
│  │  OpenAI / Anthropic                    │      │
│  └────────────────────────────────────────┘      │
└─────────────────────┬────────────────────────────┘
                      ▼
┌─────────────────────────┐
│  Faza 3: Kompozicija    │
│  → Markdown + LaTeX     │  MathFormatter · IndexBuilder
│  → Inline slike         │  Pozicioniranje usidreno na kontekst
│  → Indeks slika         │
│  → TOC hiperveze        │
└─────────────────────────┘
```

### Struktura projekta

```
packages/scimarkdown/
│       ├── filters/
│       │   ├── noise_filter.py         ← Orkestrator + uklanjanje ponovljenih paragrafa
│       │   ├── repeated_text.py        ← Detekcija zaglavlja/podnožja po poziciji stranice
│       │   ├── page_numbers.py         ← Detekcija sekvencijalnih brojeva stranica
│       │   ├── decorative_images.py    ← Filter malih/uskih/ponovljenih slika
│       │   ├── toc_processor.py        ← Konverzija TOC → hiperveze
│       │   ├── heading_detector.py     ← Poglavlje/sekcija → markdown naslovi
│       │   └── text_cleaner.py         ← Uklanjanje CID-a, normalizacija putanja, spajanje redova
```

### Strategija minimalnog forka

- **0 modifikovanih linija** u izvornom kodu MarkItDown
- `EnhancedMarkItDown` nasljeđuje od `MarkItDown`, pregazuje samo `convert_stream()` i `convert_local()`
- 100% koda za obogaćivanje živi u `packages/scimarkdown/`
- Upstream sinhronizacija svakih 14 dana putem GitHub Actions

---

## Graceful degradacija

SciMarkdown nikada ne pada na konverziji. Ako obogaćivanje ne uspije, uvijek vraća bazni markdown:

| Komponenta | Kvar | Ponašanje |
|------------|------|-----------|
| MathDetector | Lažni pozitiv regexa | Označava sa `<!-- sci:math:low-confidence -->` |
| MathOCR | Model nije instaliran | Koristi samo heuristike |
| MathClassifier | Gemini API nije dostupan | Preskače klasifikaciju, zadržava heurističke rezultate |
| SemanticLinker | Gemini API nije dostupan | Preskače semantičko povezivanje, koristi ordinalni ReferenceLinker |
| NoiseFilter | Parsiranje PDF-a ne uspije | Preskače filtriranje, zadržava sav sadržaj |
| TocProcessor | TOC nije detektovan | Bez promjena |
| HeadingDetector | Nijedan obrazac se ne podudara | Tekst nepromijenjen |
| TextCleaner | Obrada ne uspije | Tekst nepromijenjen |
| RepeatedParagraphs | Detekcija ne uspije | Svi paragrafi se čuvaju |
| ImageExtractor | Ne može ekstrahirati | Preskače sliku, bilježi upozorenje |
| LLM Fallback | API nije dostupan/timeout | Preskače LLM, nastavlja sa lokalnim rezultatima |
| Cijeli pipeline | Neočekivani izuzetak | Vraća bazni markdown bez promjena |

---

## Razvoj

### Pokretanje testova

```bash
source .venv/bin/activate

# Svi testovi (790)
python -m pytest tests/ -v --ignore=tests/upstream

# Po modulu
python -m pytest tests/unit/math/ -v
python -m pytest tests/unit/images/ -v
python -m pytest tests/unit/filters/ -v
python -m pytest tests/unit/embeddings/ -v
python -m pytest tests/unit/mcp/ -v
python -m pytest tests/unit/pipeline/ -v
python -m pytest tests/integration/ -v

# Sa pokrivenošću
python -m pytest tests/ --cov=scimarkdown --cov-report=html --ignore=tests/upstream
```

### Pragovi kvaliteta

| Metrika | Minimum |
|---------|---------|
| Ispravne LaTeX formule | >= 95% |
| Ekstrahirane slike | >= 95% |
| Povezane reference | >= 95% |
| Microsoft upstream testovi | 100% |
| Pokrivenost koda | >= 85% |

---

## Upstream sinhronizacija

SciMarkdown se sinhronizuje sa Microsoft MarkItDown svakih 14 dana:

1. GitHub Actions se izvršava 1. i 15. svakog mjeseca
2. Bez konflikata + testovi prolaze → automatski PR
3. Konflikti → kreira se issue sa detaljima

Ručna sinhronizacija:
```bash
python -m scimarkdown.sync.upstream --repo-dir .
```

---

## Verzioniranje

```
SciMarkdown v{MAJOR}.{MINOR}.{PATCH}+mit{UPSTREAM_VERSION}
Primjer: scimarkdown 0.1.0+mit0.1.1
```

---

## Troškovi ugrađivanja (embeddings)

| Operacija | Cijena/dok | 1000 dok/mj |
|-----------|------------|-------------|
| Samo offline konverzija | $0 | $0 |
| + Matematička klasifikacija | ~$0.002 | ~$2 |
| + Semantičko povezivanje | ~$0.005 | ~$5 |
| + Klasifikacija dokumenta | ~$0.001 | ~$1 |
| + Indeksiranje sadržaja (RAG) | ~$0.01 | ~$10 |
| **Sve aktivirano** | **~$0.018** | **~$18** |

---

## Licenca

Ovaj projekat je fork [Microsoft MarkItDown](https://github.com/microsoft/markitdown), licenciran pod MIT licencom.

## Zasluge

- **[Microsoft MarkItDown](https://github.com/microsoft/markitdown)** — Osnovna konverzija u Markdown
- **[Google Gemini Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)** — Multimodalna semantička analiza
- **[pix2tex](https://github.com/lukas-blecher/LaTeX-OCR)** — OCR formula (opcionalno)
- **[Nougat (Meta)](https://github.com/facebookresearch/nougat)** — OCR akademskih radova (opcionalno)
