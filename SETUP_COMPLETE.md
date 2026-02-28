# AZAN Chatbot - Setup Complete ✅

## Overview
You now have a fully functional local AI chatbot powered by **Llama3** via **Ollama**, with a modern web interface and a training pipeline.

## What's Running

### 1. **FastAPI Server** (Port 8000)
- **Web Interface**: http://localhost:8000
- **Chat API**: POST `/chat` - Send messages and get responses
- **Health Check**: GET `/health` - Server status
- **Legacy API**: GET `/predict` - Linear regression endpoint (backward compatible)

### 2. **Llama3 Model** (via Ollama)
- Base model: `llama3`
- Server: http://127.0.0.1:11434

---

## File Structure

```
/Users/azan/Desktop/AZAN/
├── src/
│   ├── train_llm.py          ✅ Training pipeline for fine-tuning
│   ├── inference.py           ✅ Inference module (fixed to use response.message.content)
│   ├── model.py              (Linear regression model)
│   └── train.py              (Linear regression training)
├── webui/
│   └── app.py                ✅ FastAPI with modern chat UI
├── data/
│   ├── chat_data.csv         ✅ Training data (10 Q&A pairs)
│   └── chat_data_training.jsonl  ✅ Prepared JSONL format
├── model/
│   ├── linear_model.npz      (Legacy)
│   ├── training_data.txt     (Text format training data)
│   ├── training_data.jsonl   (JSONL format training data)
│   ├── training_metadata.json (Metadata about training)
│   └── Modelfile            (Ollama Modelfile template)
├── .venv/                    (Python virtual environment)
├── requirements.txt          (Dependencies)
└── README.md
```

---

## How to Use

### 1. **Access the Chat Interface**
Open your browser and go to: **http://localhost:8000**

Features:
- ✅ Real-time chat with Llama3
- ✅ Beautiful gradient UI with smooth animations
- ✅ Loading indicators while waiting for responses
- ✅ Error handling with user-friendly messages
- ✅ Auto-scroll to latest messages
- ✅ Send messages with Enter key or button click

### 2. **Train the Model**
To prepare training data:
```bash
cd /Users/azan/Desktop/AZAN
source .venv/bin/activate
python -m src.train_llm
```

This:
- ✅ Loads data from `data/chat_data.csv`
- ✅ Preprocesses and deduplicates samples
- ✅ Saves in multiple formats (TXT, JSONL)
- ✅ Creates a Modelfile for Ollama fine-tuning

### 3. **Test Inference Directly**
```bash
source .venv/bin/activate
python -m src.inference
```

### 4. **Use the Chat API Programmatically**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'
```

Response:
```json
{
  "response": "Machine learning is a field of AI that enables systems to learn and improve from experience without explicit programming.",
  "model": "llama3"
}
```

---

## Key Fixes Applied

### ✅ Fixed `inference.py`
**Issue**: `AttributeError: 'ChatResponse' object has no attribute 'messages'`

**Solution**: Changed line 17 from:
```python
return response.messages[-1].content  # ❌ Wrong
```

To:
```python
return response.message.content  # ✅ Correct
```

The Ollama `ChatResponse` uses `message` (singular) not `messages` (plural).

---

## Web Interface Features

### Chat UI
- **Modern Design**: Gradient purple background with smooth animations
- **Message Bubbles**: User messages in gradient, bot responses in white
- **Typing Indicator**: Animated dots while waiting for response
- **Error Handling**: Displays user-friendly error messages
- **Responsive**: Works on desktop and mobile
- **Keyboard Support**: Send with Enter, Shift+Enter for new line

### JavaScript Interactivity
- Auto-clears empty state on first message
- Escapes HTML to prevent injection
- Smooth animations (slideIn, typing effects)
- Handles errors gracefully
- Disables send button during loading

---

## Customization Guide

### Add More Training Data
Edit `data/chat_data.csv`:
```csv
input,response
Your question here,Your answer here
```

Then run: `python -m src.train_llm`

### Change Model Parameters
Edit `src/inference.py` lines 67-75:
```python
response = chat(
    model_name,
    messages=[...],
    # Add parameters here:
    # options={"temperature": 0.7, "top_k": 40}
)
```

### Fine-tune with Ollama
Once data is prepared, use Ollama's create command:
```bash
ollama create llama3-custom -f model/Modelfile
ollama run llama3-custom
```

---

## Troubleshooting

### Server Not Starting
```bash
# Check if port 8000 is available
lsof -i :8000

# Kill any process using it
kill -9 <PID>
```

### Ollama Connection Issues
```bash
# Ensure Ollama is running
ollama serve

# Check Ollama is accessible
curl http://127.0.0.1:11434/api/tags
```

### Chat Returns Empty Response
- Check Ollama server is running
- Ensure `llama3` model is installed: `ollama pull llama3`
- Check logs in the server terminal

### Dependencies Missing
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Technology Stack

- **Backend**: FastAPI (Python web framework)
- **AI Model**: Llama3 via Ollama (local LLM)
- **Frontend**: HTML5 + Vanilla JavaScript (no external dependencies)
- **Training**: Python with CSV + JSON processing
- **Environment**: Python 3.9 virtual environment

---

## Next Steps

1. **✅ Chat Interface**: Open http://localhost:8000 and start chatting!
2. **📝 Add Training Data**: Edit `data/chat_data.csv` with your own Q&A pairs
3. **🎓 Fine-tune**: Run `python -m src.train_llm` to prepare data
4. **🚀 Deploy**: Use the FastAPI server in production with Uvicorn/Gunicorn
5. **🔧 Extend**: Add more endpoints, database integration, authentication, etc.

---

## System Information

- **OS**: macOS
- **Python**: 3.9 (in `.venv`)
- **Ollama**: Running on http://127.0.0.1:11434
- **FastAPI**: Running on http://0.0.0.0:8000
- **Status**: ✅ All systems operational

---

**Happy chatting with AZAN! 🤖💬**
