"""
unsupervised_learner.py — 24/7 autonomous background indexing loop.

Starts a daemon thread that:
  1. Runs a full index on startup (if not already done)
  2. Polls knowledge_base.txt every N seconds for changes
  3. Re-clusters after every CLUSTER_RERUN_EVERY new entries
  4. Saves checkpoint stats after every cycle
  5. Exposes status dict for the API dashboard

This is pure unsupervised INDEXING, not RL training.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class UnsupervisedLearner:
    """
    Autonomous background indexing loop.
    Thread-safe. Graceful shutdown via stop() or daemon thread auto-exit.
    """

    def __init__(
        self,
        knowledge_base_path: Path,
        embedding_engine,       # EmbeddingEngine instance
        vector_store,           # VectorStore instance
        cluster_engine,         # ClusterEngine instance
        checkpoint_file: Path,
        poll_interval: float = 5.0,
        cluster_rerun_every: int = 20,
    ):
        self.kb_path = knowledge_base_path
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.cluster_engine = cluster_engine
        self.checkpoint_file = checkpoint_file
        self.poll_interval = poll_interval
        self.cluster_rerun_every = cluster_rerun_every

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._new_since_cluster: int = 0

        # Status exposed to API
        self._status: Dict[str, Any] = {
            "running": False,
            "total_indexed": 0,
            "last_index_time": None,
            "last_cluster_time": None,
            "cluster_count": 0,
            "new_since_start": 0,
            "loop_iteration": 0,
            "error": None,
        }

        # Build indexer (wraps embedding + store)
        from core.incremental_indexer import IncrementalIndexer
        self._indexer = IncrementalIndexer(
            knowledge_base_path=self.kb_path,
            checkpoint_file=self.checkpoint_file,
            embed_fn=self.embedding_engine.embed,
            store_add_fn=self._store_add_handler,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background daemon thread."""
        if self._thread and self._thread.is_alive():
            logger.info("UnsupervisedLearner already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="AZANLearner"
        )
        self._thread.start()
        logger.info("UnsupervisedLearner background thread started.")

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("UnsupervisedLearner stopped.")

    def run_full_index(self) -> int:
        """Synchronously run a full index (use for init or manual reindex)."""
        logger.info("Running full index on all knowledge entries...")
        count = self._indexer.full_index(self.vector_store.get_all_metadata)
        self._status["total_indexed"] = self.vector_store.count()
        self._status["last_index_time"] = time.time()
        self._maybe_recluster(count)
        return count

    def get_status(self) -> Dict[str, Any]:
        """Return current status dict (thread-safe read)."""
        status = dict(self._status)
        status["total_indexed"] = self.vector_store.count()
        status["cluster_count"] = self.cluster_engine.get_k()
        status["running"] = self._thread.is_alive() if self._thread else False
        return status

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Main loop: run full index once, then poll for changes."""
        self._status["running"] = True
        logger.info("Background loop starting — running initial full index...")

        try:
            # Initial full index if store is empty
            if self.vector_store.count() == 0:
                n = self._indexer.full_index(self.vector_store.get_all_metadata)
                self._status["total_indexed"] = n
                self._status["last_index_time"] = time.time()
                self._maybe_recluster(n)
            else:
                logger.info("Existing index found (%d entries). Checking for updates...",
                            self.vector_store.count())
                n = self._indexer.check_and_update()
                if n > 0:
                    self._status["new_since_start"] += n
                    self._status["last_index_time"] = time.time()
                    self._maybe_recluster(n)

        except Exception as e:
            logger.error("Error during initial index: %s", e, exc_info=True)
            self._status["error"] = str(e)

        # Polling loop
        iteration = 0
        while not self._stop_event.is_set():
            self._stop_event.wait(self.poll_interval)
            if self._stop_event.is_set():
                break

            iteration += 1
            self._status["loop_iteration"] = iteration

            try:
                n = self._indexer.check_and_update()
                if n > 0:
                    self._status["new_since_start"] = self._status.get("new_since_start", 0) + n
                    self._status["total_indexed"] = self.vector_store.count()
                    self._status["last_index_time"] = time.time()
                    logger.info("Auto-indexed %d new entries (total: %d)", n, self.vector_store.count())
                    self._maybe_recluster(n)
            except Exception as e:
                logger.error("Error in indexing loop: %s", e, exc_info=True)
                self._status["error"] = str(e)

        self._status["running"] = False
        logger.info("Background loop stopped.")

    def _maybe_recluster(self, new_count: int) -> None:
        """Re-cluster if enough new entries have accumulated."""
        self._new_since_cluster += new_count
        if self.vector_store.count() < 10:
            return
        if self._new_since_cluster >= self.cluster_rerun_every or self.cluster_engine.get_k() == 0:
            try:
                all_meta = self.vector_store.get_all_metadata()
                if len(all_meta) < 2:
                    return
                texts = [m.get("embed_text", m.get("content", "")) for m in all_meta]
                embeddings = self.embedding_engine.embed(texts)
                self.cluster_engine.fit(embeddings)
                self._status["last_cluster_time"] = time.time()
                self._status["cluster_count"] = self.cluster_engine.get_k()
                self._new_since_cluster = 0
                logger.info("Re-clustered: %d clusters", self.cluster_engine.get_k())
            except Exception as e:
                logger.error("Clustering error: %s", e)

    def _store_add_handler(
        self, embeddings, metadata, full_rebuild: bool = False
    ) -> None:
        """Adapter so IncrementalIndexer can call either rebuild or add."""
        if full_rebuild:
            self.vector_store.rebuild(embeddings, metadata)
        else:
            self.vector_store.add(embeddings, metadata)
