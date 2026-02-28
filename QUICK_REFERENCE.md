# AZAN Quick Reference Card

## Start AZAN
```bash
python start.sh
```
Server: `http://localhost:8000`

---

## Core Features

### 📝 Collect Feedback
```bash
# 5-star rating
curl -X POST http://localhost:8000/api/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{"interaction_id":"q1","rating":5,"comment":"Great!"}'

# Thumbs up
curl -X POST "http://localhost:8000/api/feedback/thumbs-up?interaction_id=q1"
```

### 🔍 Search Articles
```bash
# Semantic search
curl "http://localhost:8000/api/search/semantic?query=AI%20developments&limit=5"

# Index articles
curl -X POST http://localhost:8000/api/search/index-articles
```

### 📰 Get News
```bash
# Update feeds
curl -X POST http://localhost:8000/api/feeds/update

# Get articles
curl "http://localhost:8000/api/feeds/articles?category=technology&limit=5"
```

### 🧠 Monitor Learning
```bash
# RLHF status
curl http://localhost:8000/api/rlhf/status

# Trigger retraining
curl -X POST http://localhost:8000/api/rlhf/retrain
```

### 🚀 Fine-tune Model
```bash
# Start fine-tuning
curl -X POST http://localhost:8000/api/finetuning/start

# Check status
curl "http://localhost:8000/api/finetuning/status/finetune_20240223_160000"
```

### 📊 Get Statistics
```bash
# Feedback stats
curl http://localhost:8000/api/feedback/stats

# Feed summary
curl http://localhost:8000/api/feeds/summary

# Search stats
curl http://localhost:8000/api/search/stats
```

### 📡 Enhance Context
```bash
# Get enhanced context for query
curl -X POST "http://localhost:8000/api/context/enhance?query=What's%20in%20AI%20news?"
```

---

## Auto-running Systems

**Background Processes** (start automatically):
- RL Pipeline Training (continuous)
- RLHF Scheduler (checks hourly)
- Fine-tuning Scheduler (checks daily)
- RSS Feed Updater (updates every 15 min)
- Auto-training (follows configuration)

---

## Data Files

**Important locations**:
- `data/user_feedback.json` - Feedback records
- `data/feedback_rewards.json` - Reward adjustments
- `data/rlhf_history.json` - RLHF events
- `data/finetuning_history.json` - Fine-tuning jobs
- `data/live_articles.json` - RSS articles
- `data/embeddings.json` - Search index
- `data/rl_training_data.json` - Training pairs

---

## Health Check

```bash
# Test all systems
for endpoint in \
  "api/rl/status" \
  "api/feedback/stats" \
  "api/rlhf/status" \
  "api/search/stats" \
  "api/feeds/summary" \
  "api/finetuning/stats" \
  "api/context/summary"; do
  echo "=== $endpoint ==="
  curl -s "http://localhost:8000/$endpoint" | jq .
done
```

---

## Configuration

**File: `src/user_feedback.py`**
```python
# No config needed - works out of box
```

**File: `src/rlhf_pipeline.py`**
```python
# Triggers when:
# - total_ratings >= 10
# - helpful_percentage >= 50%
# Checks every: 3600 seconds (1 hour)
```

**File: `src/rss_feed_integrator.py`**
```python
# Updates every: 900 seconds (15 minutes)
# Sources: 40+ across 8 categories
# Max per feed: 5 articles
```

**File: `src/fine_tuning.py`**
```python
# Checks every: 86400 seconds (1 day)
# Default epochs: 3
# Default batch: 8
```

---

## Troubleshooting

**Semantic search not working?**
```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Restart if needed
brew services restart ollama
ollama pull nomic-embed-text
```

**RLHF not triggering?**
```python
from src.user_feedback import get_feedback
feedback = get_feedback()
stats = feedback.get_feedback_stats()
print(f"Ratings: {stats['total_ratings']}")  # Need >= 10
print(f"Helpful %: {stats['helpful_percentage']}")  # Need >= 50
```

**PostgreSQL connection issues?**
```bash
# Check if running
psql -U postgres -c "SELECT version();"

# Start if needed
brew services start postgresql
```

---

## Python Usage

```python
# Feedback
from src.user_feedback import get_feedback
feedback = get_feedback()
feedback.submit_rating("q1", rating=5)
stats = feedback.get_feedback_stats()

# Search
from src.semantic_search import get_semantic_search
search = get_semantic_search()
results = search.search("machine learning", limit=5)

# RLHF
from src.rlhf_pipeline import get_rlhf
rlhf = get_rlhf()
status = rlhf.get_rlhf_status()
if status['ready_for_retraining']:
    rlhf.apply_feedback_to_training()

# Fine-tuning
from src.fine_tuning import get_finetuning
finetune = get_finetuning()
stats = finetune.get_finetuning_stats()

# Feeds
from src.rss_feed_integrator import get_feed_integrator
integrator = get_feed_integrator()
articles = integrator.get_recent_articles(category='technology', limit=5)

# Context
from src.feed_context_integration import get_context_manager
context_mgr = get_context_manager()
context = context_mgr.prepare_inference_context("What's happening in AI?")
```

---

## Documentation

- `INTEGRATION_GUIDE.md` - Complete setup guide
- `API_REFERENCE.md` - All endpoints documented
- `FINAL_STATUS.md` - Implementation summary
- Inline code comments - In each module

---

## System Requirements

- Python 3.9+
- Ollama (for embeddings)
- PostgreSQL (optional, JSON fallback available)
- 2GB RAM minimum
- Internet for RSS feeds

---

## Performance

- Chat response: <1 second
- Feedback submission: <100ms
- Semantic search: 200-500ms
- RSS update: ~5 seconds
- Context enhancement: <300ms
- RLHF decision: <100ms

---

## Support

**Check Status**:
```bash
curl http://localhost:8000/api/rl/status
```

**View Logs**:
```bash
tail -f server.log
```

**Debug**:
- Check `data/` directory for JSON files
- Review inline logging output
- Monitor individual endpoints

---

**AZAN is Ready to Use** ✅

Start the server and begin interacting!
