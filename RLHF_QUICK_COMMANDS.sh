#!/usr/bin/env bash
# RLHF Training Quick Commands Reference
# Usage: Copy commands directly to terminal

# 1. Run the RLHF demo (fast, no Ollama generation)
cd /Users/azan/Desktop/AZAN && source .venv/bin/activate && python demo_rlhf.py

# 2. Run full RLHF training (generates responses from Llama3)
cd /Users/azan/Desktop/AZAN && source .venv/bin/activate && python src/train_rlhf.py

# 3. View the training report
cat /Users/azan/Desktop/AZAN/model/rlhf_training_report.json | python -m json.tool | head -100

# 4. View the Modelfile
cat /Users/azan/Desktop/AZAN/model/Modelfile_RLHF

# 5. Count high-reward examples
grep -c '"reward_score": [4-5]' /Users/azan/Desktop/AZAN/model/rlhf_training_report.json

# 6. Create the RLHF model in Ollama
ollama create llama3_president_rlhf -f /Users/azan/Desktop/AZAN/model/Modelfile_RLHF

# 7. Test the RLHF model
ollama run llama3_president_rlhf

# 8. Compare base vs RLHF model
echo "=== Base Model ===" && ollama run llama3 "What are the key responsibilities of a president?"
echo "=== RLHF Model ===" && ollama run llama3_president_rlhf "What are the key responsibilities of a president?"

# 9. Update FastAPI to use RLHF model
# Edit src/inference.py and change:
# BASE_MODEL_NAME = "llama3"
# To:
# BASE_MODEL_NAME = "llama3_president_rlhf"

# 10. Restart FastAPI server
cd /Users/azan/Desktop/AZAN && source .venv/bin/activate && python -m uvicorn webui.app:app --reload

# 11. Add new training data
# Edit data/presidential_advisor_data.csv and add new Q&A pairs, then:
cd /Users/azan/Desktop/AZAN && source .venv/bin/activate && python src/train_rlhf.py

# 12. Run training with only 3 examples (for testing)
python << 'PYTHON'
import sys
sys.path.insert(0, '/Users/azan/Desktop/AZAN')
from src.train_rlhf import RLHFTrainer

trainer = RLHFTrainer()
result = trainer.train(batch_size=3, verbose=True)
PYTHON

# 13. View RLHF training data JSONL format
head -5 /Users/azan/Desktop/AZAN/model/rlhf_training_data.jsonl | python -m json.tool

# 14. Check average reward score
python << 'PYTHON'
import json
with open('/Users/azan/Desktop/AZAN/model/rlhf_training_report.json') as f:
    data = json.load(f)
    print(f"Average Reward: {data['average_reward']:.2f}/5.0")
    print(f"High Quality Examples: {data['high_reward_examples']}/{data['total_examples']}")
PYTHON

# 15. Analyze reward distribution
python << 'PYTHON'
import json
with open('/Users/azan/Desktop/AZAN/model/rlhf_training_report.json') as f:
    data = json.load(f)
    dist = data['reward_distribution']
    print("Reward Distribution:")
    print(f"  1-star: {dist['1_star']}")
    print(f"  2-star: {dist['2_star']}")
    print(f"  3-star: {dist['3_star']}")
    print(f"  4-star: {dist['4_star']}")
    print(f"  5-star: {dist['5_star']}")
PYTHON
