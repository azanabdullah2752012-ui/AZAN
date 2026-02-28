# AZAN Project Local Hosts

This file documents all local hosts and ports used by the AZAN system components.

| Port | Service | Purpose |
|------|---------|---------|
| **8000** | **Main AI Interface** | The primary Flask/FastAPI backend serving the premium AI Chat & Knowledge dashboard. |
| **11434** | **Ollama API** | Local LLM server running `llama3` for inference and `nomic-embed-text` for embeddings. |
| **8001** | **Unsupervised Knowledge** | API for the unsupervised learning framework (`azan_unsupervised`). |
| **5432** | **PostgreSQL** | Main database for persistence of training pairs, articles, feedback, and embeddings. |
| **8000** | **Training Dashboard** | The RLHF Training & Monitoring dashboard (integrated into the same port as main interface). |

## Connection URLs

- **Main AI Page:** [http://localhost:8000](http://localhost:8000)
- **Status API:** [http://localhost:8000/api/status](http://localhost:8000/api/status)
- **Knowledge API:** [http://localhost:8000/api/knowledge](http://localhost:8000/api/knowledge)
- **Autolearn API:** [http://localhost:8000/api/autolearn/status](http://localhost:8000/api/autolearn/status)
- **Evaluate API:** [http://localhost:8000/api/evaluate](http://localhost:8000/api/evaluate) *(POST `{"response": "<ai text>"}`) — scores knowledge for storage*
- **Ollama API:** [http://localhost:11434](http://localhost:11434)
- **Unsupervised API:** [http://localhost:8001](http://localhost:8001)

## Environment Setup

Ensure Ollama is running (`ollama serve`) and the virtual environment is activated (`source .venv/bin/activate`) before starting the backend servers.
