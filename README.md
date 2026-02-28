# AZAN - Autonomous Learning AI with Reinforcement Learning

**Status**: ✅ FULLY OPERATIONAL  
**Version**: 2.0.0  
**Server**: Running on `http://localhost:8000`

---

## 🎯 What is AZAN?

AZAN is your personal AI assistant that **learns autonomously** from news sources and continuously improves through reinforcement learning. It combines:

- ✅ **Base AI Knowledge** (Ollama + Llama3 model)
- ✅ **Autonomous Learning** (Continuous RL training, 60-second cycles)
- ✅ **Knowledge Integration** (217 Q&A pairs across 8 categories)
- ✅ **Real-time Monitoring** (API endpoints for training metrics)

---

## 🚀 Quick Start (5 Minutes)

### 1. Verify Server is Running
```bash
curl http://localhost:8000/health
# Response: {"status":"healthy","version":"2.0.0"}
```

### 2. Chat with AZAN
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What have you learned about quantum computing?"}'
```

### 3. Check Training Status
```bash
curl http://localhost:8000/api/rl/status | jq .
```

**See QUICKSTART.md for more examples and DEPLOYMENT_STATUS.md for full technical details.**

---

## 📁 Project Structure

```
AZAN/
├── 📋 Documentation (NEW)
│   ├── README.md (this file)
│   ├── QUICKSTART.md
│   ├── DEPLOYMENT_STATUS.md
│   └── RL_PIPELINE_DOCS.md
│
├── 🧠 AI Core
│   ├── webui/app.py              # FastAPI server + 7 RL endpoints
│   ├── src/inference.py          # Enhanced system prompt + inference
│   ├── src/model.py              # Model utilities
│   ├── src/train.py              # Training utilities
│   ├── src/inshorts_scraper.py   # News scraper
│   └── src/inshorts_trainer.py   # Background news trainer
│
├── 🎓 RL System (NEW - Core Feature)
│   ├── src/rl_pipeline.py        # Autonomous RL orchestrator (400+ lines)
│   ├── src/rl_inference.py       # Knowledge base + inference (300+ lines)
│   └── src/init_rl_data.py       # Data initialization
│
├── 📊 Data & Models
│   ├── data/
│   │   ├── inshorts_articles.json      # 64 source articles
│   │   ├── rl_training_data.json       # 217 Q&A pairs (NEW)
│   │   ├── rl_rewards.json             # Reward tracking (NEW)
│   │   ├── rl_checkpoints/             # Model snapshots (NEW)
│   │   └── sample_data.csv
│   ├── model/linear_model.npz
│   └── requirements.txt
│
└── 🔧 Configuration
    └── start.sh
```

---

## 🎓 What AZAN Knows

AZAN has learned from 64 Inshorts news articles with 217 Q&A pairs covering:

| Category | Topics | Pairs |
|----------|--------|-------|
| **Business** | Markets, earnings, crypto, trade, mergers | 24 |
| **Technology** | AI, quantum computing, 5G, cybersecurity | 24 |
| **Science** | Fusion energy ⭐, gene therapy, CRISPR | 24 |
| **Politics** | Policy, elections, diplomacy | 24 |
| **World** | Global events, humanitarian efforts | 24 |
| **Sports** | Achievements, championships | 24 |
| **Entertainment** | Industry trends, cultural events | 24 |
| **National** | Domestic news, infrastructure | 24 |
| **Other** | Diverse topics | 25 |

---

## 🔌 API Endpoints

### Chat Interface
```bash
POST /chat
# Input: {"prompt": "Your question here"}
# Output: {"response": "AZAN's answer with learned knowledge"}
```

### Health & Status
```bash
GET /health                  # Server status
GET /api/rl/status          # Training metrics
GET /api/rl/knowledge       # Knowledge base summary
GET /api/rl/metrics         # Detailed performance data
```

### Training Control
```bash
POST /api/rl/start-training  # Start training loop
POST /api/rl/stop-training   # Stop training loop
```

---

## ⚙️ How It Works

### Autonomous Training Loop (Every 60 Seconds)
```python
while training_enabled:
    # 1. Load batch of 5 Q&A pairs
    batch = load_batch(batch_size=5)
    
    # 2. Evaluate each pair
    for pair in batch:
        reward = evaluate_response(pair)
        model.update_state(reward)
    
    # 3. Save checkpoint every 10 iterations
    if iteration_count % 10 == 0:
        model.save_checkpoint()
    
    # 4. Wait 60 seconds
    time.sleep(60)
```

### Knowledge-Enhanced Chat
```python
# When user asks a question:
1. Search knowledge base for relevant articles
2. Build context from top matches
3. Inject context into system prompt
4. Query Ollama with enhanced prompt
5. Return response with citations
```

---

## ✨ Key Features

✅ **Fully Autonomous**
- Starts automatically on server startup
- Runs in background (no blocking)
- No manual intervention needed

✅ **Intelligent Learning**
- 60-second training cycles
- Reward-based response evaluation
- Checkpoint system saves progress every 10 iterations

✅ **Knowledge Integration**
- 64 articles indexed by category and keywords
- Smart context injection into responses
- Cites learned sources

✅ **Data Persistence**
- All training data saved to JSON
- Survives server restarts
- Graceful error handling

✅ **Real-time Monitoring**
- API endpoints for training status
- Performance metrics dashboard
- Start/stop training controls

---

## 🧪 Testing

### Verify Everything Works
```bash
# 1. Server health
curl http://localhost:8000/health

# 2. Ask about learned knowledge
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Tell me about fusion energy breakthroughs"}'

# 3. Check training status
curl http://localhost:8000/api/rl/status | jq .

# 4. View knowledge summary
curl http://localhost:8000/api/rl/knowledge | jq .
```

---

## 🔧 Troubleshooting

### Server Won't Start
```bash
# Check if already running
ps aux | grep uvicorn

# Kill and restart
pkill -f "uvicorn.*webui.app"
cd /Users/azan/Desktop/AZAN
nohup python -m uvicorn webui.app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

### Ollama Connection Error
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Start if needed
ollama serve
```

### Chat Returning Old Info
```bash
# Ensure training is enabled
curl -X POST http://localhost:8000/api/rl/start-training

# Wait for next cycle and try again
sleep 60
```

---

## 📚 Full Documentation

- **QUICKSTART.md** - Quick reference and usage examples
- **DEPLOYMENT_STATUS.md** - Complete deployment and testing guide
- **RL_PIPELINE_DOCS.md** - Detailed architecture and implementation
- **Code comments** - Extensive inline documentation

---

## 📋 Original Features (Still Available)

This project originally included:
- Linear regression model training and inference
- FastAPI web UI
- Model artifacts management

**All original functionality is preserved and enhanced with RL capabilities.**

---

## 🚀 Next Steps

1. **Start Using**: Ask AZAN questions about learned knowledge
2. **Monitor**: Check `/api/rl/status` to see training progress
3. **Explore**: Test all API endpoints with different prompts
4. **Review**: Read RL_PIPELINE_DOCS.md for technical details
5. **Customize**: Modify training interval, batch size, or knowledge categories

---

## ✅ System Requirements

- **Python**: 3.9+
- **RAM**: 2GB minimum
- **Storage**: 500MB for checkpoints
- **Network**: Localhost only (127.0.0.1)
- **Dependencies**: See requirements.txt

---

## 📊 Status

**Deployment**: ✅ COMPLETE  
**Server**: ✅ RUNNING (localhost:8000)  
**RL Pipeline**: ✅ ACTIVE  
**Knowledge Base**: ✅ LOADED (217 pairs)  
**Training**: ✅ ENABLED  
**Ready to Use**: ✅ YES

---

**AZAN v2.0.0** - Autonomous Learning AI with Reinforcement Learning  
Last Updated: February 23, 2026  
Status: Production Ready ✅
