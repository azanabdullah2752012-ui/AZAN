"""
AZAN Math Trainer — Phase 6
Implements Process-Based RLHF (PRM) for mathematical reasoning.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sympy as sp

from src.math_engine import get_math_engine

logger = logging.getLogger(__name__)

class MathTrainer:
    """
    Trainer specialized in high-reasoning math tasks.
    """
    
    def __init__(self):
        self.engine = get_math_engine()
        self.training_log_file = Path("data") / "math_training_log.json"
        self.training_log_file.parent.mkdir(exist_ok=True)
        self._load_log()

    def _load_log(self):
        if self.training_log_file.exists():
            try:
                with open(self.training_log_file) as f:
                    self.log = json.load(f)
            except:
                self.log = []
        else:
            self.log = []

    def _save_log(self):
        with open(self.training_log_file, 'w') as f:
            json.dump(self.log, f, indent=2)

    def evaluate_step_by_step(self, question: str, response: str, ground_truth_expr: str) -> Dict[str, Any]:
        """
        Evaluate a multi-step solution.
        (This is a simplified PRM implementation)
        """
        # 1. Identify final answer in the response (usually after "The answer is" or last line)
        lines = response.strip().split('\n')
        final_answer_line = lines[-1]
        
        # Try to extract the math expression from the last line
        # e.g. "The result is x**2" -> "x**2"
        match = re.search(r'is\s+([^.]+)', final_answer_line)
        extracted_answer = match.group(1) if match else final_answer_line
        
        # 2. Verify equivalence
        verification = self.engine.verify_solution(extracted_answer, ground_truth_expr)
        
        reward = 5.0 if verification.get("is_correct") else 1.0
        
        result = {
            "question": question,
            "response": response,
            "verification": verification,
            "reward": reward,
            "timestamp": datetime.now().isoformat()
        }
        
        self.log.append(result)
        self._save_log()
        return result

    def get_training_stats(self) -> Dict[str, Any]:
        if not self.log:
            return {"total": 0, "avg_reward": 0}
            
        rewards = [l['reward'] for l in self.log]
        return {
            "total_solved": len(self.log),
            "avg_reward": sum(rewards) / len(rewards),
            "last_run": self.log[-1]['timestamp'] if self.log else None
        }

# Global instances
import re
trainer = MathTrainer()

def get_math_trainer():
    return trainer
