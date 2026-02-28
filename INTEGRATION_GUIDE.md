# AZAN Advanced Enhancement Integration Guide

## 🚀 Overview

This document covers the high-impact enhancements integrated into AZAN:

1. **User Feedback System** - Collect ratings on responses
2. **Semantic Search** - Vector-based search across knowledge
3. **PostgreSQL Database** - Scalable data persistence
4. **RLHF Pipeline** - Reinforcement Learning from Human Feedback
5. **Fine-tuning Module** - Domain-specific model optimization
6. **RSS Feed Integration** - Real-time news context injection

## 📦 Module Descriptions

### 1. User Feedback System (`src/user_feedback.py`)

**Purpose**: Collect user ratings and feedback to improve model responses.

**Features**:
- 1-5 star ratings for responses
- User comments and identification
- Automatic reward adjustment calculation
- High/low rated response tracking
- RLHF training data preparation

**API Endpoints**:
```
POST   /api/feedback/submit         - Submit detailed rating
POST   /api/feedback/thumbs-up      - Quick 5-star rating
POST   /api/feedback/thumbs-down    - Quick 1-star rating
GET    /api/feedback/stats          - Get feedback statistics
```

**Usage**:
```python
from src.user_feedback import get_feedback

feedback = get_feedback()

# Submit rating
feedback.submit_rating(
    interaction_id="q1_2024",
    rating=5,
    comment="Excellent response!",
    user_id="user123"
)

# Get stats
stats = feedback.get_feedback_stats()
print(f"Average rating: {stats['average_rating']}")
```

---

### 2. Semantic Search (`src/semantic_search.py`)

**Purpose**: Find relevant information using embeddings instead of keywords.

**Features**:
- Ollama embeddings (nomic-embed-text model)
- Vector similarity search
- Article and knowledge base indexing
- Category-based filtering
- Embedding caching

**API Endpoints**:
```
GET    /api/search/semantic         - Search across all content
POST   /api/search/index-articles   - Index RSS articles
GET    /api/search/stats            - Get indexing statistics
```

**Usage**:
```python
from src.semantic_search import get_semantic_search

search = get_semantic_search()

# Index articles
search.index_articles(articles_dict)

# Search
results = search.search("latest AI developments", limit=5)
for result in results:
    print(f"{result['headline']} (relevance: {result['similarity']})")
```

---

### 3. PostgreSQL Database (`src/database.py`)

**Purpose**: Scalable, persistent storage for all system data.

**Features**:
- Connection pooling with configurable limits
- Tables for: training pairs, articles, feedback, checkpoints, sessions, embeddings
- CRUD operations for all entities
- Automatic table creation
- Transaction support

**Configuration**:
```python
from src.database import initialize_database

db = initialize_database(
    host="localhost",
    port=5432,
    database="azan_db",
    user="azan",
    password="secure_password"
)
```

**Tables**:
- `training_pairs` - Q&A pairs with rewards
- `articles` - News articles with embeddings
- `user_feedback` - User ratings and comments
- `model_checkpoints` - Saved model versions
- `user_sessions` - User interaction history
- `embeddings` - Vector embeddings for search

---

### 4. RLHF Pipeline (`src/rlhf_pipeline.py`)

**Purpose**: Improve model through reinforcement learning from human feedback.

**Features**:
- Collects high-rated responses for positive examples
- Identifies low-rated responses for targeted improvement
- Automatic retraining trigger when thresholds met
- Improvement metrics and trend analysis
- Scheduled automatic retraining

**API Endpoints**:
```
GET    /api/rlhf/status            - Get RLHF system status
POST   /api/rlhf/retrain           - Trigger retraining immediately
```

**Usage**:
```python
from src.rlhf_pipeline import get_rlhf

rlhf = get_rlhf()

# Check status
status = rlhf.get_rlhf_status()
print(f"Ready for retraining: {status['ready_for_retraining']}")

# Trigger retraining
result = rlhf.apply_feedback_to_training()
```

**Automatic Scheduling**:
The RLHF scheduler runs in background (checks every hour) and automatically triggers retraining when:
- Total ratings >= 10
- Helpful percentage >= 50%

---

### 5. Fine-tuning Module (`src/fine_tuning.py`)

**Purpose**: Continuously fine-tune Llama3 on domain-specific knowledge.

**Features**:
- Training corpus preparation from Q&A pairs
- Validation set creation
- Fine-tuning job management
- Checkpoint tracking
- Automatic scheduling

**API Endpoints**:
```
POST   /api/finetuning/start        - Start fine-tuning job
GET    /api/finetuning/status/{id}  - Get job status
GET    /api/finetuning/checkpoints  - Get recent checkpoints
GET    /api/finetuning/stats        - Get fine-tuning statistics
```

**Usage**:
```python
from src.fine_tuning import get_finetuning

finetune = get_finetuning()

# Start fine-tuning
job = finetune.start_finetuning(
    training_file="data/finetune_training.jsonl",
    epochs=3,
    batch_size=8,
    learning_rate=1e-5
)

# Check status
status = finetune.get_job_status(job["id"])
print(f"Progress: {status['progress']}%")
```

---

### 6. RSS Feed Integration (`src/rss_feed_integrator.py`)

**Purpose**: Pull real-time news and inject into context.

**Features**:
- 40+ RSS sources across 8 categories
- Background automatic updates (15 minutes)
- Article caching to prevent duplicates
- Category-based organization
- Feed error handling

**API Endpoints**:
```
POST   /api/feeds/update            - Manually trigger feed update
GET    /api/feeds/articles          - Get recent articles
GET    /api/feeds/summary           - Get feed summary
```

**Categories**:
- Business, Technology, Science, Politics, World, Sports, Entertainment, National

---

### 7. Feed Context Integration (`src/feed_context_integration.py`)

**Purpose**: Automatically inject relevant news into inference context.

**Features**:
- Intelligent query analysis to determine news relevance
- Semantic search for matching articles
- Context building with article summaries
- Fallback to recent articles
- Context quality tracking

**API Endpoints**:
```
GET    /api/context/summary         - Get context sources
POST   /api/context/enhance         - Get enhanced context for query
```

**Usage**:
```python
from src.feed_context_integration import get_context_manager

context_mgr = get_context_manager()

# Get enhanced context
context = context_mgr.prepare_inference_context(
    query="What happened in tech today?"
)
print(context['news_context'])  # Includes relevant articles
```

---

## 🔗 Integration Architecture

```
User Input (Chat)
     ↓
Feed Context Integration
├─→ Checks if query needs news
├─→ Semantic search for articles
└─→ Builds enhanced context
     ↓
Enhanced Inference
├─→ Uses base knowledge
├─→ Adds news context
└─→ Generates response
     ↓
User Feedback
├─→ Thumbs up/down or rating
├─→ Stores in database
└─→ Triggers RLHF when ready
     ↓
RLHF Pipeline
├─→ Collects high-rated responses
├─→ Identifies weak areas
└─→ Prepares retraining data
     ↓
Fine-tuning
└─→ Retrains model on improved data
```

## 🚀 Getting Started

### Installation

**Required Python packages**:
```bash
pip install feedparser psycopg2-binary numpy requests
```

**Optional but recommended**:
```bash
# For PostgreSQL support (if using database)
brew install postgresql  # macOS
sudo apt-get install postgresql  # Linux

# Start PostgreSQL
brew services start postgresql  # macOS
```

### Configuration

**Ollama Setup**:
```bash
# Install embedding model (required for semantic search)
ollama pull nomic-embed-text
```

**Database Setup** (optional):
```bash
# Create database
createdb azan_db

# Create user
createuser -P azan  # Enter password when prompted
```

### Startup

All systems initialize automatically on server startup:

```bash
python start.sh
```

Or manually:
```bash
cd /Users/azan/Desktop/AZAN
python -m uvicorn webui.app:app --host 0.0.0.0 --port 8000
```

**Initialization output**:
```
✅ RL Pipeline started
✅ RL Inference engine initialized
✅ User Feedback system initialized
✅ Semantic Search engine initialized
✅ RSS Feed integrator and updater initialized
✅ RLHF pipeline and scheduler initialized
✅ Fine-tuning system initialized
✅ Feed context integration initialized
✅ Auto-training scheduler started
```

## 📊 Monitoring

### Dashboard Updates

**New metrics available**:
- User feedback statistics (average rating, helpful percentage)
- RLHF readiness and improvement trends
- RSS feed coverage (articles by category)
- Semantic search index status
- Fine-tuning job progress
- Context enhancement metrics

### API Health Check

Test all systems:
```bash
# Core systems
curl http://localhost:8000/api/rl/status
curl http://localhost:8000/api/feedback/stats
curl http://localhost:8000/api/rlhf/status
curl http://localhost:8000/api/finetuning/stats
curl http://localhost:8000/api/feeds/summary
curl http://localhost:8000/api/search/stats
curl http://localhost:8000/api/context/summary
```

## 🔄 Data Flow Examples

### Example 1: User gives feedback
```
1. User rates response: rating=5
   POST /api/feedback/submit
   
2. System stores feedback
   UserFeedback.submit_rating()
   
3. Reward adjustment calculated
   feedback_system.reward_adjustments[id] = {value: 1.0}
   
4. RLHF checks readiness
   rlhf.ready_for_retraining() → True after 10 ratings
   
5. Auto retraining triggered
   rlhf.apply_feedback_to_training()
   
6. Model improved with high-rated examples
```

### Example 2: News-aware response
```
1. User asks: "What's happening in AI?"
   
2. Enhanced context created
   FeedContextInjector.should_include_news_context() → True
   
3. Semantic search for articles
   SemanticSearchEngine.search("AI developments")
   
4. Articles ranked by relevance
   Results: [{headline, similarity: 0.95}]
   
5. Context injected into inference
   System prompt includes: "Recent news: [articles]"
   
6. Response includes current information
```

### Example 3: Fine-tuning cycle
```
1. 50+ new Q&A pairs accumulated
   AutomatedFineTuningScheduler detects threshold
   
2. Training corpus prepared
   FineTuningData.prepare_training_corpus()
   Creates: data/finetune_training.jsonl
   
3. Fine-tuning job started
   FineTuneManager.start_finetuning()
   
4. Training runs for 3 epochs
   Progress: 33% → 66% → 100%
   
5. Checkpoint saved
   Checkpoint path: data/finetuned_models/finetune_20240223_*/
   
6. Metrics recorded
   Loss: 0.15, Validation accuracy: 0.92
```

## 📈 Performance Expectations

**Semantic Search**:
- Index speed: ~100 docs/second
- Query latency: 200-500ms for embedding + search

**RLHF Retraining**:
- Trigger time: ~5 minutes after feedback threshold met
- Data preparation: <1 second per 100 pairs

**Fine-tuning**:
- Epoch duration: ~2-5 minutes (depends on corpus size)
- Total per cycle: ~10-15 minutes for 3 epochs

**RSS Updates**:
- Feed fetch: ~5 seconds for all 40 sources
- Article storage: <100ms per article

## 🐛 Troubleshooting

### Semantic Search not working
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, restart Ollama and pull model
ollama serve
ollama pull nomic-embed-text
```

### PostgreSQL connection fails
```bash
# Check if PostgreSQL is running
psql -U postgres -c "SELECT version();"

# If not, start it
brew services start postgresql

# Check credentials
psql -U azan -d azan_db -c "SELECT COUNT(*) FROM training_pairs;"
```

### RSS feeds not updating
```python
# Check feed status
from src.rss_feed_integrator import get_feed_updater
updater = get_feed_updater()
# If not updating, check error logs for network issues
```

### RLHF not triggering
```python
# Check requirements
from src.rlhf_pipeline import get_rlhf
rlhf = get_rlhf()
status = rlhf.get_rlhf_status()
print(f"Total ratings: {status['total_ratings']}")  # Need >= 10
print(f"Helpful %: {status['helpful_percentage']}")  # Need >= 50%
```

## 📚 Additional Resources

- **Ollama Embeddings**: https://github.com/ollama/ollama#embedding-models
- **PostgreSQL**: https://www.postgresql.org/docs/
- **RLHF**: https://huggingface.co/blog/rlhf
- **Semantic Search**: https://www.sbert.net/

## 🎯 Next Steps

Potential enhancements:
1. **Vector Database** (Pinecone/Weaviate) - Replace JSON embeddings
2. **User Authentication** - Multi-user support with sessions
3. **Advanced Analytics** - Elasticsearch for logs and metrics
4. **Automated Testing** - Unit tests for all modules
5. **Performance Caching** - Redis for frequent queries
6. **Multi-language Support** - Expand beyond English
7. **Custom Models** - Fine-tune on specific domains
8. **Monitoring Dashboards** - Prometheus + Grafana integration

---

**Last Updated**: February 23, 2026
**Version**: 1.0
