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

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.inference import predict_chat
from src.training_dashboard import dashboard
from src.rl_pipeline import initialize_rl_pipeline, get_rl_pipeline
from src.rl_inference import initialize_inference, predict as rl_predict

# Import AZAN curated RL system
try:
    from src.azan_rl_pipeline import initialize_rl_pipeline as init_azan_rl, get_rl_engine, get_rl_trainer
    from src.azan_rl_inference import initialize_inference_engine as init_azan_inference, get_inference_engine
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
    """Initialize auto-training scheduler and RL pipeline on startup."""
    # Initialize AZAN Curated RL System (Priority)
    if AZAN_RL_AVAILABLE:
        try:
            engine, trainer = init_azan_rl(update_interval=30)
            trainer.start()
            logger.info("✅ AZAN Curated RL Pipeline started (Indian Constitution, UN Treaties, Military Strategies, Political Definitions)")
        except Exception as e:
            logger.warning(f"Could not start AZAN RL pipeline: {e}")
        
        try:
            init_azan_inference()
            logger.info("✅ AZAN Data-Only Inference Engine initialized")
        except Exception as e:
            logger.warning(f"Could not initialize AZAN inference: {e}")
    
    try:
        # Initialize RL pipeline with 60-second update interval
        rl_pipeline = initialize_rl_pipeline(update_interval=60)
        rl_pipeline.start_training()
        logger.info("✅ RL Pipeline started on server startup")
    except Exception as e:
        logger.warning(f"Could not start RL pipeline: {e}")
    
    try:
        # Initialize RL inference engine
        initialize_inference()
        logger.info("✅ RL Inference engine initialized")
    except Exception as e:
        logger.warning(f"Could not initialize RL inference: {e}")
    
    try:
        # Initialize restricted inference (training data only)
        from src.restricted_inference import initialize_restricted_inference
        initialize_restricted_inference()
        logger.info("✅ Restricted Inference engine initialized (training data only)")
    except Exception as e:
        logger.warning(f"Could not initialize restricted inference: {e}")
    
    try:
        # Initialize user feedback system
        from src.user_feedback import initialize_feedback
        initialize_feedback()
        logger.info("✅ User Feedback system initialized")
    except Exception as e:
        logger.warning(f"Could not initialize feedback system: {e}")
    
    try:
        # Initialize semantic search engine
        from src.semantic_search import initialize_semantic_search
        initialize_semantic_search()
        logger.info("✅ Semantic Search engine initialized")
    except Exception as e:
        logger.warning(f"Could not initialize semantic search: {e}")
    
    try:
        # Initialize RSS feed integrator and updater
        from src.rss_feed_integrator import initialize_feed_integrator, initialize_feed_updater
        initialize_feed_integrator()
        initialize_feed_updater(update_interval=900)  # 15 minutes
        logger.info("✅ RSS Feed integrator and updater initialized")
    except Exception as e:
        logger.warning(f"Could not initialize RSS feeds: {e}")
    
    try:
        # Initialize RLHF pipeline
        from src.rlhf_pipeline import initialize_rlhf, initialize_rlhf_scheduler
        initialize_rlhf()
        initialize_rlhf_scheduler(check_interval=3600)  # 1 hour
        logger.info("✅ RLHF pipeline and scheduler initialized")
    except Exception as e:
        logger.warning(f"Could not initialize RLHF: {e}")
    
    try:
        # Initialize fine-tuning system
        from src.fine_tuning import initialize_finetuning, initialize_finetuning_scheduler
        initialize_finetuning()
        initialize_finetuning_scheduler(check_interval=86400)  # 1 day
        logger.info("✅ Fine-tuning system initialized")
    except Exception as e:
        logger.warning(f"Could not initialize fine-tuning: {e}")
    
    try:
        # Initialize feed context integration
        from src.feed_context_integration import initialize_context_manager
        initialize_context_manager()
        logger.info("✅ Feed context integration initialized")
    except Exception as e:
        logger.warning(f"Could not initialize feed context: {e}")
    
    try:
        from src.auto_training_scheduler import get_scheduler
        scheduler = get_scheduler()
        
        # Check if auto-training is enabled in config
        if scheduler.config.get("enabled", True):
            scheduler.start()
            logger.info("✅ Auto-training scheduler started on server startup")
        else:
            logger.info("⚠️ Auto-training is disabled in configuration")
    except Exception as e:
        logger.warning(f"Could not start auto-training scheduler: {e}")


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
    """Serve the main HTML dashboard with chat, training, and analytics."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AZAN - AI Chat & RLHF Training Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
        }
        
        .container {
            display: flex;
            width: 100%;
            height: 100vh;
        }
        
        .sidebar {
            width: 250px;
            background: #2c3e50;
            border-right: 2px solid #34495e;
            overflow-y: auto;
            padding: 20px;
            color: #ecf0f1;
        }
        
        .sidebar h2 {
            font-size: 18px;
            margin-bottom: 20px;
            color: #667eea;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .nav-item {
            padding: 12px 15px;
            margin: 8px 0;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.3s ease;
            border-left: 3px solid transparent;
        }
        
        .nav-item:hover {
            background: #34495e;
            border-left-color: #667eea;
        }
        
        .nav-item.active {
            background: #667eea;
            border-left-color: #667eea;
            font-weight: bold;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: white;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 28px;
            font-weight: 600;
        }
        
        .content-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: none;
        }
        
        .content-area.active {
            display: block;
        }
        
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        
        .messages {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 20px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .message {
            margin: 12px 0;
            animation: slideIn 0.3s ease;
        }
        
        .message.user {
            text-align: right;
        }
        
        .message-bubble {
            display: inline-block;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 70%;
            word-wrap: break-word;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .message.user .message-bubble {
            background: #667eea;
            color: white;
        }
        
        .message.bot .message-bubble {
            background: #e9ecef;
            color: #2c3e50;
        }
        
        .input-area {
            display: flex;
            gap: 10px;
        }
        
        input[type="text"], textarea {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-family: inherit;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .loading {
            text-align: center;
            color: #667eea;
            padding: 20px;
        }
        
        .training-form {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
        }
        
        .form-group textarea {
            width: 100%;
            min-height: 100px;
            resize: vertical;
        }
        
        .training-result {
            background: white;
            border: 2px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .reward-score {
            font-size: 48px;
            color: #667eea;
            font-weight: bold;
            text-align: center;
            margin: 20px 0;
        }
        
        .reward-breakdown {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .breakdown-item {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        
        .breakdown-item-value {
            color: #667eea;
            font-size: 18px;
            font-weight: bold;
            margin-top: 5px;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .stat-card h3 {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
        }
        
        .history-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .history-table th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }
        
        .history-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }
        
        .reward-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 12px;
        }
        
        .reward-high {
            background: #d4edda;
            color: #155724;
        }
        
        .reward-medium {
            background: #fff3cd;
            color: #856404;
        }
        
        .reward-low {
            background: #f8d7da;
            color: #721c24;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
            border-left: 4px solid #721c24;
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
            border-left: 4px solid #155724;
        }
        
        .select-model {
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            width: 100%;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>🎯 AZAN</h2>
            <div class="nav-item active" onclick="switchTab('chat')">💬 Chat</div>
            <div class="nav-item" onclick="switchTab('train')">📚 Train AI</div>
            <div class="nav-item" onclick="switchTab('models')">🤖 Models</div>
        </div>
        
        <div class="main-content">
            <div class="header">
                <h1>🎯 AZAN AI Chat & RLHF Training System</h1>
            </div>
            
            <!-- CHAT TAB -->
            <div id="chat" class="content-area active">
                <div class="chat-container">
                    <div class="messages" id="chatMessages"></div>
                    <div class="input-area">
                        <input type="text" id="chatInput" placeholder="Ask me anything..." onkeypress="handleChatKeypress(event)">
                        <button onclick="sendChat()">Send</button>
                    </div>
                </div>
            </div>
            
            <!-- TRAINING TAB -->
            <div id="train" class="content-area">
                <h2>🎓 Interactive RLHF Training</h2>
                <p style="margin-bottom: 20px;">Train the AI by providing Q&A pairs. System generates responses and rates quality.</p>
                
                <div class="training-form">
                    <div class="form-group">
                        <label>Question</label>
                        <textarea id="trainQuestion" placeholder="Ask a question..."></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Ideal Answer</label>
                        <textarea id="trainAnswer" placeholder="What's the ideal answer?"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Model</label>
                        <select id="trainModel" class="select-model">
                            <option value="llama3">Llama3 (Base)</option>
                            <option value="llama3_president_rlhf">Presidential Advisor</option>
                        </select>
                    </div>

                    <div class="form-group" style="display: flex; align-items: center;">
                        <input type="checkbox" id="quickMode" style="margin-right: 10px; width: auto;">
                        <label for="quickMode" style="margin: 0;">⚡ Quick Mode (10x faster with cached responses)</label>
                    </div>
                    
                    <button onclick="submitTraining()" style="width: 100%; margin-top: 10px;">🚀 Train</button>
                </div>
                
                <div id="trainingResult"></div>
            </div>
            
            <!-- DASHBOARD TAB -->
            <div id="dashboard" class="content-area">
                <h2>📊 Training Dashboard</h2>
                <div class="dashboard-grid" id="dashboardStats"></div>
                <h3 style="margin: 20px 0;">Recent Sessions</h3>
                <table class="history-table" id="historyTable">
                    <thead>
                        <tr><th>Model</th><th>Date</th><th>Examples</th><th>Avg Reward</th><th>Status</th></tr>
                    </thead>
                    <tbody id="historyBody"><tr><td colspan="5" style="text-align:center;">Loading...</td></tr></tbody>
                </table>
            </div>
            
            <!-- MODELS TAB -->
            <div id="models" class="content-area">
                <h2>🤖 Model Comparison</h2>
                <div id="modelComparison" style="color: #999;">Loading models...</div>
            </div>
            
            <!-- ANALYTICS TAB -->
            <div id="analytics" class="content-area">
                <h2>📈 Training Analytics</h2>
                <div class="dashboard-grid" id="analyticsStats"></div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;
        
        function switchTab(tabName) {
            document.querySelectorAll('.content-area').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            if (tabName === 'dashboard') loadDashboard();
            if (tabName === 'models') loadModelComparison();
            if (tabName === 'analytics') loadAnalytics();
        }
        
        function handleChatKeypress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendChat();
            }
        }
        
        async function sendChat() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if (!message) return;
            
            addChatMessage(message, 'user');
            input.value = '';
            
            const loadingEl = document.createElement('div');
            loadingEl.className = 'message bot';
            loadingEl.innerHTML = '<div class="message-bubble">⏳ Thinking...</div>';
            document.getElementById('chatMessages').appendChild(loadingEl);
            
            try {
                const response = await fetch(`${API_BASE}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: message })
                });
                
                const data = await response.json();
                loadingEl.remove();
                addChatMessage(data.response, 'bot');
            } catch (error) {
                loadingEl.remove();
                addChatMessage('Error: ' + error.message, 'bot');
            }
        }
        
        function addChatMessage(text, sender) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageEl = document.createElement('div');
            messageEl.className = 'message ' + sender;
            messageEl.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
            messagesDiv.appendChild(messageEl);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        async function submitTraining() {
            const question = document.getElementById('trainQuestion').value.trim();
            const answer = document.getElementById('trainAnswer').value.trim();
            const model = document.getElementById('trainModel').value;
            const quickMode = document.getElementById('quickMode').checked;
            
            if (!question || !answer) {
                showTrainingResult('Fill in both question and answer', false);
                return;
            }
            
            const trainBtn = event.target;
            const originalText = trainBtn.textContent;
            trainBtn.disabled = true;
            trainBtn.textContent = quickMode ? '⚡ Quick Training...' : '🚀 Training...';
            
            document.getElementById('trainingResult').innerHTML = '<div class="loading">⏳ ' + (quickMode ? 'Quick ' : '') + 'Training...</div>';
            
            try {
                const response = await fetch(`${API_BASE}/train`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question, ideal_answer: answer, model, quick_mode: quickMode })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    displayTrainingResult(data);
                    document.getElementById('trainQuestion').value = '';
                    document.getElementById('trainAnswer').value = '';
                } else {
                    showTrainingResult(data.error, false);
                }
            } catch (error) {
                showTrainingResult('Error: ' + error.message, false);
            } finally {
                trainBtn.disabled = false;
                trainBtn.textContent = originalText;
            }
        }
        
        function displayTrainingResult(result) {
            const resultDiv = document.getElementById('trainingResult');
            const score = result.reward_score;
            let badgeClass = score >= 4 ? 'reward-high' : score >= 3 ? 'reward-medium' : 'reward-low';
            
            let breakdown = '';
            if (result.reward_breakdown) {
                const bd = result.reward_breakdown;
                const items = ['relevance', 'depth', 'leadership', 'policy', 'balance', 'quality_signals', 'reference_similarity', 'structure'];
                breakdown = '<div class="reward-breakdown">';
                items.forEach(item => {
                    if (item in bd) {
                        breakdown += `<div class="breakdown-item"><strong>${item.replace(/_/g, ' ')}</strong><div class="breakdown-item-value">${bd[item]}</div></div>`;
                    }
                });
                breakdown += '</div>';
            }
            
            resultDiv.innerHTML = `
                <div class="training-result">
                    <div class="success-message">✅ Training complete!</div>
                    <div class="reward-score">${score.toFixed(2)} <span style="font-size: 24px;">/5.0</span></div>
                    <div style="text-align: center; margin-bottom: 20px;">
                        <span class="reward-badge ${badgeClass}">${score >= 4 ? '⭐⭐⭐⭐ Excellent' : score >= 3 ? '⭐⭐⭐ Good' : '⭐⭐ Needs Work'}</span>
                    </div>
                    <h4>Model Response:</h4>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 10px 0;">${escapeHtml(result.model_response)}</div>
                    ${breakdown}
                </div>
            `;
        }
        
        function showTrainingResult(message, success = true) {
            const resultDiv = document.getElementById('trainingResult');
            resultDiv.innerHTML = `<div class="${success ? 'success-message' : 'error-message'}">${success ? '✅' : '❌'} ${escapeHtml(message)}</div>`;
        }
        
        async function loadDashboard() {
            try {
                const response = await fetch(`${API_BASE}/dashboard/summary`);
                const data = await response.json();
                
                const statsDiv = document.getElementById('dashboardStats');
                statsDiv.innerHTML = `<div class="stat-card"><h3>Total Sessions</h3><div class="stat-value">${data.total_sessions}</div></div>`;
                
                const historyBody = document.getElementById('historyBody');
                if (data.sessions && data.sessions.length > 0) {
                    historyBody.innerHTML = data.sessions.map(s => {
                        const reward = s.average_reward;
                        let badgeClass = reward >= 4 ? 'reward-high' : reward >= 3 ? 'reward-medium' : 'reward-low';
                        return `<tr><td><strong>${s.model_name}</strong></td><td>${new Date(s.created_at).toLocaleDateString()}</td><td>${s.total_examples}</td><td><span class="reward-badge ${badgeClass}">${reward.toFixed(2)}/5.0</span></td><td>${s.status}</td></tr>`;
                    }).join('');
                } else {
                    historyBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No sessions yet</td></tr>';
                }
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        async function loadModelComparison() {
            try {
                const response = await fetch(`${API_BASE}/dashboard/models`);
                const data = await response.json();
                
                const container = document.getElementById('modelComparison');
                if (data.models && data.models.length > 0) {
                    container.innerHTML = data.models.map(m => `
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                            <h3>${m.name}</h3>
                            <p>Avg Reward: ${m.average_reward.toFixed(2)}/5.0</p>
                            <p>Total Trainings: ${m.total_trainings}</p>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<p style="color: #999;">No models trained yet</p>';
                }
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        async function loadAnalytics() {
            try {
                const response = await fetch(`${API_BASE}/dashboard/analytics`);
                const data = await response.json();
                
                const statsDiv = document.getElementById('analyticsStats');
                statsDiv.innerHTML = `
                    <div class="stat-card"><h3>Avg Reward</h3><div class="stat-value">${data.average_reward.toFixed(2)}</div></div>
                    <div class="stat-card"><h3>Highest</h3><div class="stat-value">${data.highest_reward.toFixed(2)}</div></div>
                    <div class="stat-card"><h3>Total</h3><div class="stat-value">${data.total_trainings}</div></div>
                `;
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        loadDashboard();
    </script>
</body>
</html>"""


# ============================================================================
# ROUTE 2: CHAT API (/chat)
# ============================================================================

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint for real-time AI responses.
    Uses RL-enhanced inference with learned knowledge base.
    """
    try:
        # Use RL-enhanced inference with knowledge base
        response = rl_predict(request.prompt)
        return ChatResponse(response=response, model=request.model)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        # Fallback to original inference if RL fails
        try:
            response = predict_chat(request.prompt, model_name=request.model, speed_mode=True)
            return ChatResponse(response=response, model=request.model)
        except:
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
