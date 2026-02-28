"""
incremental_indexer.py — Detects file changes and reindexes only new data.

Uses file modification time and line count tracking to detect additions
to knowledge_base.txt. Generates embeddings only for new entries and
appends to the FAISS index without a full rebuild.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_CHECKPOINT_VERSION = 1


class IncrementalIndexer:
    """
    Monitors knowledge_base.txt for file changes and reindexes new entries.

    State tracked in checkpoint.json:
        - last_line_count: total lines when last indexed
        - last_mtime: file modification timestamp
        - indexed_ids: set of raw_ids already indexed (to avoid duplicates)
        - total_indexed: cumulative count of indexed entries
    """

    def __init__(
        self,
        knowledge_base_path: Path,
        checkpoint_file: Path,
        embed_fn: Callable[[List[str]], Any],   # embedding_engine.embed
        store_add_fn: Callable,                 # vector_store.add
        cluster_fn: Optional[Callable] = None, # cluster_engine.should_recluster + fit
    ):
        self.kb_path = Path(knowledge_base_path)
        self.checkpoint_file = Path(checkpoint_file)
        self.embed_fn = embed_fn
        self.store_add_fn = store_add_fn
        self.cluster_fn = cluster_fn
        self._state = self._load_checkpoint()

    # ── Public API ────────────────────────────────────────────────────────────

    def full_index(self, all_metadata_getter: Callable) -> int:
        """
        Full (re)index: load all entries from knowledge base,
        embed them, and rebuild the vector store.
        Returns number of entries indexed.
        """
        from core.knowledge_loader import KnowledgeLoader
        loader = KnowledgeLoader(self.kb_path)
        entries = loader.load_all()

        if not entries:
            logger.warning("No entries found in knowledge base!")
            return 0

        texts = [e["embed_text"] for e in entries]
        logger.info("Full indexing: %d entries...", len(entries))
        embeddings = self.embed_fn(texts)

        # Reset vector store and add all
        self.store_add_fn(embeddings, entries, full_rebuild=True)
        self._state["last_line_count"] = loader.count_lines()
        self._state["last_mtime"] = self.kb_path.stat().st_mtime
        self._state["indexed_ids"] = sorted([e["raw_id"] for e in entries])  # list not set
        self._state["total_indexed"] = len(entries)
        self._save_checkpoint()

        logger.info("Full index complete: %d entries", len(entries))
        return len(entries)

    def check_and_update(self) -> int:
        """
        Check if knowledge_base.txt has been modified since last index.
        If so, find and index only new entries.
        Returns number of newly indexed entries (0 if no change).
        """
        if not self.kb_path.exists():
            logger.error("Knowledge base file missing: %s", self.kb_path)
            return 0

        current_mtime = self.kb_path.stat().st_mtime
        last_mtime = self._state.get("last_mtime", 0)

        if current_mtime <= last_mtime:
            return 0  # No change

        logger.info("Knowledge base changed — checking for new entries...")
        return self._index_new_entries()

    def total_indexed(self) -> int:
        return self._state.get("total_indexed", 0)

    def last_run_time(self) -> float:
        return self._state.get("last_mtime", 0.0)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _index_new_entries(self) -> int:
        from core.knowledge_loader import KnowledgeLoader
        loader = KnowledgeLoader(self.kb_path)
        last_line = self._state.get("last_line_count", 0)
        indexed_ids: set = set(self._state.get("indexed_ids", []))

        # Load entries starting from where we left off
        new_entries = [
            e for e in loader.load_from_line(last_line)
            if e["raw_id"] not in indexed_ids
        ]

        if not new_entries:
            # File changed but no new parseable entries (e.g. whitespace edit)
            self._state["last_mtime"] = self.kb_path.stat().st_mtime
            self._save_checkpoint()
            return 0

        texts = [e["embed_text"] for e in new_entries]
        logger.info("Incrementally indexing %d new entries...", len(new_entries))
        embeddings = self.embed_fn(texts)

        # Append to existing vector store
        self.store_add_fn(embeddings, new_entries, full_rebuild=False)

        # Update state — ensure indexed_ids is always serializable list (not set)
        for e in new_entries:
            indexed_ids.add(e["raw_id"])
        self._state["indexed_ids"] = sorted(list(indexed_ids))  # sort for determinism
        self._state["last_line_count"] = loader.count_lines()
        self._state["last_mtime"] = self.kb_path.stat().st_mtime
        self._state["total_indexed"] = self._state.get("total_indexed", 0) + len(new_entries)
        self._save_checkpoint()

        logger.info("Incremental index done: +%d entries (total: %d)",
                    len(new_entries), self._state["total_indexed"])
        return len(new_entries)

    def _load_checkpoint(self) -> Dict[str, Any]:
        if self.checkpoint_file.exists():
            try:
                with self.checkpoint_file.open("r") as f:
                    state = json.load(f)
                logger.info(
                    "Checkpoint loaded: %d total indexed", state.get("total_indexed", 0)
                )
                return state
            except Exception as e:
                logger.warning("Checkpoint load failed (%s) — starting fresh", e)
        return {
            "version": _CHECKPOINT_VERSION,
            "last_line_count": 0,
            "last_mtime": 0.0,
            "indexed_ids": [],
            "total_indexed": 0,
        }

    def _save_checkpoint(self) -> None:
        try:
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            with self.checkpoint_file.open("w") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.error("Checkpoint save failed: %s", e)
