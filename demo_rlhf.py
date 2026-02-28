"""
Demo script showing RLHF training with simulated responses.
Use this to understand the reward function and RLHF pipeline without waiting for LLM generation.
"""

import sys
sys.path.insert(0, '/Users/azan/Desktop/AZAN')

from src.train_rlhf import RLHFTrainer, TrainingExample, RewardFunction
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_rlhf():
    """Run RLHF demo with simulated responses."""
    
    logger.info("\n" + "="*70)
    logger.info("🎓 RLHF Training Demo - Presidential Advisor Fine-tuning")
    logger.info("="*70 + "\n")
    
    # Initialize trainer
    trainer = RLHFTrainer(
        base_model="llama3",
        output_dir="model",
        rlhf_model_name="llama3_president_rlhf"
    )
    
    # Load training data
    logger.info("Step 1: Loading presidential advisor training data...")
    trainer.load_training_data("data/presidential_advisor_data.csv")
    
    # Skip Ollama generation - use simulated responses instead
    logger.info("Step 2: Creating simulated responses (demo mode - skipping Ollama)...\n")
    
    simulated_responses = {
        "What are the key responsibilities of a president?": 
            "A president must lead the nation with vision and strategic decision-making. This includes managing the economy, ensuring national security, diplomatic relations, and building consensus across political divides while upholding constitutional principles.",
        
        "How should a president handle economic crises?":
            "During economic crises, a president should consult with economic advisors, implement balanced fiscal policies, stabilize financial markets, protect employment, and communicate transparently with the public to maintain confidence.",
        
        "What makes an effective leader in government?":
            "Effective leadership requires clear vision, strong decision-making, ethical integrity, the ability to listen to diverse perspectives, build consensus, and inspire confidence while remaining accountable to the people.",
        
        "What's the importance of transparency in government?":
            "Transparency builds public trust, ensures accountability, enables informed citizen participation, and is fundamental to democratic governance. It strengthens institutions and prevents corruption.",
        
        "How do you unite a divided nation?":
            "Unifying a divided nation requires respecting diverse viewpoints, finding common ground on shared values, elevating national interest above partisan concerns, and demonstrating that different perspectives can coexist in a strong democracy.",
    }
    
    # Assign simulated responses to first 5 examples
    for i, example in enumerate(trainer.examples[:5]):
        if example.input in simulated_responses:
            example.model_response = simulated_responses[example.input]
            logger.info(f"Q: {example.input}")
            logger.info(f"A: {example.model_response[:100]}...\n")
    
    # For remaining examples, create reasonable but shorter responses
    logger.info("Generating baseline responses for remaining examples...\n")
    for i, example in enumerate(trainer.examples[5:], start=5):
        example.model_response = (
            f"This is an important question about governance. A president should consider "
            f"multiple perspectives, work with Congress, consult experts, and maintain ethical "
            f"principles while implementing policy solutions."
        )
    
    # Step 2.5: Apply rewards to simulated responses
    logger.info("Applied simulated responses to all examples.")
    logger.info("Proceeding to reward calculation...\n")
    
    # Apply reward function
    logger.info("="*70)
    logger.info("Step 3: Evaluating responses with reward function")
    logger.info("="*70 + "\n")
    
    trainer.apply_rewards(verbose=True)
    
    # Display reward distribution
    logger.info("\n" + "="*70)
    logger.info("Reward Distribution Analysis")
    logger.info("="*70 + "\n")
    
    rewards = [e.reward_score for e in trainer.examples if e.reward_score]
    
    star_counts = {
        "⭐ (1.0-1.99)": len([r for r in rewards if 1.0 <= r < 2.0]),
        "⭐⭐ (2.0-2.99)": len([r for r in rewards if 2.0 <= r < 3.0]),
        "⭐⭐⭐ (3.0-3.99)": len([r for r in rewards if 3.0 <= r < 4.0]),
        "⭐⭐⭐⭐ (4.0-4.99)": len([r for r in rewards if 4.0 <= r < 5.0]),
        "⭐⭐⭐⭐⭐ (5.0)": len([r for r in rewards if r == 5.0]),
    }
    
    for rating, count in star_counts.items():
        bar = "█" * count
        logger.info(f"{rating:20} {count:2} {bar}")
    
    avg_reward = sum(rewards) / len(rewards) if rewards else 0
    logger.info(f"\n📊 Average Reward: {avg_reward:.2f}/5.0")
    logger.info(f"🎯 High Quality (≥3.5): {len([r for r in rewards if r >= 3.5])}/{len(rewards)}")
    
    # Show top and bottom responses
    logger.info("\n" + "="*70)
    logger.info("Top Performing Responses")
    logger.info("="*70 + "\n")
    
    sorted_examples = sorted(trainer.examples, key=lambda e: e.reward_score or 0, reverse=True)
    
    for example in sorted_examples[:3]:
        logger.info(f"Score: {example.reward_score:.2f}/5.0 ⭐")
        logger.info(f"Q: {example.input}")
        response_text = example.model_response if example.model_response else "(No response)"
        logger.info(f"A: {response_text[:120]}...\n")
    
    logger.info("="*70)
    logger.info("Bottom Performing Responses")
    logger.info("="*70 + "\n")
    
    for example in sorted_examples[-3:]:
        logger.info(f"Score: {example.reward_score:.2f}/5.0 ⭐")
        logger.info(f"Q: {example.input}")
        response_text = example.model_response if example.model_response else "(No response)"
        logger.info(f"A: {response_text[:120]}...\n")
    
    # Create training artifacts
    logger.info("="*70)
    logger.info("Step 4: Creating training artifacts")
    logger.info("="*70 + "\n")
    
    jsonl_path = trainer.create_training_jsonl()
    modelfile_path = trainer.save_modelfile()
    report_path = trainer.save_training_report()
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("✅ RLHF Training Demo Complete!")
    logger.info("="*70)
    logger.info(f"""
📁 Training Artifacts Created:
   • JSONL Training Data: {jsonl_path}
   • Modelfile Template: {modelfile_path}
   • Detailed Report: {report_path}

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

📊 Reward Function Features:
   • Relevance: Checks question-answer word overlap
   • Depth: Evaluates response length and complexity
   • Leadership: Scores presence of leadership keywords
   • Policy: Detects governance and policy understanding
   • Balance: Rewards nuanced, balanced perspectives
   • Quality Indicators: Avoids uncertainty/weakness signals
   • Sentence Structure: Encourages multi-sentence responses

🎯 How to Improve Scores:
   1. Add more high-quality examples to training data
   2. Ensure responses are 80-300 words (optimal length)
   3. Include leadership and policy keywords naturally
   4. Show balanced perspectives (use "however", "consider", etc.)
   5. Provide concrete, well-structured answers
    """)
    logger.info("="*70 + "\n")

def demo_reward_function():
    """Demonstrate the reward function on specific examples."""
    
    logger.info("\n" + "="*70)
    logger.info("📐 Reward Function Demonstration")
    logger.info("="*70 + "\n")
    
    reward_fn = RewardFunction()
    
    examples = [
        {
            "question": "What makes an effective leader?",
            "bad_response": "A good leader is someone who leads.",
            "good_response": "Effective leadership requires clear vision, strong ethical principles, the ability to listen to diverse perspectives, and decisiveness in challenging situations. A leader must balance competing interests while maintaining integrity and accountability to stakeholders."
        },
        {
            "question": "How should a president handle a crisis?",
            "bad_response": "I'm not sure how to handle that.",
            "good_response": "During a crisis, a president should consult with expert advisors, communicate transparently with the public, implement evidence-based policies, coordinate with Congress, and provide clear leadership while balancing immediate needs with long-term consequences."
        }
    ]
    
    for i, example in enumerate(examples, 1):
        logger.info(f"\nExample {i}: {example['question']}\n")
        
        bad_score = reward_fn.calculate_reward(
            example['question'],
            example['bad_response'],
            example['good_response']
        )
        
        good_score = reward_fn.calculate_reward(
            example['question'],
            example['good_response'],
            example['good_response']
        )
        
        logger.info(f"❌ Weak Response: Score {bad_score:.2f}/5.0")
        logger.info(f"   \"{example['bad_response']}\"\n")
        
        logger.info(f"✅ Strong Response: Score {good_score:.2f}/5.0")
        logger.info(f"   \"{example['good_response']}\"\n")
        
        logger.info(f"📈 Improvement: {good_score - bad_score:.2f} points\n")

if __name__ == "__main__":
    # Run demonstrations
    demo_reward_function()
    demo_rlhf()
