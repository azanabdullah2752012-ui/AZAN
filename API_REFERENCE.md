# AZAN Enhanced API Reference

## Quick Index

### User Feedback & RLHF
- `POST /api/feedback/submit` - Submit detailed rating
- `POST /api/feedback/thumbs-up` - Quick 5-star rating
- `POST /api/feedback/thumbs-down` - Quick 1-star rating
- `GET /api/feedback/stats` - Feedback statistics
- `GET /api/rlhf/status` - RLHF system status
- `POST /api/rlhf/retrain` - Trigger retraining

### Semantic Search
- `GET /api/search/semantic` - Vector-based search
- `POST /api/search/index-articles` - Index for search
- `GET /api/search/stats` - Index statistics

### RSS Feeds
- `POST /api/feeds/update` - Manually update feeds
- `GET /api/feeds/articles` - Get recent articles
- `GET /api/feeds/summary` - Feed statistics

### Context Enhancement
- `GET /api/context/summary` - Available context sources
- `POST /api/context/enhance` - Get enhanced context

### Fine-tuning
- `POST /api/finetuning/start` - Start fine-tuning
- `GET /api/finetuning/status/{job_id}` - Job status
- `GET /api/finetuning/checkpoints` - Recent checkpoints
- `GET /api/finetuning/stats` - Fine-tuning statistics

---

## Detailed Endpoints

### Feedback: Submit Rating
```
POST /api/feedback/submit

Request:
{
  "interaction_id": "q1_2024",
  "rating": 5,
  "comment": "Excellent response!",
  "user_id": "user123"
}

Response:
{
  "status": "success",
  "feedback_id": "q1_2024_1708644000",
  "rating": 5
}
```

### Feedback: Thumbs Up/Down
```
POST /api/feedback/thumbs-up?interaction_id=q1_2024
POST /api/feedback/thumbs-down?interaction_id=q1_2024

Response:
{
  "status": "success",
  "rating": 5  # or 1 for thumbs down
}
```

### Feedback: Statistics
```
GET /api/feedback/stats

Response:
{
  "total_ratings": 45,
  "average_rating": 4.2,
  "helpful_percentage": 78.5,
  "by_rating": {
    "1": 3,
    "2": 4,
    "3": 7,
    "4": 15,
    "5": 16
  },
  "recommendation": "good"
}
```

### RLHF: Status
```
GET /api/rlhf/status

Response:
{
  "status": "ready",
  "total_ratings": 45,
  "average_rating": 4.2,
  "helpful_percentage": 78.5,
  "ready_for_retraining": true,
  "high_rated_count": 31,
  "low_rated_count": 7,
  "improvement_metrics": {
    "total_retrainings": 3,
    "last_retraining": "2024-02-23T10:30:00",
    "improvement_trend": "improving",
    "user_satisfaction_trend": [75, 76, 78.5],
    "average_rating_trend": [3.8, 4.0, 4.2]
  }
}
```

### RLHF: Trigger Retraining
```
POST /api/rlhf/retrain

Response:
{
  "status": "success",
  "event_id": "rlhf_1708644000",
  "training_data": {
    "positive_examples": 31,
    "negative_examples": 7,
    "total_examples": 38,
    "positive_ratio": 0.82
  },
  "feedback_stats": {
    "total_ratings": 45,
    "average_rating": 4.2,
    "helpful_percentage": 78.5
  }
}
```

### Semantic Search: Query
```
GET /api/search/semantic?query=latest%20AI%20developments&limit=5&category=technology

Response:
{
  "query": "latest AI developments",
  "results": [
    {
      "id": "article_123",
      "headline": "OpenAI Releases GPT-5",
      "source": "TechCrunch",
      "category": "technology",
      "similarity": 0.95,
      "timestamp": "2024-02-23T15:30:00"
    },
    {
      "id": "article_124",
      "headline": "Meta AI Advances in Vision",
      "source": "The Verge",
      "category": "technology",
      "similarity": 0.92,
      "timestamp": "2024-02-23T14:00:00"
    }
  ],
  "count": 2
}
```

### Semantic Search: Index Articles
```
POST /api/search/index-articles

Response:
{
  "indexed": 125,
  "failed": 3,
  "total": 128
}
```

### Semantic Search: Statistics
```
GET /api/search/stats

Response:
{
  "total_documents": 128,
  "by_category": {
    "technology": 28,
    "business": 22,
    "science": 18,
    "politics": 15,
    "world": 20,
    "sports": 12,
    "entertainment": 10,
    "national": 3
  }
}
```

### RSS Feeds: Update
```
POST /api/feeds/update

Response:
{
  "status": "success",
  "results": {
    "business": 2,
    "technology": 3,
    "science": 1,
    "politics": 0,
    "world": 2,
    "sports": 1,
    "entertainment": 0,
    "national": 1
  },
  "summary": {
    "total_articles": 152,
    "by_category": {...},
    "last_updated": "2024-02-23T16:00:00"
  }
}
```

### RSS Feeds: Get Articles
```
GET /api/feeds/articles?category=technology&limit=5

Response:
{
  "articles": [
    {
      "id": "feed_456",
      "headline": "New GPU Released",
      "body": "Summary...",
      "source": "TechCrunch",
      "category": "technology",
      "published": "2024-02-23T15:00:00",
      "link": "https://techcrunch.com/...",
      "timestamp": "2024-02-23T16:00:00"
    }
  ],
  "count": 5,
  "category": "technology"
}
```

### RSS Feeds: Summary
```
GET /api/feeds/summary

Response:
{
  "total_articles": 152,
  "by_category": {
    "technology": 28,
    "business": 22,
    "science": 18,
    "politics": 15,
    "world": 20,
    "sports": 12,
    "entertainment": 10,
    "national": 7
  },
  "last_updated": "2024-02-23T16:00:00"
}
```

### Context: Summary
```
GET /api/context/summary

Response:
{
  "articles_available": 152,
  "by_category": {...},
  "last_updated": "2024-02-23T16:00:00",
  "context_sources": ["knowledge_base", "rss_feeds"]
}
```

### Context: Enhance
```
POST /api/context/enhance?query=What's%20happening%20in%20AI%20today?

Response:
{
  "query": "What's happening in AI today?",
  "timestamp": "2024-02-23T16:05:00",
  "sources": ["knowledge_base", "rss_feeds"],
  "knowledge_base": {...},
  "news_context": "🔔 Recent News Context:\n=======================\n1. [TechCrunch] New GPU Released\n   Relevance: 92%\n2. [The Verge] Meta AI Advances\n   Relevance: 89%\n=======================\n",
  "has_news": true,
  "context_quality": "enhanced"
}
```

### Fine-tuning: Start
```
POST /api/finetuning/start

Response:
{
  "status": "started",
  "job_id": "finetune_20240223_160000",
  "model": "llama3"
}
```

### Fine-tuning: Status
```
GET /api/finetuning/status/finetune_20240223_160000

Response:
{
  "id": "finetune_20240223_160000",
  "model": "llama3",
  "training_file": "data/finetune_training.jsonl",
  "epochs": 3,
  "batch_size": 8,
  "learning_rate": 1e-05,
  "started_at": "2024-02-23T16:00:00",
  "status": "training_epoch_2",
  "progress": 66,
  "current_epoch": 2
}
```

### Fine-tuning: Checkpoints
```
GET /api/finetuning/checkpoints

Response:
{
  "checkpoints": [
    {
      "id": "finetune_20240223_120000",
      "status": "completed",
      "completed_at": "2024-02-23T12:30:00",
      "checkpoint": "/data/finetuned_models/finetune_20240223_120000_model",
      "metrics": {
        "final_loss": 0.15,
        "validation_accuracy": 0.92
      }
    }
  ],
  "count": 1
}
```

### Fine-tuning: Statistics
```
GET /api/finetuning/stats

Response:
{
  "total_jobs": 15,
  "completed": 14,
  "running": 1,
  "success_rate": 93.3,
  "last_checkpoint": [
    {
      "id": "finetune_20240223_120000",
      "status": "completed",
      "metrics": {
        "final_loss": 0.15,
        "validation_accuracy": 0.92
      }
    }
  ]
}
```

---

## Usage Examples

### Example 1: Collect feedback on chat response
```bash
# Chat with AZAN
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning?"}'

# Response returns with interaction_id: "q1_2024"

# User gives feedback
curl -X POST http://localhost:8000/api/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_id": "q1_2024",
    "rating": 5,
    "comment": "Very clear explanation!"
  }'
```

### Example 2: Get enhanced context for news-related query
```bash
curl -X POST "http://localhost:8000/api/context/enhance?query=What's%20happening%20in%20tech%20today%3F"

# Returns context with recent tech news articles injected
```

### Example 3: Monitor RLHF progress
```bash
curl http://localhost:8000/api/rlhf/status

# If ready_for_retraining is true, trigger:
curl -X POST http://localhost:8000/api/rlhf/retrain
```

### Example 4: Search and index articles
```bash
# Manually update feeds
curl -X POST http://localhost:8000/api/feeds/update

# Index new articles for search
curl -X POST http://localhost:8000/api/search/index-articles

# Search across indexed content
curl "http://localhost:8000/api/search/semantic?query=machine%20learning&limit=5"
```

---

## Error Handling

All endpoints return standard error responses:

```json
{
  "error": "Description of what went wrong",
  "status": "error"
}
```

Common status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Not found (resource doesn't exist)
- `500` - Server error (check logs)

---

## Rate Limits & Performance

**Recommended usage**:
- Feedback submissions: No limit (per request)
- Semantic search: Limit to 10 queries/minute
- Feed updates: 1 per 5 minutes (automatic every 15 minutes)
- Fine-tuning: 1 job at a time
- RLHF retraining: Automatic (hourly checks)

**Performance targets**:
- Feedback submission: <100ms
- Semantic search: <500ms
- Feed update: <10s
- Fine-tuning epoch: 2-5 minutes

---

## Real-time Monitoring

Use this endpoint to monitor all systems:

```bash
# Shell script for monitoring
#!/bin/bash
echo "=== AZAN System Status ==="
echo "Feedback: $(curl -s http://localhost:8000/api/feedback/stats | jq '.total_ratings')"
echo "RLHF Ready: $(curl -s http://localhost:8000/api/rlhf/status | jq '.ready_for_retraining')"
echo "Articles: $(curl -s http://localhost:8000/api/feeds/summary | jq '.total_articles')"
echo "Search Index: $(curl -s http://localhost:8000/api/search/stats | jq '.total_documents')"
echo "Fine-tuning: $(curl -s http://localhost:8000/api/finetuning/stats | jq '.running')"
```

---

## Integration with Frontend

Example HTML for feedback buttons:

```html
<div class="response-actions">
  <button onclick="submitFeedback('q1', 5)">👍 Thumbs Up</button>
  <button onclick="submitFeedback('q1', 1)">👎 Thumbs Down</button>
</div>

<script>
function submitFeedback(id, rating) {
  fetch('/api/feedback/submit', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      interaction_id: id,
      rating: rating
    })
  }).then(r => r.json()).then(data => {
    console.log('Feedback recorded:', data);
  });
}
</script>
```

---

**Last Updated**: February 23, 2026
**Version**: 1.0
