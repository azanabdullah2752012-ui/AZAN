"""
AZAN Unsupervised Learning Framework - Central Configuration
All paths, model settings, thresholds, and hyperparameters live here.
"""

import os
from pathlib import Path

# ─── Base Paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CACHE_DIR = BASE_DIR / "cache"
INDEX_DIR = BASE_DIR / "index"

# ─── Primary Data Source ──────────────────────────────────────────────────────
KNOWLEDGE_BASE_PATH = DATA_DIR / "knowledge_base.txt"

# ─── Embedding Model ──────────────────────────────────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384          # Dimension for all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE = 32    # Entries per embedding batch (memory-efficient)
EMBEDDING_CACHE_FILE = CACHE_DIR / "embedding_cache.pkl"

# ─── FAISS Vector Store ───────────────────────────────────────────────────────
FAISS_INDEX_FILE = INDEX_DIR / "knowledge.index"
FAISS_METADATA_FILE = INDEX_DIR / "metadata.json"
FAISS_CHECKPOINT_FILE = INDEX_DIR / "checkpoint.json"

# ─── Chunking ─────────────────────────────────────────────────────────────────
CHUNK_MIN_TOKENS = 30        # Skip entries shorter than this
CHUNK_MAX_TOKENS = 800       # Truncate entries longer than this (token approx)

# ─── Retrieval & Inference ────────────────────────────────────────────────────
TOP_K = 5                    # Top-k results to retrieve from FAISS
SIMILARITY_THRESHOLD = 0.35  # Below this cosine score → hard refusal
REFUSAL_MESSAGE = "No verified data available in the local knowledge base."

# ─── Clustering ───────────────────────────────────────────────────────────────
CLUSTER_MIN_ENTRIES = 10     # Don't cluster until we have at least this many
CLUSTER_MAX_K = 30           # Maximum number of clusters (KMeans)
CLUSTER_RERUN_EVERY = 20     # Re-cluster after every N new entries
CLUSTER_STATE_FILE = INDEX_DIR / "clusters.json"

# ─── Background Indexer ───────────────────────────────────────────────────────
WATCHER_POLL_INTERVAL = 5.0  # Seconds between file-change checks
WATCHER_DEBOUNCE = 2.0       # Seconds to wait after change before indexing

# ─── Ollama / Llama3 Inference ────────────────────────────────────────────────
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3"
OLLAMA_TIMEOUT = 60          # Request timeout (seconds)
OLLAMA_MAX_TOKENS = 512

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_FILE = LOGS_DIR / "system.log"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB log rotation
LOG_BACKUP_COUNT = 3

# ─── API ─────────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8001
API_TITLE = "AZAN Unsupervised Knowledge System"
API_VERSION = "1.0.0"

# ─── Auto-create directories ─────────────────────────────────────────────────
for _d in [DATA_DIR, LOGS_DIR, CACHE_DIR, INDEX_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
