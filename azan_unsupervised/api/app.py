"""
app.py — FastAPI server for AZAN Unsupervised Knowledge System.

Starts the UnsupervisedLearner background thread on startup.
Provides all required API endpoints + dashboard.
"""

import logging
import logging.handlers
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Add parent to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from core.embedding_engine import EmbeddingEngine
from core.vector_store import VectorStore
from core.cluster_engine import ClusterEngine
from core.unsupervised_learner import UnsupervisedLearner
from core.data_only_inference import DataOnlyInference

# ── Logging Setup ─────────────────────────────────────────────────────────────
config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
handler = logging.handlers.RotatingFileHandler(
    config.LOG_FILE, maxBytes=config.LOG_MAX_BYTES, backupCount=config.LOG_BACKUP_COUNT
)
logging.basicConfig(
    level=logging.INFO,
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
    handlers=[handler, logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ── Global singletons (initialized in lifespan) ───────────────────────────────
_embedding_engine: Optional[EmbeddingEngine] = None
_vector_store: Optional[VectorStore] = None
_cluster_engine: Optional[ClusterEngine] = None
_learner: Optional[UnsupervisedLearner] = None
_inference: Optional[DataOnlyInference] = None
_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all components on startup; clean up on shutdown."""
    global _embedding_engine, _vector_store, _cluster_engine, _learner, _inference

    logger.info("=== AZAN Unsupervised System Starting ===")

    _embedding_engine = EmbeddingEngine(
        model_name=config.EMBEDDING_MODEL,
        cache_path=config.EMBEDDING_CACHE_FILE,
        batch_size=config.EMBEDDING_BATCH_SIZE,
    )
    _vector_store = VectorStore(
        index_file=config.FAISS_INDEX_FILE,
        metadata_file=config.FAISS_METADATA_FILE,
        dim=config.EMBEDDING_DIM,
    )
    _cluster_engine = ClusterEngine(
        state_file=config.CLUSTER_STATE_FILE,
        min_entries=config.CLUSTER_MIN_ENTRIES,
        max_k=config.CLUSTER_MAX_K,
        rerun_every=config.CLUSTER_RERUN_EVERY,
    )
    _learner = UnsupervisedLearner(
        knowledge_base_path=config.KNOWLEDGE_BASE_PATH,
        embedding_engine=_embedding_engine,
        vector_store=_vector_store,
        cluster_engine=_cluster_engine,
        checkpoint_file=config.FAISS_CHECKPOINT_FILE,
        poll_interval=config.WATCHER_POLL_INTERVAL,
        cluster_rerun_every=config.CLUSTER_RERUN_EVERY,
    )
    _inference = DataOnlyInference(
        vector_store=_vector_store,
        embedding_engine=_embedding_engine,
        ollama_host=config.OLLAMA_HOST,
        ollama_model=config.OLLAMA_MODEL,
        ollama_timeout=config.OLLAMA_TIMEOUT,
        top_k=config.TOP_K,
        similarity_threshold=config.SIMILARITY_THRESHOLD,
    )

    # Start 24/7 background indexing loop
    _learner.start()
    logger.info("Background indexing loop started.")

    yield

    # Shutdown
    logger.info("Shutting down AZAN Unsupervised System...")
    if _learner:
        _learner.stop()


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    lifespan=lifespan,
)


# ── Request / Response Models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str
    model: Optional[str] = None  # Override model if needed


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "system": "AZAN Unsupervised Knowledge System"}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Data-only grounded response using Ollama Llama3.
    Returns REFUSAL if no relevant knowledge is found.
    """
    if not _inference:
        raise HTTPException(503, "System not initialized")
    result = _inference.chat(req.query)
    return result


@app.post("/knowledge/search")
def knowledge_search(req: SearchRequest):
    """Semantic search returning top-k matching knowledge chunks."""
    if not _inference:
        raise HTTPException(503, "System not initialized")
    if req.top_k < 1 or req.top_k > 50:
        raise HTTPException(400, "top_k must be between 1 and 50")
    result = _inference.search(req.query)
    if result is None:
        return {"chunks": [], "max_score": 0.0}
    return result


@app.get("/clusters/view")
def clusters_view():
    """Return cluster distribution and representative entries per cluster."""
    if not _cluster_engine or not _vector_store:
        raise HTTPException(503, "System not initialized")
    metadata = _vector_store.get_all_metadata()
    labels = _cluster_engine.get_labels()
    k = _cluster_engine.get_k()

    summary = _cluster_engine.get_cluster_summary(metadata)
    distribution = {str(cluster_id): len(titles) for cluster_id, titles in summary.items()}
    # Return top-3 representative titles per cluster
    representatives = {
        str(cluster_id): titles[:3] for cluster_id, titles in summary.items()
    }
    return {
        "cluster_count": k,
        "total_entries": len(metadata),
        "distribution": distribution,
        "representatives": representatives,
    }


@app.get("/system/status")
def system_status():
    """System health and current indexing state."""
    if not _learner:
        raise HTTPException(503, "System not initialized")
    status = _learner.get_status()
    status["uptime_seconds"] = int(time.time() - _start_time)
    status["knowledge_base_exists"] = config.KNOWLEDGE_BASE_PATH.exists()
    return status


@app.get("/system/metrics")
def system_metrics():
    """Detailed metrics: embedding count, index size, memory, latency."""
    if not _vector_store or not _embedding_engine:
        raise HTTPException(503, "System not initialized")
    process = psutil.Process()
    mem_info = process.memory_info()
    index_bytes = _vector_store.index_size_bytes()
    return {
        "embedding_count": _vector_store.count(),
        "index_size_mb": round(index_bytes / 1024 / 1024, 2),
        "cache_size": _embedding_engine.cache_size(),
        "memory_used_mb": round(mem_info.rss / 1024 / 1024, 1),
        "cluster_count": _cluster_engine.get_k() if _cluster_engine else 0,
        "uptime_seconds": int(time.time() - _start_time),
        "learner_status": _learner.get_status() if _learner else {},
    }


@app.post("/system/reindex")
def system_reindex():
    """Manually trigger a full reindex of all knowledge entries."""
    if not _learner:
        raise HTTPException(503, "System not initialized")
    logger.info("Manual reindex triggered via API")
    count = _learner.run_full_index()
    return {"status": "reindex_complete", "entries_indexed": count}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Serve the real-time monitoring dashboard."""
    from dashboard.dashboard import get_dashboard_html
    return HTMLResponse(content=get_dashboard_html())
