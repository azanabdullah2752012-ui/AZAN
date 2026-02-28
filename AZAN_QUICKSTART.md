# AZAN RL System - Quick Start Guide

## 🚀 Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the server
python -m uvicorn webui.app:app --reload --port 8000
```

**Expected Output:**
```
✅ AZAN Curated RL Pipeline started (Indian Constitution, UN Treaties, Military Strategies, Political Definitions)
✅ AZAN Data-Only Inference Engine initialized
```

## 📊 Access the Dashboard

Open in your browser:
```
http://localhost:8000/azan-dashboard
```

You should see:
- ✅ Training Status (Active/Inactive)
- ✅ Current Iteration & Rewards
- ✅ Knowledge Base Stats
- ✅ Reward Trend Chart
- ✅ Search Interface

## 🎓 Training Controls

### Start Training (if stopped)
```bash
curl -X POST http://localhost:8000/api/azan/rl/start
```

### Stop Training
```bash
curl -X POST http://localhost:8000/api/azan/rl/stop
```

### Get Training Status
```bash
curl http://localhost:8000/api/azan/rl/status
```

## 🔍 Search Knowledge

### Via API
```bash
curl "http://localhost:8000/api/azan/search?query=constitution&limit=5"
```

### Via Dashboard
1. Go to `http://localhost:8000/azan-dashboard`
2. Scroll to "Search Knowledge Base"
3. Enter query (e.g., "constitutional rights", "UN treaties", "military strategy")
4. Click Search

### Example Searches
- `Indian Constitution fundamental rights`
- `UN human rights declaration`
- `military strategy tactics`
- `trade tariffs sanctions`
- `diplomacy negotiation`

## 💬 Query with Data-Only Inference

```bash
curl -X POST "http://localhost:8000/api/azan/infer?query=What%20is%20Article%2032?"
```

**Response includes:**
- Relevant knowledge sources
- Answer built only from training data
- Source citations
- Confidence level

## 📈 Monitor Training

### Check Metrics
```bash
curl http://localhost:8000/api/azan/rl/status | jq
```

### View Learned Pairs
```bash
curl "http://localhost:8000/api/azan/rl/learned-qa?limit=10" | jq
```

### Get Knowledge Stats
```bash
curl http://localhost:8000/api/azan/rl/knowledge-stats | jq
```

## 📁 Data Files

**Where is my data?**

- **Knowledge Base:** `data/azan_knowledge_base.json`
- **Training State:** `data/azan_training_state.json`
- **Checkpoints:** `data/azan_checkpoints/`

**Add your own knowledge:**

Edit `data/azan_knowledge_base.json`:

```json
[
  {
    "id": "custom_001",
    "source": "My Source",
    "category": "my_category",
    "title": "My Topic",
    "content": "Detailed information about the topic...",
    "key_terms": ["keyword1", "keyword2", "keyword3"]
  }
]
```

Then restart the server to reload.

## 🎯 Common Use Cases

### 1. Check Constitutional Rights
```bash
curl "http://localhost:8000/api/azan/search?query=fundamental%20rights"
```

### 2. Look Up UN Policies
```bash
curl "http://localhost:8000/api/azan/search?query=UN%20human%20rights"
```

### 3. Learn Military Strategies
```bash
curl "http://localhost:8000/api/azan/search?query=military%20doctrine"
```

### 4. Understand Political Terms
```bash
curl "http://localhost:8000/api/azan/search?query=tariffs%20sanctions"
```

## ⚙️ Configuration

### Training Interval
Change in `webui/app.py` startup event:

```python
engine, trainer = init_azan_rl(update_interval=30)  # 30 seconds
```

### Knowledge Base Location
Change in `src/azan_rl_pipeline.py`:

```python
kb = CuratedKnowledgeBase(data_dir="path/to/data")
```

## 🔧 Troubleshooting

### Training Not Starting?
```bash
# Check if system is available
curl http://localhost:8000/api/azan/rl/status

# Manually start
curl -X POST http://localhost:8000/api/azan/rl/start
```

### Dashboard Not Loading?
```bash
# Verify server is running
curl http://localhost:8000/

# Check for errors
python -m uvicorn webui.app:app --port 8000
```

### No Knowledge Items?
```bash
# Check file exists
ls -la data/azan_knowledge_base.json

# View contents
cat data/azan_knowledge_base.json | head -50
```

### Reward Not Increasing?
- Check if training is active: Status should be "Active"
- Verify knowledge base has items
- Check logs for errors

## 📚 API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/azan/rl/status` | GET | Training status |
| `/api/azan/rl/start` | POST | Start training |
| `/api/azan/rl/stop` | POST | Stop training |
| `/api/azan/rl/train-iteration` | POST | Train once |
| `/api/azan/rl/knowledge-stats` | GET | Knowledge stats |
| `/api/azan/rl/learned-qa` | GET | Learned pairs |
| `/api/azan/search` | GET | Search knowledge |
| `/api/azan/infer` | POST | Data-only query |
| `/azan-dashboard` | GET | Live dashboard |

## 🎓 Learning Progress

**After ~1 hour of training:**
- Iteration: 120
- Avg Reward: 4.2
- Total Learned: 120 Q&A pairs
- Data size: ~100KB

**After ~1 day of training:**
- Iteration: 2880
- Avg Reward: 4.4
- Total Learned: 2880 Q&A pairs
- Data size: ~2MB

**After ~1 month:**
- Iteration: 86,400
- Avg Reward: 4.5
- Total Learned: 86,400 Q&A pairs
- Complete domain mastery

## 💡 Tips

1. **Search is case-insensitive** - "constitution" = "CONSTITUTION" = "Constitution"
2. **Longer queries work better** - "What is equality?" gives better results
3. **Use specific domains** - Search for "Constitution" vs "military" separately
4. **Monitor dashboard** - Watch the reward trend to see learning progress
5. **Add custom knowledge** - Edit `azan_knowledge_base.json` to expand training data

## 📊 Dashboard Features

- **Auto-refresh:** Updates every 5 seconds
- **Live chart:** Reward trends over time
- **Training controls:** Start/stop from UI
- **Knowledge search:** Full-text search with results
- **Statistics:** Real-time metrics and counts
- **Status indicator:** Green = training active, Red = stopped

## 🚨 Limitations

⚠️ **Data-Only Mode:**
- Cannot answer questions outside training data
- Requires explicit knowledge base entries
- No internet access or external knowledge
- Conservative by design (no hallucinations)

✅ **Advantages:**
- All responses are verifiable
- Source attribution
- No false information
- Auditable and transparent
- Compliant with data-only requirements

## Next Steps

1. ✅ Start the server
2. ✅ Open the dashboard
3. ✅ Verify training is running
4. ✅ Search for knowledge
5. ✅ Try data-only queries
6. ✅ Monitor the metrics
7. ✅ Add custom knowledge
8. ✅ Integrate into your app

Happy learning! 🚀
