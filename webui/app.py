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

import json
import logging
from typing import Optional
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
from src.rl_inference import initialize_inference, predict as rl_predict, get_inference_engine

# Import AZAN curated RL system
try:
    from src.azan_rl_pipeline import initialize_rl_pipeline as init_azan_rl, get_rl_engine, get_rl_trainer
    from src.azan_rl_inference import initialize_inference_engine as init_azan_inference, get_inference_engine
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


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize systems on startup. Background training paused for performance."""
    if AZAN_RL_AVAILABLE:
        try:
            logger.info("⏸ AZAN Curated RL Pipeline initialization (training paused)")
            init_azan_inference()
        except Exception as e:
            logger.warning(f"Startup error in AZAN inference: {e}")
    
    try:
        initialize_inference()
        from src.restricted_inference import initialize_restricted_inference
        initialize_restricted_inference()
        from src.user_feedback import initialize_feedback
        initialize_feedback()
        from src.semantic_search import initialize_semantic_search
        initialize_semantic_search()
        from src.rss_feed_integrator import initialize_feed_integrator
        initialize_feed_integrator()
        logger.info("✅ Core systems initialized")
    except Exception as e:
        logger.warning(f"General startup error: {e}")


@app.on_event("shutdown")
def shutdown_event():
    """Stop auto-training scheduler on shutdown."""
    try:
        from src.auto_training_scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler.is_running:
            scheduler.stop()
            logger.info("Auto-training scheduler stopped")
    except Exception as e:
        logger.warning(f"Error during scheduler shutdown: {e}")


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


# ============================================================================
# ROUTE 1: MAIN HTML INTERFACE
# ============================================================================

@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    """Serve the AZAN AI Chat — Phase 4+5 Pro UX with Agentic features."""
    return """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AZAN AI Chat</title>
    <meta name="description" content="AZAN — AI Assistant powered by RL-enhanced knowledge, semantic RAG, and autonomous learning.">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        /* ===== THEME VARIABLES ===== */
        [data-theme="dark"] {
            --bg-primary: #0a0a14;
            --bg-secondary: #12121f;
            --bg-card: #16162a;
            --bg-input: #1a1a30;
            --bg-hover: #1e1e38;
            --text-primary: #e0e0f0;
            --text-secondary: #8888aa;
            --text-muted: #555570;
            --accent: #7c5cfc;
            --accent-glow: rgba(124, 92, 252, 0.25);
            --accent-dim: #5a3fd4;
            --green: #34d399;
            --orange: #fb923c;
            --red: #f87171;
            --border: #222240;
            --msg-user-bg: #7c5cfc;
            --msg-azan-bg: #1e1e38;
            --radius: 10px;
        }
        [data-theme="light"] {
            --bg-primary: #f4f4f8;
            --bg-secondary: #ffffff;
            --bg-card: #f0f0f5;
            --bg-input: #e8e8f0;
            --bg-hover: #dddde8;
            --text-primary: #1a1a2e;
            --text-secondary: #555580;
            --text-muted: #888899;
            --accent: #6c4ce0;
            --accent-glow: rgba(108, 76, 224, 0.15);
            --accent-dim: #5a3fd4;
            --green: #16a34a;
            --orange: #ea580c;
            --red: #dc2626;
            --border: #d0d0e0;
            --msg-user-bg: #6c4ce0;
            --msg-azan-bg: #e8e8f0;
            --radius: 10px;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            overflow: hidden;
            transition: background 0.3s, color 0.3s;
        }

        /* ===== SIDEBAR ===== */
        .sidebar {
            width: 280px;
            min-width: 280px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 18px 14px;
            gap: 14px;
            overflow-y: auto;
            transition: background 0.3s;
        }
        .sidebar::-webkit-scrollbar { width: 4px; }
        .sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

        .logo-row { display: flex; justify-content: space-between; align-items: center; }
        .logo { display: flex; align-items: center; gap: 8px; font-size: 20px; font-weight: 700; color: var(--accent); }
        .logo sub { font-size: 10px; color: var(--text-muted); font-weight: 400; vertical-align: baseline; }

        .theme-toggle {
            background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary);
            width: 34px; height: 34px; border-radius: 8px; cursor: pointer; font-size: 16px;
            display: flex; align-items: center; justify-content: center; transition: all 0.2s;
        }
        .theme-toggle:hover { background: var(--accent); color: #fff; }

        .new-chat-btn {
            width: 100%; padding: 10px; background: var(--accent); color: #fff;
            border: none; border-radius: 8px; font-weight: 600; font-size: 13px;
            cursor: pointer; transition: all 0.2s;
        }
        .new-chat-btn:hover { background: var(--accent-dim); transform: translateY(-1px); }

        .sidebar-card {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: var(--radius); padding: 12px; transition: background 0.3s;
        }
        .sidebar-card h3 {
            font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px;
            color: var(--text-muted); margin-bottom: 10px;
        }

        .status-row { display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-bottom: 6px; }
        .status-row .label { color: var(--text-secondary); }
        .status-row .value { color: var(--text-primary); font-weight: 500; }
        .badge { padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 600; }
        .badge-online { background: rgba(52,211,153,.15); color: var(--green); }
        .badge-training { background: rgba(251,146,60,.15); color: var(--orange); }

        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; text-align: center; }
        .stat-box { background: var(--bg-input); border-radius: 8px; padding: 8px 4px; }
        .stat-box .num { font-size: 20px; font-weight: 700; color: var(--accent); }
        .stat-box .lbl { font-size: 8px; text-transform: uppercase; color: var(--text-muted); letter-spacing: .5px; margin-top: 2px; }

        .tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
        .tag { background: var(--bg-input); border: 1px solid var(--border); color: var(--text-secondary);
               padding: 3px 9px; border-radius: 6px; font-size: 10px; cursor: default; transition: all .2s; }

        /* Settings panel */
        .settings-group { margin-bottom: 10px; }
        .settings-group label { font-size: 11px; color: var(--text-secondary); display: block; margin-bottom: 4px; }
        .settings-group select, .settings-group input[type=range] {
            width: 100%; background: var(--bg-input); color: var(--text-primary);
            border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; font-size: 12px;
            outline: none; cursor: pointer;
        }
        .settings-group select:focus { border-color: var(--accent); }
        .range-row { display: flex; align-items: center; gap: 8px; }
        .range-row input[type=range] { flex: 1; accent-color: var(--accent); padding: 0; border: none; background: transparent; }
        .range-row .range-val { font-size: 11px; color: var(--accent); font-weight: 600; min-width: 28px; text-align: right; }

        /* Upload zone */
        .upload-zone {
            border: 2px dashed var(--border); border-radius: 8px; padding: 14px;
            text-align: center; cursor: pointer; transition: all .2s; position: relative;
        }
        .upload-zone:hover, .upload-zone.dragover { border-color: var(--accent); background: var(--accent-glow); }
        .upload-zone p { font-size: 11px; color: var(--text-muted); }
        .upload-zone .icon { font-size: 22px; margin-bottom: 4px; }
        .upload-zone input { display: none; }
        .upload-status { font-size: 10px; color: var(--green); margin-top: 4px; }

        /* Session list */
        .session-list { display: flex; flex-direction: column; gap: 3px; margin-top: 6px; max-height: 150px; overflow-y: auto; }
        .session-item {
            display: flex; justify-content: space-between; align-items: center;
            padding: 7px 9px; border-radius: 6px; font-size: 11px;
            color: var(--text-secondary); cursor: pointer; transition: background .2s;
        }
        .session-item:hover { background: var(--bg-hover); }
        .session-item.active { background: var(--accent-glow); color: var(--text-primary); }
        .session-item .del-btn {
            background: none; border: none; color: var(--text-muted); cursor: pointer;
            font-size: 13px; padding: 0 3px; opacity: 0; transition: opacity .2s;
        }
        .session-item:hover .del-btn { opacity: 1; }
        .session-item .del-btn:hover { color: var(--red); }

        /* ===== MAIN CHAT ===== */
        .main { flex: 1; display: flex; flex-direction: column; }

        .chat-header {
            padding: 14px 24px; border-bottom: 1px solid var(--border);
            display: flex; justify-content: space-between; align-items: center;
            background: var(--bg-secondary); transition: background .3s;
        }
        .chat-header h1 { font-size: 18px; font-weight: 700; }
        .chat-header p { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
        .header-actions { display: flex; gap: 8px; align-items: center; }
        .clear-btn {
            background: var(--bg-card); border: 1px solid var(--border); color: var(--text-muted);
            width: 34px; height: 34px; border-radius: 8px; cursor: pointer; font-size: 15px;
            display: flex; align-items: center; justify-content: center; transition: all .2s;
        }
        .clear-btn:hover { color: var(--red); border-color: var(--red); }

        .messages {
            flex: 1; overflow-y: auto; padding: 20px 24px; display: flex;
            flex-direction: column; gap: 12px;
        }
        .messages::-webkit-scrollbar { width: 5px; }
        .messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

        .msg { display: flex; flex-direction: column; animation: fadeIn .3s ease; }
        .msg.user { align-items: flex-end; }
        .msg.azan { align-items: flex-start; }
        .msg-bubble {
            max-width: 70%; padding: 12px 16px; border-radius: 14px;
            font-size: 14px; line-height: 1.55; word-wrap: break-word;
            white-space: pre-wrap;
        }
        .msg.user .msg-bubble { background: var(--msg-user-bg); color: #fff; border-bottom-right-radius: 4px; }
        .msg.azan .msg-bubble { background: var(--msg-azan-bg); color: var(--text-primary); border-bottom-left-radius: 4px; }
        .msg-meta { font-size: 10px; color: var(--text-muted); margin-top: 3px; display: flex; align-items: center; gap: 6px; }

        /* Fact-check badges */
        .badge-verified { background: rgba(52,211,153,.15); color: var(--green); padding: 1px 7px; border-radius: 10px; font-size: 9px; font-weight: 600; }
        .badge-unverified { background: rgba(251,146,60,.15); color: var(--orange); padding: 1px 7px; border-radius: 10px; font-size: 9px; font-weight: 600; }

        .typing-indicator { display: flex; gap: 4px; padding: 4px 0; }
        .typing-indicator span { width: 7px; height: 7px; background: var(--text-muted); border-radius: 50%; animation: bounce .6s infinite alternate; }
        .typing-indicator span:nth-child(2) { animation-delay: .15s; }
        .typing-indicator span:nth-child(3) { animation-delay: .3s; }
        @keyframes bounce { to { transform: translateY(-6px); opacity: .5; } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

        .input-bar {
            padding: 14px 24px; border-top: 1px solid var(--border);
            display: flex; gap: 10px; align-items: center;
            background: var(--bg-secondary); transition: background .3s;
        }
        .input-bar input {
            flex: 1; padding: 12px 16px; background: var(--bg-input);
            border: 1px solid var(--border); border-radius: 10px;
            color: var(--text-primary); font-size: 14px; outline: none;
            transition: border-color .2s;
        }
        .input-bar input:focus { border-color: var(--accent); }
        .input-bar input::placeholder { color: var(--text-muted); }
        .send-btn {
            width: 44px; height: 44px; background: var(--accent); color: #fff;
            border: none; border-radius: 10px; cursor: pointer; font-size: 18px;
            display: flex; align-items: center; justify-content: center;
            transition: all .2s;
        }
        .send-btn:hover { background: var(--accent-dim); transform: scale(1.05); }
        .send-btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }

        /* Cmd hint */
        .cmd-hint { font-size: 10px; color: var(--text-muted); padding: 0 24px 6px; }
        .cmd-hint code { background: var(--bg-card); padding: 1px 5px; border-radius: 3px; font-size: 10px; }
    </style>
</head>
<body>

    <!-- SIDEBAR -->
    <aside class="sidebar">
        <div class="logo-row">
            <div class="logo">✦ AZAN <sub>v3.0</sub></div>
            <button class="theme-toggle" onclick="toggleTheme()" id="themeBtn" title="Toggle theme">🌙</button>
        </div>

        <button class="new-chat-btn" onclick="newChat()">+ New Chat</button>

        <!-- System Status -->
        <div class="sidebar-card">
            <h3>◆ System Status</h3>
            <div class="status-row"><span class="label">Status</span><span class="badge badge-online">Online</span></div>
            <div class="status-row"><span class="label">Model</span><span class="value" id="sysModel">llama3</span></div>
            <div class="status-row"><span class="label">Database</span><span class="value" id="sysDbSize">—</span></div>
            <div class="status-row"><span class="label">Vectors</span><span class="value" id="sysVectors">—</span></div>
        </div>

        <!-- Knowledge Base -->
        <div class="sidebar-card">
            <h3>✦ Knowledge Base</h3>
            <div class="stats-grid">
                <div class="stat-box"><div class="num" id="statArticles">0</div><div class="lbl">Articles</div></div>
                <div class="stat-box"><div class="num" id="statPairs">0</div><div class="lbl">Training<br>Pairs</div></div>
                <div class="stat-box"><div class="num" id="statSessions">0</div><div class="lbl">Sessions</div></div>
            </div>
            <div class="tags">
                <span class="tag">business</span><span class="tag">technology</span>
                <span class="tag">politics</span><span class="tag">world</span><span class="tag">science</span>
                <span class="tag">sports</span><span class="tag">entertainment</span><span class="tag">national</span>
            </div>
        </div>

        <!-- AI Settings (Phase 4) -->
        <div class="sidebar-card">
            <h3>⚙ AI Settings</h3>
            <div class="settings-group">
                <label>Model</label>
                <select id="modelSelect" onchange="updateModelLabel()">
                    <option value="llama3" selected>Loading models...</option>
                </select>
                <button id="pullModelsBtn" onclick="pullModel()" style="width: 100%; padding: 4px; margin-top: 5px; font-size: 10px; background: var(--bg-input); color: var(--text-secondary); border: 1px solid var(--border); border-radius: 4px; cursor: pointer;">Pull Selected Model</button>
            </div>
            <div class="settings-group">
                <label>Temperature</label>
                <div class="range-row">
                    <input type="range" id="tempSlider" min="0" max="100" value="50"
                           oninput="document.getElementById('tempVal').textContent=(this.value/100).toFixed(2)">
                    <span class="range-val" id="tempVal">0.50</span>
                </div>
            </div>
            <div class="settings-group">
                <label>Top-P</label>
                <div class="range-row">
                    <input type="range" id="topPSlider" min="0" max="100" value="90"
                           oninput="document.getElementById('topPVal').textContent=(this.value/100).toFixed(2)">
                    <span class="range-val" id="topPVal">0.90</span>
                </div>
            </div>
        </div>

        <!-- Auto-Training Status (Phase 4) -->
        <div class="sidebar-card">
            <h3>🧠 Auto-Training</h3>
            <div class="status-row"><span class="label">Status</span><span class="badge badge-training" id="trainStatus">Active</span></div>
            <div class="status-row"><span class="label">Sessions</span><span class="value" id="trainCount">—</span></div>
            <div class="status-row"><span class="label">Last Run</span><span class="value" id="trainLast">—</span></div>
            <div class="status-row"><span class="label">Avg Reward</span><span class="value" id="trainReward">—</span></div>
        </div>

        <!-- Document Upload (Phase 3+4) -->
        <div class="sidebar-card">
            <h3>📄 Learn from Documents</h3>
            <div class="upload-zone" id="uploadZone" onclick="document.getElementById('fileInput').click()">
                <div class="icon">📁</div>
                <p>Drop PDF / Markdown here</p>
                <input type="file" id="fileInput" accept=".pdf,.md,.markdown,.txt" onchange="uploadFile(this)">
            </div>
            <div class="upload-status" id="uploadStatus"></div>
        </div>

        <!-- Sessions -->
        <div class="sidebar-card">
            <h3>◉ Chat Sessions</h3>
            <div class="session-list" id="sessionList"><span style="color:var(--text-muted);font-size:11px;">Loading…</span></div>
        </div>
    </aside>

    <!-- MAIN CHAT -->
    <div class="main">
        <div class="chat-header">
            <div>
                <h1>AZAN AI Chat</h1>
                <p>Powered by Semantic RAG · RL-enhanced Knowledge · <span id="headerModel">Llama3</span></p>
            </div>
            <div class="header-actions">
                <button class="clear-btn" onclick="clearChat()" title="Clear chat">🗑</button>
            </div>
        </div>

        <div class="messages" id="messages"></div>

        <div class="cmd-hint">💡 Commands: <code>solve x^2+5x+6</code> · <code>integrate sin(x)</code> · <code>limit sin(x)/x as x-&gt;0</code> · <code>physics v=20 u=0 t=5 find a</code> · <code>convert 100 celsius to fahrenheit</code></div>
        <div class="input-bar">
            <input type="text" id="chatInput" placeholder="Ask me anything..." onkeydown="if(event.key==='Enter')sendChat()" autocomplete="off">
            <button class="send-btn" id="sendBtn" onclick="sendChat()">➤</button>
        </div>
    </div>

<script>
const API = window.location.origin;
let currentSession = 'sess_' + Date.now();

// ==================== THEME ====================
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('azan-theme', next);
    document.getElementById('themeBtn').textContent = next === 'dark' ? '🌙' : '☀️';
}
(function initTheme() {
    const saved = localStorage.getItem('azan-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    document.getElementById('themeBtn').textContent = saved === 'dark' ? '🌙' : '☀️';
})();

// ==================== SIDEBAR DATA ====================
async function loadSidebarStats() {
    try {
        const res = await fetch(API + '/api/db/summary');
        const d = await res.json();
        document.getElementById('statArticles').textContent = d.articles || 0;
        document.getElementById('statPairs').textContent = d.training_pairs || 0;
        document.getElementById('statSessions').textContent = d.sessions || 0;
        document.getElementById('sysDbSize').textContent = (d.db_size_kb || 0) + ' KB';
        if (d.vector_store && d.vector_store.total_vectors !== undefined) {
            document.getElementById('sysVectors').textContent = d.vector_store.total_vectors;
        }
    } catch(e) { console.error(e); }
}

async function loadTrainingStatus() {
    try {
        const res = await fetch(API + '/auto-training/status');
        const d = await res.json();
        const badge = document.getElementById('trainStatus');
        badge.textContent = d.is_running ? 'Active' : 'Stopped';
        badge.className = 'badge ' + (d.is_running ? 'badge-training' : 'badge-online');
        document.getElementById('trainCount').textContent = d.training_count || 0;
        if (d.last_training_time) {
            const t = new Date(d.last_training_time);
            document.getElementById('trainLast').textContent = t.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
        }
    } catch(e) {}
    try {
        const res2 = await fetch(API + '/auto-training/stats');
        const s = await res2.json();
        document.getElementById('trainReward').textContent = s.average_reward || '—';
    } catch(e) {}
}

async function loadSessions() {} // overridden in Phase 7 script below

function switchSession(sid) { currentSession = sid; loadSessionHistory(sid); loadSessions(); }

async function loadSessionHistory(sid) {
    const msgs = document.getElementById('messages');
    msgs.innerHTML = '';
    try {
        const res = await fetch(API + '/chat/history/' + sid);
        const d = await res.json();
        if (d.history) d.history.forEach(m => addMessage(m.content, m.role === 'user' ? 'user' : 'azan', false));
    } catch(e) { console.error(e); }
}

async function deleteSession(sid) {
    try { await fetch(API + '/api/sessions/' + sid, { method: 'DELETE' }); if (sid === currentSession) newChat(); loadSessions(); loadSidebarStats(); } catch(e) {}
}

function newChat() {
    currentSession = 'sess_' + Date.now();
    document.getElementById('messages').innerHTML = '';
    addMessage("Hello! I'm AZAN, your AI assistant. How can I help you today?", 'azan', false);
    loadSessions();
}

async function loadModels() {
    try {
        const res = await fetch(API + '/dashboard/models-list');
        const d = await res.json();
        const sel = document.getElementById('modelSelect');
        const currentModel = sel.value || 'llama3';
        
        if (d.models && d.models.length > 0) {
            sel.innerHTML = d.models.map(m => {
                const name = m.includes(':') ? m.split(':')[0] : m;
                const isSelected = m === currentModel || name === currentModel ? ' selected' : '';
                return `<option value="${m}"${isSelected}>${name.charAt(0).toUpperCase() + name.slice(1)}</option>`;
            }).join('');
            
            // Add non-installed popular models if not present
            const popular = ['mistral', 'gemma2', 'phi3', 'codellama'];
            popular.forEach(p => {
                if (!d.models.some(m => m.startsWith(p))) {
                    sel.innerHTML += `<option value="${p}" style="color:var(--text-muted);">(Not installed) ${p.charAt(0).toUpperCase() + p.slice(1)}</option>`;
                }
            });
        }
        updateModelLabel();
    } catch(e) { console.error(e); }
}

async function pullModel() {
    const model = document.getElementById('modelSelect').value;
    const btn = document.getElementById('pullModelsBtn');
    btn.textContent = 'Pulling ' + model + '...';
    btn.disabled = true;
    try {
        const res = await fetch(API + '/api/models/pull', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: model })
        });
        const d = await res.json();
        if (d.status === 'success') {
            alert('Model pulled successfully! Refreshing list.');
            await loadModels();
        } else {
            alert('Failed to pull model: ' + d.message);
        }
    } catch(e) {
        alert('Error pulling model: ' + e.message);
    }
    btn.textContent = 'Pull Selected Model';
    btn.disabled = false;
}

function updateModelLabel() {
    const sel = document.getElementById('modelSelect');
    if (sel.options[sel.selectedIndex]) {
        document.getElementById('sysModel').textContent = sel.options[sel.selectedIndex].text;
        document.getElementById('headerModel').textContent = sel.options[sel.selectedIndex].text.replace('(Not installed) ', '');
    }
}

// NOTE: sendChat, addMessage, clearChat, scrollDown, escapeHtml, loadSessions, and INIT
// are defined in the Phase 7 <script> block below this one.
</script>

<style>
/* ===== MARKDOWN STYLES ===== */
.msg-bubble pre { background: #0d1117; border-radius: 6px; padding: 10px 12px; overflow-x: auto; margin: 8px 0; }
.msg-bubble pre code { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px; background: none; padding: 0; }
.msg-bubble code:not(pre code) { background: rgba(124,92,252,.2); padding: 1px 5px; border-radius: 3px; font-size: 12px; }
.msg-bubble h1, .msg-bubble h2, .msg-bubble h3 { margin: 10px 0 4px; font-weight: 700; }
.msg-bubble h1 { font-size: 1.1em; } .msg-bubble h2 { font-size: 1em; } .msg-bubble h3 { font-size: .95em; }
.msg-bubble p { margin: 5px 0; }
.msg-bubble ul, .msg-bubble ol { padding-left: 20px; margin: 5px 0; }
.msg-bubble li { margin: 3px 0; }
.msg-bubble blockquote { border-left: 3px solid var(--accent); padding-left: 10px; color: var(--text-secondary); margin: 6px 0; }
.msg-bubble table { border-collapse: collapse; width: 100%; margin: 8px 0; }
.msg-bubble th, .msg-bubble td { border: 1px solid var(--border); padding: 5px 8px; font-size: 12px; }
.msg-bubble th { background: var(--bg-input); font-weight: 600; }
.msg-bubble strong { color: var(--text-primary); }
.stream-cursor::after { content: '▋'; animation: blink .7s steps(1) infinite; color: var(--accent); margin-left: 1px; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
</style>

<script>
// ==================== STREAMING SEND CHAT (Phase 7) ====================
async function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    addMessage(msg, 'user');
    input.value = '';
    document.getElementById('sendBtn').disabled = true;

    const typing = document.createElement('div');
    typing.className = 'msg azan';
    typing.id = 'typingIndicator';
    typing.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    document.getElementById('messages').appendChild(typing);
    scrollDown();

    // Detect agentic commands (non-streaming)
    const lc = msg.toLowerCase();
    const chatBody = {
        prompt: msg,
        session_id: currentSession,
        model: document.getElementById('modelSelect').value,
        temperature: parseFloat(document.getElementById('tempSlider').value) / 100,
        top_p: parseFloat(document.getElementById('topPSlider').value) / 100
    };

    let agentCommand = null;
    let agentBody = null;

    if (lc.startsWith('fact-check ') || lc.startsWith('factcheck ')) {
        agentCommand = '/api/agent/fact-check';
        agentBody = { claim: msg.replace(/^(fact-?check\s+)/i, '') };
    } else if (lc.startsWith('scrape ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'scrape', args: { url: msg.replace(/^scrape\s+/i, '').trim() } };
    } else if (lc.startsWith('solve ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'solve_math', args: { expression: msg.replace(/^solve\s+/i, '').trim(), task: 'auto' } };
    } else if (lc.startsWith('integrate ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'solve_math', args: { expression: msg.replace(/^integrate\s+/i, '').trim(), task: 'integrate' } };
    } else if (lc.startsWith('differentiate ') || lc.startsWith('diff ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'solve_math', args: { expression: msg.replace(/^(?:differentiate|diff)\s+/i, '').trim(), task: 'differentiate' } };
    } else if (lc.startsWith('limit ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'solve_math', args: { expression: msg.replace(/^limit\s+/i, '').trim(), task: 'limit' } };
    } else if (lc.startsWith('series ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'solve_math', args: { expression: msg.replace(/^series\s+/i, '').trim(), task: 'series' } };
    } else if (lc.startsWith('physics ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'solve_physics', args: { problem: msg.replace(/^physics\s+/i, '').trim(), domain: 'auto' } };
    } else if (lc.startsWith('calc ') || lc.startsWith('calculate ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'solve_math', args: { expression: msg.replace(/^(?:calc|calculate)\s+/i, '').trim(), task: 'auto' } };
    } else if (lc.startsWith('convert ')) {
        agentCommand = '/api/agent/execute';
        agentBody = { command: 'unit_convert', args: { problem: msg.replace(/^convert\s+/i, '').trim() } };
    }

    try {
        if (agentCommand) {
            // Non-streaming agentic commands
            const res = await fetch(API + agentCommand, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(agentBody)
            });
            const data = await res.json();
            typing.remove();
            if (agentCommand === '/api/agent/fact-check') {
                const verdict = data.verdict || 'unverified';
                const badge = verdict === 'confirmed' ? 'verified' : 'unverified';
                addMessage(data.reasoning || data.detail || JSON.stringify(data), 'azan', true, badge);
            } else {
                addMessage(data.result || data.detail || JSON.stringify(data), 'azan');
            }
        } else {
            // === STREAMING CHAT ===
            typing.remove();
            const msgDiv = createStreamingBubble();

            const res = await fetch(API + '/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(chatBody)
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fullText = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.token) {
                            fullText += data.token;
                            renderMarkdownInBubble(msgDiv, fullText, true);
                            scrollDown();
                        }
                        if (data.done) {
                            renderMarkdownInBubble(msgDiv, fullText, false);
                        }
                    } catch(e) {}
                }
            }
        }
        loadSessions();
        loadSidebarStats();
    } catch(e) {
        try { typing.remove(); } catch(_) {}
        addMessage('Error: ' + e.message, 'azan');
    }
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('chatInput').focus();
}

// ==================== MARKDOWN RENDERING ====================
function initMarked() {
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function(code, lang) {
                if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                    try { return hljs.highlight(code, { language: lang }).value; } catch(e) {}
                }
                return code;
            }
        });
    }
}
initMarked();

function renderMd(text) {
    if (typeof marked === 'undefined') return escapeHtml(text);
    try { return marked.parse(text); }
    catch(e) { return escapeHtml(text); }
}

function createStreamingBubble() {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'msg azan';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    div.innerHTML = '<div class="msg-bubble stream-cursor"></div><div class="msg-meta">' + time + '</div>';
    msgs.appendChild(div);
    scrollDown();
    return div.querySelector('.msg-bubble');
}

function renderMarkdownInBubble(bubble, text, streaming) {
    bubble.innerHTML = renderMd(text);
    if (streaming) { bubble.classList.add('stream-cursor'); }
    else { bubble.classList.remove('stream-cursor'); }
    if (typeof hljs !== 'undefined') {
        bubble.querySelectorAll('pre code').forEach(b => { try { hljs.highlightElement(b); } catch(e) {} });
    }
}

function addMessage(text, role, animate = true, factBadge = null) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    if (!animate) div.style.animation = 'none';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let badgeHtml = '';
    if (role === 'azan' && factBadge) {
        const cls = factBadge === 'verified' ? 'badge-verified' : 'badge-unverified';
        const label = factBadge === 'verified' ? '✓ Verified' : '⚠ Unverified';
        badgeHtml = '<span class="' + cls + '">' + label + '</span>';
    }
    // AI messages get markdown rendering, user messages get escaped HTML
    const content = role === 'azan' ? renderMd(text) : escapeHtml(text);
    div.innerHTML = '<div class="msg-bubble">' + content + '</div><div class="msg-meta">' + time + ' ' + badgeHtml + '</div>';
    if (role === 'azan' && typeof hljs !== 'undefined') {
        div.querySelectorAll('pre code').forEach(b => { try { hljs.highlightElement(b); } catch(e) {} });
    }
    msgs.appendChild(div);
    scrollDown();
}

function clearChat() { deleteSession(currentSession); }
function scrollDown() { const m = document.getElementById('messages'); m.scrollTop = m.scrollHeight; }
function escapeHtml(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
function clearChat() { deleteSession(currentSession); }
function scrollDown() { const m = document.getElementById('messages'); m.scrollTop = m.scrollHeight; }

// ==================== FILE UPLOAD ====================
const uploadZone = document.getElementById('uploadZone');
['dragover','dragenter'].forEach(e => uploadZone.addEventListener(e, ev => { ev.preventDefault(); uploadZone.classList.add('dragover'); }));
['dragleave','drop'].forEach(e => uploadZone.addEventListener(e, ev => { ev.preventDefault(); uploadZone.classList.remove('dragover'); }));
uploadZone.addEventListener('drop', ev => { if (ev.dataTransfer.files.length) uploadFileObj(ev.dataTransfer.files[0]); });

function uploadFile(input) { if (input.files.length) uploadFileObj(input.files[0]); }

async function uploadFileObj(file) {
    const status = document.getElementById('uploadStatus');
    status.textContent = 'Uploading ' + file.name + '...';
    status.style.color = 'var(--text-secondary)';
    const form = new FormData();
    form.append('file', file);
    try {
        const res = await fetch(API + '/api/documents/upload', { method: 'POST', body: form });
        const d = await res.json();
        if (d.success) {
            status.textContent = '✓ ' + d.chunks + ' chunks indexed from ' + file.name;
            status.style.color = 'var(--green)';
            loadSidebarStats();
        } else {
            status.textContent = '✗ ' + (d.detail || d.error || 'Failed');
            status.style.color = 'var(--red)';
        }
    } catch(e) {
        status.textContent = '✗ Upload failed';
        status.style.color = 'var(--red)';
    }
}

function timeAgo(ts) {
    if (!ts) return '';
    const diff = (Date.now() - new Date(ts + ' UTC').getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
}

async function loadSessions() {
    try {
        const res = await fetch(API + '/api/sessions');
        const d = await res.json();
        const list = document.getElementById('sessionList');
        if (!d.sessions || d.sessions.length === 0) {
            list.innerHTML = '<span style="color:var(--text-muted);font-size:11px;">No sessions yet</span>';
            return;
        }
        list.innerHTML = d.sessions.map(s => {
            const active = s.session_id === currentSession ? ' active' : '';
            const title = (s.title || 'Untitled').substring(0, 26);
            const when = timeAgo(s.last_activity);
            return '<div class="session-item' + active + '" onclick="switchSession(\'' + s.session_id + '\')">' +
                '<div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">' +
                '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(title) + '</span>' +
                '<span style="font-size:9px;color:var(--text-muted);flex-shrink:0;">' + when + '</span>' +
                '</div>' +
                '<button class="del-btn" onclick="event.stopPropagation();deleteSession(\'' + s.session_id + '\')")>✕</button>' +
                '</div>';
        }).join('');
    } catch(e) { console.error(e); }
}

// ==================== INIT ====================
loadSidebarStats();
loadSessions();
loadTrainingStatus();
loadModels();
addMessage("Hello! I'm AZAN, your AI assistant. How can I help you today?", 'azan', false);
document.getElementById('chatInput').focus();
setInterval(loadTrainingStatus, 30000);
setInterval(loadSidebarStats, 60000);
setInterval(loadSessions, 15000);
</script>

</body>
</html>"""




# ============================================================================
# ROUTE 2: CHAT API (/chat)
# ============================================================================

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with multi-turn memory.
    Loads last N messages from SQLite and passes them to Ollama for context.
    """
    try:
        # 1. Load conversation history from SQLite for multi-turn memory
        history = []
        try:
            db = get_database()
            raw_history = db.get_chat_history(request.session_id, limit=20)
            history = [{"role": m["role"], "content": m["content"]} for m in raw_history]
        except Exception as e:
            logger.warning(f"Could not load history: {e}")

        # 2. Use RL-enhanced inference with knowledge base + history
        try:
            engine = get_inference_engine()
            response_text = engine.predict(
                request.prompt,
                model=request.model,
                temperature=request.temperature or 0.5,
                top_p=request.top_p or 0.9,
                history=history
            )
        except Exception as e:
            logger.warning(f"RL Inference failed, falling back: {e}")
            response_text = predict_chat(request.prompt, model_name=request.model, speed_mode=True)

        # 3. Store in Chat History (SQLite)
        try:
            db = get_database()
            db.add_chat_message(request.session_id, "user", request.prompt, request.model)
            db.add_chat_message(request.session_id, "azan", response_text, request.model)
        except Exception as e:
            logger.warning(f"Failed to log chat to database: {e}")

        return ChatResponse(response=response_text, model=request.model)

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
def chat_stream_endpoint(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.
    Streams tokens from Ollama token-by-token so the UI can display words as they arrive.
    """
    import json as _json

    # 1. Load history
    history = []
    try:
        db = get_database()
        raw_history = db.get_chat_history(request.session_id, limit=20)
        history = [{"role": m["role"], "content": m["content"]} for m in raw_history]
    except Exception as e:
        logger.warning(f"Could not load history for streaming: {e}")

    # 2. Log user message immediately
    try:
        db = get_database()
        db.add_chat_message(request.session_id, "user", request.prompt, request.model)
    except Exception as e:
        logger.warning(f"Failed to log user message: {e}")

    full_response = []

    def event_generator():
        # Stream from RL inference engine
        try:
            engine = get_inference_engine()
            for chunk in engine.stream_predict(
                request.prompt,
                model=request.model,
                temperature=request.temperature or 0.5,
                top_p=request.top_p or 0.9,
                history=history
            ):
                full_response.append(chunk)
                yield f"data: {_json.dumps({'token': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {_json.dumps({'token': f'[Error: {e}]'})}\n\n"

        # Save full response to DB after streaming completes
        full_text = "".join(full_response)
        try:
            db = get_database()
            db.add_chat_message(request.session_id, "azan", full_text, request.model)
        except Exception as e:
            logger.warning(f"Failed to log streamed response: {e}")

        # Send done signal
        yield f"data: {_json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
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
        engine = get_inference_engine()
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
        engine = get_inference_engine()
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
