"""File-based embedding cache using SHA-256 content hashing."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Persistent file-based cache for embedding vectors.

    Each entry is stored as a JSON file named by its key inside *cache_dir*.
    Keys are typically SHA-256 hashes of the input text/bytes, but any
    string key is accepted.

    Parameters
    ----------
    cache_dir:
        Directory where cache files are stored.  Created on first write if
        it does not exist.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._dir = Path(cache_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def content_hash(self, text: str) -> str:
        """Return a deterministic SHA-256 hex digest for *text*."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[list[float]]:
        """Return cached embedding for *key*, or ``None`` if not found."""
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("embedding")
        except Exception as exc:
            logger.debug("Cache read error for key %r: %s", key, exc)
            return None

    def put(self, key: str, embedding: list[float]) -> None:
        """Store *embedding* under *key*, creating the cache dir if needed."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path_for(key)
        try:
            path.write_text(
                json.dumps({"embedding": embedding}),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Cache write error for key %r: %s", key, exc)

    def clear(self) -> None:
        """Delete all cached entries."""
        if not self._dir.exists():
            return
        for p in self._dir.glob("*.json"):
            try:
                p.unlink()
            except Exception as exc:
                logger.debug("Could not remove cache file %s: %s", p, exc)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _path_for(self, key: str) -> Path:
        # Sanitise key so it is safe as a filename (replace slashes etc.)
        safe = key.replace("/", "_").replace("\\", "_")[:200]
        return self._dir / f"{safe}.json"
