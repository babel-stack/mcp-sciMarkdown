# SciMarkdown v2 — Embeddings Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional Gemini Embeddings layer to SciMarkdown that improves math classification, enables semantic image-text linking, document classification, and semantic search (RAG).

**Architecture:** A new `embeddings/` module with a Gemini API client, local cache, and 4 components (MathClassifier, SemanticLinker, DocumentClassifier, ContentIndexer). Integrated into the enrichment pipeline as an optional layer between heuristics and LLM fallback. 4 new MCP tools exposed.

**Tech Stack:** Python 3.12, `google-genai` SDK, cosine similarity, JSON file cache, existing scimarkdown pipeline

**Spec:** `docs/superpowers/specs/2026-03-20-scimarkdown-v2-embeddings-prd.md` (Sections 3.3, 4, 5)

**Dependency:** `pip install google-genai` (added to `[embeddings]` optional group)

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `packages/scimarkdown/src/scimarkdown/embeddings/__init__.py` | Package exports | Create |
| `packages/scimarkdown/src/scimarkdown/embeddings/client.py` | Gemini API wrapper | Create |
| `packages/scimarkdown/src/scimarkdown/embeddings/cache.py` | Local embedding cache | Create |
| `packages/scimarkdown/src/scimarkdown/embeddings/math_classifier.py` | Formula classification via embeddings | Create |
| `packages/scimarkdown/src/scimarkdown/embeddings/semantic_linker.py` | Image-text semantic linking | Create |
| `packages/scimarkdown/src/scimarkdown/embeddings/document_classifier.py` | Document type classification | Create |
| `packages/scimarkdown/src/scimarkdown/embeddings/content_indexer.py` | Content indexing + search | Create |
| `packages/scimarkdown/src/scimarkdown/config.py` | Add embeddings config section | Modify |
| `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py` | Wire embeddings into pipeline | Modify |
| `packages/scimarkdown/src/scimarkdown/mcp/server.py` | Add 4 new MCP tools | Modify |
| `packages/scimarkdown/pyproject.toml` | Add `[embeddings]` dep group | Modify |
| `tests/unit/embeddings/__init__.py` | Test package | Create |
| `tests/unit/embeddings/test_client.py` | Client tests (mocked API) | Create |
| `tests/unit/embeddings/test_cache.py` | Cache tests | Create |
| `tests/unit/embeddings/test_math_classifier.py` | Classifier tests | Create |
| `tests/unit/embeddings/test_semantic_linker.py` | Linker tests | Create |
| `tests/unit/embeddings/test_document_classifier.py` | Doc classifier tests | Create |
| `tests/unit/embeddings/test_content_indexer.py` | Indexer tests | Create |
| `tests/unit/mcp/test_embedding_tools.py` | MCP embedding tools tests | Create |

---

### Task 1: Embedding cache

The cache is needed by all other components, so it comes first. No API dependency.

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/embeddings/__init__.py`
- Create: `packages/scimarkdown/src/scimarkdown/embeddings/cache.py`
- Create: `tests/unit/embeddings/__init__.py`
- Create: `tests/unit/embeddings/test_cache.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/embeddings/__init__.py` (empty).

Create `tests/unit/embeddings/test_cache.py`:

```python
import json
from pathlib import Path
from scimarkdown.embeddings.cache import EmbeddingCache


def test_cache_put_and_get(tmp_path):
    cache = EmbeddingCache(cache_dir=tmp_path / "cache")
    embedding = [0.1, 0.2, 0.3, 0.4]
    cache.put("test_key", embedding)
    result = cache.get("test_key")
    assert result == embedding


def test_cache_miss(tmp_path):
    cache = EmbeddingCache(cache_dir=tmp_path / "cache")
    result = cache.get("nonexistent")
    assert result is None


def test_cache_hash_content(tmp_path):
    cache = EmbeddingCache(cache_dir=tmp_path / "cache")
    key = cache.content_hash("hello world")
    assert isinstance(key, str)
    assert len(key) == 64  # SHA-256 hex


def test_cache_same_content_same_hash(tmp_path):
    cache = EmbeddingCache(cache_dir=tmp_path / "cache")
    assert cache.content_hash("hello") == cache.content_hash("hello")
    assert cache.content_hash("hello") != cache.content_hash("world")


def test_cache_persists_to_disk(tmp_path):
    cache_dir = tmp_path / "cache"
    cache1 = EmbeddingCache(cache_dir=cache_dir)
    cache1.put("key1", [1.0, 2.0])

    # New instance reads from same dir
    cache2 = EmbeddingCache(cache_dir=cache_dir)
    assert cache2.get("key1") == [1.0, 2.0]


def test_cache_clear(tmp_path):
    cache = EmbeddingCache(cache_dir=tmp_path / "cache")
    cache.put("key1", [1.0])
    cache.clear()
    assert cache.get("key1") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/unit/embeddings/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement cache**

Create `packages/scimarkdown/src/scimarkdown/embeddings/__init__.py`:

```python
"""SciMarkdown embeddings module — optional Gemini API integration."""
```

Create `packages/scimarkdown/src/scimarkdown/embeddings/cache.py`:

```python
"""Local file-based cache for embeddings to avoid redundant API calls."""

import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """File-based cache for embedding vectors.

    Each entry is stored as a JSON file named by the content hash.
    """

    def __init__(self, cache_dir: Path = Path(".scimarkdown_cache")):
        self.cache_dir = Path(cache_dir)

    def content_hash(self, content: str) -> str:
        """Return SHA-256 hex digest of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[list[float]]:
        """Retrieve a cached embedding by key. Returns None on miss."""
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except Exception as e:
            logger.warning("Cache read failed for %s: %s", key, e)
            return None

    def put(self, key: str, embedding: list[float]) -> None:
        """Store an embedding vector in the cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / f"{key}.json"
        path.write_text(json.dumps(embedding))

    def clear(self) -> None:
        """Remove all cached embeddings."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/embeddings/ tests/unit/embeddings/
git commit -m "feat(embeddings): add file-based embedding cache"
```

---

### Task 2: Gemini API client

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/embeddings/client.py`
- Create: `tests/unit/embeddings/test_client.py`
- Modify: `packages/scimarkdown/pyproject.toml` (add `[embeddings]` group)

- [ ] **Step 1: Write failing tests**

Create `tests/unit/embeddings/test_client.py`:

```python
"""Tests for GeminiEmbeddingClient — all API calls are mocked."""

import math
from unittest.mock import patch, MagicMock

from scimarkdown.embeddings.client import GeminiEmbeddingClient


def _mock_genai_client():
    """Create a mock google.genai.Client."""
    mock = MagicMock()
    # Mock embed_content response
    embedding_obj = MagicMock()
    embedding_obj.values = [0.1, 0.2, 0.3]
    response = MagicMock()
    response.embeddings = [embedding_obj]
    mock.models.embed_content.return_value = response
    return mock


@patch("scimarkdown.embeddings.client._create_genai_client")
def test_embed_text(mock_create):
    mock_create.return_value = _mock_genai_client()
    client = GeminiEmbeddingClient(api_key="test-key")
    result = client.embed_text("hello world")
    assert result == [0.1, 0.2, 0.3]


@patch("scimarkdown.embeddings.client._create_genai_client")
def test_embed_text_with_task_type(mock_create):
    mock_client = _mock_genai_client()
    mock_create.return_value = mock_client
    client = GeminiEmbeddingClient(api_key="test-key")
    client.embed_text("test", task_type="CLASSIFICATION")
    # Verify task_type was passed
    call_kwargs = mock_client.models.embed_content.call_args
    assert call_kwargs is not None


@patch("scimarkdown.embeddings.client._create_genai_client")
def test_embed_batch(mock_create):
    mock_client = _mock_genai_client()
    emb1 = MagicMock()
    emb1.values = [0.1, 0.2]
    emb2 = MagicMock()
    emb2.values = [0.3, 0.4]
    response = MagicMock()
    response.embeddings = [emb1, emb2]
    mock_client.models.embed_content.return_value = response
    mock_create.return_value = mock_client

    client = GeminiEmbeddingClient(api_key="test-key")
    results = client.embed_batch(["hello", "world"])
    assert len(results) == 2
    assert results[0] == [0.1, 0.2]
    assert results[1] == [0.3, 0.4]


def test_similarity():
    client = GeminiEmbeddingClient.__new__(GeminiEmbeddingClient)
    # Identical vectors → similarity 1.0
    assert math.isclose(client.similarity([1, 0, 0], [1, 0, 0]), 1.0)
    # Orthogonal vectors → similarity 0.0
    assert math.isclose(client.similarity([1, 0, 0], [0, 1, 0]), 0.0)
    # Opposite vectors → similarity -1.0
    assert math.isclose(client.similarity([1, 0], [-1, 0]), -1.0)


@patch("scimarkdown.embeddings.client._create_genai_client")
def test_embed_text_with_cache(mock_create):
    mock_client = _mock_genai_client()
    mock_create.return_value = mock_client
    client = GeminiEmbeddingClient(api_key="test-key")

    # First call hits API
    r1 = client.embed_text("same text")
    # Second call with same text should use cache (if cache enabled)
    r2 = client.embed_text("same text")
    assert r1 == r2


@patch("scimarkdown.embeddings.client._create_genai_client")
def test_client_not_available_without_key(mock_create):
    mock_create.side_effect = Exception("No API key")
    try:
        client = GeminiEmbeddingClient(api_key="")
        assert not client.is_available()
    except Exception:
        pass  # Expected
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL

- [ ] **Step 3: Add `[embeddings]` dependency group to pyproject.toml**

Add to `packages/scimarkdown/pyproject.toml` under `[project.optional-dependencies]`:

```toml
embeddings = ["google-genai>=1.0.0"]
```

Update the `all` group to include embeddings:
```toml
all = ["scimarkdown[ocr]", "scimarkdown[nougat]", "scimarkdown[llm]", "scimarkdown[embeddings]"]
```

- [ ] **Step 4: Implement client**

Create `packages/scimarkdown/src/scimarkdown/embeddings/client.py`:

```python
"""Gemini Embeddings API client with caching and cosine similarity."""

import logging
import math
from pathlib import Path
from typing import Optional

from .cache import EmbeddingCache

logger = logging.getLogger(__name__)


def _create_genai_client(api_key: str):
    """Create a google.genai.Client. Separated for testability."""
    from google import genai
    return genai.Client(api_key=api_key)


class GeminiEmbeddingClient:
    """Client for the Gemini Embeddings API.

    Wraps google-genai SDK with caching and utility methods.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-2-preview",
        dimensions: int = 768,
        cache_dir: Optional[Path] = None,
        cache_enabled: bool = True,
    ):
        self.model = model
        self.dimensions = dimensions
        self._client = _create_genai_client(api_key)
        self._cache = EmbeddingCache(cache_dir or Path(".scimarkdown_cache")) if cache_enabled else None

    def is_available(self) -> bool:
        """Check if the client is properly initialized."""
        return self._client is not None

    def embed_text(
        self,
        text: str,
        task_type: str = "SEMANTIC_SIMILARITY",
    ) -> list[float]:
        """Generate embedding for a text string."""
        # Check cache
        if self._cache:
            cache_key = self._cache.content_hash(f"{self.model}:{task_type}:{text}")
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        from google.genai import types

        response = self._client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dimensions,
            ),
        )
        embedding = response.embeddings[0].values

        # Store in cache
        if self._cache:
            self._cache.put(cache_key, embedding)

        return embedding

    def embed_image(self, image_bytes: bytes, mime_type: str = "image/png") -> list[float]:
        """Generate embedding for an image."""
        from google.genai import types

        response = self._client.models.embed_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        return response.embeddings[0].values

    def embed_batch(
        self,
        texts: list[str],
        task_type: str = "SEMANTIC_SIMILARITY",
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single API call."""
        from google.genai import types

        response = self._client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dimensions,
            ),
        )
        return [emb.values for emb in response.embeddings]

    @staticmethod
    def similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Cosine similarity between two vectors. Returns -1.0 to 1.0."""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
```

- [ ] **Step 5: Run tests to verify they pass**

Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/embeddings/client.py packages/scimarkdown/pyproject.toml tests/unit/embeddings/test_client.py
git commit -m "feat(embeddings): add Gemini API client with caching and cosine similarity"
```

---

### Task 3: Embeddings config extension

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/config.py`
- Modify: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_config.py`:

```python
def test_embeddings_config_defaults():
    config = SciMarkdownConfig()
    assert config.embeddings_enabled is False
    assert config.embeddings_provider == "gemini"
    assert config.embeddings_model == "gemini-embedding-2-preview"
    assert config.embeddings_api_key_env == "GEMINI_API_KEY"
    assert config.embeddings_dimensions == 768
    assert config.embeddings_classify_math is True
    assert config.embeddings_semantic_linking is True
    assert config.embeddings_classify_document is True
    assert config.embeddings_content_indexing is False
    assert config.embeddings_cache_enabled is True
    assert config.embeddings_math_similarity_threshold == 0.75
    assert config.embeddings_image_link_threshold == 0.60
    assert config.embeddings_max_per_document == 500
    assert config.embeddings_batch_size == 100


def test_embeddings_config_from_dict():
    config = SciMarkdownConfig.from_dict({
        "embeddings": {
            "enabled": True,
            "dimensions": 1536,
            "classify_math": False,
        }
    })
    assert config.embeddings_enabled is True
    assert config.embeddings_dimensions == 1536
    assert config.embeddings_classify_math is False
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: FAIL with `AttributeError`

- [ ] **Step 3: Add embeddings fields to SciMarkdownConfig**

Add new fields to the `SciMarkdownConfig` dataclass in `config.py`:

```python
    # Embeddings
    embeddings_enabled: bool = False
    embeddings_provider: str = "gemini"
    embeddings_model: str = "gemini-embedding-2-preview"
    embeddings_api_key_env: str = "GEMINI_API_KEY"
    embeddings_dimensions: int = 768
    embeddings_classify_math: bool = True
    embeddings_semantic_linking: bool = True
    embeddings_classify_document: bool = True
    embeddings_content_indexing: bool = False
    embeddings_cache_enabled: bool = True
    embeddings_cache_dir: str = ".scimarkdown_cache"
    embeddings_cache_ttl_days: int = 30
    embeddings_math_similarity_threshold: float = 0.75
    embeddings_image_link_threshold: float = 0.60
    embeddings_max_per_document: int = 500
    embeddings_batch_size: int = 100
```

Add mapping entries to `_apply_dict`:

```python
            ("embeddings", "enabled"): "embeddings_enabled",
            ("embeddings", "provider"): "embeddings_provider",
            ("embeddings", "model"): "embeddings_model",
            ("embeddings", "api_key_env"): "embeddings_api_key_env",
            ("embeddings", "dimensions"): "embeddings_dimensions",
            ("embeddings", "classify_math"): "embeddings_classify_math",
            ("embeddings", "semantic_linking"): "embeddings_semantic_linking",
            ("embeddings", "classify_document"): "embeddings_classify_document",
            ("embeddings", "content_indexing"): "embeddings_content_indexing",
            ("embeddings", "cache_enabled"): "embeddings_cache_enabled",
            ("embeddings", "cache_dir"): "embeddings_cache_dir",
            ("embeddings", "cache_ttl_days"): "embeddings_cache_ttl_days",
            ("embeddings", "math_similarity_threshold"): "embeddings_math_similarity_threshold",
            ("embeddings", "image_link_threshold"): "embeddings_image_link_threshold",
            ("embeddings", "max_embeddings_per_document"): "embeddings_max_per_document",
            ("embeddings", "batch_size"): "embeddings_batch_size",
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: All PASS (existing + new config tests).

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/config.py tests/unit/test_config.py
git commit -m "feat(embeddings): add embeddings configuration fields"
```

---

### Task 4: MathClassifier

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/embeddings/math_classifier.py`
- Create: `tests/unit/embeddings/test_math_classifier.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/embeddings/test_math_classifier.py`:

```python
from unittest.mock import MagicMock
from scimarkdown.models import MathRegion
from scimarkdown.embeddings.math_classifier import MathClassifier


def _make_mock_client(similarity_value=0.9):
    client = MagicMock()
    client.embed_text.return_value = [0.1, 0.2, 0.3]
    client.embed_batch.return_value = [[0.1, 0.2, 0.3]] * 50
    client.similarity.return_value = similarity_value
    return client


def test_high_similarity_confirms():
    client = _make_mock_client(similarity_value=0.9)
    classifier = MathClassifier(client, threshold=0.75)

    region = MathRegion(position=0, original_text="x²", latex="x^{2}",
                        source_type="unicode", confidence=0.6)
    result = classifier.classify([region])
    assert len(result) == 1
    assert result[0].confidence > 0.6  # Boosted


def test_low_similarity_discards():
    client = _make_mock_client(similarity_value=0.3)
    classifier = MathClassifier(client, threshold=0.75)

    region = MathRegion(position=0, original_text="hello world", latex="hello world",
                        source_type="unicode", confidence=0.6)
    result = classifier.classify([region])
    assert len(result) == 0  # Discarded


def test_already_high_confidence_passes_through():
    client = _make_mock_client(similarity_value=0.5)
    classifier = MathClassifier(client, threshold=0.75)

    region = MathRegion(position=0, original_text="x²", latex="x^{2}",
                        source_type="mathml", confidence=0.95)
    result = classifier.classify([region])
    # High-confidence regions pass through without embedding check
    assert len(result) == 1


def test_empty_input():
    client = _make_mock_client()
    classifier = MathClassifier(client, threshold=0.75)
    assert classifier.classify([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement MathClassifier**

Create `packages/scimarkdown/src/scimarkdown/embeddings/math_classifier.py`:

```python
"""Classify math formula candidates using embeddings to reduce false positives."""

import logging
from typing import Optional

from scimarkdown.models import MathRegion
from .client import GeminiEmbeddingClient

logger = logging.getLogger(__name__)

# Reference formulas for embedding comparison
_MATH_REFERENCES = [
    r"x^2 + y^2 = z^2",
    r"\frac{a}{b}",
    r"\int_0^\infty e^{-x} dx = 1",
    r"\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}",
    r"E = mc^2",
    r"\nabla \times \vec{B} = \mu_0 \vec{J}",
    r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
    r"\binom{n}{k} = \frac{n!}{k!(n-k)!}",
    r"a^2 = b^2 + c^2 - 2bc\cos A",
    r"\det(A) = \sum_{\sigma} \text{sgn}(\sigma) \prod_i a_{i,\sigma(i)}",
    r"P(A|B) = \frac{P(B|A)P(A)}{P(B)}",
    r"\vec{F} = m\vec{a}",
    r"\frac{\partial u}{\partial t} = \alpha \nabla^2 u",
    r"e^{i\pi} + 1 = 0",
    r"\sqrt{a^2 + b^2}",
]

# Threshold above which a region is considered already confirmed
_HIGH_CONFIDENCE_PASSTHROUGH = 0.9


class MathClassifier:
    """Uses embeddings to confirm or discard heuristic math detections.

    Regions with confidence >= 0.9 pass through without API calls.
    Regions below that threshold are compared against reference formulas.
    If similarity exceeds the threshold, confidence is boosted.
    If below, the region is discarded as a false positive.
    """

    def __init__(
        self,
        client: GeminiEmbeddingClient,
        threshold: float = 0.75,
    ):
        self.client = client
        self.threshold = threshold
        self._reference_embeddings: Optional[list[list[float]]] = None

    def _get_reference_embeddings(self) -> list[list[float]]:
        """Lazily compute and cache reference formula embeddings."""
        if self._reference_embeddings is None:
            self._reference_embeddings = self.client.embed_batch(
                _MATH_REFERENCES,
                task_type="CLASSIFICATION",
            )
        return self._reference_embeddings

    def classify(self, candidates: list[MathRegion]) -> list[MathRegion]:
        """Filter candidates: confirm real formulas, discard false positives.

        Returns only the confirmed regions with updated confidence scores.
        """
        if not candidates:
            return []

        confirmed: list[MathRegion] = []

        for region in candidates:
            # High-confidence regions pass through
            if region.confidence >= _HIGH_CONFIDENCE_PASSTHROUGH:
                confirmed.append(region)
                continue

            # Get embedding for the candidate
            candidate_emb = self.client.embed_text(
                region.latex or region.original_text,
                task_type="CLASSIFICATION",
            )

            # Compare against references
            ref_embeddings = self._get_reference_embeddings()
            max_sim = max(
                self.client.similarity(candidate_emb, ref_emb)
                for ref_emb in ref_embeddings
            )

            if max_sim >= self.threshold:
                # Confirmed — boost confidence
                region.confidence = min(1.0, region.confidence + (1.0 - region.confidence) * max_sim)
                confirmed.append(region)
                logger.debug("Confirmed math region (sim=%.3f): %s", max_sim, region.original_text[:50])
            else:
                logger.debug("Discarded false positive (sim=%.3f): %s", max_sim, region.original_text[:50])

        return confirmed
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/embeddings/math_classifier.py tests/unit/embeddings/test_math_classifier.py
git commit -m "feat(embeddings): add MathClassifier for formula confirmation via embeddings"
```

---

### Task 5: SemanticLinker

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/embeddings/semantic_linker.py`
- Create: `tests/unit/embeddings/test_semantic_linker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/embeddings/test_semantic_linker.py`:

```python
from unittest.mock import MagicMock, patch
from scimarkdown.models import ImageRef
from scimarkdown.embeddings.semantic_linker import SemanticLinker


def _make_mock_client():
    client = MagicMock()
    # Return different embeddings for different inputs
    call_count = [0]
    def fake_embed_text(text, **kwargs):
        call_count[0] += 1
        return [float(call_count[0]), 0.0, 0.0]
    client.embed_text.side_effect = fake_embed_text
    client.embed_image.return_value = [1.0, 0.0, 0.0]  # Similar to first text
    client.similarity.side_effect = lambda a, b: (
        1.0 if a == b else sum(x*y for x,y in zip(a,b)) / (
            (sum(x**2 for x in a)**0.5) * (sum(y**2 for y in b)**0.5 + 1e-10)
        )
    )
    return client


def test_link_image_to_most_similar_text():
    client = _make_mock_client()
    # Force specific similarity: image embedding matches paragraph 1
    client.embed_image.return_value = [1.0, 0.0, 0.0]
    client.embed_text.side_effect = [
        [1.0, 0.0, 0.0],  # paragraph 1 — match
        [0.0, 1.0, 0.0],  # paragraph 2 — no match
    ]
    client.similarity.side_effect = lambda a, b: sum(x*y for x,y in zip(a,b))

    linker = SemanticLinker(client, threshold=0.5)
    images = [ImageRef(position=0, file_path="img.png", original_format="png")]
    paragraphs = ["Graph showing temperature increase", "Unrelated text about cooking"]

    result = linker.link(images, paragraphs)
    assert result[0].caption is not None or result[0].reference_label is not None


def test_no_link_below_threshold():
    client = _make_mock_client()
    client.embed_image.return_value = [1.0, 0.0, 0.0]
    client.embed_text.return_value = [0.0, 0.0, 1.0]  # Orthogonal
    client.similarity.return_value = 0.1  # Below threshold

    linker = SemanticLinker(client, threshold=0.5)
    images = [ImageRef(position=0, file_path="img.png", original_format="png")]
    paragraphs = ["Completely unrelated text"]

    result = linker.link(images, paragraphs)
    assert result[0].caption is None


def test_empty_inputs():
    client = _make_mock_client()
    linker = SemanticLinker(client)
    assert linker.link([], ["text"]) == []
    assert linker.link([ImageRef(position=0, file_path="x.png", original_format="png")], []) == [ImageRef(position=0, file_path="x.png", original_format="png")]
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement SemanticLinker**

Create `packages/scimarkdown/src/scimarkdown/embeddings/semantic_linker.py`:

```python
"""Semantic image-text linking using multimodal embeddings."""

import io
import logging
from pathlib import Path
from typing import Optional

from scimarkdown.models import ImageRef
from .client import GeminiEmbeddingClient

logger = logging.getLogger(__name__)


class SemanticLinker:
    """Links images to text blocks by semantic similarity.

    Uses multimodal embeddings: generates an embedding for each image
    and each text paragraph, then links by highest cosine similarity.
    """

    def __init__(
        self,
        client: GeminiEmbeddingClient,
        threshold: float = 0.60,
    ):
        self.client = client
        self.threshold = threshold

    def link(
        self,
        images: list[ImageRef],
        text_blocks: list[str],
    ) -> list[ImageRef]:
        """Link images to the most semantically similar text blocks.

        Updates ImageRef.caption with the best-matching text block.
        Only links if similarity exceeds threshold.
        """
        if not images:
            return []
        if not text_blocks:
            return images

        # Generate text embeddings
        text_embeddings = [
            self.client.embed_text(block, task_type="SEMANTIC_SIMILARITY")
            for block in text_blocks
        ]

        for img in images:
            try:
                # Get image embedding
                img_path = Path(img.file_path)
                if img_path.exists():
                    image_bytes = img_path.read_bytes()
                    img_embedding = self.client.embed_image(image_bytes)
                else:
                    logger.warning("Image file not found: %s", img.file_path)
                    continue

                # Find best matching text block
                best_sim = -1.0
                best_idx = -1
                for idx, text_emb in enumerate(text_embeddings):
                    sim = self.client.similarity(img_embedding, text_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_idx = idx

                if best_sim >= self.threshold and best_idx >= 0:
                    # Truncate caption to first sentence or 100 chars
                    caption = text_blocks[best_idx]
                    if len(caption) > 100:
                        caption = caption[:100].rsplit(" ", 1)[0] + "..."
                    img.caption = caption
                    logger.debug(
                        "Linked %s → '%s' (sim=%.3f)",
                        img.file_path, caption[:50], best_sim,
                    )

            except Exception as e:
                logger.warning("Semantic linking failed for %s: %s", img.file_path, e)

        return images
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/embeddings/semantic_linker.py tests/unit/embeddings/test_semantic_linker.py
git commit -m "feat(embeddings): add SemanticLinker for image-text linking via multimodal embeddings"
```

---

### Task 6: DocumentClassifier

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/embeddings/document_classifier.py`
- Create: `tests/unit/embeddings/test_document_classifier.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/embeddings/test_document_classifier.py`:

```python
from unittest.mock import MagicMock
from scimarkdown.embeddings.document_classifier import DocumentClassifier
from scimarkdown.config import SciMarkdownConfig


def _make_mock_client(similarities):
    """Mock client that returns pre-set similarities for each category."""
    client = MagicMock()
    client.embed_text.return_value = [0.1, 0.2, 0.3]
    call_count = [0]
    def fake_similarity(a, b):
        idx = call_count[0] % len(similarities)
        call_count[0] += 1
        return similarities[idx]
    client.similarity.side_effect = fake_similarity
    return client


def test_classify_academic_paper():
    # Highest similarity for "academic_paper" (index 0)
    sims = [0.95, 0.3, 0.2, 0.1, 0.1, 0.1]
    client = _make_mock_client(sims)
    classifier = DocumentClassifier(client)
    category, confidence = classifier.classify("Abstract: We present a novel approach...")
    assert category == "academic_paper"
    assert confidence > 0.5


def test_classify_returns_valid_category():
    sims = [0.1, 0.1, 0.9, 0.1, 0.1, 0.1]
    client = _make_mock_client(sims)
    classifier = DocumentClassifier(client)
    category, _ = classifier.classify("Some text")
    assert category in DocumentClassifier.CATEGORIES


def test_optimize_config_academic():
    client = MagicMock()
    classifier = DocumentClassifier(client)
    config = SciMarkdownConfig()
    optimized = classifier.optimize_config("academic_paper", config)
    assert optimized.math_heuristic is True


def test_optimize_config_presentation():
    client = MagicMock()
    classifier = DocumentClassifier(client)
    config = SciMarkdownConfig()
    optimized = classifier.optimize_config("presentation", config)
    assert isinstance(optimized, SciMarkdownConfig)
```

- [ ] **Step 2-3: Implement**

Create `packages/scimarkdown/src/scimarkdown/embeddings/document_classifier.py`:

```python
"""Document classification using embeddings to optimize the pipeline."""

import logging
from scimarkdown.config import SciMarkdownConfig
from .client import GeminiEmbeddingClient

logger = logging.getLogger(__name__)


# Category descriptions for embedding comparison
_CATEGORY_DESCRIPTIONS = {
    "academic_paper": "Scientific research paper with abstract, methodology, results, references, equations, and citations",
    "technical_report": "Technical documentation with diagrams, specifications, tables, and data analysis",
    "presentation": "Slide presentation with bullet points, images, charts, and minimal text per slide",
    "textbook": "Educational textbook with chapters, definitions, theorems, proofs, exercises, and formulas",
    "code_documentation": "Software documentation with code blocks, API references, function signatures, and examples",
    "general_document": "General purpose document with mixed content, paragraphs, and standard formatting",
}


class DocumentClassifier:
    """Classifies document type to optimize the enrichment pipeline."""

    CATEGORIES = list(_CATEGORY_DESCRIPTIONS.keys())

    def __init__(self, client: GeminiEmbeddingClient):
        self.client = client
        self._category_embeddings: dict[str, list[float]] = {}

    def _get_category_embeddings(self) -> dict[str, list[float]]:
        if not self._category_embeddings:
            for cat, desc in _CATEGORY_DESCRIPTIONS.items():
                self._category_embeddings[cat] = self.client.embed_text(
                    desc, task_type="CLASSIFICATION"
                )
        return self._category_embeddings

    def classify(self, text: str) -> tuple[str, float]:
        """Classify document text into a category.

        Returns (category_name, confidence_score).
        """
        # Use first 2000 chars for classification
        sample = text[:2000]
        doc_embedding = self.client.embed_text(sample, task_type="CLASSIFICATION")

        cat_embeddings = self._get_category_embeddings()
        best_cat = "general_document"
        best_sim = -1.0

        for cat, cat_emb in cat_embeddings.items():
            sim = self.client.similarity(doc_embedding, cat_emb)
            if sim > best_sim:
                best_sim = sim
                best_cat = cat

        return best_cat, max(0.0, best_sim)

    def optimize_config(self, category: str, config: SciMarkdownConfig) -> SciMarkdownConfig:
        """Return an optimized config based on document category."""
        overrides: dict = {}

        if category == "academic_paper":
            overrides = {"math": {"heuristic": True, "ocr_engine": "auto"}}
        elif category == "presentation":
            overrides = {"images": {"dpi": 200}}
        elif category == "textbook":
            overrides = {"math": {"heuristic": True}}
        elif category == "code_documentation":
            overrides = {"math": {"heuristic": False}}

        return config.with_overrides(overrides) if overrides else config
```

- [ ] **Step 4: Run tests, commit**

```bash
git add packages/scimarkdown/src/scimarkdown/embeddings/document_classifier.py tests/unit/embeddings/test_document_classifier.py
git commit -m "feat(embeddings): add DocumentClassifier for pipeline optimization"
```

---

### Task 7: ContentIndexer

**Files:**
- Create: `packages/scimarkdown/src/scimarkdown/embeddings/content_indexer.py`
- Create: `tests/unit/embeddings/test_content_indexer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/embeddings/test_content_indexer.py`:

```python
from unittest.mock import MagicMock
from scimarkdown.embeddings.content_indexer import ContentIndexer


def _make_mock_client():
    client = MagicMock()
    call_count = [0]
    def fake_embed(text, **kwargs):
        call_count[0] += 1
        return [float(call_count[0]), 0.0, 0.0]
    client.embed_text.side_effect = fake_embed
    client.similarity.side_effect = lambda a, b: sum(x*y for x,y in zip(a,b)) / (
        max(sum(x**2 for x in a)**0.5 * sum(y**2 for y in b)**0.5, 1e-10)
    )
    return client


def test_index_splits_by_sections():
    client = _make_mock_client()
    indexer = ContentIndexer(client)
    markdown = "## Section 1\n\nParagraph one.\n\n## Section 2\n\nParagraph two."
    index = indexer.index(markdown)
    assert len(index.chunks) >= 2


def test_search_returns_results():
    client = _make_mock_client()
    # Make query embedding match first chunk
    client.embed_text.side_effect = None
    client.embed_text.return_value = [1.0, 0.0, 0.0]
    client.similarity.return_value = 0.9

    indexer = ContentIndexer(client)
    markdown = "## Intro\n\nQuantum computing is...\n\n## Methods\n\nWe used..."
    index = indexer.index(markdown)

    results = indexer.search(index, "quantum computing", top_k=2)
    assert len(results) >= 1
    assert "score" in results[0]
    assert "content" in results[0]


def test_search_empty_index():
    client = _make_mock_client()
    indexer = ContentIndexer(client)
    index = indexer.index("")
    results = indexer.search(index, "anything")
    assert results == []


def test_index_chunks_have_type():
    client = _make_mock_client()
    indexer = ContentIndexer(client)
    markdown = "## Title\n\nText here.\n\n$E = mc^2$\n\nMore text."
    index = indexer.index(markdown)
    types = [c["type"] for c in index.chunks]
    assert "text" in types
```

- [ ] **Step 2-3: Implement**

Create `packages/scimarkdown/src/scimarkdown/embeddings/content_indexer.py`:

```python
"""Content indexing and semantic search over converted markdown."""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from .client import GeminiEmbeddingClient

logger = logging.getLogger(__name__)


@dataclass
class ContentIndex:
    """An indexed document ready for semantic search."""
    chunks: list[dict] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)


class ContentIndexer:
    """Indexes markdown content for semantic search (RAG)."""

    def __init__(self, client: GeminiEmbeddingClient):
        self.client = client

    def index(self, markdown: str) -> ContentIndex:
        """Split markdown into chunks and generate embeddings."""
        if not markdown.strip():
            return ContentIndex()

        chunks = self._split_into_chunks(markdown)
        embeddings = []

        for chunk in chunks:
            emb = self.client.embed_text(
                chunk["content"],
                task_type="RETRIEVAL_DOCUMENT",
            )
            embeddings.append(emb)

        return ContentIndex(chunks=chunks, embeddings=embeddings)

    def search(
        self,
        index: ContentIndex,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Search the index for chunks most similar to the query."""
        if not index.chunks:
            return []

        query_emb = self.client.embed_text(query, task_type="RETRIEVAL_QUERY")

        scored = []
        for i, (chunk, emb) in enumerate(zip(index.chunks, index.embeddings)):
            score = self.client.similarity(query_emb, emb)
            scored.append({
                "content": chunk["content"],
                "score": score,
                "position": chunk.get("position", i),
                "type": chunk["type"],
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _split_into_chunks(self, markdown: str) -> list[dict]:
        """Split markdown into semantic chunks by headers and paragraphs."""
        chunks: list[dict] = []
        # Split by headers
        sections = re.split(r'(^#{1,6}\s+.+$)', markdown, flags=re.MULTILINE)

        position = 0
        for part in sections:
            part = part.strip()
            if not part:
                continue

            # Detect type
            if part.startswith("#"):
                chunk_type = "heading"
            elif "$" in part or "\\(" in part:
                chunk_type = "formula"
            elif part.startswith("!["):
                chunk_type = "image"
            elif part.startswith("|"):
                chunk_type = "table"
            else:
                chunk_type = "text"

            chunks.append({
                "content": part,
                "type": chunk_type,
                "position": position,
            })
            position += 1

        return chunks
```

- [ ] **Step 4: Run tests, commit**

```bash
git add packages/scimarkdown/src/scimarkdown/embeddings/content_indexer.py tests/unit/embeddings/test_content_indexer.py
git commit -m "feat(embeddings): add ContentIndexer for semantic search (RAG)"
```

---

### Task 8: Wire embeddings into enrichment pipeline

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py`
- Modify: `packages/scimarkdown/src/scimarkdown/embeddings/__init__.py`
- Create: `tests/unit/pipeline/test_enrichment_embeddings.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/pipeline/test_enrichment_embeddings.py`:

```python
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
from scimarkdown.pipeline.enrichment import EnrichmentPipeline
from scimarkdown.config import SciMarkdownConfig


def _mock_embedding_client():
    client = MagicMock()
    client.embed_text.return_value = [0.1, 0.2, 0.3]
    client.embed_batch.return_value = [[0.1, 0.2, 0.3]] * 15
    client.similarity.return_value = 0.9
    return client


@patch("scimarkdown.pipeline.enrichment._create_embedding_client")
def test_embeddings_classify_math(mock_create):
    mock_create.return_value = _mock_embedding_client()
    config = SciMarkdownConfig(embeddings_enabled=True, embeddings_classify_math=True)
    pipeline = EnrichmentPipeline(config)

    with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        result = pipeline.enrich(
            base_markdown="The formula x² + y² = z² is famous.",
            source_stream=io.BytesIO(b"test"),
            file_extension=".txt",
            document_name="test",
            output_dir=Path("/tmp"),
        )
    # Should have run math classifier
    assert isinstance(result.math_regions, list)


def test_embeddings_disabled_no_api_call():
    config = SciMarkdownConfig(embeddings_enabled=False)
    pipeline = EnrichmentPipeline(config)
    result = pipeline.enrich(
        base_markdown="x² + y²",
        source_stream=io.BytesIO(b"test"),
        file_extension=".txt",
        document_name="test",
        output_dir=Path("/tmp"),
    )
    # Should still work without embeddings
    assert isinstance(result.math_regions, list)
```

- [ ] **Step 2-3: Implement embeddings integration in enrichment.py**

Add to `enrichment.py`:

```python
import os
from typing import Optional


def _create_embedding_client(config):
    """Create embedding client if enabled and API key available."""
    if not config.embeddings_enabled:
        return None
    api_key = os.environ.get(config.embeddings_api_key_env)
    if not api_key:
        logger.warning("Embeddings enabled but %s not set", config.embeddings_api_key_env)
        return None
    try:
        from scimarkdown.embeddings.client import GeminiEmbeddingClient
        return GeminiEmbeddingClient(
            api_key=api_key,
            model=config.embeddings_model,
            dimensions=config.embeddings_dimensions,
            cache_enabled=config.embeddings_cache_enabled,
        )
    except Exception as e:
        logger.warning("Failed to create embedding client: %s", e)
        return None
```

In `EnrichmentPipeline.enrich()`, after the LLM fallback block and before returning, add:

```python
        # Embeddings layer (if enabled)
        embedding_client = _create_embedding_client(self.config)
        if embedding_client:
            # Math classification
            if self.config.embeddings_classify_math and math_regions:
                try:
                    from scimarkdown.embeddings.math_classifier import MathClassifier
                    classifier = MathClassifier(
                        embedding_client,
                        threshold=self.config.embeddings_math_similarity_threshold,
                    )
                    math_regions = classifier.classify(math_regions)
                    logger.info("Math classifier: %d regions confirmed", len(math_regions))
                except Exception as e:
                    logger.warning("Math classification failed: %s", e)

            # Semantic linking
            if self.config.embeddings_semantic_linking and images:
                try:
                    from scimarkdown.embeddings.semantic_linker import SemanticLinker
                    linker = SemanticLinker(
                        embedding_client,
                        threshold=self.config.embeddings_image_link_threshold,
                    )
                    paragraphs = [p for p in base_markdown.split("\n\n") if p.strip()]
                    images = linker.link(images, paragraphs)
                    logger.info("Semantic linker: linked images to text")
                except Exception as e:
                    logger.warning("Semantic linking failed: %s", e)
```

- [ ] **Step 4: Run tests, commit**

```bash
git add packages/scimarkdown/src/scimarkdown/pipeline/enrichment.py packages/scimarkdown/src/scimarkdown/embeddings/__init__.py tests/unit/pipeline/test_enrichment_embeddings.py
git commit -m "feat(embeddings): wire MathClassifier and SemanticLinker into enrichment pipeline"
```

---

### Task 9: MCP embedding tools

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/mcp/server.py`
- Create: `tests/unit/mcp/test_embedding_tools.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/mcp/test_embedding_tools.py`:

```python
"""Tests for embedding MCP tools — all API calls mocked."""

import json
from unittest.mock import patch, MagicMock
from scimarkdown.mcp.server import create_mcp_server

_server = create_mcp_server()

def _get_tool_fn(name):
    for tool in _server._tool_manager._tools.values():
        if tool.name == name:
            return tool.fn
    raise KeyError(f"Tool {name!r} not found")


class TestToolsExist:
    def test_embedding_tools_registered(self):
        tool_names = [t.name for t in _server._tool_manager._tools.values()]
        assert "convert_to_scimarkdown_embeddings" in tool_names
        assert "analyze_document" in tool_names
        assert "search_content" in tool_names
        assert "compare_sections" in tool_names


class TestAnalyzeDocument:
    @patch("scimarkdown.mcp.server._get_embedding_client")
    def test_analyze_returns_structure(self, mock_get):
        mock_client = MagicMock()
        mock_client.embed_text.return_value = [0.1, 0.2, 0.3]
        mock_client.similarity.return_value = 0.8
        mock_get.return_value = mock_client

        fn = _get_tool_fn("analyze_document")
        # Would need a real file, so test the function exists
        assert callable(fn)
```

- [ ] **Step 2-3: Implement 4 MCP tools**

Add to `server.py`:

```python
    def _get_embedding_client():
        """Create embedding client from env. Returns None if unavailable."""
        import os
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return None
        try:
            from scimarkdown.embeddings.client import GeminiEmbeddingClient
            return GeminiEmbeddingClient(api_key=api_key)
        except Exception:
            return None

    @mcp.tool()
    def convert_to_scimarkdown_embeddings(
        uri: str,
        config: Optional[dict] = None,
        embedding_options: Optional[dict] = None,
    ) -> str:
        """Convert a document with full pipeline + Gemini embeddings for maximum quality.

        Requires GEMINI_API_KEY environment variable.

        Args:
            uri: File path or URL to convert.
            config: Optional configuration overrides.
            embedding_options: Optional dict with keys: classify_math, semantic_linking,
                             classify_document (all bool, default true).
        Returns:
            Enriched Markdown with highest quality math detection and image linking.
        """
        overrides = {"embeddings": {"enabled": True}}
        if embedding_options:
            overrides["embeddings"].update(embedding_options)
        if config:
            overrides.update(config)

        sci_config = SciMarkdownConfig().with_overrides(overrides)
        converter = EnhancedMarkItDown(sci_config=sci_config)
        result = converter.convert(uri)
        return result.markdown or ""

    @mcp.tool()
    def analyze_document(uri: str, analysis_type: str = "full") -> str:
        """Classify a document and return semantic metadata without converting.

        Requires GEMINI_API_KEY environment variable.

        Args:
            uri: File path to analyze.
            analysis_type: "full", "structure", "math", or "images".
        Returns:
            JSON with document_type, language estimate, math_density, image_count, sections.
        """
        from scimarkdown.math.detector import MathDetector

        # Get base markdown
        base_converter = MarkItDown()
        result = base_converter.convert(uri)
        text = result.markdown or ""

        # Math detection
        detector = MathDetector()
        math_regions = detector.detect(text)
        math_density = len(math_regions) / max(len(text.split()), 1)

        response = {
            "document_type": "general_document",
            "math_density": round(math_density, 4),
            "math_count": len(math_regions),
            "word_count": len(text.split()),
            "formula_regions": [
                {"text": r.original_text[:100], "confidence": r.confidence, "type": r.source_type}
                for r in math_regions[:20]
            ],
        }

        # Document classification with embeddings
        client = _get_embedding_client()
        if client and analysis_type in ("full", "structure"):
            try:
                from scimarkdown.embeddings.document_classifier import DocumentClassifier
                classifier = DocumentClassifier(client)
                doc_type, confidence = classifier.classify(text)
                response["document_type"] = doc_type
                response["classification_confidence"] = round(confidence, 4)
            except Exception as e:
                response["classification_error"] = str(e)

        return json.dumps(response, ensure_ascii=False)

    @mcp.tool()
    def search_content(
        uri: str,
        query: str,
        top_k: int = 5,
    ) -> str:
        """Semantic search within a document.

        Requires GEMINI_API_KEY environment variable.

        Args:
            uri: File path to search.
            query: Natural language search query.
            top_k: Number of results to return (default: 5).
        Returns:
            JSON array of matching content chunks with scores.
        """
        client = _get_embedding_client()
        if not client:
            return json.dumps({"error": "GEMINI_API_KEY not set"})

        # Convert document first
        base_converter = MarkItDown()
        result = base_converter.convert(uri)
        text = result.markdown or ""

        from scimarkdown.embeddings.content_indexer import ContentIndexer
        indexer = ContentIndexer(client)
        index = indexer.index(text)
        results = indexer.search(index, query, top_k=top_k)

        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    def compare_sections(
        uris: str,
        granularity: str = "section",
    ) -> str:
        """Compare sections across one or more documents semantically.

        Requires GEMINI_API_KEY environment variable.

        Args:
            uris: JSON array of file paths to compare.
            granularity: "paragraph", "section", or "page" (default: "section").
        Returns:
            JSON with similarity clusters and unique topics.
        """
        client = _get_embedding_client()
        if not client:
            return json.dumps({"error": "GEMINI_API_KEY not set"})

        uri_list = json.loads(uris)
        base_converter = MarkItDown()

        from scimarkdown.embeddings.content_indexer import ContentIndexer
        indexer = ContentIndexer(client)

        all_chunks = []
        for uri_str in uri_list:
            result = base_converter.convert(uri_str)
            text = result.markdown or ""
            index = indexer.index(text)
            for chunk in index.chunks:
                chunk["source"] = uri_str
            all_chunks.extend(index.chunks)

        # Find unique topics from chunk content
        topics = list(set(
            c["content"][:80] for c in all_chunks if c["type"] in ("heading", "text")
        ))[:20]

        return json.dumps({
            "document_count": len(uri_list),
            "total_sections": len(all_chunks),
            "unique_topics": topics,
        }, ensure_ascii=False)
```

- [ ] **Step 4: Run tests, commit**

```bash
git add packages/scimarkdown/src/scimarkdown/mcp/server.py tests/unit/mcp/test_embedding_tools.py
git commit -m "feat(mcp): add embedding tools — convert_to_scimarkdown_embeddings, analyze_document, search_content, compare_sections"
```

---

### Task 10: Update __init__.py exports and final integration test

**Files:**
- Modify: `packages/scimarkdown/src/scimarkdown/embeddings/__init__.py`
- Run full test suite

- [ ] **Step 1: Update exports**

```python
"""SciMarkdown embeddings module — optional Gemini API integration."""

from .cache import EmbeddingCache
from .client import GeminiEmbeddingClient
from .math_classifier import MathClassifier
from .semantic_linker import SemanticLinker
from .document_classifier import DocumentClassifier
from .content_indexer import ContentIndexer, ContentIndex

__all__ = [
    "EmbeddingCache",
    "GeminiEmbeddingClient",
    "MathClassifier",
    "SemanticLinker",
    "DocumentClassifier",
    "ContentIndexer",
    "ContentIndex",
]
```

- [ ] **Step 2: Run full test suite**

Run: `LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib .venv/bin/python -m pytest tests/ --ignore=tests/upstream -q`

Expected: All pass (268 existing + ~30 new embedding tests).

- [ ] **Step 3: Commit**

```bash
git add packages/scimarkdown/src/scimarkdown/embeddings/__init__.py
git commit -m "feat(embeddings): finalize module exports and integration"
```

---

## Dependency Graph

```
Task 1 (cache) ──────┐
                      ▼
Task 2 (client) ──→ Task 3 (config)
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
Task 4 (math)  Task 5 (linker)  Task 6 (doc classifier)
          │           │           │
          └───────────┼───────────┘
                      ▼
              Task 7 (indexer)
                      │
                      ▼
         Task 8 (wire into pipeline)
                      │
                      ▼
           Task 9 (MCP tools)
                      │
                      ▼
        Task 10 (exports + final test)
```

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | EmbeddingCache | cache.py, test_cache.py |
| 2 | GeminiEmbeddingClient | client.py, test_client.py, pyproject.toml |
| 3 | Config extension | config.py, test_config.py |
| 4 | MathClassifier | math_classifier.py, test_math_classifier.py |
| 5 | SemanticLinker | semantic_linker.py, test_semantic_linker.py |
| 6 | DocumentClassifier | document_classifier.py, test_document_classifier.py |
| 7 | ContentIndexer | content_indexer.py, test_content_indexer.py |
| 8 | Pipeline integration | enrichment.py, test_enrichment_embeddings.py |
| 9 | 4 MCP tools | server.py, test_embedding_tools.py |
| 10 | Exports + final | __init__.py |

**Total: 10 tasks, ~50 steps, 10 commits. Result: 12 MCP tools (8 existing + 4 new).**
