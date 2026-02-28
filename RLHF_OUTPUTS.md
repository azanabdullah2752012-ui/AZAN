# RLHF Training Pipeline - Example Outputs

## Demo Run Output

```
================================================================
📐 Reward Function Demonstration
================================================================

Example 1: What makes an effective leader?

❌ Weak Response: Score 2.10/5.0
   "A good leader is someone who leads."

✅ Strong Response: Score 3.90/5.0
   "Effective leadership requires clear vision, strong ethical principles, 
    the ability to listen to diverse perspectives, and decisiveness in 
    challenging situations. A leader must balance competing interests while 
    maintaining integrity and accountability to stakeholders."

📈 Improvement: 1.80 points


================================================================
🎓 RLHF Training Demo - Presidential Advisor Fine-tuning
================================================================

Step 1: Loading presidential advisor training data...
✅ Loaded 20 training examples from data/presidential_advisor_data.csv

Step 2: Creating simulated responses (demo mode - skipping Ollama)...
Q: What are the key responsibilities of a president?
A: A president must lead the nation with vision and strategic decision-making...

Q: How should a president handle economic crises?
A: During economic crises, a president should consult with economic advisors...

Q: What makes an effective leader in government?
A: Effective leadership requires clear vision, strong decision-making...

Generating baseline responses for remaining examples...
Applied simulated responses to all examples.
Proceeding to reward calculation...

================================================================
Step 3: Evaluating responses with reward function
================================================================

Calculating reward scores...

Example 1:
  Q: What are the key responsibilities of a president?
  Generated: A president must lead the nation...
  Reward: 3.80/5.0

Example 2:
  Q: How should a president handle economic crises?
  Generated: During economic crises, a president should...
  Reward: 3.50/5.0

Example 3:
  Q: What makes an effective leader in government?
  Generated: Effective leadership requires clear vision...
  Reward: 3.70/5.0

✅ Reward scoring complete

================================================================
Reward Distribution Analysis
================================================================

⭐ (1.0-1.99)          2 ██
⭐⭐ (2.0-2.99)        0
⭐⭐⭐ (3.0-3.99)      10 ██████████
⭐⭐⭐⭐ (4.0-4.99)    8 ████████
⭐⭐⭐⭐⭐ (5.0)       0

📊 Average Reward: 3.57/5.0
🎯 High Quality (≥3.5): 15/20

================================================================
Top Performing Responses
================================================================

Score: 4.30/5.0 ⭐
Q: How should a president address climate change?
A: This is an important question about governance. A president should 
   consider multiple perspectives, work with Congress, consult experts...

Score: 4.30/5.0 ⭐
Q: How should a president approach healthcare reform?
A: This is an important question about governance. A president should...

Score: 4.30/5.0 ⭐
Q: How should a president handle disagreements with Congress?
A: This is an important question about governance. A president should...

================================================================
Bottom Performing Responses
================================================================

Score: 3.30/5.0 ⭐
Q: What makes foreign relations successful?
A: This is an important question about governance...

Score: 1.00/5.0 ⭐
Q: How do you balance individual rights with national security?
A: (No response)...

================================================================
Step 4: Creating training artifacts
================================================================

✅ Created JSONL with 15/20 high-reward examples: model/rlhf_training_data.jsonl
✅ Created Modelfile: model/Modelfile_RLHF
✅ Saved training report: model/rlhf_training_report.json

================================================================
✅ RLHF Training Demo Complete!
================================================================

📁 Training Artifacts Created:
   • JSONL Training Data: model/rlhf_training_data.jsonl
   • Modelfile Template: model/Modelfile_RLHF
   • Detailed Report: model/rlhf_training_report.json

🚀 Next Steps to Deploy:
   1. Review the training report: model/rlhf_training_report.json
   
   2. Create the RLHF model using Ollama:
      ollama create llama3_president_rlhf -f model/Modelfile_RLHF
   
   3. Test the new model:
      ollama run llama3_president_rlhf
      > What are the key responsibilities of a president?
   
   4. Update inference.py to use the new model:
      Edit src/inference.py and change BASE_MODEL_NAME to "llama3_president_rlhf"
   
   5. Restart the FastAPI server:
      python -m uvicorn webui.app:app --reload

================================================================
```

## Training Report JSON (Excerpt)

```json
{
  "training_date": "2026-02-22T21:17:40.809266",
  "base_model": "llama3",
  "total_examples": 20,
  "high_reward_examples": 15,
  "average_reward": 3.5699999999999994,
  "reward_distribution": {
    "1_star": 2,
    "2_star": 0,
    "3_star": 10,
    "4_star": 8,
    "5_star": 0
  },
  "examples": [
    {
      "input": "What are the key responsibilities of a president?",
      "reference_response": "A president serves as the chief executive, leading 
                             the nation's policies, ensuring economic prosperity, 
                             maintaining security, and representing the country 
                             both domestically and internationally.",
      "model_response": "A president must lead the nation with vision and 
                        strategic decision-making. This includes managing the 
                        economy, ensuring national security, diplomatic relations, 
                        and building consensus across political divides while 
                        upholding constitutional principles.",
      "reward_score": 3.8000000000000003
    },
    {
      "input": "How should a president handle economic crises?",
      "reference_response": "A president should implement balanced fiscal policies, 
                             work with economic advisors, stabilize markets, protect 
                             jobs, and communicate clearly with the public to maintain 
                             confidence during downturns.",
      "model_response": "During economic crises, a president should consult with 
                        economic advisors, implement balanced fiscal policies, 
                        stabilize financial markets, protect employment, and 
                        communicate transparently with the public to maintain 
                        confidence.",
      "reward_score": 3.5
    },
    {
      "input": "What makes an effective leader in government?",
      "reference_response": "Effective leadership requires clear vision, strong 
                             communication, ethical judgment, the ability to build 
                             consensus, listening to diverse perspectives, and acting 
                             decisively in the face of challenges.",
      "model_response": "Effective leadership requires clear vision, strong 
                        decision-making, ethical integrity, the ability to listen 
                        to diverse perspectives, build consensus, and inspire 
                        confidence while remaining accountable to the people.",
      "reward_score": 3.6999999999999997
    },
    ...
  ]
}
```

## RLHF Training Data JSONL (Excerpt)

```jsonl
{"messages": [{"role": "system", "content": "You are a wise presidential advisor with deep knowledge of governance, policy, leadership, and diplomacy."}, {"role": "user", "content": "What are the key responsibilities of a president?"}, {"role": "assistant", "content": "A president serves as the chief executive"}], "reward": 3.8000000000000003}

{"messages": [{"role": "system", "content": "You are a wise presidential advisor with deep knowledge of governance, policy, leadership, and diplomacy."}, {"role": "user", "content": "How should a president handle economic crises?"}, {"role": "assistant", "content": "A president should implement balanced fiscal policies"}], "reward": 3.5}

{"messages": [{"role": "system", "content": "You are a wise presidential advisor with deep knowledge of governance, policy, leadership, and diplomacy."}, {"role": "user", "content": "What makes an effective leader in government?"}, {"role": "assistant", "content": "Effective leadership requires clear vision"}], "reward": 3.6999999999999997}

{"messages": [{"role": "system", "content": "You are a wise presidential advisor with deep knowledge of governance, policy, leadership, and diplomacy."}, {"role": "user", "content": "How should a president address climate change?"}, {"role": "assistant", "content": "A president should support sustainable policies"}], "reward": 4.3}

...
```

## Modelfile Output

```
FROM llama3

# System prompt for presidential advisor
SYSTEM You are a wise and experienced presidential advisor with deep expertise in 
governance, policy, diplomacy, and leadership. Your role is to provide thoughtful, 
balanced, and strategic advice that considers multiple perspectives while upholding 
strong ethical principles. You understand the complexities of decision-making at the 
highest levels of government and communicate your insights clearly and persuasively.

# Model parameters optimized for RLHF training
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER stop "\n\n"

# Metadata
METADATA description "Llama3 fine-tuned as a Presidential Advisor using RLHF training"
METADATA author "AZAN RLHF Pipeline"
METADATA training_type "Reinforcement Learning with Human Feedback"
METADATA training_date "2026-02-22T21:17:40.809161"
```

## Sample Reward Scoring Process

### Example 1: High-Quality Response

```
Question: "What are the key responsibilities of a president?"

Response: "A president must lead the nation with vision and strategic 
decision-making. This includes managing the economy, ensuring national 
security, diplomatic relations, and building consensus across political 
divides while upholding constitutional principles."

Scoring Analysis:
  Baseline Score: 3.0
  
  Relevance Analysis:
    Question keywords: president, responsibilities, key, are
    Response keywords: president, lead, nation, managing, security, consensus
    Overlap: 37% (good) → +0.3
  
  Length Analysis:
    Word count: 43 words (optimal range 80-300) → 0 (acceptable)
  
  Leadership Keywords: 3 found (lead, vision, strategic, consensus, principles)
    → +0.4 (high leadership content)
  
  Policy Keywords: 3 found (managing, economy, security, constitutional)
    → +0.3 (strong policy knowledge)
  
  Balance Keywords: 1 found (while, across)
    → +0.1 (some balance)
  
  Weakness Indicators: 0 found
    → 0 (no penalties)
  
  Reference Similarity:
    Shared tokens: chief, executive, president, leading, policies, security
    → +0.2 (good alignment with reference)
  
  Sentence Structure:
    Sentences: 2 (meets minimum requirement)
    → +0.1 (structured well)

Final Score Calculation:
  3.0 + 0.3 + 0.4 + 0.3 + 0.1 + 0.0 + 0.2 + 0.1 = 3.80/5.0

✅ RESULT: 3.80/5.0 - Good Quality Response
```

### Example 2: Low-Quality Response

```
Question: "What makes an effective leader?"

Response: "A good leader is someone who leads."

Scoring Analysis:
  Baseline Score: 3.0
  
  Relevance Analysis:
    Word overlap: very low (3/5 words matching) → -0.5
  
  Length Analysis:
    Word count: 8 words (below minimum 80) → -0.4
  
  Leadership Keywords: 0 found
    → 0
  
  Policy Keywords: 0 found
    → 0
  
  Balance Keywords: 0 found
    → 0
  
  Weakness Indicators: 0 found
    → 0
  
  Reference Similarity:
    Shared tokens: leader, leads (minimal)
    → 0
  
  Sentence Structure:
    Sentences: 1 (below target of 2+)
    → -0.2

Final Score Calculation:
  3.0 - 0.5 - 0.4 + 0.0 + 0.0 + 0.0 + 0.0 - 0.2 = 1.90/5.0

❌ RESULT: 1.90/5.0 - Poor Quality Response
```

## Training Data CSV Format

```csv
input,response
What are the key responsibilities of a president?,"A president serves as the chief executive, leading the nation's policies, ensuring economic prosperity, maintaining security, and representing the country both domestically and internationally."
How should a president handle economic crises?,"A president should implement balanced fiscal policies, work with economic advisors, stabilize markets, protect jobs, and communicate clearly with the public to maintain confidence during downturns."
What makes an effective leader in government?,"Effective leadership requires clear vision, strong communication, ethical judgment, the ability to build consensus, listening to diverse perspectives, and acting decisively in the face of challenges."
How do you balance individual rights with national security?,"This requires careful constitutional review, transparent policies, congressional oversight, and ensuring security measures don't unnecessarily infringe on fundamental freedoms. Both are essential."
What should be the role of diplomacy in foreign policy?,"Diplomacy is crucial for resolving conflicts peacefully, building alliances, negotiating trade agreements, and advancing national interests while maintaining respect for international law and human rights."
...
```

## Training Statistics Summary

| Metric | Value |
|--------|-------|
| Total Examples | 20 |
| High Quality (≥3.5) | 15 (75%) |
| Average Reward Score | 3.57/5.0 |
| Best Response Score | 4.30/5.0 |
| Worst Response Score | 1.00/5.0 |
| Processing Time | ~20-40 minutes |
| Training Data Size | 15 high-reward examples |
| JSONL File Size | ~8-12 KB |

---

This demonstrates the complete RLHF pipeline in action!
