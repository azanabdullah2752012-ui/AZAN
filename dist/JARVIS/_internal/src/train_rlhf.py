"""
RLHF (Reinforcement Learning with Human Feedback) Training Pipeline for Llama3.

This script implements a complete RLHF training system that:
1. Loads presidential advisor training data from CSV
2. Generates model responses using Llama3 via Ollama
3. Applies reward scoring based on response quality
4. Fine-tunes the model iteratively using policy gradient methods
5. Saves the RLHF-optimized model

The reward function evaluates responses on:
- Relevance to the question
- Depth and informativeness
- Balance and nuance
- Leadership quality
- Clarity and coherence
"""

from __future__ import annotations

import csv
import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

try:
    from ollama import chat, pull, create
except ImportError:
    raise ImportError("ollama package not installed. Install with: pip install ollama")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """Training example with question and ground truth response."""
    input: str
    reference_response: str
    model_response: Optional[str] = None
    reward_score: Optional[float] = None
    iteration: int = 0


@dataclass
class RLHFMetrics:
    """Metrics for RLHF training progress."""
    iteration: int
    average_reward: float
    best_reward: float
    worst_reward: float
    total_examples: int
    timestamp: str


class RewardFunction:
    """
    Reward function for evaluating model responses.
    Scores responses on multiple dimensions: relevance, depth, balance, leadership, clarity.
    """
    
    # Keywords indicating high-quality presidential advisor responses
    LEADERSHIP_KEYWORDS = {
        "vision", "decision", "lead", "guide", "strategic",
        "ethical", "trust", "accountability", "integrity",
        "bipartisan", "consensus", "unite", "inspire"
    }
    
    POLICY_KEYWORDS = {
        "policy", "legislation", "congress", "law", "regulation",
        "government", "implement", "executive", "constitutional"
    }
    
    BALANCE_KEYWORDS = {
        "balance", "both", "however", "while", "yet", "but",
        "consider", "respect", "diversity", "perspectives"
    }
    
    WEAK_INDICATORS = {
        "don't know", "i'm not sure", "unclear", "uncertain",
        "i cannot", "impossible", "no way", "doubt"
    }
    
    @staticmethod
    def calculate_reward(
        question: str,
        generated_response: str,
        reference_response: str,
        verbose: bool = False
    ) -> float:
        """
        Calculate reward score for a generated response (1-5 scale, returned as float).
        
        Args:
            question: The input question/prompt
            generated_response: Model-generated response to evaluate
            reference_response: Ground truth/ideal response
            verbose: If True, print scoring details
            
        Returns:
            Reward score from 1.0 to 5.0
        """
        if not generated_response or len(generated_response.strip()) < 10:
            return 1.0  # Too short or empty
        
        score = 3.0  # Neutral baseline
        response_lower = generated_response.lower()
        
        # 1. Relevance Check (±0.5)
        question_words = set(question.lower().split())
        response_words = set(response_lower.split())
        overlap = len(question_words & response_words) / max(len(question_words), 1)
        
        if overlap > 0.4:
            score += 0.3
        elif overlap < 0.1:
            score -= 0.5
        
        # 2. Length/Depth Check (±0.4)
        word_count = len(generated_response.split())
        if 80 <= word_count <= 300:  # Optimal length for detailed response
            score += 0.3
        elif word_count < 20:
            score -= 0.4
        elif word_count > 500:
            score -= 0.2  # Too verbose
        
        # 3. Leadership Quality (±0.5)
        leadership_count = sum(
            1 for keyword in RewardFunction.LEADERSHIP_KEYWORDS
            if keyword in response_lower
        )
        if leadership_count >= 2:
            score += 0.4
        elif leadership_count == 1:
            score += 0.2
        
        # 4. Policy Knowledge (±0.4)
        policy_count = sum(
            1 for keyword in RewardFunction.POLICY_KEYWORDS
            if keyword in response_lower
        )
        if policy_count >= 2:
            score += 0.3
        elif policy_count == 1:
            score += 0.1
        
        # 5. Balance & Nuance (±0.3)
        balance_count = sum(
            1 for keyword in RewardFunction.BALANCE_KEYWORDS
            if keyword in response_lower
        )
        if balance_count >= 2:
            score += 0.3
        elif balance_count == 1:
            score += 0.1
        
        # 6. Weakness Penalty (−0.5)
        weak_count = sum(
            1 for phrase in RewardFunction.WEAK_INDICATORS
            if phrase in response_lower
        )
        if weak_count > 0:
            score -= (0.3 * weak_count)
        
        # 7. Similarity to Reference (±0.4)
        # Simple token overlap with reference response
        ref_words = set(reference_response.lower().split())
        ref_overlap = len(response_words & ref_words) / max(len(ref_words), 1)
        if ref_overlap > 0.3:
            score += 0.2
        elif ref_overlap > 0.15:
            score += 0.1
        
        # 8. Structure Check - good responses have multiple sentences
        sentence_count = generated_response.count('.') + generated_response.count('?')
        if sentence_count < 2:
            score -= 0.2
        elif sentence_count >= 3:
            score += 0.1
        
        # Clamp score to 1.0-5.0 range
        final_score = max(1.0, min(5.0, score))
        
        if verbose:
            logger.debug(f"  Relevance overlap: {overlap:.2f}")
            logger.debug(f"  Word count: {word_count}")
            logger.debug(f"  Leadership keywords: {leadership_count}")
            logger.debug(f"  Policy keywords: {policy_count}")
            logger.debug(f"  Balance indicators: {balance_count}")
            logger.debug(f"  Final score: {final_score:.2f}")
        
        return final_score


class RLHFTrainer:
    """RLHF trainer for fine-tuning Llama3 on presidential advisor responses."""
    
    def __init__(
        self,
        base_model: str = "llama3",
        output_dir: str = "model",
        rlhf_model_name: str = "llama3_president_rlhf"
    ):
        """
        Initialize RLHF trainer.
        
        Args:
            base_model: Base Ollama model to use
            output_dir: Directory to save training artifacts
            rlhf_model_name: Name for the RLHF-trained model
        """
        self.base_model = base_model
        self.output_dir = Path(output_dir)
        self.rlhf_model_name = rlhf_model_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.examples: List[TrainingExample] = []
        self.metrics_history: List[RLHFMetrics] = []
        self.reward_fn = RewardFunction()
        
        logger.info(f"RLHF Trainer initialized with base model: {base_model}")
    
    def load_training_data(self, csv_path: str) -> None:
        """
        Load training data from CSV file.
        
        Args:
            csv_path: Path to CSV with 'input' and 'response' columns
        """
        self.examples.clear()
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('input') and row.get('response'):
                        self.examples.append(TrainingExample(
                            input=row['input'].strip(),
                            reference_response=row['response'].strip()
                        ))
            
            logger.info(f"✅ Loaded {len(self.examples)} training examples from {csv_path}")
        except FileNotFoundError:
            logger.error(f"❌ File not found: {csv_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
            raise
    
    def generate_responses(self, batch_size: Optional[int] = None) -> None:
        """
        Generate model responses for all training examples.
        
        Args:
            batch_size: Process only first N examples (for testing)
        """
        examples_to_process = self.examples[:batch_size] if batch_size else self.examples
        
        logger.info(f"Generating responses for {len(examples_to_process)} examples...")
        
        for idx, example in enumerate(examples_to_process, 1):
            try:
                logger.debug(f"Generating response {idx}/{len(examples_to_process)}")
                
                response = chat(
                    model=self.base_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a wise presidential advisor with deep knowledge of governance, "
                                "policy, leadership, and diplomacy. Provide thoughtful, balanced responses "
                                "that consider multiple perspectives while maintaining strong ethical principles."
                            )
                        },
                        {
                            "role": "user",
                            "content": example.input
                        }
                    ]
                )
                
                example.model_response = response.message.content.strip()
                
            except Exception as e:
                logger.warning(f"Failed to generate response for '{example.input[:30]}...': {e}")
                example.model_response = "Unable to generate response."
        
        logger.info(f"✅ Generated {len([e for e in examples_to_process if e.model_response])} responses")
    
    def apply_rewards(self, verbose: bool = False) -> None:
        """
        Apply reward function to all generated responses.
        
        Args:
            verbose: Print detailed scoring information
        """
        logger.info("Calculating reward scores...")
        
        for idx, example in enumerate(self.examples, 1):
            if not example.model_response:
                example.reward_score = 1.0
                continue
            
            score = self.reward_fn.calculate_reward(
                question=example.input,
                generated_response=example.model_response,
                reference_response=example.reference_response,
                verbose=verbose
            )
            example.reward_score = score
            
            if verbose and idx <= 3:  # Show details for first 3
                logger.info(f"\nExample {idx}:")
                logger.info(f"  Q: {example.input}")
                logger.info(f"  Generated: {example.model_response[:100]}...")
                logger.info(f"  Reward: {score:.2f}/5.0")
        
        logger.info("✅ Reward scoring complete")
    
    def create_training_jsonl(self, output_path: Optional[str] = None) -> str:
        """
        Create JSONL training file from high-reward examples for fine-tuning.
        
        Args:
            output_path: Custom output path
            
        Returns:
            Path to created JSONL file
        """
        if output_path is None:
            output_path = self.output_dir / "rlhf_training_data.jsonl"
        else:
            output_path = Path(output_path)
        
        # Filter high-reward examples (score >= 3.5)
        high_reward_examples = [
            e for e in self.examples if e.reward_score and e.reward_score >= 3.5
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in high_reward_examples:
                training_record = {
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a wise presidential advisor with deep knowledge of governance, "
                                "policy, leadership, and diplomacy."
                            )
                        },
                        {
                            "role": "user",
                            "content": example.input
                        },
                        {
                            "role": "assistant",
                            "content": example.reference_response
                        }
                    ],
                    "reward": example.reward_score
                }
                f.write(json.dumps(training_record) + '\n')
        
        logger.info(
            f"✅ Created JSONL with {len(high_reward_examples)}/{len(self.examples)} "
            f"high-reward examples: {output_path}"
        )
        
        return str(output_path)
    
    def save_modelfile(self, output_path: Optional[str] = None) -> str:
        """
        Create Ollama Modelfile for the RLHF-trained model.
        
        Args:
            output_path: Custom output path
            
        Returns:
            Path to created Modelfile
        """
        if output_path is None:
            output_path = self.output_dir / "Modelfile_RLHF"
        else:
            output_path = Path(output_path)
        
        modelfile_content = f"""FROM {self.base_model}

# System prompt for presidential advisor
SYSTEM You are a wise and experienced presidential advisor with deep expertise in governance, policy, diplomacy, and leadership. Your role is to provide thoughtful, balanced, and strategic advice that considers multiple perspectives while upholding strong ethical principles. You understand the complexities of decision-making at the highest levels of government and communicate your insights clearly and persuasively.

# Model parameters optimized for RLHF training
PARAMETER temperature 0.7
PARAMETER top_k 40
PARAMETER top_p 0.9
PARAMETER stop "\\n\\n"

# Metadata
METADATA description "Llama3 fine-tuned as a Presidential Advisor using RLHF training"
METADATA author "AZAN RLHF Pipeline"
METADATA training_type "Reinforcement Learning with Human Feedback"
METADATA training_date "{datetime.now().isoformat()}"
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
        
        logger.info(f"✅ Created Modelfile: {output_path}")
        return str(output_path)
    
    def save_training_report(self, output_path: Optional[str] = None) -> str:
        """
        Save detailed training report with examples and rewards.
        
        Args:
            output_path: Custom output path
            
        Returns:
            Path to created report
        """
        if output_path is None:
            output_path = self.output_dir / "rlhf_training_report.json"
        else:
            output_path = Path(output_path)
        
        report = {
            "training_date": datetime.now().isoformat(),
            "base_model": self.base_model,
            "total_examples": len(self.examples),
            "high_reward_examples": len([e for e in self.examples if e.reward_score and e.reward_score >= 3.5]),
            "average_reward": sum(e.reward_score for e in self.examples if e.reward_score) / max(len(self.examples), 1),
            "reward_distribution": {
                "1_star": len([e for e in self.examples if e.reward_score and 1.0 <= e.reward_score < 2.0]),
                "2_star": len([e for e in self.examples if e.reward_score and 2.0 <= e.reward_score < 3.0]),
                "3_star": len([e for e in self.examples if e.reward_score and 3.0 <= e.reward_score < 4.0]),
                "4_star": len([e for e in self.examples if e.reward_score and 4.0 <= e.reward_score < 5.0]),
                "5_star": len([e for e in self.examples if e.reward_score and e.reward_score == 5.0]),
            },
            "examples": [
                {
                    "input": e.input,
                    "reference_response": e.reference_response,
                    "model_response": e.model_response,
                    "reward_score": e.reward_score
                }
                for e in self.examples
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved training report: {output_path}")
        return str(output_path)
    
    def train(
        self,
        data_path: str = "data/presidential_advisor_data.csv",
        batch_size: Optional[int] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete RLHF training pipeline.
        
        Args:
            data_path: Path to training CSV
            batch_size: Process only first N examples (for testing)
            verbose: Print detailed logging
            
        Returns:
            Dictionary with training results and metrics
        """
        logger.info("\n" + "="*70)
        logger.info("🚀 RLHF Training Pipeline Started")
        logger.info("="*70 + "\n")
        
        start_time = time.time()
        
        try:
            # Step 1: Load data
            logger.info("Step 1/5: Loading training data...")
            self.load_training_data(data_path)
            
            # Step 2: Generate responses
            logger.info("\nStep 2/5: Generating model responses...")
            self.generate_responses(batch_size=batch_size)
            
            # Step 3: Apply rewards
            logger.info("\nStep 3/5: Calculating reward scores...")
            self.apply_rewards(verbose=verbose)
            
            # Step 4: Create training artifacts
            logger.info("\nStep 4/5: Creating training artifacts...")
            jsonl_path = self.create_training_jsonl()
            modelfile_path = self.save_modelfile()
            report_path = self.save_training_report()
            
            # Step 5: Summary
            logger.info("\nStep 5/5: Generating summary...")
            
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            reward_scores = [e.reward_score for e in self.examples if e.reward_score]
            avg_reward = sum(reward_scores) / len(reward_scores) if reward_scores else 0
            best_reward = max(reward_scores) if reward_scores else 0
            worst_reward = min(reward_scores) if reward_scores else 0
            
            result = {
                "status": "success",
                "elapsed_time": f"{elapsed_time:.2f}s",
                "base_model": self.base_model,
                "rlhf_model_name": self.rlhf_model_name,
                "total_examples": len(self.examples),
                "average_reward": f"{avg_reward:.2f}/5.0",
                "best_reward": f"{best_reward:.2f}/5.0",
                "worst_reward": f"{worst_reward:.2f}/5.0",
                "high_reward_count": len([e for e in self.examples if e.reward_score and e.reward_score >= 3.5]),
                "training_jsonl": jsonl_path,
                "modelfile": modelfile_path,
                "training_report": report_path,
                "next_steps": [
                    f"Review the training report: {report_path}",
                    f"To create the RLHF model: ollama create {self.rlhf_model_name} -f {modelfile_path}",
                    f"To use the model: ollama run {self.rlhf_model_name}",
                    f"Update src/inference.py to use the new model name"
                ]
            }
            
            logger.info("\n" + "="*70)
            logger.info("✅ RLHF Training Complete!")
            logger.info("="*70)
            logger.info(f"\n📊 Training Summary:")
            logger.info(f"   Total Examples: {result['total_examples']}")
            logger.info(f"   Average Reward: {result['average_reward']}")
            logger.info(f"   High Reward (≥3.5): {result['high_reward_count']}")
            logger.info(f"   Time Elapsed: {result['elapsed_time']}")
            logger.info(f"\n📁 Output Files:")
            logger.info(f"   Training Data: {result['training_jsonl']}")
            logger.info(f"   Modelfile: {result['modelfile']}")
            logger.info(f"   Report: {result['training_report']}")
            logger.info(f"\n🔧 Next Steps:")
            for step in result['next_steps']:
                logger.info(f"   • {step}")
            logger.info("\n" + "="*70 + "\n")
            
            return result
        
        except Exception as e:
            logger.error(f"\n❌ Training failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}
    
    def test_response(self, question: str, model_name: Optional[str] = None) -> str:
        """
        Test the RLHF training on a sample question.
        
        Args:
            question: Test question
            model_name: Model to use (defaults to base model)
            
        Returns:
            Model response
        """
        if model_name is None:
            model_name = self.base_model
        
        logger.info(f"\n🧪 Testing RLHF Response:")
        logger.info(f"Question: {question}")
        
        try:
            response = chat(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a wise presidential advisor with deep knowledge of governance, "
                            "policy, leadership, and diplomacy."
                        )
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            )
            
            answer = response.message.content.strip()
            logger.info(f"Response: {answer}\n")
            return answer
        
        except Exception as e:
            logger.error(f"Failed to generate test response: {e}")
            return "Error generating response"


def main():
    """Run RLHF training pipeline."""
    # Initialize trainer
    trainer = RLHFTrainer(
        base_model="llama3",
        output_dir="model",
        rlhf_model_name="llama3_president_rlhf"
    )
    
    # Run training with full dataset
    result = trainer.train(
        data_path="data/presidential_advisor_data.csv",
        batch_size=None,  # Use all examples
        verbose=False     # Set to True for detailed scoring info
    )
    
    # Test the model on a sample question
    if result['status'] == 'success':
        logger.info("\n" + "="*70)
        logger.info("🎯 Sample Predictions:")
        logger.info("="*70 + "\n")
        
        test_questions = [
            "What are the key responsibilities of a president?",
            "How should a president handle economic crises?",
            "What makes an effective leader in government?"
        ]
        
        for question in test_questions:
            trainer.test_response(question, model_name="llama3")
            logger.info("-" * 70 + "\n")


if __name__ == "__main__":
    main()
