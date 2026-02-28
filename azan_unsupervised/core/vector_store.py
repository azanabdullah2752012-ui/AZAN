"""
vector_store.py — FAISS persistent vector database.

Stores normalized float32 embeddings + aligned metadata JSON.
Supports add, search (cosine via inner product), rebuild, save, load.
Targets <2 GB RAM for 10k–100k+ entries.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss
except ImportError:
    faiss = None
    logger.error("faiss-cpu not installed! Run: pip install faiss-cpu")


class VectorStore:
    """
    FAISS-backed persistent vector store.

    Index type: IndexFlatIP (inner product = cosine when vectors are normalized)
    Metadata: parallel JSON list, aligned by integer FAISS ID.
    """

    def __init__(self, index_file: Path, metadata_file: Path, dim: int = 384):
        if faiss is None:
            raise RuntimeError("faiss-cpu is required. Install with: pip install faiss-cpu")
        self.index_file = Path(index_file)
        self.metadata_file = Path(metadata_file)
        self.dim = dim
        self._lock = threading.RLock()
        self._index: Optional[faiss.Index] = None
        self._metadata: List[Dict[str, Any]] = []
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """
        Add normalized embeddings and their metadata to the store.
        embeddings: float32 array (N, dim), metadata: list of N dicts.
        """
        if len(embeddings) == 0:
            return
        embeddings = embeddings.astype(np.float32)
        self._ensure_index()

        with self._lock:
            self._index.add(embeddings)
            self._metadata.extend(metadata)

        logger.info("Added %d entries. Total: %d", len(embeddings), self.count())
        self.save()

    def search(
        self, query_vector: np.ndarray, top_k: int = 5
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Search for top_k nearest neighbours.
        Returns list of (cosine_score, metadata_dict) tuples, descending by score.
        Returns [] if index is empty.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        query = query_vector.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(query)

        k = min(top_k, self._index.ntotal)
        with self._lock:
            scores, indices = self._index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            results.append((float(score), self._metadata[idx]))
        return results

    def rebuild(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """Wipe and rebuild the index from scratch (for full reindex)."""
        with self._lock:
            self._index = faiss.IndexFlatIP(self.dim)
            self._metadata = []
        self.add(embeddings, metadata)
        logger.info("Index rebuilt: %d entries", self.count())

    def count(self) -> int:
        """Total number of entries currently indexed."""
        if self._index is None:
            return 0
        return int(self._index.ntotal)

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Return copy of metadata list."""
        with self._lock:
            return list(self._metadata)

    def index_size_bytes(self) -> int:
        """Approximate RAM size of the FAISS index in bytes."""
        if self._index is None:
            return 0
        # Float32: 4 bytes * dim * count
        return 4 * self.dim * self.count()

    def save(self) -> None:
        """Persist FAISS index and metadata to disk."""
        with self._lock:
            try:
                self.index_file.parent.mkdir(parents=True, exist_ok=True)
                faiss.write_index(self._index, str(self.index_file))
                with self.metadata_file.open("w", encoding="utf-8") as f:
                    json.dump(self._metadata, f, ensure_ascii=False, indent=2)
                logger.debug("VectorStore saved: %d entries", self.count())
            except Exception as e:
                logger.error("VectorStore save failed: %s", e)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ensure_index(self) -> None:
        if self._index is None:
            self._index = faiss.IndexFlatIP(self.dim)

    def _load(self) -> None:
        """Load existing index and metadata from disk if available."""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self._index = faiss.read_index(str(self.index_file))
                with self.metadata_file.open("r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
                logger.info("VectorStore loaded: %d entries", self.count())
            except Exception as e:
                logger.warning("VectorStore load failed (%s) — starting fresh", e)
                self._index = faiss.IndexFlatIP(self.dim)
                self._metadata = []
        else:
            self._index = faiss.IndexFlatIP(self.dim)
            self._metadata = []
            logger.info("VectorStore initialized (empty)")
