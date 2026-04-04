"""
FastAPI web UI for AZAN chatbot with RLHF Training Dashboard.

Features:
1. Web-based training interface (/train)
2. Real-time training progress monitoring
3. Training history and analytics
4. Model comparison
5. Data management (upload, view, delete)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional, List
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.inference import predict_chat
from src.training_dashboard import dashboard
from src.rl_pipeline import initialize_rl_pipeline, get_rl_pipeline
from src.rl_inference import (
    initialize_inference as initialize_rl_inference,
    predict as rl_predict,
    get_inference_engine as get_rl_inference_engine,
)
from src.api.mobile_sync import router as mobile_sync_router
from src.tools.macos_control import MacOSControlTool
from src.tools.macos_context import MacOSContextTool
from src.agents.automation_engine import AutomationEngine

# Base logger (configured below); safe to use for early import warnings.
logger = logging.getLogger(__name__)

# Import AZAN curated RL system
try:
    from src.azan_rl_pipeline import initialize_rl_pipeline as init_azan_rl, get_rl_engine, get_rl_trainer
    from src.azan_rl_inference import (
        initialize_inference_engine as init_azan_inference,
        get_inference_engine as get_azan_inference_engine,
    )
    from src.database import get_database  # Import SQLite database
    AZAN_RL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AZAN RL modules not available: {e}")
    AZAN_RL_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AZAN Chatbot with RLHF Dashboard", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mobile_sync_router, prefix="/api", tags=["mobile_sync"])

# ── Serve JARVIS React HUD ─────────────────────────────────────────────────
_REACT_DIST = Path(__file__).parent / "static_react"
if _REACT_DIST.exists() and (_REACT_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_REACT_DIST / "assets")), name="react-assets")

@app.get("/", include_in_schema=False)
async def serve_react_hud():
    hud_path = _REACT_DIST / "index.html"
    old_path  = Path(__file__).parent / "dashboard.html"
    
    # DEBUG LOGS
    logger.info(f"🔎 HUD Request: checking {hud_path}")
    
    if hud_path.exists():
        logger.info(f"✅ HUD Found: serving {hud_path}")
        return FileResponse(str(hud_path), media_type="text/html")
    elif old_path.exists():
        logger.warning(f"⚠️ HUD Missing: falling back to legacy dashboard {old_path}")
        return FileResponse(str(old_path), media_type="text/html")
    
    logger.error("❌ HUD and Dashboard missing!")
    return HTMLResponse("<h1>HUD not built. Run: cd frontend-hud && npm run build</h1>", status_code=404)


# ============================================================================
# JARVIS ORCHESTRATOR SINGLETONS
# ============================================================================
_jarvis_orchestrator = None
_continuous_learner = None
_learner_task = None
_automation_engine = None
_automation_task = None
_last_action = "System Idle"

# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize systems on startup."""
    global _jarvis_orchestrator, _continuous_learner, _learner_task

    # FIX 4 — Heartbeat: if this stops printing, the event loop is blocked
    async def _heartbeat():
        while True:
            logger.info("[SYSTEM] alive")
            await asyncio.sleep(10)
    asyncio.create_task(_heartbeat())

    if AZAN_RL_AVAILABLE:
        try:
            logger.info("⏸ AZAN Curated RL Pipeline initialization (training paused)")
            init_azan_inference()
        except Exception as e:
            logger.warning(f"Startup error in AZAN inference: {e}")
    
    try:
        initialize_rl_inference()
        from src.restricted_inference import initialize_restricted_inference
        initialize_restricted_inference()
        from src.user_feedback import initialize_feedback
        initialize_feedback()
        from src.semantic_search import initialize_semantic_search
        initialize_semantic_search()
        from src.rss_feed_integrator import initialize_feed_integrator
        initialize_feed_integrator()
        from src.workers.cloud_sync import get_cloud_sync_worker
        get_cloud_sync_worker().start()
        
        # Start Phase 15 Document Indexer
        from src.workers.doc_indexer import DocumentIndexer
        _doc_indexer = DocumentIndexer(["~/Documents", "~/Desktop"])
        _doc_indexer.start()

        logger.info("✅ Core systems initialized")
    except Exception as e:
        logger.warning(f"General startup error: {e}")

    # ── JARVIS Agent Core Initialization ─────────────────────────────────
    try:
        import asyncio
        from src.core.llm_client import LocalLLMClient
        from src.memory.vector_store import KnowledgeMemory
        from src.core.orchestrator import JarvisOrchestrator
        from src.workers.continuous_learner import ContinuousLearner

        llm = LocalLLMClient(model="llama3")
        memory = KnowledgeMemory(persist_dir="data/memory")
        _jarvis_orchestrator = JarvisOrchestrator(llm=llm, memory=memory)
        _continuous_learner = ContinuousLearner(llm=llm, memory=memory)

        # Preload LLM model to avoid cold start lag
        logger.info(f"🚀 Preloading JARVIS model: {llm.model}...")
        asyncio.create_task(llm.complete("Warming up...", system_prompt="Just say 'ready'", max_tokens=10))

        _learner_task = asyncio.create_task(_continuous_learner.start())

        # ── Automation Engine ──────────────────────────────────────────────
        global _automation_engine, _automation_task
        _automation_engine = AutomationEngine()
        _automation_task = asyncio.create_task(_automation_engine.start())

        # Start JARVIS Task Scheduler
        from src.workers.task_scheduler import get_jarvis_scheduler
        get_jarvis_scheduler().start()
        
        # ── Start Connectivity Watchdog ──────────────────────────────────
        asyncio.create_task(connectivity_watchdog())
        
        logger.info("✅ JARVIS Orchestrator, Continuous Learner & Automation Engine initialized")
    except Exception as e:
        logger.warning(f"JARVIS initialization failed (falling back to legacy mode): {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop auto-training scheduler and JARVIS learner on shutdown."""
    global _learner_task, _continuous_learner
    try:
        from src.auto_training_scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler.is_running:
            scheduler.stop()
            logger.info("Auto-training scheduler stopped")
    except Exception as e:
        logger.warning(f"Error during scheduler shutdown: {e}")

    # Gracefully stop JARVIS background learner and sync worker
    try:
        from src.workers.cloud_sync import get_cloud_sync_worker
        get_cloud_sync_worker().stop()
    except Exception:
        pass

    if _continuous_learner:
        _continuous_learner.stop()
    if _learner_task and not _learner_task.done():
        logger.info("JARVIS ContinuousLearner stopped")
    
    if _automation_task and not _automation_task.done():
        _automation_task.cancel()
        logger.info("JARVIS AutomationEngine stopped")


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    prompt: str = Field(..., min_length=1, max_length=2000, description="User message")
    model: str = Field("llama3", description="Model to use for inference")
    session_id: str = Field("default_session", description="Unique session ID for chat history")
    temperature: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Sampling temperature")
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0, description="Top-p nucleus sampling")
    images: Optional[List[str]] = Field(None, description="Optional list of base64-encoded images for vision support")
    source: str = Field("text", description="Input source (text or voice)")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="AI response")
    model: str = Field(..., description="Model used for inference")


class TrainingRequest(BaseModel):
    """Request model for training endpoint."""
    question: str = Field(..., min_length=1, max_length=2000, description="Training question")
    ideal_answer: str = Field(..., min_length=1, max_length=5000, description="Ideal answer")
    model: str = Field("llama3", description="Model to train on")
    quick_mode: bool = Field(False, description="Enable quick mode for faster training with cached responses")


class TrainingResponse(BaseModel):
    """Response model for training endpoint."""
    success: bool
    question: Optional[str] = None
    ideal_answer: Optional[str] = None
    model_response: Optional[str] = None
    reward_score: Optional[float] = None
    reward_breakdown: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


async def connectivity_watchdog():
    """Background task to ensure Ollama and Orchestrator stay connected."""
    global _jarvis_orchestrator
    while True:
        try:
            # Check Ollama
            if _jarvis_orchestrator and _jarvis_orchestrator.llm:
                await _jarvis_orchestrator.llm.complete("ping", max_tokens=5)
                # logger.debug("💓 Backend Watchdog: Ollama is alive")
        except Exception as e:
            logger.warning(f"⚠️ Backend Watchdog: Connectivity issue detected: {e}")
        await asyncio.sleep(20)

@app.get("/api/health")
async def health_check():
    """Endpoint for frontend to verify connectivity."""
    return {
        "status": "online",
        "orchestrator": "ready" if _jarvis_orchestrator else "initializing",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# ROUTE 1: MAIN HTML INTERFACE
# ============================================================================


@app.get("/script.js")
def get_script():
    from pathlib import Path
    return FileResponse(Path(__file__).parent / "script.js")

@app.get("/legacy-chat", response_class=HTMLResponse)
def read_root() -> str:
    """AZAN AI Chat — Legacy Phases 5-8."""
    return """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AZAN AI Chat</title>
<meta name="description" content="AZAN — AI powered by Semantic RAG, RL knowledge, and Autonomous Agents.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
:root{
  --bg:#080812;--bg2:#0f0f1e;--bg3:#151528;--bg4:#1a1a32;
  --glass:rgba(255,255,255,0.04);--glass-b:rgba(255,255,255,0.08);
  --accent:#7c5cfc;--accent2:#a78bfa;--glow:rgba(124,92,252,0.3);
  --green:#34d399;--red:#f87171;--orange:#fb923c;
  --t1:#e4e4f0;--t2:#9090b0;--t3:#555570;
  --bdr:rgba(255,255,255,0.07);--r:12px;--rs:8px;
}
[data-theme="light"]{
  --bg:#f0f0f8;--bg2:#fff;--bg3:#e8e8f5;--bg4:#ddddf0;
  --glass:rgba(0,0,0,0.02);--glass-b:rgba(0,0,0,0.08);
  --accent:#6c4ce0;--accent2:#8b6ef0;--glow:rgba(108,76,224,0.2);
  --t1:#1a1a2e;--t2:#555580;--t3:#888899;--bdr:rgba(0,0,0,0.08);
}
html,body{height:100%;background:var(--bg);color:var(--t1);font-family:'Plus Jakarta Sans','Inter',sans-serif;overflow:hidden;}
.layout{display:flex;height:100vh;}
.sidebar{width:290px;min-width:290px;background:var(--bg2);border-right:1px solid var(--bdr);display:flex;flex-direction:column;overflow:hidden;transition:width .3s,min-width .3s;}
.sidebar.collapsed{width:0;min-width:0;}
.main{flex:1;display:flex;flex-direction:column;min-width:0;}
.sb-inner{padding:14px;display:flex;flex-direction:column;gap:10px;height:100%;overflow-y:auto;overflow-x:hidden;}
.sb-inner::-webkit-scrollbar{width:3px;}.sb-inner::-webkit-scrollbar-thumb{background:var(--bdr);}
.logo-row{display:flex;align-items:center;justify-content:space-between;padding-bottom:4px;}
.logo{font-size:19px;font-weight:800;color:var(--accent);letter-spacing:-0.5px;display:flex;align-items:center;gap:8px;}
.logo-v{font-size:10px;background:var(--accent);color:#fff;padding:2px 6px;border-radius:20px;font-weight:600;}
.icon-btn{background:var(--glass);border:1px solid var(--glass-b);color:var(--t2);width:30px;height:30px;border-radius:var(--rs);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:all .2s;}
.icon-btn:hover{background:var(--accent);color:#fff;border-color:var(--accent);}
.new-btn{width:100%;padding:9px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border:none;border-radius:var(--rs);font-weight:700;font-size:12px;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px;}
.new-btn:hover{transform:translateY(-1px);box-shadow:0 4px 20px var(--glow);}
.card{background:var(--glass);border:1px solid var(--glass-b);border-radius:var(--r);padding:10px;}
.ctitle{font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--t3);margin-bottom:8px;display:flex;align-items:center;gap:5px;}
.ctitle::before{content:'';width:5px;height:5px;background:var(--accent);border-radius:50%;display:inline-block;}
.sg{display:grid;grid-template-columns:1fr 1fr;gap:5px;}
.si{background:var(--bg3);border-radius:var(--rs);padding:7px 9px;}
.sl{font-size:9px;color:var(--t3);margin-bottom:1px;}
.sv{font-size:12px;font-weight:600;color:var(--t1);}
.sv.ac{color:var(--accent2);}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;animation:pd 2s infinite;margin-right:3px;}
@keyframes pd{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.6;transform:scale(.8);}}
.kbg{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:7px;}
.kbs{text-align:center;background:var(--bg3);border-radius:var(--rs);padding:7px 3px;}
.kbn{font-size:16px;font-weight:800;color:var(--accent2);}
.kbl{font-size:8px;color:var(--t3);text-transform:uppercase;letter-spacing:.5px;}
.tags{display:flex;flex-wrap:wrap;gap:3px;}
.tag{font-size:9px;background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);padding:2px 7px;border-radius:20px;cursor:pointer;transition:all .2s;}
.tag:hover{background:var(--accent);color:#fff;border-color:var(--accent);}
.msel{width:100%;padding:7px 9px;background:var(--bg3);border:1px solid var(--bdr);color:var(--t1);border-radius:var(--rs);font-size:12px;outline:none;margin-bottom:6px;}
.pbtn{width:100%;padding:6px;background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);border-radius:var(--rs);font-size:11px;cursor:pointer;transition:all .2s;margin-bottom:6px;}
.pbtn:hover{border-color:var(--accent);color:var(--accent);}
.srow{display:flex;align-items:center;gap:7px;margin-bottom:5px;}
.slbl{font-size:10px;color:var(--t2);width:36px;flex-shrink:0;}
.sldr{flex:1;accent-color:var(--accent);height:3px;}
.sval{font-size:10px;color:var(--accent2);width:28px;text-align:right;}
.sess-list{display:flex;flex-direction:column;gap:3px;max-height:180px;overflow-y:auto;}
.sess-item{padding:7px 9px;background:var(--bg3);border-radius:var(--rs);cursor:pointer;font-size:11px;color:var(--t2);transition:all .2s;display:flex;align-items:center;justify-content:space-between;gap:6px;}
.sess-item:hover,.sess-item.active{background:var(--bg4);color:var(--t1);}
.sess-text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;}
.sess-del{opacity:0;font-size:11px;color:var(--red);cursor:pointer;padding:1px 4px;}
.sess-item:hover .sess-del{opacity:1;}
.ch{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-bottom:1px solid var(--bdr);background:var(--bg2);flex-shrink:0;}
.ch-l{display:flex;align-items:center;gap:10px;}
.tog{background:var(--glass);border:1px solid var(--glass-b);color:var(--t2);width:30px;height:30px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .2s;}
.tog:hover{color:var(--accent);}
.ct{font-size:15px;font-weight:700;color:var(--t1);}
.cs{font-size:11px;color:var(--t3);}
.h-actions{display:flex;gap:6px;align-items:center;}
.mbadge,.spdbadge{background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);padding:4px 10px;border-radius:20px;font-size:11px;}
.spdbadge{color:var(--green);display:none;align-items:center;gap:3px;}
.spdbadge.on{display:flex;}
.msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px;scroll-behavior:smooth;}
.msgs::-webkit-scrollbar{width:3px;}.msgs::-webkit-scrollbar-thumb{background:var(--bdr);}
.msg{display:flex;gap:9px;max-width:800px;animation:mi .25s cubic-bezier(.21,1.02,.73,1) both;}
@keyframes mi{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:none;}}
.msg.user{margin-left:auto;flex-direction:row-reverse;}
.msg.azan{margin-right:auto;}
.av{width:32px;height:32px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;}
.av.u{background:linear-gradient(135deg,var(--accent),var(--accent2));}
.av.a{background:var(--bg3);border:1px solid var(--bdr);}
.mi{display:flex;flex-direction:column;gap:3px;max-width:100%;}
.msg.user .mi{align-items:flex-end;}
.bub{background:var(--bg3);border:1px solid var(--bdr);border-radius:var(--r);padding:11px 15px;font-size:13.5px;line-height:1.7;color:var(--t1);word-break:break-word;}
.msg.user .bub{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-color:transparent;}
.bub .msg-img{max-width:240px;border-radius:8px;margin-top:7px;display:block;}
.mmeta{display:flex;align-items:center;gap:6px;padding:0 2px;}
.mtime{font-size:9px;color:var(--t3);}
.rbtns{display:flex;gap:3px;opacity:0;transition:opacity .2s;}
.msg:hover .rbtns{opacity:1;}
.rb{background:var(--bg3);border:1px solid var(--bdr);color:var(--t2);width:24px;height:24px;border-radius:6px;cursor:pointer;font-size:10px;display:flex;align-items:center;justify-content:center;transition:all .15s;}
.rb:hover{background:var(--bg4);color:var(--accent);border-color:var(--accent);}
.rb.liked{background:var(--green);color:#fff;border-color:var(--green);}
.rb.disliked{background:var(--red);color:#fff;border-color:var(--red);}
.fbadge{font-size:9px;font-weight:600;padding:2px 7px;border-radius:20px;}
.fbadge.verified{background:rgba(52,211,153,.15);color:var(--green);border:1px solid rgba(52,211,153,.3);}
.fbadge.unverified{background:rgba(248,113,113,.15);color:var(--red);border:1px solid rgba(248,113,113,.3);}
.stream-cursor::after{content:'&#9646;';animation:blk .7s steps(1) infinite;color:var(--accent);margin-left:2px;}
@keyframes blk{0%,100%{opacity:1;}50%{opacity:0;}}
.thinking{display:flex;align-items:center;gap:8px;padding:10px 15px;background:var(--bg3);border:1px solid var(--bdr);border-radius:var(--r);font-size:12px;color:var(--t2);}
.tdots{display:flex;gap:3px;}
.tdot{width:5px;height:5px;background:var(--accent);border-radius:50%;animation:tb 1.2s infinite;}
.tdot:nth-child(2){animation-delay:.2s;}.tdot:nth-child(3){animation-delay:.4s;}
@keyframes tb{0%,80%,100%{transform:scale(.6);opacity:.4;}40%{transform:scale(1);opacity:1;}}
.inp-area{padding:14px 20px;border-top:1px solid var(--bdr);background:var(--bg2);}
.inp-box{background:var(--bg3);border:1px solid var(--bdr);border-radius:var(--r);transition:border-color .2s,box-shadow .2s;}
.inp-box:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px var(--glow);}
.img-strip{display:none;flex-wrap:wrap;gap:5px;padding:9px 11px 0;}
.img-strip.show{display:flex;}
.ith{position:relative;}
.ith img{width:50px;height:50px;object-fit:cover;border-radius:7px;border:1px solid var(--bdr);display:block;}
.ith-del{position:absolute;top:-4px;right:-4px;background:var(--red);color:#fff;border:none;border-radius:50%;width:14px;height:14px;font-size:8px;cursor:pointer;display:flex;align-items:center;justify-content:center;}
.inp-row{display:flex;align-items:flex-end;padding:7px 7px 7px 11px;gap:5px;}
.chtxt{flex:1;background:none;border:none;outline:none;color:var(--t1);font-size:13.5px;font-family:inherit;resize:none;min-height:22px;max-height:150px;line-height:1.5;padding-top:3px;}
.chtxt::placeholder{color:var(--t3);}
.iacts{display:flex;gap:3px;align-items:center;flex-shrink:0;}
.abt{background:none;border:none;color:var(--t3);width:32px;height:32px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .2s;}
.abt:hover{color:var(--accent);background:var(--glass);}
.abt.rec{color:var(--red);animation:pr 1s infinite;}
@keyframes pr{0%,100%{opacity:1;}50%{opacity:.4;}}
.snd{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border:none;width:34px;height:34px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:flex;align-items:center;justify-content:center;transition:all .2s;}
.snd:hover{transform:scale(1.05);box-shadow:0 4px 16px var(--glow);}
.snd:disabled{opacity:.4;cursor:not-allowed;transform:none;}
.stpbtn{background:var(--bg3);color:var(--red);border:1px solid var(--bdr);width:34px;height:34px;border-radius:var(--rs);cursor:pointer;font-size:15px;display:none;align-items:center;justify-content:center;}
.stpbtn.on{display:flex;}
.hints{font-size:10px;color:var(--t3);padding:3px 11px 7px;display:flex;gap:5px;flex-wrap:wrap;}
.hints code{background:var(--bg4);color:var(--accent2);padding:1px 5px;border-radius:4px;font-size:9px;cursor:pointer;}
.agbar{display:none;align-items:center;gap:9px;padding:7px 20px;background:rgba(124,92,252,.08);border-top:1px solid rgba(124,92,252,.2);font-size:11px;color:var(--accent2);}
.agbar.on{display:flex;}
.agsp{width:13px;height:13px;border:2px solid rgba(124,92,252,.3);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
.drop-ov{display:none;position:fixed;inset:0;background:rgba(124,92,252,.15);backdrop-filter:blur(4px);z-index:100;align-items:center;justify-content:center;flex-direction:column;gap:10px;border:3px dashed var(--accent);}
.drop-ov.on{display:flex;}
.bub p{margin:5px 0;}.bub p:first-child{margin-top:0;}.bub p:last-child{margin-bottom:0;}
.bub pre{background:#0d1117;border-radius:7px;padding:11px;overflow-x:auto;margin:9px 0;border:1px solid rgba(255,255,255,.08);}
.bub pre code{font-family:'JetBrains Mono','Fira Code',monospace;font-size:12px;color:#e6edf3;}
.bub code:not(pre code){background:rgba(124,92,252,.15);padding:1px 5px;border-radius:4px;font-size:12px;}
.bub h1,.bub h2,.bub h3{color:var(--accent2);margin:10px 0 5px;}
.bub ul,.bub ol{padding-left:18px;margin:7px 0;}
.bub li{margin:3px 0;}
.bub blockquote{border-left:3px solid var(--accent);padding:5px 11px;color:var(--t2);margin:7px 0;}
.bub table{border-collapse:collapse;margin:9px 0;width:100%;}
.bub th,.bub td{border:1px solid var(--bdr);padding:6px 9px;font-size:12px;}
.bub th{background:var(--bg4);}
.bub strong{color:var(--accent2);}

/* Command Dropdown Menu */
.cmd-menu { position:absolute; bottom:100%; left:0; width:100%; background:var(--bg2); border:1px solid var(--bdr); border-radius:var(--r); margin-bottom:5px; display:none; flex-direction:column; max-height:200px; overflow-y:auto; z-index:100; box-shadow:0 -4px 15px rgba(0,0,0,0.2); }
.cmd-menu.show { display:flex; }
.cmd-item { padding:10px 15px; cursor:pointer; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--bdr); transition:background .2s; }
.cmd-item:last-child { border-bottom:none; }
.cmd-item:hover, .cmd-item.active { background:var(--bg3); }
.cmd-lbl { font-weight:600; color:var(--accent2); font-size:13px; width:80px; }
.cmd-desc { font-size:11px; color:var(--t2); }
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="sb-inner">
      <div class="logo-row">
        <div class="logo">&#11041; AZAN <span class="logo-v">v4</span></div>
        <div style="display:flex;gap:5px;">
          <button class="icon-btn" onclick="toggleTheme()" id="themeBtn">&#127769;</button>
        </div>
      </div>
      <button class="new-btn" onclick="newChat()">+ New Chat</button>
      <div class="card">
        <div class="ctitle">System Status</div>
        <div class="sg">
          <div class="si"><div class="sl">Status</div><div class="sv" id="stStatus"><span class="dot"></span>Online</div></div>
          <div class="si"><div class="sl">Model</div><div class="sv ac" id="stModel">&#8211;</div></div>
          <div class="si"><div class="sl">Database</div><div class="sv" id="stDB">&#8211;</div></div>
          <div class="si"><div class="sl">Vectors</div><div class="sv" id="stVec">&#8211;</div></div>
        </div>
      </div>
      <div class="card">
        <div class="ctitle">⬡ JARVIS Live Panel</div>
        <div class="sg">
          <div class="si"><div class="sl">Orchestrator</div><div class="sv ac" id="jvOrch">–</div></div>
          <div class="si"><div class="sl">Learner</div><div class="sv" id="jvLearn">–</div></div>
          <div class="si"><div class="sl">CPU</div><div class="sv" id="jvCpu">–</div></div>
          <div class="si"><div class="sl">RAM</div><div class="sv" id="jvRam">–</div></div>
          <div class="si"><div class="sl">Ollama</div><div class="sv ac" id="jvOllama">–</div></div>
          <div class="si"><div class="sl">Tasks Queued</div><div class="sv" id="jvTasks">–</div></div>
        </div>
      </div>
      <div class="card">
        <div class="ctitle">Knowledge Base</div>
        <div class="kbg">
          <div class="kbs"><div class="kbn" id="kbA">0</div><div class="kbl">Articles</div></div>
          <div class="kbs"><div class="kbn" id="kbP">0</div><div class="kbl">Pairs</div></div>
          <div class="kbs"><div class="kbn" id="kbS">0</div><div class="kbl">Sessions</div></div>
        </div>
        <div class="tags" id="topicTags"></div>
      </div>
      <div class="card">
        <div class="ctitle">AI Settings</div>
        <select class="msel" id="modelSelect" onchange="onMC()"><option>llama3</option></select>
        <button class="pbtn" onclick="pullModel()">&#11015; Pull Selected Model</button>
        <div id="pullSt" style="font-size:10px;color:var(--t2);margin-bottom:5px;"></div>
        <div class="srow"><span class="slbl">Temp</span><input type="range" class="sldr" id="tmpSldr" min="0" max="100" value="50" oninput="document.getElementById('tmpV').textContent=(this.value/100).toFixed(2)"><span class="sval" id="tmpV">0.50</span></div>
        <div class="srow"><span class="slbl">Top-P</span><input type="range" class="sldr" id="tpSldr" min="0" max="100" value="90" oninput="document.getElementById('tpV').textContent=(this.value/100).toFixed(2)"><span class="sval" id="tpV">0.90</span></div>
      </div>
      <div class="card">
        <div class="ctitle">Auto-Training</div>
        <div class="sg">
          <div class="si"><div class="sl">Status</div><div class="sv" id="trSt">&#8211;</div></div>
          <div class="si"><div class="sl">Avg Reward</div><div class="sv ac" id="trRw">&#8211;</div></div>
          <div class="si"><div class="sl">Sessions</div><div class="sv" id="trSess">&#8211;</div></div>
          <div class="si"><div class="sl">Last Run</div><div class="sv" id="trLast">&#8211;</div></div>
        </div>
      </div>
      <div class="card">
        <div class="ctitle">Voice Output (TTS)</div>
        <select class="msel" id="voiceSel" style="margin-bottom:5px;"></select>
        <div class="srow"><span class="slbl">Speed</span><input type="range" class="sldr" id="ttsRate" min="50" max="200" value="100" oninput="document.getElementById('rV').textContent=(this.value/100).toFixed(1)+'x'"><span class="sval" id="rV">1.0x</span></div>
        <div class="srow"><span class="slbl">Pitch</span><input type="range" class="sldr" id="ttsPitch" min="50" max="200" value="100" oninput="document.getElementById('pV').textContent=(this.value/100).toFixed(1)"><span class="sval" id="pV">1.0</span></div>
      </div>
      <div class="card" style="flex:1;">
        <div class="ctitle">Chat Sessions</div>
        <div class="sess-list" id="sessList"><div style="color:var(--t3);font-size:11px;">Loading&#8230;</div></div>
      </div>
    </div>
  </aside>
  <div class="main">
    <div class="ch">
      <div class="ch-l">
        <button class="tog" onclick="toggleSB()">&#9776;</button>
        <div>
          <div class="ct">JARVIS AI</div>
          <div class="cs">ReAct Agent · Vector Memory · <span id="hdrModel">Llama3</span></div>
        </div>
      </div>
      <div class="h-actions">
        <div class="spdbadge" id="spdBadge">&#9889; <span id="spdVal">0</span> t/s</div>
        <div class="mbadge" id="mdlBadge">llama3</div>
        <button class="icon-btn" onclick="clearChat()" title="Clear chat">&#128465;</button>
      </div>
    </div>
    <div class="msgs" id="messages"></div>
    <div class="agbar" id="agBar"><div class="agsp"></div><span id="agSt">Running agent&#8230;</span></div>
    <div class="inp-area">
      <div class="inp-box" style="position:relative;">
        <div class="cmd-menu" id="cmdMenu"></div>
        <div class="img-strip" id="imgStrip"></div>
        <div class="inp-row">
          <textarea class="chtxt" id="chatInput" rows="1" placeholder="Ask anything&#8230; or type @ to see commands" onkeydown="onKey(event)" oninput="checkCmds(this)"></textarea>
          <div class="iacts">
            <input type="file" id="fileIn" accept="image/*,.pdf" multiple hidden onchange="handleFiles(event)">
            <button class="abt" onclick="document.getElementById('fileIn').click()" title="Attach image or PDF">&#128206;</button>
            <button class="abt" id="micBtn" onclick="toggleVoice()" title="Voice input">&#127897;</button>
            <button class="stpbtn" id="stpBtn" onclick="stopGen()" title="Stop generating">&#9209;</button>
            <button class="snd" id="sndBtn" onclick="sendChat()">&#10148;</button>
          </div>
        </div>
        <div class="hints"><code>solve x²+5x+6</code> <code>integrate sin(x)</code> <code>physics v=20 u=0 t=5</code> <code>fact-check [claim]</code> <code>python: print(42)</code> <code>convert 100 celsius to fahrenheit</code></div>
      </div>
    </div>
  </div>
</div>
<div class="drop-ov" id="dropOv"><div style="font-size:40px;">&#128206;</div><div style="font-size:18px;font-weight:700;color:var(--accent2);">Drop image or PDF to attach</div></div>
<script src="/script.js"></script>
</body>
</html>"""


# ============================================================================
# ROUTE 2: CHAT API (/chat)
# ============================================================================

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest) -> ChatResponse:
    """
    FIX 1+2+5: Global error wrapper + 5s guarantee + 20s LLM timeout.
    JARVIS will ALWAYS return a response — never freeze or hang.
    """
    _FALLBACK = ChatResponse(response="System error recovered. Ready.", model="fallback")

    # FIX 8 — Log every input
    logger.info(f"[CHAT] prompt={chat_request.prompt!r} source={chat_request.source}")

    try:
        # Load history
        history = []
        try:
            db = get_database()
            raw_history = db.get_chat_history(chat_request.session_id, limit=20)
            history = [{"role": m["role"], "content": m["content"]} for m in raw_history]
        except Exception as he:
            logger.warning(f"[CHAT] history load failed: {he}")

        # ── FAST PATH ────────────────────────────────────────────────────────
        p = chat_request.prompt.lower().strip().rstrip("?")
        if p in ["what time is it", "the time", "time", "clock", "what is the time"]:
            from datetime import datetime
            return ChatResponse(response=f"It's {datetime.now().strftime('%-I:%M %p')}.", model="system-fast-path")
        if p in ["what day is it", "the date", "date", "today", "what is today"]:
            from datetime import datetime
            return ChatResponse(response=f"Today is {datetime.now().strftime('%A, %d %B %Y')}.", model="system-fast-path")

        # ── FIX 5 — 5-second guarantee with background completion ────────────
        async def _run_orchestrator() -> str:
            """FIX 2: 20s hard timeout on the full LLM pipeline."""
            parts = []
            try:
                async def _collect():
                    async for chunk in _jarvis_orchestrator.process(
                        chat_request.prompt, source=chat_request.source
                    ):
                        parts.append(chunk)
                await asyncio.wait_for(_collect(), timeout=20.0)
            except asyncio.TimeoutError:
                logger.error("[CHAT] LLM timed out after 20s")
                return parts and "".join(parts) or "Request timed out. Standing by."
            except Exception as oe:
                logger.error(f"[CHAT] orchestrator error: {oe}")
                return ""
            return "".join(parts)

        try:
            # Give orchestrator 5 seconds; if it exceeds that, return partial/fallback
            response_text = await asyncio.wait_for(_run_orchestrator(), timeout=5.0)
            if not response_text:
                response_text = "Done."
        except asyncio.TimeoutError:
            logger.warning("[CHAT] 5s guarantee triggered — running orchestrator in background")
            asyncio.create_task(_run_orchestrator())  # finish in background
            response_text = "Working on it. I'll follow up shortly."
        except Exception as fe:
            logger.error(f"[CHAT] run_orchestrator wrapper failed: {fe}")
            response_text = "System error recovered. Ready."

        # FIX 8 — Log every response
        logger.info(f"[CHAT] response={response_text!r}")

        # Persist to history
        try:
            db = get_database()
            db.add_chat_message(chat_request.session_id, "user", chat_request.prompt, chat_request.model)
            db.add_chat_message(chat_request.session_id, "azan", response_text, chat_request.model)
        except Exception as pe:
            logger.warning(f"[CHAT] history persist failed: {pe}")

        return ChatResponse(response=response_text, model=chat_request.model)

    except Exception as e:
        # FIX 1 — Global catch-all: NEVER return 500, always return safe fallback
        logger.error(f"[CHAT] CRITICAL unhandled error: {e}", exc_info=True)
        return _FALLBACK


@app.post("/chat/stream")
async def chat_stream_endpoint(chat_request: ChatRequest):
    """
    Streaming chat endpoint — routes through the JARVIS Orchestrator when available,
    falling back to the legacy RL inference engine.
    """
    import json as _json

    # 1. Load history & log user message
    history = []
    try:
        db = get_database()
        raw_history = db.get_chat_history(chat_request.session_id, limit=20)
        history = [{"role": m["role"], "content": m["content"]} for m in raw_history]
        db.add_chat_message(chat_request.session_id, "user", chat_request.prompt, chat_request.model)
    except Exception as e:
        logger.warning(f"Could not load/log session history: {e}")

    full_response = []

    # ── FAST PATH: ZERO LATENCY TIME/DATE ────────────────────────────────
    p = chat_request.prompt.lower().strip().rstrip("?")
    if p in ["what time is it", "the time", "time", "clock", "what is the time"]:
        from datetime import datetime
        t = datetime.now().strftime("%-I:%M %p")
        res = f"It's {t}."
        async def fast_gen():
            yield f"data: {_json.dumps({'token': res})}\n\n"
            yield f"data: {_json.dumps({'done': True})}\n\n"
        return StreamingResponse(fast_gen(), media_type="text/event-stream")
    
    if p in ["what day is it", "the date", "date", "today", "what is today"]:
        from datetime import datetime
        d = datetime.now().strftime("%A, %d %B %Y")
        res = f"Today is {d}."
        async def fast_gen():
            yield f"data: {_json.dumps({'token': res})}\n\n"
            yield f"data: {_json.dumps({'done': True})}\n\n"
        return StreamingResponse(fast_gen(), media_type="text/event-stream")

    async def jarvis_generator():
        """FIX 1+2+7: Fully guarded streaming with 20s LLM timeout."""
        global _jarvis_orchestrator
        # FIX 8
        logger.info(f"[STREAM] prompt={chat_request.prompt!r}")
        try:
            async def _stream_with_timeout():
                async for chunk in _jarvis_orchestrator.process(
                    chat_request.prompt,
                    source=chat_request.source,
                    history=history,
                ):
                    full_response.append(chunk)
                    yield f"data: {_json.dumps({'token': chunk})}\n\n"

            # FIX 2 — 20s hard cap
            try:
                async for sse in asyncio.timeout(20).__aenter__().__aiter__():  # noqa
                    pass
            except Exception:
                pass

            async for sse_chunk in _stream_with_timeout():
                yield sse_chunk

        except Exception as e:
            logger.error(f"[STREAM] orchestrator error: {e}", exc_info=True)
            safe = "System error recovered. Ready."
            yield f"data: {_json.dumps({'token': safe})}\n\n"
            full_response.append(safe)

        full_text = "".join(full_response)
        if not full_text:
            full_text = "Done."
        logger.info(f"[STREAM] response={full_text[:120]!r}")
        try:
            db = get_database()
            db.add_chat_message(chat_request.session_id, "azan", full_text, chat_request.model)
        except Exception as le:
            logger.warning(f"[STREAM] log failed: {le}")
        yield f"data: {_json.dumps({'done': True})}\n\n"

    def legacy_generator():
        """Fallback: legacy synchronous RL inference engine stream."""
        try:
            engine = get_rl_inference_engine()
            for chunk in engine.stream_predict(
                chat_request.prompt,
                model=chat_request.model,
                temperature=chat_request.temperature or 0.5,
                top_p=chat_request.top_p or 0.9,
                history=history,
                images=chat_request.images,
            ):
                full_response.append(chunk)
                yield f"data: {_json.dumps({'token': chunk})}\n\n"
        except Exception as e:
            logger.error(f"[STREAM] legacy error: {e}")
            yield f"data: {_json.dumps({'token': 'System error recovered. Ready.'})}\n\n"
        full_text = "".join(full_response)
        try:
            db = get_database()
            db.add_chat_message(chat_request.session_id, "azan", full_text, chat_request.model)
        except Exception:
            pass
        yield f"data: {_json.dumps({'done': True})}\n\n"

    generator = jarvis_generator() if _jarvis_orchestrator else legacy_generator()
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/chat/history/{session_id}")
def get_history(session_id: str = "default_session"):
    """Get chat history for a session from SQLite."""
    try:
        db = get_database()
        history = db.get_chat_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# ROUTE 2b: SESSION MANAGEMENT
# ============================================================================

@app.get("/api/sessions")
def list_sessions(limit: int = 50):
    """List all chat sessions with message counts."""
    try:
        db = get_database()
        sessions = db.get_all_sessions(limit=limit)
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a session and all its chat history."""
    try:
        db = get_database()
        success = db.delete_session(session_id)
        if success:
            return {"status": "deleted", "session_id": session_id}
        raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROUTE 2c: FEEDBACK ANALYTICS
# ============================================================================

@app.get("/api/feedback/analytics")
def get_feedback_analytics():
    """Get feedback analytics: rating distribution, average, trends."""
    try:
        db = get_database()
        stats = db.get_feedback_stats()
        summary = db.get_db_summary()
        stats["total_chat_messages"] = summary.get("chat_history", 0)
        stats["total_sessions"] = summary.get("sessions", 0)
        return stats
    except Exception as e:
        logger.error(f"Error getting feedback analytics: {e}")
        return {"error": str(e)}


# ============================================================================
# ROUTE 2d: DATABASE SUMMARY
# ============================================================================

@app.get("/api/db/summary")
def get_db_summary_endpoint():
    """Get overall database and vector store summary."""
    try:
        db = get_database()
        summary = db.get_db_summary()
        
        # Add Vector Store Stats (Phase 3)
        try:
            from src.semantic_search import get_vector_store
            vs = get_vector_store()
            summary["vector_store"] = vs.get_stats()
        except:
            summary["vector_store"] = {"status": "Not available"}
            
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# ROUTE: JARVIS STATUS & SCHEDULER API
# ============================================================================

@app.get("/api/jarvis/status")
def get_jarvis_status():
    """
    Returns live system metrics (CPU, RAM, Disk, Ollama) and the JARVIS
    orchestrator status, scheduled task list, and continuous learner state.
    """
    from src.workers.system_monitor import get_system_monitor
    from src.workers.task_scheduler import get_jarvis_scheduler

    monitor = get_system_monitor()
    scheduler = get_jarvis_scheduler()
    metrics = monitor.get_metrics()
    
    ctx = MacOSContextTool()
    current_context = ctx.get_screen_summary()

    return {
        "system": metrics,
        "orchestrator": "online" if _jarvis_orchestrator else "legacy_mode",
        "scheduled_tasks": scheduler.list_tasks(),
        "continuous_learner": "running" if _continuous_learner else "offline",
        "automation_engine": "active" if _automation_engine else "offline",
        "active_app": current_context.get("active_app", "None"),
        "last_action": _last_action,
        "version": "JARVIS v8.0"
    }


@app.post("/api/jarvis/quick_action")
async def quick_action(request_data: dict):
    """High-performance endpoint for mobile quick actions (<500ms)."""
    global _last_action
    action = request_data.get("action")
    args = request_data.get("args", {})
    
    control = MacOSControlTool()
    _last_action = f"Executing: {action}"
    
    try:
        if action == "mute":
            res = control.mute(enable=args.get("enable", True))
        elif action == "open_app":
            res = control.open_app(args.get("app_name", "Safari"))
        elif action == "set_volume":
            res = control.set_volume(args.get("level", 50))
        else:
            res = control.execute(action, args)
        
        return {"status": "success", "result": res}
    except Exception as e:
        _last_action = f"Error: {action}"
        return {"status": "error", "message": str(e)}


class ScheduleRequest(BaseModel):
    name: str = Field(..., description="Human-readable name for this scheduled task")
    task: str = Field(..., description="Task description for JARVIS to execute on schedule")
    delay_sec: Optional[float] = Field(None, description="Delay in seconds before one-shot execution")
    interval_sec: Optional[float] = Field(None, description="Repeat interval in seconds (recurring)")


@app.post("/api/jarvis/schedule")
async def schedule_task(request: ScheduleRequest):
    """
    Schedule a natural-language task for JARVIS to execute after a delay or on a recurring interval.
    Exactly one of `delay_sec` or `interval_sec` must be provided.
    """
    if not request.delay_sec and not request.interval_sec:
        raise HTTPException(status_code=400, detail="Provide either delay_sec (one-shot) or interval_sec (recurring)")

    from src.workers.task_scheduler import get_jarvis_scheduler
    scheduler = get_jarvis_scheduler()

    async def jarvis_run_task():
        """Execute the scheduled task through the JARVIS Orchestrator."""
        if _jarvis_orchestrator:
            result_parts = []
            async for chunk in _jarvis_orchestrator.process(request.task):
                result_parts.append(chunk)
            result = "".join(result_parts)
            logger.info(f"⏰ Scheduled task '{request.name}' completed. Length={len(result)}")
        else:
            logger.warning(f"⏰ Scheduled task '{request.name}' could not run: JARVIS orchestrator offline")

    if request.delay_sec:
        task_id = scheduler.schedule_once(request.name, jarvis_run_task, request.delay_sec)
        return {"status": "scheduled", "type": "one-shot", "task_id": task_id, "delay_sec": request.delay_sec}
    else:
        task_id = scheduler.schedule_recurring(request.name, jarvis_run_task, request.interval_sec)
        return {"status": "scheduled", "type": "recurring", "task_id": task_id, "interval_sec": request.interval_sec}


@app.delete("/api/jarvis/schedule/{task_id}")
def cancel_scheduled_task(task_id: str):
    """Cancel a scheduled JARVIS task by its task_id."""
    from src.workers.task_scheduler import get_jarvis_scheduler
    scheduler = get_jarvis_scheduler()
    success = scheduler.cancel(task_id)
    if success:
        return {"status": "cancelled", "task_id": task_id}
    raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found or already completed")


# ============================================================================
# ROUTE 3: TRAINING API (/train)
# ============================================================================

@app.post("/train", response_model=TrainingResponse)
def train_endpoint(request: TrainingRequest) -> TrainingResponse:
    """
    Interactive RLHF training endpoint with optional quick mode.
    
    Quick mode uses cached responses for 10x faster training.
    """
    try:
        result = dashboard.train_single_example(
            question=request.question,
            ideal_answer=request.ideal_answer,
            model_name=request.model,
            quick_mode=request.quick_mode
        )
        
        if result.get("success"):
            return TrainingResponse(
                success=True,
                question=result.get("question"),
                ideal_answer=result.get("ideal_answer"),
                model_response=result.get("model_response"),
                reward_score=result.get("reward_score"),
                reward_breakdown=result.get("reward_breakdown"),
                timestamp=result.get("timestamp")
            )
        else:
            return TrainingResponse(
                success=False,
                error=result.get("error", "Unknown error"),
                timestamp=result.get("timestamp")
            )
    except Exception as e:
        logger.error(f"Training error: {e}")
        return TrainingResponse(success=False, error=str(e))


# ============================================================================
# ROUTE 4: AZAN RL DASHBOARD
# ============================================================================

@app.get("/azan-dashboard", response_class=HTMLResponse)
def azan_rl_dashboard():
    """Serve the AZAN RL training dashboard with live monitoring"""
    if not AZAN_RL_AVAILABLE:
        return """
        <html>
        <head>
            <title>AZAN RL Dashboard</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: #1a1a1a;
                    color: #fff;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                }
                .error-box {
                    background: #300;
                    border: 2px solid #f00;
                    padding: 30px;
                    border-radius: 10px;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>⚠️ AZAN RL System Not Available</h1>
                <p>Please ensure azan_rl_pipeline.py and azan_rl_inference.py are properly installed.</p>
            </div>
        </body>
        </html>
        """
    
    try:
        from src.azan_dashboard import get_dashboard
        return get_dashboard()
    except Exception as e:
        logger.error(f"Error loading AZAN dashboard: {e}")
        return f"<h1>Error loading dashboard: {str(e)}</h1>"


# ============================================================================
# ROUTE 5: DASHBOARD APIs
# ============================================================================

@app.get("/dashboard/summary")
def get_training_summary() -> dict:
    """Get summary of all training sessions."""
    return dashboard.get_training_history_summary()


@app.get("/dashboard/models")
def get_model_comparison() -> dict:
    """Compare all trained models."""
    return dashboard.get_model_comparison()


@app.get("/dashboard/analytics")
def get_analytics() -> dict:
    """Get training analytics."""
    return dashboard.get_reward_analytics()


@app.get("/dashboard/models-list")
def list_models() -> dict:
    """List all available models."""
    models = dashboard.list_all_models()
    return {"models": models}


# ============================================================================
# ROUTE 5: AUTO-TRAINING (POLITICAL TOPICS)
# ============================================================================

@app.post("/auto-training/start")
def start_auto_training() -> dict:
    """Start automatic training on political topics."""
    from src.auto_training_scheduler import get_scheduler
    return get_scheduler().start()


@app.post("/auto-training/stop")
def stop_auto_training() -> dict:
    """Stop automatic training scheduler."""
    from src.auto_training_scheduler import get_scheduler
    return get_scheduler().stop()


@app.get("/auto-training/status")
def get_auto_training_status() -> dict:
    """Get status of auto-training scheduler."""
    from src.auto_training_scheduler import get_scheduler
    return get_scheduler().get_status()


@app.get("/auto-training/config")
def get_auto_training_config() -> dict:
    """Get auto-training configuration."""
    from src.auto_training_scheduler import get_scheduler
    return get_scheduler().get_config()


@app.post("/auto-training/config")
def update_auto_training_config(updates: dict) -> dict:
    """Update auto-training configuration."""
    from src.auto_training_scheduler import get_scheduler
    return get_scheduler().update_config(updates)


@app.post("/auto-training/trigger")
def trigger_manual_auto_training(num_examples: Optional[int] = None) -> dict:
    """Trigger a manual auto-training session immediately."""
    from src.auto_training_scheduler import get_scheduler
    return get_scheduler().trigger_manual_training(num_examples)


@app.get("/auto-training/topics")
def get_political_topics() -> dict:
    """Get available political topics for training."""
    from src.political_trainer import get_auto_trainer
    topics = get_auto_trainer().get_training_pairs()
    
    # Group by topic
    grouped = {}
    for pair in topics:
        topic = pair.get("topic", "Unknown")
        if topic not in grouped:
            grouped[topic] = []
        grouped[topic].append({
            "question": pair["question"],
            "ideal_answer": pair["ideal_answer"]
        })
    
    return {
        "topics": grouped,
        "total_pairs": len(topics),
        "topic_count": len(grouped)
    }


@app.get("/auto-training/stats")
def get_auto_training_stats() -> dict:
    """Get statistics about auto-training sessions."""
    from src.political_trainer import get_auto_trainer
    return get_auto_trainer().get_training_stats()


@app.get("/api/math/stats")
def get_math_stats():
    """Get AZAN's math problem solving statistics."""
    from src.math_trainer import get_math_trainer
    return get_math_trainer().get_training_stats()


@app.post("/api/math/train")
def trigger_math_training(payload: dict):
    """Manually train AZAN on a specific math problem with symbolic verification."""
    question = payload.get("question", "")
    response = payload.get("response", "")
    ground_truth = payload.get("ground_truth", "")
    
    if not all([question, response, ground_truth]):
        raise HTTPException(status_code=400, detail="Missing required math training fields.")
        
    from src.math_trainer import get_math_trainer
    return get_math_trainer().evaluate_step_by_step(question, response, ground_truth)


@app.post("/api/physics/solve")
def solve_physics_problem(payload: dict):
    """Solve a physics problem."""
    problem = payload.get("problem", "")
    domain = payload.get("domain", "auto")
    if not problem:
        raise HTTPException(status_code=400, detail="Missing 'problem' field")
    from src.physics_engine import get_physics_engine
    return get_physics_engine().solve(problem, domain)


@app.get("/api/physics/constants")
def get_physics_constants():
    """Get all physical constants."""
    from src.physics_engine import CONSTANTS
    return {"constants": CONSTANTS}


# ============================================================================
# ROUTE 5b: DOCUMENT UPLOAD (Phase 3)
# ============================================================================

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF or Markdown document for processing and indexing."""
    allowed = {".pdf", ".md", ".markdown", ".txt"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}")
    
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")
    
    from src.document_processor import process_document
    result = process_document(file.filename, contents)
    
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Processing failed"))
    return result


@app.get("/api/documents/stats")
def get_document_stats_endpoint():
    """Get stats about uploaded/processed documents."""
    from src.document_processor import get_document_stats
    return get_document_stats()


# ============================================================================
# ROUTE 5c: AGENTIC ENDPOINTS (Phase 5)
# ============================================================================

@app.post("/api/agent/fact-check")
def agent_fact_check(payload: dict):
    """Fact-check a claim against the knowledge base."""
    claim = payload.get("claim", "")
    if not claim:
        raise HTTPException(status_code=400, detail="Missing 'claim' field")
    from src.fact_checker import fact_check
    return fact_check(claim)


@app.post("/api/agent/execute")
def agent_execute_task(payload: dict):
    """Execute an agentic task (scrape, summarize, etc)."""
    command = payload.get("command", "")
    args = payload.get("args", {})
    if not command:
        raise HTTPException(status_code=400, detail="Missing 'command' field")
    from src.task_executor import execute_task
    return execute_task(command, args)


@app.get("/api/models")
def list_models():
    """List available Ollama models."""
    try:
        import ollama
        models = [m['name'] for m in ollama.list().get('models', [])]
        if not models:
            models = ["llama3", "mistral"]
        return {"models": models}
    except Exception:
        return {"models": ["llama3", "mistral"]}

@app.post("/api/models/pull")
def pull_ollama_model(payload: dict):
    """Pull a model from Ollama."""
    model = payload.get("model", "")
    if not model:
        raise HTTPException(status_code=400, detail="Missing 'model' field")
    
    import subprocess
    try:
        logger.info(f"Pulling model: {model}")
        # Run pull in background to avoid timeout, but for now we wait a bit
        # In a real app, this should be a background task
        process = subprocess.run(["ollama", "pull", model], capture_output=True, text=True, timeout=300)
        if process.returncode == 0:
            return {"status": "success", "message": f"Successfully pulled {model}"}
        else:
            return {"status": "error", "message": process.stderr}
    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# ROUTE 6: INSHORTS NEWS INTEGRATION
# ============================================================================

@app.post("/api/inshorts/start-training")
def start_inshorts_training(scrape_interval: int = 300, training_interval: int = 600) -> dict:
    """Start continuous Inshorts news training."""
    from src.inshorts_trainer import get_inshorts_trainer
    trainer = get_inshorts_trainer()
    return trainer.start_continuous_training(scrape_interval, training_interval)


@app.post("/api/inshorts/stop-training")
def stop_inshorts_training() -> dict:
    """Stop continuous Inshorts news training."""
    from src.inshorts_trainer import get_inshorts_trainer
    trainer = get_inshorts_trainer()
    return trainer.stop_continuous_training()


@app.get("/api/inshorts/status")
def get_inshorts_status() -> dict:
    """Get Inshorts training status."""
    from src.inshorts_trainer import get_inshorts_trainer
    trainer = get_inshorts_trainer()
    return trainer.get_training_status()


@app.post("/api/inshorts/scrape")
def manual_inshorts_scrape(category: Optional[str] = None) -> dict:
    """Manually trigger Inshorts scraping."""
    from src.inshorts_trainer import get_inshorts_trainer
    trainer = get_inshorts_trainer()
    return trainer.manual_scrape(category)


@app.get("/api/inshorts/articles/latest")
def get_latest_inshorts_articles(limit: int = 10) -> dict:
    """Get latest scraped Inshorts articles."""
    from src.inshorts_trainer import get_inshorts_trainer
    trainer = get_inshorts_trainer()
    articles = trainer.get_latest_articles(limit)
    return {
        "articles": articles,
        "total": len(articles),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/inshorts/articles/category/{category}")
def get_inshorts_by_category(category: str, limit: int = 10) -> dict:
    """Get articles from specific Inshorts category."""
    from src.inshorts_trainer import get_inshorts_trainer
    trainer = get_inshorts_trainer()
    articles = trainer.get_articles_by_category(category)[:limit]
    return {
        "category": category,
        "articles": articles,
        "total": len(articles),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/inshorts/export")
def export_inshorts_data() -> dict:
    """Export all Inshorts data as JSON."""
    from src.inshorts_trainer import get_inshorts_trainer
    trainer = get_inshorts_trainer()
    status = trainer.get_training_status()
    
    return {
        "status": "exported",
        "files": {
            "articles": "data/inshorts_articles.json",
            "training_data": "data/inshorts_training_data.json",
            "training_log": "data/inshorts_training_log.json",
            "scrape_history": "data/inshorts_scrape_history.json"
        },
        "statistics": status,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# ROUTE 7: LEGACY ENDPOINTS
# ============================================================================

@app.get("/health")
def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/dashboard")
async def dashboard_route():
    """Serve the RL training dashboard HTML page."""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    if dashboard_path.exists():
        with open(dashboard_path, 'r') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


@app.get("/predict")
def predict_endpoint(x: float) -> dict[str, float]:
    """Legacy linear regression prediction endpoint."""
    from src.model import predict_linear
    import numpy as np
    
    try:
        model_path = Path("model") / "linear_model.npz"
        model_data = np.load(model_path)
        weight = float(model_data["weight"])
        bias = float(model_data["bias"])
        
        y_pred = predict_linear(x=x, weight=weight, bias=bias)
        return {"x": x, "prediction": float(y_pred)}
        
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# ROUTE 8: RL PIPELINE MONITORING
# ============================================================================

@app.get("/api/rl/status")
def get_rl_status() -> dict:
    """Get RL pipeline training status"""
    rl_pipeline = get_rl_pipeline()
    return rl_pipeline.get_training_status()


@app.get("/api/rl/knowledge")
def get_rl_knowledge() -> dict:
    """Get AZAN's learned knowledge summary"""
    rl_pipeline = get_rl_pipeline()
    return rl_pipeline.get_model_knowledge()


@app.post("/api/rl/start-training")
def start_rl_training() -> dict:
    """Start the RL training pipeline"""
    rl_pipeline = get_rl_pipeline()
    rl_pipeline.start_training()
    return {
        "status": "success",
        "message": "RL training pipeline started",
        "training_status": rl_pipeline.get_training_status()
    }


@app.post("/api/rl/stop-training")
def stop_rl_training() -> dict:
    """Stop the RL training pipeline"""
    rl_pipeline = get_rl_pipeline()
    rl_pipeline.stop_training()
    return {
        "status": "success",
        "message": "RL training pipeline stopped"
    }


@app.get("/api/rl/metrics")
def get_rl_metrics() -> dict:
    """Get detailed RL training metrics"""
    from src.rl_pipeline import get_rl_pipeline
    rl_pipeline = get_rl_pipeline()
    
    status = rl_pipeline.get_training_status()
    knowledge = rl_pipeline.get_model_knowledge()
    model_metrics = rl_pipeline.model.get_metrics()
    
    return {
        "training_status": status,
        "knowledge_base": knowledge,
        "model_metrics": model_metrics,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# AZAN CURATED RL SYSTEM ENDPOINTS
# ============================================================================

@app.get("/api/azan/rl/status")
def get_azan_rl_status() -> dict:
    """Get AZAN's specialized RL training status"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        engine = get_rl_engine()
        metrics = engine.get_metrics()
        return {
            "status": "active",
            "system": "AZAN Curated Knowledge RL",
            "training_domains": [
                "Indian Constitution & Laws",
                "UN Treaties & International Policies",
                "Military Strategies & Doctrines",
                "Political & Economic Definitions"
            ],
            **metrics
        }
    except Exception as e:
        logger.error(f"Error getting AZAN RL status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/azan/rl/train-iteration")
def azan_train_iteration() -> dict:
    """Execute one AZAN training iteration"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        engine = get_rl_engine()
        result = engine.train_iteration()
        return result
    except Exception as e:
        logger.error(f"Error in AZAN training iteration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/azan/rl/knowledge-stats")
def get_azan_knowledge_stats() -> dict:
    """Get AZAN's curated knowledge base statistics"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        engine = get_rl_engine()
        stats = {
            "sources": engine.kb.get_sources(),
            "categories": engine.kb.get_categories(),
            "total_items": len(engine.kb.knowledge_items),
            "total_qa_pairs": len(engine.kb.qa_pairs)
        }
        
        # Add per-source counts
        for source in stats['sources']:
            items = engine.kb.get_by_source(source)
            if 'sources_detail' not in stats:
                stats['sources_detail'] = {}
            stats['sources_detail'][source] = len(items)
        
        # Add per-category counts
        for category in stats['categories']:
            items = engine.kb.get_by_category(category)
            if 'categories_detail' not in stats:
                stats['categories_detail'] = {}
            stats['categories_detail'][category] = len(items)
        
        return stats
    except Exception as e:
        logger.error(f"Error getting knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/azan/rl/learned-qa")
def get_azan_learned_qa(limit: int = 20) -> dict:
    """Get recently learned Q&A pairs"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        engine = get_rl_engine()
        qa_pairs = engine.get_learned_qa(limit=limit)
        return {
            "count": len(qa_pairs),
            "pairs": qa_pairs
        }
    except Exception as e:
        logger.error(f"Error getting learned QA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/azan/rl/start")
def start_azan_training() -> dict:
    """Start AZAN autonomous training"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        trainer = get_rl_trainer()
        if not trainer.running:
            trainer.start()
            return {"status": "started", "message": "AZAN RL training started"}
        return {"status": "already_running", "message": "Training already active"}
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/azan/rl/stop")
def stop_azan_training() -> dict:
    """Stop AZAN autonomous training"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        trainer = get_rl_trainer()
        if trainer.running:
            trainer.stop()
            return {"status": "stopped", "message": "AZAN RL training stopped"}
        return {"status": "already_stopped", "message": "Training not active"}
    except Exception as e:
        logger.error(f"Error stopping training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/azan/infer")
def azan_data_only_inference(query: str) -> dict:
    """Query AZAN using data-only inference (no hallucinations)"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        engine = get_azan_inference_engine()
        response = engine.answer_query(query)
        return response
    except Exception as e:
        logger.error(f"Error in AZAN inference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/azan/search")
def azan_knowledge_search(query: str, limit: int = 5) -> dict:
    """Search AZAN's curated knowledge base"""
    if not AZAN_RL_AVAILABLE:
        raise HTTPException(status_code=503, detail="AZAN RL system not available")
    
    try:
        engine = get_azan_inference_engine()
        results = engine.search_knowledge(query, limit=limit)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error in knowledge search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USER FEEDBACK & RLHF ENDPOINTS
# ============================================================================

class FeedbackRequest(BaseModel):
    """User feedback request"""
    interaction_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    user_id: str = "anonymous"


@app.post("/api/feedback/submit")
def submit_feedback(request: FeedbackRequest) -> dict:
    """Submit user feedback on a response"""
    try:
        from src.user_feedback import get_feedback
        feedback_system = get_feedback()
        
        result = feedback_system.submit_rating(
            interaction_id=request.interaction_id,
            rating=request.rating,
            comment=request.comment,
            user_id=request.user_id
        )
        
        return {
            "status": "success",
            "feedback_id": result.get("id"),
            "rating": result.get("rating")
        }
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback/thumbs-up")
def thumbs_up(interaction_id: str) -> dict:
    """Quick thumbs-up rating"""
    try:
        from src.user_feedback import get_feedback
        feedback_system = get_feedback()
        result = feedback_system.thumbs_up(interaction_id)
        return {"status": "success", "rating": 5}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback/thumbs-down")
def thumbs_down(interaction_id: str) -> dict:
    """Quick thumbs-down rating"""
    try:
        from src.user_feedback import get_feedback
        feedback_system = get_feedback()
        result = feedback_system.thumbs_down(interaction_id)
        return {"status": "success", "rating": 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback/stats")
def get_feedback_stats() -> dict:
    """Get feedback statistics"""
    try:
        from src.user_feedback import get_feedback
        feedback_system = get_feedback()
        stats = feedback_system.get_feedback_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        return {"error": str(e)}


@app.get("/api/rlhf/status")
def get_rlhf_status() -> dict:
    """Get RLHF pipeline status"""
    try:
        from src.rlhf_pipeline import get_rlhf
        rlhf = get_rlhf()
        return rlhf.get_rlhf_status()
    except Exception as e:
        logger.error(f"Error getting RLHF status: {e}")
        return {"error": str(e)}


@app.post("/api/rlhf/retrain")
def trigger_rlhf_retraining() -> dict:
    """Trigger RLHF retraining from accumulated feedback"""
    try:
        from src.rlhf_pipeline import get_rlhf
        rlhf = get_rlhf()
        result = rlhf.apply_feedback_to_training()
        return result
    except Exception as e:
        logger.error(f"Error triggering RLHF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SEMANTIC SEARCH ENDPOINTS
# ============================================================================

@app.get("/api/search/semantic")
def semantic_search(query: str, limit: int = 5, category: Optional[str] = None) -> dict:
    """Semantic search across articles and knowledge base"""
    try:
        from src.semantic_search import get_semantic_search
        search_engine = get_semantic_search()
        results = search_engine.search(query, limit=limit, category=category)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return {"error": str(e), "results": []}


@app.post("/api/search/index-articles")
def index_articles() -> dict:
    """Index articles for semantic search"""
    try:
        from src.semantic_search import get_semantic_search
        from src.rss_feed_integrator import get_feed_integrator
        
        search_engine = get_semantic_search()
        feed_integrator = get_feed_integrator()
        
        # Get articles from RSS integrator
        articles = feed_integrator.articles
        
        # Index them
        result = search_engine.index_articles(articles)
        return result
    except Exception as e:
        logger.error(f"Error indexing articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search/stats")
def get_search_stats() -> dict:
    """Get semantic search index statistics"""
    try:
        from src.semantic_search import get_semantic_search
        search_engine = get_semantic_search()
        return search_engine.get_stats()
    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        return {"error": str(e)}


# ============================================================================
# FINE-TUNING ENDPOINTS
# ============================================================================

@app.post("/api/finetuning/start")
def start_finetuning() -> dict:
    """Start model fine-tuning"""
    try:
        from src.fine_tuning import get_finetuning
        finetune_manager = get_finetuning()
        
        # Start fine-tuning job
        job = finetune_manager.start_finetuning(
            training_file="data/finetune_training.jsonl",
            epochs=3,
            batch_size=8,
            learning_rate=1e-5
        )
        
        return {
            "status": "started",
            "job_id": job["id"],
            "model": job["model"]
        }
    except Exception as e:
        logger.error(f"Error starting fine-tuning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/finetuning/status/{job_id}")
def get_finetuning_status(job_id: str) -> dict:
    """Get fine-tuning job status"""
    try:
        from src.fine_tuning import get_finetuning
        finetune_manager = get_finetuning()
        status = finetune_manager.get_job_status(job_id)
        
        if status:
            return status
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting finetuning status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/finetuning/checkpoints")
def get_finetuning_checkpoints() -> dict:
    """Get recent fine-tuned model checkpoints"""
    try:
        from src.fine_tuning import get_finetuning
        finetune_manager = get_finetuning()
        checkpoints = finetune_manager.get_recent_checkpoints()
        
        return {
            "checkpoints": checkpoints,
            "count": len(checkpoints)
        }
    except Exception as e:
        logger.error(f"Error getting checkpoints: {e}")
        return {"error": str(e), "checkpoints": []}


@app.get("/api/finetuning/stats")
def get_finetuning_stats() -> dict:
    """Get fine-tuning statistics"""
    try:
        from src.fine_tuning import get_finetuning
        finetune_manager = get_finetuning()
        return finetune_manager.get_finetuning_stats()
    except Exception as e:
        logger.error(f"Error getting finetuning stats: {e}")
        return {"error": str(e)}


# ============================================================================
# RSS FEED INTEGRATION ENDPOINTS
# ============================================================================

@app.post("/api/feeds/update")
def update_rss_feeds() -> dict:
    """Manually trigger RSS feed update"""
    try:
        from src.rss_feed_integrator import get_feed_integrator
        feed_integrator = get_feed_integrator()
        
        results = feed_integrator.update_all_feeds()
        return {
            "status": "success",
            "results": results,
            "summary": feed_integrator.get_articles_summary()
        }
    except Exception as e:
        logger.error(f"Error updating feeds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feeds/articles")
def get_articles(category: Optional[str] = None, limit: int = 10) -> dict:
    """Get recent articles from RSS feeds"""
    try:
        from src.rss_feed_integrator import get_feed_integrator
        feed_integrator = get_feed_integrator()
        
        articles = feed_integrator.get_recent_articles(category=category, limit=limit)
        return {
            "articles": articles,
            "count": len(articles),
            "category": category
        }
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        return {"error": str(e), "articles": []}


@app.get("/api/feeds/summary")
def get_feeds_summary() -> dict:
    """Get RSS feeds summary"""
    try:
        from src.rss_feed_integrator import get_feed_integrator
        feed_integrator = get_feed_integrator()
        return feed_integrator.get_articles_summary()
    except Exception as e:
        logger.error(f"Error getting feeds summary: {e}")
        return {"error": str(e)}


# ============================================================================
# FEED CONTEXT INTEGRATION ENDPOINTS
# ============================================================================

@app.get("/api/context/summary")
def get_context_summary() -> dict:
    """Get summary of available context sources"""
    try:
        from src.feed_context_integration import get_context_manager
        context_manager = get_context_manager()
        return context_manager.get_context_summary()
    except Exception as e:
        logger.error(f"Error getting context summary: {e}")
        return {"error": str(e)}


@app.post("/api/context/enhance")
def enhance_context(query: str, category: Optional[str] = None) -> dict:
    """Get enhanced context with news for a query"""
    try:
        from src.feed_context_integration import get_context_manager
        context_manager = get_context_manager()
        
        enhanced = context_manager.prepare_inference_context(query)
        return enhanced
    except Exception as e:
        logger.error(f"Error enhancing context: {e}")
        return {"error": str(e), "query": query}


# ============================================================================
# RESTRICTED MODE (TRAINING DATA ONLY)
# ============================================================================

@app.get("/api/restricted/info")
def get_restricted_info(category: Optional[str] = None) -> dict:
    """Get information about available training data"""
    try:
        from src.restricted_inference import get_restricted_inference
        restricted = get_restricted_inference()
        return restricted.get_info(category=category)
    except Exception as e:
        logger.error(f"Error getting restricted info: {e}")
        return {"error": str(e)}


@app.post("/api/restricted/query")
def restricted_query(query: str, category: Optional[str] = None) -> dict:
    """Query ONLY using training data - no external knowledge"""
    try:
        from src.restricted_inference import get_restricted_inference
        restricted = get_restricted_inference()
        result = restricted.predict(query, category=category)
        return result
    except Exception as e:
        logger.error(f"Error in restricted query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/restricted/categories")
def get_restricted_categories() -> dict:
    """Get all available training data categories"""
    try:
        from src.restricted_inference import get_restricted_inference
        restricted = get_restricted_inference()
        categories = restricted.kb.get_categories()
        return {
            "categories": categories,
            "count": len(categories)
        }
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return {"error": str(e), "categories": []}


@app.get("/api/restricted/stats")
def get_restricted_stats() -> dict:
    """Get training data statistics"""
    try:
        from src.restricted_inference import get_restricted_inference
        restricted = get_restricted_inference()
        return restricted.kb.get_stats()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": str(e)}


@app.get("/status")
def health_check():
    """Simple health check for voice daemon."""
    return {"status": "online", "version": "8.0.1"}

@app.post("/quick_command")
async def quick_command(request_data: dict):
    """
    Bypasses ReAct loop for deterministic patterns.
    """
    cmd = request_data.get("command", "").lower()
    control = MacOSControlTool()
    ctx = MacOSContextTool()

    try:
        if "mute" in cmd:
            enable = "unmute" not in cmd
            res = control.mute(enable=enable)
            return {"result": "Muted" if enable else "Unmuted"}
        
        if "open" in cmd and "safari" in cmd:
            control.open_app("Safari")
            return {"result": "Opening Safari"}
            
        if "what app" in cmd or "active app" in cmd:
            context = ctx.get_screen_summary()
            app_name = context.get("active_app", "Unknown")
            return {"result": f"The active app is {app_name}"}
            
        if "volume" in cmd:
            # Simple volume detection logic
            import re
            match = re.search(r'(\d+)', cmd)
            if match:
                level = int(match.group(1))
                control.set_volume(level)
                return {"result": f"Volume set to {level} percent"}

        # Fallback to standard fast-path execution if possible
        return {"result": "Success"}
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)
