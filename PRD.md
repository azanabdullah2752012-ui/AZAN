# Product Requirements Document (PRD) - AZAN AI Chatbot

**Document Version:** 1.0  
**Last Updated:** February 22, 2026  
**Status:** Active / Production

---

## 1. Executive Summary

AZAN is a **local, privacy-first AI chatbot platform** powered by Llama3 via Ollama. It provides intelligent conversational capabilities through a modern web interface with optional fine-tuning for specialized roles (currently: Presidential Advisor).

**Key Value Proposition:**
- 🔒 **Privacy**: All processing happens locally, no data sent to external APIs
- ⚡ **Performance**: Instant responses with local inference
- 🎓 **Customizable**: Fine-tunable models for domain-specific use cases
- 🎯 **Production-Ready**: Deployed and tested on macOS

---

## 2. Product Vision

Create an accessible, customizable local AI assistant that can be:
1. **Deployed locally** without external dependencies
2. **Fine-tuned** for specific use cases (presidential advisor, domain expert, etc.)
3. **Extended** with additional features and integrations
4. **Scaled** to support multiple concurrent users

---

## 3. User Personas

### 3.1 Primary Users
- **Individual Developers** - Want local AI without API costs
- **Organizations** - Need privacy-compliant AI solutions
- **Researchers** - Study fine-tuning and RLHF techniques
- **Power Users** - Customize models for specific tasks

### 3.2 Use Cases
- General knowledge Q&A
- Specialized domain expertise (law, medicine, governance)
- Training data for ML pipelines
- AI model experimentation
- Privacy-sensitive applications

---

## 4. Feature Set

### 4.1 Core Features (MVP - Current)

#### Chat Interface
- ✅ Web-based chat UI (HTML/CSS/JavaScript)
- ✅ Real-time message streaming
- ✅ Message history within session
- ✅ Error handling and user feedback
- ✅ Responsive design (desktop/mobile)
- ✅ Modern gradient UI with animations

#### API Endpoints
- ✅ `GET /` - Serve web interface
- ✅ `POST /chat` - Send message and get response
- ✅ `GET /health` - Server health check
- ✅ `GET /predict` - Legacy linear regression endpoint
- ✅ `GET /docs` - Auto-generated API documentation (Swagger)

#### Model Management
- ✅ Base model: Llama3 (8B parameters)
- ✅ Fine-tuned variant: llama3_president_rlhf
- ✅ Model switching capability
- ✅ Configurable inference parameters (temperature, top_k, top_p)

#### Training & Fine-tuning
- ✅ Data loading from CSV format
- ✅ Data preprocessing and deduplication
- ✅ RLHF (Reinforcement Learning with Human Feedback)
- ✅ 8-dimensional reward function scoring
- ✅ Training artifact generation (JSONL, Modelfile, JSON report)

### 4.2 Planned Features (Roadmap)

#### Phase 2: User Management
- [ ] User accounts and authentication
- [ ] Conversation history persistence
- [ ] User preferences (model selection, temperature, etc.)
- [ ] Usage analytics and metrics

#### Phase 3: Advanced Training
- [ ] Web UI for data upload and training
- [ ] Real-time training progress monitoring
- [ ] Model versioning and rollback
- [ ] A/B testing different models
- [ ] Batch inference for document processing

#### Phase 4: Enterprise Features
- [ ] Multi-user support with rate limiting
- [ ] Role-based access control (RBAC)
- [ ] Audit logging
- [ ] API key management
- [ ] Webhook integrations
- [ ] Database backend (PostgreSQL)

#### Phase 5: Integrations
- [ ] Slack bot integration
- [ ] Discord bot integration
- [ ] Email processing
- [ ] File upload and processing
- [ ] Integration with external APIs
- [ ] Custom knowledge base (RAG - Retrieval Augmented Generation)

---

## 5. Technical Architecture

### 5.1 Technology Stack

**Backend**
- FastAPI 0.128.8 (REST API framework)
- Uvicorn 0.39.0 (ASGI server)
- Python 3.9 (runtime)
- Ollama (local LLM runtime)
- Llama3 (base model)

**Frontend**
- HTML5 (markup)
- CSS3 (styling with animations)
- Vanilla JavaScript (no frameworks)
- Fetch API (HTTP requests)

**ML/AI**
- Ollama (local inference)
- Llama3 (8B parameters)
- RLHF training pipeline
- Reward function (8-dimensional scoring)

**Data**
- CSV (training data input)
- JSONL (training data format)
- JSON (reports and metadata)
- NumPy (numerical operations)

**Development**
- Virtual environment (.venv)
- pip (package manager)
- zsh (shell)
- Git (version control)

### 5.2 System Architecture

```
User Browser
    ↓ (HTTP/JSON)
FastAPI Server (Port 8000)
    ├── webui/app.py (routes)
    ├── src/inference.py (LLM interface)
    └── src/train_rlhf.py (training pipeline)
    ↓ (HTTP/REST)
Ollama Server (Port 11434)
    └── Llama3 Model (local inference)
```

### 5.3 Data Flow

```
User Input → Browser → POST /chat → Inference → Ollama → Llama3 → Response → Browser → Display
```

### 5.4 File Structure

```
/Users/azan/Desktop/AZAN/
├── src/
│   ├── inference.py           # Core LLM inference module
│   ├── train_rlhf.py          # RLHF training pipeline
│   ├── model.py               # Legacy linear regression
│   └── train.py               # Legacy training script
├── webui/
│   └── app.py                 # FastAPI application with web UI
├── data/
│   ├── chat_data.csv          # General Q&A training data
│   ├── presidential_advisor_data.csv  # Presidential advisor training
│   └── *.jsonl                # Processed training formats
├── model/
│   ├── Modelfile_RLHF         # Ollama model specification
│   ├── rlhf_training_data.jsonl # Training examples
│   └── rlhf_training_report.json # Training metrics
├── .venv/                     # Python virtual environment
├── requirements.txt           # Python dependencies
├── PRD.md                     # This document
├── SETUP_COMPLETE.md          # Setup guide
├── README.md                  # Project overview
└── start.sh                   # Launch script
```

---

## 6. Requirements

### 6.1 Functional Requirements

#### FR-1: Chat Interface
- Users must be able to input questions/prompts
- System must display responses in real-time
- System must handle long responses gracefully
- System must show loading indicators during inference

#### FR-2: Model Inference
- System must support multiple model variants (base and fine-tuned)
- System must allow configurable inference parameters
- System must return structured JSON responses
- System must handle connection failures gracefully

#### FR-3: Training Pipeline
- System must load training data from CSV format
- System must preprocess and validate training data
- System must calculate reward scores (1-5 scale)
- System must generate high-quality training examples (≥3.5 score)
- System must export training artifacts in JSONL format
- System must create Ollama Modelfile specification
- System must generate detailed training reports (JSON)

#### FR-4: Model Management
- System must support switching between model variants
- System must validate model availability before inference
- System must provide model health checks
- System must track which model is currently active

### 6.2 Non-Functional Requirements

#### NFR-1: Performance
- Chat response time: < 30 seconds per message
- Training time: < 15 minutes for 20 examples
- API response time: < 100ms (excluding LLM inference)
- Throughput: Support 10+ concurrent users

#### NFR-2: Reliability
- System uptime: 99% during business hours
- Error recovery: Auto-restart on connection loss
- Data integrity: No data loss on failure
- Graceful degradation: Clear error messages to users

#### NFR-3: Security
- No external API keys or credentials in code
- No user data sent to external services
- All processing local and private
- CORS properly configured for web access

#### NFR-4: Scalability
- Support additional models without code changes
- Support custom training data easily
- API can handle future features without refactor
- Database-ready architecture (for Phase 4)

#### NFR-5: Maintainability
- Code is well-documented
- Training pipeline is reproducible
- Models are version-controlled
- Clear separation of concerns

#### NFR-6: User Experience
- Intuitive chat interface
- Clear error messages
- Responsive on mobile/desktop
- Smooth animations and transitions
- Keyboard shortcuts (Enter to send)

---

## 7. Success Metrics

### 7.1 User Engagement
- Average conversation length (messages per session)
- Session duration
- Daily/weekly active users
- Feature usage analytics

### 7.2 Model Performance
- Average response quality rating (1-5)
- Response time distribution
- Error rate percentage
- Reward score average (target: > 3.5/5.0)

### 7.3 System Health
- API uptime percentage
- Error rate per endpoint
- Server resource usage (CPU, memory)
- Model inference latency

### 7.4 Training Metrics
- Training time for different dataset sizes
- Final reward score distribution
- High-quality example percentage (target: > 75%)
- Training stability (score variance)

---

## 8. Constraints & Assumptions

### 8.1 Constraints
- **Hardware**: Requires machine with 8GB+ RAM for Llama3
- **Network**: Ollama must run locally (no remote inference)
- **Scale**: Single-user or small team use (not enterprise SaaS)
- **Latency**: AI inference adds 20-60 second delay per message

### 8.2 Assumptions
- **Users**: Technical users comfortable with Python/CLI
- **Deployment**: Runs on developer's personal machine
- **Data**: Users provide their own training data
- **Models**: Ollama and Llama3 remain available/free

### 8.3 Dependencies
- Ollama must be installed and running
- Llama3 model must be pulled: `ollama pull llama3`
- Python 3.9+ with pip
- macOS or Linux OS
- Internet connection for initial model download

---

## 9. Training & Reward Function Specification

### 9.1 RLHF Training Pipeline

**Purpose**: Fine-tune Llama3 to specialize in specific domains (e.g., presidential advisor)

**Steps**:
1. **Load Data**: Read CSV with input (question) and response (ideal answer)
2. **Generate Responses**: Query base Llama3 for candidate responses
3. **Score Responses**: Apply 8-dimensional reward function (1-5 scale)
4. **Filter High-Quality**: Keep examples scoring ≥ 3.5
5. **Export Artifacts**: Generate JSONL, Modelfile, and JSON report
6. **Deploy**: Create new model in Ollama with fine-tuned parameters

### 9.2 Reward Function Dimensions

| Dimension | Weight | Scoring | Purpose |
|-----------|--------|---------|---------|
| **Relevance** | ±0.5 | Word overlap analysis | Ensures answer addresses question |
| **Depth** | ±0.4 | Length (80-300 words) | Prevents shallow or verbose responses |
| **Leadership** | ±0.5 | Keyword presence | For domain-specific roles |
| **Policy Knowledge** | ±0.4 | Governance keywords | Domain expertise indicators |
| **Balance** | ±0.3 | Nuance keywords | Rewards multi-perspective views |
| **Quality Signals** | −0.5 | Weakness penalties | Penalizes uncertainty ("don't know") |
| **Reference Similarity** | ±0.4 | Token overlap | Compares to ideal response |
| **Structure** | ±0.2 | Multi-sentence check | Ensures proper formatting |

**Base Score**: 3.0/5.0 (neutral)  
**Final Score Range**: 1.0 - 5.0

### 9.3 Training Data Format

**Input (CSV)**:
```csv
input,response
"What are the key responsibilities of a president?","A president must lead the nation with vision and strategic decision-making..."
```

**Output (JSONL)**:
```json
{"messages": [{"role": "system", "content": "You are a presidential advisor..."}, {"role": "user", "content": "What are..."}, {"role": "assistant", "content": "A president must..."}], "reward_score": 4.3}
```

---

## 10. API Specification

### 10.1 Endpoints

#### GET / (Root)
- **Purpose**: Serve web chat interface
- **Response**: HTML page with chat UI
- **Status**: 200 OK

#### POST /chat
- **Purpose**: Send message and get AI response
- **Request Body**: 
  ```json
  {"prompt": "Your question here"}
  ```
- **Response Body**:
  ```json
  {
    "response": "AI's response here",
    "model": "llama3_president_rlhf"
  }
  ```
- **Status**: 200 OK on success, 500 on error

#### GET /health
- **Purpose**: Check server health
- **Response**: `{"status": "healthy"}`
- **Status**: 200 OK

#### GET /docs
- **Purpose**: Interactive API documentation (Swagger UI)
- **Response**: HTML page with API docs
- **Status**: 200 OK

#### GET /predict (Legacy)
- **Purpose**: Linear regression prediction (backward compatible)
- **Query Params**: `input` (float)
- **Response**: `{"prediction": value}`
- **Status**: 200 OK

---

## 11. Deployment & Operations

### 11.1 System Requirements

**Minimum**:
- macOS 10.14+ or Linux
- 8GB RAM
- 10GB disk space (for Llama3 model)
- Python 3.9+

**Recommended**:
- 16GB+ RAM
- 20GB disk space
- SSD storage
- Intel/Apple Silicon processor

### 11.2 Installation

```bash
cd /Users/azan/Desktop/AZAN
source .venv/bin/activate
pip install -r requirements.txt
ollama pull llama3
```

### 11.3 Running the Server

```bash
source .venv/bin/activate
python -m uvicorn webui.app:app --reload --host 0.0.0.0 --port 8000
```

Then access: **http://localhost:8000**

### 11.4 Training a Custom Model

```bash
source .venv/bin/activate
python src/train_rlhf.py
ollama create my_custom_model -f model/Modelfile_RLHF
```

### 11.5 Monitoring

- Check server logs for errors
- Monitor Ollama process: `ollama serve`
- Check port availability: `lsof -i :8000`
- Test health: `curl http://localhost:8000/health`

---

## 12. Future Roadmap

### Q1 2026 (Next 3 Months)
- [ ] Add conversation history persistence (SQLite)
- [ ] Implement user authentication (basic)
- [ ] Add model selection dropdown in UI
- [ ] Temperature/top_k controls in chat UI

### Q2 2026
- [ ] PostgreSQL database integration
- [ ] User accounts and login
- [ ] Conversation export (PDF/JSON)
- [ ] Admin dashboard

### Q3 2026
- [ ] Advanced RAG (Retrieval Augmented Generation)
- [ ] Document upload and Q&A
- [ ] Fine-tuning from web UI
- [ ] Real-time training progress

### Q4 2026 & Beyond
- [ ] Multi-user support with rate limiting
- [ ] Enterprise deployment (Docker, Kubernetes)
- [ ] Integration marketplace (Slack, Discord, etc.)
- [ ] Custom model training service
- [ ] Public API tier

---

## 13. Risk Assessment & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Ollama server crashes | User can't chat | Medium | Auto-restart, health checks, error recovery |
| Model generates harmful content | Reputation risk | Low | Input validation, output filters, content moderation |
| Memory exhaustion | Server crash | Medium | Resource limits, request timeouts, cleanup |
| Poor model quality | User dissatisfaction | Medium | Rigorous RLHF training, testing, feedback loop |
| Dependency issues | Build failures | Low | Pin versions, automated testing, CI/CD |

---

## 14. Success Criteria for v1.0

✅ **Completed**:
- Working chat interface
- Base Llama3 inference
- RLHF training pipeline
- Presidential advisor fine-tuning
- API endpoints
- Web UI with animations
- Error handling

🎯 **For Future Versions**:
- User authentication
- Persistent storage
- Advanced features
- Enterprise readiness
- Scalability improvements

---

## 15. Glossary

| Term | Definition |
|------|-----------|
| **RLHF** | Reinforcement Learning with Human Feedback - training method using reward signals |
| **Ollama** | Local LLM runtime for running models like Llama3 |
| **Llama3** | Open-source LLM by Meta, 8B parameters |
| **FastAPI** | Modern Python web framework for building APIs |
| **Modelfile** | Ollama specification for creating custom models |
| **JSONL** | JSON Lines format - one JSON object per line |
| **ASGI** | Asynchronous Server Gateway Interface |
| **Reward Function** | Scoring mechanism (1-5) for evaluating response quality |
| **Fine-tuning** | Training process to specialize model for specific domain |
| **Inference** | Running model to generate predictions/responses |

---

## 16. Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Feb 22, 2026 | AZAN Team | Initial baseline PRD |
| TBD | TBD | TBD | Updates for Phase 2 features |

---

**Document Owner**: AZAN Development Team  
**Last Review Date**: February 22, 2026  
**Next Review Date**: May 22, 2026 (Q2 Planning)

---

**Questions?** Refer to `SETUP_COMPLETE.md` for troubleshooting or `README.md` for project overview.
