"""
embedding_engine.py — Batch embeddings with persistent disk cache.

Uses sentence-transformers (all-MiniLM-L6-v2) locally.
Thread-safe via threading.Lock. Caches embeddings by content hash to
avoid re-computing embeddings across restarts.
"""

import hashlib
import logging
import pickle
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    Local sentence-transformer embedding engine with persistent cache.

    - Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, CPU-optimized)
    - Cache: pickled dict {text_hash: np.ndarray} stored at EMBEDDING_CACHE_FILE
    - Thread-safe: single threading.Lock guards model inference and cache writes
    """

    def __init__(self, model_name: str, cache_path: Path, batch_size: int = 32):
        self.model_name = model_name
        self.cache_path = Path(cache_path)
        self.batch_size = batch_size
        self._lock = threading.Lock()
        self._model = None  # lazy-loaded on first call
        self._cache: Dict[str, np.ndarray] = self._load_cache()
        self._dirty = False  # True when cache has unsaved changes

    # ── Public API ────────────────────────────────────────────────────────────

    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of texts. Returns float32 ndarray shape (N, dim).
        Checks cache first; only calls the model for uncached texts.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        embeddings = np.zeros((len(texts), 384), dtype=np.float32)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        # Cache lookup
        for i, text in enumerate(texts):
            key = self._hash(text)
            if key in self._cache:
                embeddings[i] = self._cache[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Compute only uncached
        if uncached_texts:
            logger.info("Computing embeddings for %d new texts...", len(uncached_texts))
            new_embeddings = self._batch_embed(uncached_texts)
            for idx, (orig_i, text) in enumerate(zip(uncached_indices, uncached_texts)):
                vec = new_embeddings[idx]
                embeddings[orig_i] = vec
                self._cache[self._hash(text)] = vec
            self._dirty = True
            self.save_cache()

        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single query string. Returns shape (384,)."""
        return self.embed([text])[0]

    def save_cache(self) -> None:
        """Persist embedding cache to disk."""
        if not self._dirty:
            return
        with self._lock:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("wb") as f:
                pickle.dump(self._cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            self._dirty = False
            logger.debug("Embedding cache saved (%d entries)", len(self._cache))

    def cache_size(self) -> int:
        """Number of cached embeddings."""
        return len(self._cache)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_model(self):
        """Lazy-load the model on first call (thread-safe)."""
        if self._model is None:
            with self._lock:
                if self._model is None:  # double-check after lock
                    logger.info("Loading embedding model: %s", self.model_name)
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer(self.model_name)
                    logger.info("Embedding model loaded.")
        return self._model

    def _batch_embed(self, texts: List[str]) -> np.ndarray:
        """Run model inference in batches. Returns float32 ndarray."""
        model = self._get_model()
        all_vecs: List[np.ndarray] = []
        with self._lock:
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start : start + self.batch_size]
                vecs = model.encode(
                    batch,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # unit vectors for cosine via dot product
                )
                all_vecs.append(vecs.astype(np.float32))
        return np.vstack(all_vecs)

    @staticmethod
    def _hash(text: str) -> str:
        """SHA-256 hash of text for cache key."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load_cache(self) -> Dict[str, np.ndarray]:
        """Load cache from disk, or return empty dict."""
        if self.cache_path.exists():
            try:
                with self.cache_path.open("rb") as f:
                    cache = pickle.load(f)
                logger.info("Loaded embedding cache: %d entries", len(cache))
                return cache
            except Exception as e:
                logger.warning("Cache load failed (%s) — starting fresh", e)
        return {}
