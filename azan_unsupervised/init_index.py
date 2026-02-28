"""
init_index.py — First-time indexing script.

Run this manually before starting the API server to build the initial
FAISS index from knowledge_base.txt.

Usage:
    cd /Applications/AZAN/azan_unsupervised
    python init_index.py
"""

import logging
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

import config
from core.embedding_engine import EmbeddingEngine
from core.vector_store import VectorStore
from core.cluster_engine import ClusterEngine
from core.unsupervised_learner import UnsupervisedLearner

# Setup logging to console for visibility during init
logging.basicConfig(
    level=logging.INFO,
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("init")


def main():
    logger.info("═" * 60)
    logger.info("  AZAN Unsupervised Learning — First-Time Initialization")
    logger.info("═" * 60)

    if not config.KNOWLEDGE_BASE_PATH.exists():
        logger.error("knowledge_base.txt not found at: %s", config.KNOWLEDGE_BASE_PATH)
        sys.exit(1)

    logger.info("Step 1/4: Loading embedding model (%s)...", config.EMBEDDING_MODEL)
    embedding_engine = EmbeddingEngine(
        model_name=config.EMBEDDING_MODEL,
        cache_path=config.EMBEDDING_CACHE_FILE,
        batch_size=config.EMBEDDING_BATCH_SIZE,
    )

    logger.info("Step 2/4: Initializing FAISS vector store...")
    vector_store = VectorStore(
        index_file=config.FAISS_INDEX_FILE,
        metadata_file=config.FAISS_METADATA_FILE,
        dim=config.EMBEDDING_DIM,
    )

    logger.info("Step 3/4: Setting up cluster engine...")
    cluster_engine = ClusterEngine(
        state_file=config.CLUSTER_STATE_FILE,
        min_entries=config.CLUSTER_MIN_ENTRIES,
        max_k=config.CLUSTER_MAX_K,
        rerun_every=config.CLUSTER_RERUN_EVERY,
    )

    logger.info("Step 4/4: Running full index on knowledge_base.txt...")
    learner = UnsupervisedLearner(
        knowledge_base_path=config.KNOWLEDGE_BASE_PATH,
        embedding_engine=embedding_engine,
        vector_store=vector_store,
        cluster_engine=cluster_engine,
        checkpoint_file=config.FAISS_CHECKPOINT_FILE,
        poll_interval=config.WATCHER_POLL_INTERVAL,
        cluster_rerun_every=config.CLUSTER_RERUN_EVERY,
    )

    count = learner.run_full_index()

    logger.info("═" * 60)
    logger.info("✅ Initialization complete!")
    logger.info("   Entries indexed : %d", count)
    logger.info("   FAISS index size: %.2f MB", vector_store.index_size_bytes() / 1024 / 1024)
    logger.info("   Cluster count   : %d", cluster_engine.get_k())
    logger.info("   Embedding cache : %d entries", embedding_engine.cache_size())
    logger.info("═" * 60)
    logger.info("")
    logger.info("Start the API server with:")
    logger.info("  cd /Applications/AZAN/azan_unsupervised")
    logger.info("  uvicorn api.app:app --host 0.0.0.0 --port 8001")
    logger.info("")
    logger.info("Open dashboard at: http://localhost:8001/dashboard")


if __name__ == "__main__":
    main()
