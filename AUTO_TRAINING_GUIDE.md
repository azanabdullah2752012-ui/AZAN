# Auto-Training on Political Topics - Complete Guide

## Overview

Your AI system is now equipped with **automatic training on world political matters**. The system:

- ✅ Fetches and manages a comprehensive database of political topics
- ✅ Automatically trains the model on current political matters
- ✅ Runs on a configurable schedule (default: every 30 minutes)
- ✅ Tracks training progress and statistics
- ✅ Supports manual triggers for immediate training
- ✅ Uses your existing RLHF training dashboard

## Key Features

### 1. **Automatic Scheduled Training**
- Runs in the background on a configurable interval
- Default: Every 30 minutes
- Trains 5 examples per session (configurable)
- Quick mode enabled for speed
- Focuses on major political topics

### 2. **Coverage of Political Topics**
The system trains on these major world political areas:

1. **Global Trade Relationships**
   - Trade tensions between powers
   - Trade agreements and impacts
   - Supply chain dynamics
   - Economic interdependence

2. **Climate Policy and International Action**
   - International climate agreements
   - Carbon neutrality implementations
   - Renewable energy politics
   - Environmental regulations

3. **Democratic Institutions and Elections**
   - Electoral trends worldwide
   - Election security
   - Voting systems
   - Democratic participation

4. **International Security and Conflicts**
   - Geopolitical tensions
   - Conflict resolution mechanisms
   - Military alliances
   - Cyber security threats

5. **Economic Development and Inequality**
   - Development strategies
   - Inequality reduction policies
   - Labor standards
   - Automation and employment

6. **Migration and Border Policy**
   - Immigration policies
   - Refugee management
   - Labor migration
   - Border relations

7. **Technology and Governance**
   - Tech regulation
   - AI and governance
   - Data privacy
   - Tech innovation in politics

8. **Healthcare and Pandemics**
   - Pandemic preparedness
   - Vaccine distribution
   - Healthcare policy
   - Global health initiatives

9. **Energy Independence and Resources**
   - Energy independence strategies
   - Resource geopolitics
   - Renewable transitions
   - Resource conflicts

10. **Human Rights and Social Justice**
    - Human rights concerns
    - Systemic inequality
    - Activism and movements
    - Rights protection mechanisms

## API Endpoints

### Start Auto-Training
```bash
POST /auto-training/start
```
Response:
```json
{
  "status": "started",
  "message": "Auto-training scheduler has been started",
  "config": { ... }
}
```

### Stop Auto-Training
```bash
POST /auto-training/stop
```
Response:
```json
{
  "status": "stopped",
  "message": "Auto-training scheduler has been stopped"
}
```

### Get Auto-Training Status
```bash
GET /auto-training/status
```
Response:
```json
{
  "is_running": true,
  "enabled": true,
  "total_sessions": 5,
  "last_training": "2026-02-22T14:30:45.123456",
  "next_training": "2026-02-22T15:00:45.123456",
  "schedule_interval_minutes": 30,
  "examples_per_session": 5,
  "quick_mode": true,
  "focused_topics": ["Global Trade Relationships", "Climate Policy..."]
}
```

### Get Configuration
```bash
GET /auto-training/config
```
Response:
```json
{
  "enabled": true,
  "schedule_interval_minutes": 30,
  "examples_per_session": 5,
  "quick_mode": true,
  "topics_to_focus": ["Global Trade Relationships", "Climate Policy..."]
}
```

### Update Configuration
```bash
POST /auto-training/config
Content-Type: application/json

{
  "schedule_interval_minutes": 60,
  "examples_per_session": 10,
  "quick_mode": false
}
```

### Trigger Manual Training
```bash
POST /auto-training/trigger?num_examples=5
```
Response:
```json
{
  "success": true,
  "examples_trained": 5,
  "avg_reward": 0.752,
  "duration_seconds": 15.3
}
```

### Get Available Topics
```bash
GET /auto-training/topics
```
Response:
```json
{
  "topics": {
    "Global Trade Relationships": [
      {
        "question": "What are the current trade tensions between major world powers?",
        "ideal_answer": "Trade relationships are complex..."
      },
      ...
    ],
    ...
  },
  "total_pairs": 40,
  "topic_count": 10
}
```

### Get Training Statistics
```bash
GET /auto-training/stats
```
Response:
```json
{
  "total_sessions": 5,
  "total_examples_trained": 25,
  "average_reward": 0.725,
  "last_training": "2026-02-22T14:30:45.123456",
  "sessions_by_topic": {
    "Global Trade Relationships": {
      "count": 2,
      "examples": 8
    },
    ...
  }
}
```

## Configuration Options

The auto-training system is controlled by configuration file: `data/auto_training_config.json`

### Default Configuration
```json
{
  "enabled": true,
  "schedule_interval_minutes": 30,
  "examples_per_session": 5,
  "quick_mode": true,
  "topics_to_focus": [
    "Global Trade Relationships",
    "Climate Policy and International Action",
    "Democratic Institutions and Elections",
    "International Security and Conflicts"
  ]
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable auto-training |
| `schedule_interval_minutes` | int | `30` | Minutes between training sessions |
| `examples_per_session` | int | `5` | Training examples per session |
| `quick_mode` | bool | `true` | Use quick mode (faster, uses cache) |
| `topics_to_focus` | array | See default | Which topics to prioritize |

### Example: Train Every Hour on More Examples
```bash
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_interval_minutes": 60,
    "examples_per_session": 10
  }'
```

### Example: Disable Auto-Training
```bash
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## Usage Examples

### 1. Monitor Auto-Training Progress
```bash
# Check current status
curl http://localhost:8000/auto-training/status

# View training statistics
curl http://localhost:8000/auto-training/stats

# Get next training time
curl http://localhost:8000/auto-training/status | jq '.next_training'
```

### 2. Run Manual Training Immediately
```bash
# Train on 5 examples right now
curl -X POST http://localhost:8000/auto-training/trigger

# Train on 10 examples
curl -X POST http://localhost:8000/auto-training/trigger?num_examples=10
```

### 3. Customize Focus Topics
```bash
# Only train on climate and trade topics
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
    "topics_to_focus": [
      "Climate Policy and International Action",
      "Global Trade Relationships"
    ]
  }'
```

### 4. Aggressive Training Schedule
```bash
# Train every 15 minutes on 8 examples
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_interval_minutes": 15,
    "examples_per_session": 8,
    "quick_mode": true
  }'
```

### 5. High-Quality Training Mode
```bash
# Disable quick mode for better quality responses
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{"quick_mode": false}'
```

## Training Flow

```
┌─────────────────────────────────────────────────────────┐
│  Auto-Training Scheduler (Background Thread)             │
│                                                           │
│  1. Wait for scheduled interval                          │
│  2. Fetch political topics                               │
│  3. Sample random topics to focus on                     │
│  4. Train on N examples with RLHF reward system          │
│  5. Calculate average reward                             │
│  6. Log session statistics                               │
│  7. Repeat at next interval                              │
└─────────────────────────────────────────────────────────┘

Training Data Flow:
  Political Topics (10 categories)
       ↓
  Generate Q&A Pairs (40+ pairs)
       ↓
  Random Sampling (configurable)
       ↓
  RLHF Training (with reward calculation)
       ↓
  Model Update & Logging
```

## Performance Metrics

The system tracks:
- Total training sessions completed
- Total examples trained
- Average reward per session
- Training time per session
- Topic distribution
- Success rate

Example statistics:
```
Total Sessions:      12
Total Examples:      60
Average Reward:      0.754
Topics Covered:      All 10 topics
Duration Per Session: ~12 seconds (quick mode)
                     ~45 seconds (full mode)
```

## Logs and History

### Training Log
`data/auto_training_log.json` contains all training sessions:
```json
{
  "sessions": [
    {
      "auto_training": true,
      "examples_trained": 5,
      "avg_reward": 0.752,
      "duration_seconds": 14.2,
      "topics_covered": {
        "Global Trade Relationships": 2,
        "Democratic Institutions": 3
      },
      "quick_mode_used": true,
      "timestamp": "2026-02-22T14:30:45.123456"
    },
    ...
  ]
}
```

### Data Files
- `data/political_topics.json` - Cached political topics
- `data/auto_training_config.json` - Current configuration
- `data/auto_training_log.json` - Training session history
- `data/inference_cache.json` - Response cache (from previous optimization)

## Troubleshooting

### Auto-training Not Starting
```bash
# Check if scheduler is running
curl http://localhost:8000/auto-training/status

# Check if enabled in config
curl http://localhost:8000/auto-training/config | jq '.enabled'

# View server logs for errors
tail -f /tmp/server.log
```

### No Training Progress
```bash
# Trigger manual training to verify it works
curl -X POST http://localhost:8000/auto-training/trigger

# Check training statistics
curl http://localhost:8000/auto-training/stats
```

### Reset Configuration
```bash
# Delete config file to reset to defaults
rm data/auto_training_config.json

# Restart server
pkill -f "uvicorn webui.app"
python -m uvicorn webui.app:app --reload --port 8000
```

## Integration with Existing Systems

### Works With:
- ✅ Speed-optimized inference (2-second responses)
- ✅ Persistent response caching (instant on repeats)
- ✅ RLHF training dashboard
- ✅ Quick training mode
- ✅ All existing chat endpoints

### Training Loop:
1. Auto-trainer fetches political topics
2. Generates Q&A pairs with ideal answers
3. Calls `/train` endpoint with quick mode
4. RLHF system calculates rewards
5. Model learns political knowledge
6. Responses improve over time

## Best Practices

1. **Start Small, Scale Up**
   - Begin with default: 5 examples every 30 minutes
   - Monitor reward trends
   - Increase interval or examples based on performance

2. **Focus on Key Topics**
   - Use `topics_to_focus` to prioritize important areas
   - Change focus based on current events

3. **Balance Speed vs Quality**
   - Use `quick_mode: true` for consistent training
   - Switch to `false` for higher quality but slower training

4. **Monitor Progress**
   - Check `/auto-training/stats` regularly
   - Look for upward trends in average reward
   - Track coverage across all topics

5. **Manual Training for Hot Topics**
   - Use `/auto-training/trigger` when major events occur
   - Train on 10+ examples for significant events
   - Helps model stay current

## Next Steps

1. **Start the system:**
   ```bash
   # Server will auto-start training on startup
   # Or manually trigger:
   curl -X POST http://localhost:8000/auto-training/start
   ```

2. **Monitor progress:**
   ```bash
   curl http://localhost:8000/auto-training/status
   ```

3. **Test the improved model:**
   ```bash
   # Chat with the model - it now understands political topics!
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What are current trade tensions in the world?"}'
   ```

4. **Customize for your needs:**
   - Adjust schedule interval
   - Change focus topics
   - Toggle quick mode
   - Monitor reward trends

## Summary

Your AI now:
- 🤖 Trains automatically on world political matters
- 📊 Tracks 40+ political Q&A pairs across 10 major topics
- ⚡ Trains every 30 minutes (configurable)
- 📈 Learns through RLHF with reward feedback
- 🎯 Focuses on topics you care about most
- 📝 Logs all training sessions for analysis
- 🔧 Provides full API control and monitoring

The system runs automatically in the background, continuously improving your AI's understanding of global politics while you use it normally.
