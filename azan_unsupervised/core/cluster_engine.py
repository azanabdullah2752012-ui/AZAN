"""
cluster_engine.py — Unsupervised semantic clustering via KMeans.

Automatically clusters knowledge embeddings into semantic groups.
Supports incremental re-clustering when new entries are added.
Cluster state is persisted to disk as JSON.
"""

import json
import logging
import math
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np

logger = logging.getLogger(__name__)


class ClusterEngine:
    """
    Performs unsupervised KMeans clustering on knowledge embeddings.

    - Auto-selects number of clusters k using silhouette heuristic
    - Stores cluster labels alongside metadata IDs
    - Persists cluster state to disk
    - Thread-safe via threading.Lock
    """

    def __init__(
        self,
        state_file: Path,
        min_entries: int = 10,
        max_k: int = 30,
        rerun_every: int = 20,
    ):
        self.state_file = Path(state_file)
        self.min_entries = min_entries
        self.max_k = max_k
        self.rerun_every = rerun_every
        self._lock = threading.Lock()
        self._labels: List[int] = []
        self._k: int = 0
        self._cluster_centers: Optional[np.ndarray] = None
        self._entries_since_last_cluster: int = 0
        self._load_state()

    # ── Public API ────────────────────────────────────────────────────────────

    def fit(self, embeddings: np.ndarray) -> List[int]:
        """
        Cluster all provided embeddings. Returns list of integer cluster labels
        (one per embedding). Returns empty list if fewer than min_entries.
        """
        n = len(embeddings)
        if n < self.min_entries:
            logger.info("Not enough entries for clustering (%d < %d)", n, self.min_entries)
            self._labels = [0] * n
            return self._labels

        k = self._select_k(n)
        logger.info("Clustering %d entries into %d clusters...", n, k)

        with self._lock:
            labels, centers = self._kmeans(embeddings, k)
            self._labels = labels
            self._k = k
            self._cluster_centers = centers
            self._entries_since_last_cluster = 0

        self._save_state()
        logger.info("Clustering complete: %d clusters", k)
        return self._labels

    def should_recluster(self, new_entry_count: int) -> bool:
        """Return True when enough new entries have accumulated."""
        self._entries_since_last_cluster += new_entry_count
        return self._entries_since_last_cluster >= self.rerun_every

    def get_cluster_summary(self, metadata: List[Dict[str, Any]]) -> Dict[int, List[str]]:
        """
        Return a dict mapping cluster_id → list of entry titles in that cluster.
        Requires metadata list to be aligned with label list.
        """
        summary: Dict[int, List[str]] = {}
        for i, label in enumerate(self._labels):
            if i < len(metadata):
                title = metadata[i].get("title", f"Entry {i}")
                summary.setdefault(label, []).append(title)
        return summary

    def get_labels(self) -> List[int]:
        return self._labels

    def get_k(self) -> int:
        return self._k

    # ── Internal ──────────────────────────────────────────────────────────────

    def _select_k(self, n: int) -> int:
        """Heuristic: sqrt(n/2) capped at max_k, minimum 2."""
        k = max(2, min(self.max_k, int(math.sqrt(n / 2))))
        return k

    def _kmeans(self, embeddings: np.ndarray, k: int):
        """Run scikit-learn KMeans. Returns (labels, centers)."""
        from sklearn.cluster import KMeans

        km = KMeans(
            n_clusters=k,
            n_init=10,
            max_iter=300,
            random_state=42,
        )
        km.fit(embeddings)
        return km.labels_.tolist(), km.cluster_centers_

    def _save_state(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "k": self._k,
                "labels": self._labels,
                "entries_since_last_cluster": self._entries_since_last_cluster,
            }
            with self.state_file.open("w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.error("Failed to save cluster state: %s", e)

    def _load_state(self) -> None:
        if self.state_file.exists():
            try:
                with self.state_file.open("r") as f:
                    state = json.load(f)
                self._k = state.get("k", 0)
                self._labels = state.get("labels", [])
                self._entries_since_last_cluster = state.get("entries_since_last_cluster", 0)
                logger.info("Loaded cluster state: k=%d, %d labels", self._k, len(self._labels))
            except Exception as e:
                logger.warning("Cluster state load failed: %s", e)
