#!/bin/bash

# ============================================================================
# AZAN AUTO-TRAINING QUICK COMMANDS
# ============================================================================
# Use these commands to control the auto-training system
# Copy and paste into your terminal (with proper environment)

echo "🤖 AZAN Auto-Training Control Panel"
echo "===================================="
echo ""

# ============================================================================
# 1. START AUTO-TRAINING
# ============================================================================
echo "📌 START AUTO-TRAINING:"
echo 'curl -X POST http://localhost:8000/auto-training/start'
echo ""

# ============================================================================
# 2. STOP AUTO-TRAINING  
# ============================================================================
echo "⏹️  STOP AUTO-TRAINING:"
echo 'curl -X POST http://localhost:8000/auto-training/stop'
echo ""

# ============================================================================
# 3. CHECK STATUS
# ============================================================================
echo "📊 CHECK AUTO-TRAINING STATUS:"
echo 'curl http://localhost:8000/auto-training/status'
echo ""

# ============================================================================
# 4. GET STATISTICS
# ============================================================================
echo "📈 GET TRAINING STATISTICS:"
echo 'curl http://localhost:8000/auto-training/stats'
echo ""

# ============================================================================
# 5. VIEW AVAILABLE TOPICS
# ============================================================================
echo "📚 VIEW AVAILABLE POLITICAL TOPICS:"
echo 'curl http://localhost:8000/auto-training/topics'
echo ""

# ============================================================================
# 6. TRIGGER MANUAL TRAINING
# ============================================================================
echo "🔥 TRIGGER MANUAL TRAINING (5 examples):"
echo 'curl -X POST "http://localhost:8000/auto-training/trigger?num_examples=5"'
echo ""

echo "🔥 TRIGGER MANUAL TRAINING (10 examples for important events):"
echo 'curl -X POST "http://localhost:8000/auto-training/trigger?num_examples=10"'
echo ""

# ============================================================================
# 7. VIEW CONFIGURATION
# ============================================================================
echo "⚙️  GET CONFIGURATION:"
echo 'curl http://localhost:8000/auto-training/config'
echo ""

# ============================================================================
# 8. MODIFY SCHEDULE (Train every 60 minutes)
# ============================================================================
echo "⏰ MODIFY SCHEDULE - Train every 60 minutes:"
cat << 'EOF'
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_interval_minutes": 60
  }'
EOF
echo ""

# ============================================================================
# 9. INCREASE TRAINING EXAMPLES
# ============================================================================
echo "📚 INCREASE EXAMPLES - Train on 10 examples per session:"
cat << 'EOF'
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
    "examples_per_session": 10
  }'
EOF
echo ""

# ============================================================================
# 10. FOCUS ON SPECIFIC TOPICS
# ============================================================================
echo "🎯 FOCUS ON CLIMATE & TRADE TOPICS ONLY:"
cat << 'EOF'
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
    "topics_to_focus": [
      "Climate Policy and International Action",
      "Global Trade Relationships"
    ]
  }'
EOF
echo ""

# ============================================================================
# 11. AGGRESSIVE TRAINING (Every 15 min, 8 examples, high quality)
# ============================================================================
echo "⚡ AGGRESSIVE TRAINING - Every 15 min with 8 examples:"
cat << 'EOF'
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_interval_minutes": 15,
    "examples_per_session": 8,
    "quick_mode": true
  }'
EOF
echo ""

# ============================================================================
# 12. RESET TO DEFAULT CONFIGURATION
# ============================================================================
echo "🔄 RESET TO DEFAULT CONFIGURATION:"
cat << 'EOF'
curl -X POST http://localhost:8000/auto-training/config \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
EOF
echo ""

# ============================================================================
# 13. TEST YOUR AI ON POLITICAL TOPICS
# ============================================================================
echo "💬 TEST YOUR AI ON POLITICAL TOPICS:"
cat << 'EOF'
# Ask about trade
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the current trade tensions in the world?"}'

# Ask about climate
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How are countries addressing climate change?"}'

# Ask about security
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are major geopolitical tensions today?"}'
EOF
echo ""

echo "✅ Commands ready! Copy and paste any command above into your terminal"
echo ""
echo "📖 For full guide, see: AUTO_TRAINING_GUIDE.md"
