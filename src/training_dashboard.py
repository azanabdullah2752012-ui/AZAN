"""
RLHF Training Dashboard Backend for Web Interface.

Provides endpoints and logic for:
1. Web-based training interface
2. Real-time training progress monitoring
3. Training history and analytics
4. Model comparison
5. Data management (upload, view, delete)
"""

from __future__ import annotations

import json
import logging
import hashlib
import httpx
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from functools import lru_cache

try:
    from ollama import chat
    OLLAMA_PKG_AVAILABLE = True
except ImportError:
    chat = None
    OLLAMA_PKG_AVAILABLE = False
    logger.warning("ollama package not installed. Using httpx fallback for dashboard.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data")
MODEL_DIR = Path("model")
TRAINING_HISTORY_FILE = DATA_DIR / "training_history.json"
MODELS_METADATA_FILE = MODEL_DIR / "models_metadata.json"


class TrainingStatus(Enum):
    """Training job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TrainingMetadata:
    """Metadata for a training session."""
    session_id: str
    model_name: str
    created_at: str
    completed_at: Optional[str] = None
    status: str = "pending"
    total_examples: int = 0
    high_quality_examples: int = 0
    average_reward: float = 0.0
    training_time_seconds: float = 0.0
    reward_distribution: Dict[str, int] = field(default_factory=dict)
    training_data_path: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SingleTrainingExample:
    """Single training example with results."""
    question: str
    ideal_answer: str
    model_response: str
    reward_score: float
    timestamp: str
    reward_breakdown: Dict[str, float] = field(default_factory=dict)


class RewardFunctionV2:
    """Enhanced reward function with breakdown tracking."""
    
    LEADERSHIP_KEYWORDS = {
        "vision", "decision", "lead", "guide", "strategic",
        "ethical", "trust", "accountability", "integrity",
        "bipartisan", "consensus", "unite", "inspire", "leader"
    }
    
    POLICY_KEYWORDS = {
        "policy", "legislation", "congress", "law", "regulation",
        "government", "implement", "executive", "constitutional",
        "federal", "statute", "act"
    }
    
    BALANCE_KEYWORDS = {
        "balance", "both", "however", "while", "yet", "but",
        "consider", "respect", "diversity", "perspectives",
        "multifaceted", "complex", "nuance"
    }
    
    WEAK_INDICATORS = {
        "don't know", "i'm not sure", "unclear", "uncertain",
        "i cannot", "impossible", "no way", "doubt", "maybe"
    }
    
    @staticmethod
    def calculate_reward_with_breakdown(
        question: str,
        generated_response: str,
        reference_response: str
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate reward with detailed breakdown.
        
        Returns:
            (total_score, breakdown_dict)
        """
        breakdown = {}
        base_score = 3.0
        
        # 1. Relevance (word overlap)
        question_words = set(question.lower().split())
        response_words = set(generated_response.lower().split())
        overlap = len(question_words & response_words) / max(len(question_words), 1)
        relevance_bonus = (overlap - 0.1) * 0.5 if overlap > 0.1 else -0.5
        breakdown["relevance"] = round(min(0.5, max(-0.5, relevance_bonus)), 2)
        
        # 2. Depth (length analysis)
        words = len(generated_response.split())
        if 80 <= words <= 300:
            depth_bonus = 0.4
        elif 50 <= words < 80 or 300 < words <= 500:
            depth_bonus = 0.2
        else:
            depth_bonus = -0.4
        breakdown["depth"] = round(depth_bonus, 2)
        
        # 3. Leadership keywords
        response_lower = generated_response.lower()
        leadership_count = sum(1 for kw in RewardFunctionV2.LEADERSHIP_KEYWORDS if kw in response_lower)
        leadership_bonus = min(0.5, leadership_count * 0.1)
        breakdown["leadership"] = round(leadership_bonus, 2)
        
        # 4. Policy keywords
        policy_count = sum(1 for kw in RewardFunctionV2.POLICY_KEYWORDS if kw in response_lower)
        policy_bonus = min(0.4, policy_count * 0.08)
        breakdown["policy"] = round(policy_bonus, 2)
        
        # 5. Balance/Nuance
        balance_count = sum(1 for kw in RewardFunctionV2.BALANCE_KEYWORDS if kw in response_lower)
        balance_bonus = min(0.3, balance_count * 0.06)
        breakdown["balance"] = round(balance_bonus, 2)
        
        # 6. Quality signals (penalize weakness)
        weak_count = sum(1 for wi in RewardFunctionV2.WEAK_INDICATORS if wi in response_lower)
        quality_penalty = -0.5 * weak_count
        breakdown["quality_signals"] = round(quality_penalty, 2)
        
        # 7. Reference similarity (token overlap with ideal)
        ref_words = set(reference_response.lower().split())
        resp_words = set(generated_response.lower().split())
        ref_overlap = len(ref_words & resp_words) / max(len(ref_words), 1)
        reference_bonus = (ref_overlap - 0.2) * 0.4 if ref_overlap > 0.2 else -0.2
        breakdown["reference_similarity"] = round(min(0.4, max(-0.4, reference_bonus)), 2)
        
        # 8. Structure (multi-sentence)
        sentences = len([s for s in generated_response.split(".") if s.strip()])
        structure_bonus = 0.2 if sentences >= 2 else -0.2
        breakdown["structure"] = round(structure_bonus, 2)
        
        # Calculate total
        total_score = base_score + sum(breakdown.values())
        total_score = round(max(1.0, min(5.0, total_score)), 2)
        breakdown["total"] = total_score
        
        return total_score, breakdown


class TrainingDashboard:
    """Dashboard manager for RLHF training."""
    
    def __init__(self):
        """Initialize dashboard."""
        self.data_dir = DATA_DIR
        self.model_dir = MODEL_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.model_dir.mkdir(exist_ok=True)
        self.reward_fn = RewardFunctionV2()
        self._load_training_history()
        self._load_models_metadata()
        # Cache for model responses (question -> response)
        self._response_cache: Dict[str, str] = {}
    
    def _load_training_history(self) -> None:
        """Load training history from file."""
        self.training_history: List[TrainingMetadata] = []
        if TRAINING_HISTORY_FILE.exists():
            try:
                with open(TRAINING_HISTORY_FILE) as f:
                    data = json.load(f)
                    self.training_history = [
                        TrainingMetadata(**item) for item in data.get("sessions", [])
                    ]
            except Exception as e:
                logger.warning(f"Could not load training history: {e}")
    
    def _load_models_metadata(self) -> None:
        """Load models metadata."""
        self.models_metadata: Dict[str, Dict] = {}
        if MODELS_METADATA_FILE.exists():
            try:
                with open(MODELS_METADATA_FILE) as f:
                    self.models_metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load models metadata: {e}")
    
    def _save_training_history(self) -> None:
        """Save training history to file."""
        try:
            with open(TRAINING_HISTORY_FILE, "w") as f:
                json.dump(
                    {"sessions": [m.to_dict() for m in self.training_history]},
                    f,
                    indent=2
                )
        except Exception as e:
            logger.error(f"Failed to save training history: {e}")
    
    def _save_models_metadata(self) -> None:
        """Save models metadata."""
        try:
            with open(MODELS_METADATA_FILE, "w") as f:
                json.dump(self.models_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save models metadata: {e}")
    
    def generate_model_response(self, question: str, model_name: str = "llama3", use_cache: bool = True, timeout: int = 30) -> str:
        """
        Generate model response via Ollama with caching and timeout.
        
        Args:
            question: Input question
            model_name: Model to use
            use_cache: Whether to use cached responses
            timeout: Timeout in seconds
        
        Returns:
            Model response (cached if available)
        """
        # Check cache first
        cache_key = f"{model_name}:{question}"
        if use_cache and cache_key in self._response_cache:
            logger.debug(f"Using cached response for: {question[:50]}...")
            return self._response_cache[cache_key]
        
        try:
            # Use stream=False for faster complete response (default)
            if OLLAMA_PKG_AVAILABLE:
                response = chat(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant. Provide clear, concise answers in 1-2 sentences."
                        },
                        {"role": "user", "content": question}
                    ],
                    stream=False,
                    options={
                        "num_predict": 100,  # Limit response length to 100 tokens for speed
                        "temperature": 0.7
                    }
                )
                result = response.message.content.strip()
            else:
                # Fallback to direct httpx call
                import httpx
                resp = httpx.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant. Provide clear, concise answers in 1-2 sentences."},
                            {"role": "user", "content": question}
                        ],
                        "stream": False,
                        "options": {"num_predict": 100, "temperature": 0.7}
                    },
                    timeout=60.0
                )
                resp.raise_for_status()
                result = resp.json().get("message", {}).get("content", "").strip()
            
            # Cache the result
            self._response_cache[cache_key] = result
            
            return result
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Unable to generate response. Error: {str(e)[:50]}"
    
    def train_single_example(
        self,
        question: str,
        ideal_answer: str,
        model_name: str = "llama3",
        quick_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Train on a single example (interactive training).
        
        Args:
            question: User question
            ideal_answer: Ideal answer
            model_name: Model to use
            quick_mode: If True, uses cached/shorter responses for speed
        
        Returns:
            Training result with model response and reward
        """
        try:
            # Validate inputs
            if not question.strip():
                raise ValueError("Question cannot be empty")
            if not ideal_answer.strip():
                raise ValueError("Ideal answer cannot be empty")
            
            # Generate model response (with caching in quick mode)
            logger.info(f"Generating response for: {question[:50]}...")
            model_response = self.generate_model_response(
                question, 
                model_name,
                use_cache=True  # Always use cache for speed
            )
            
            # ── Evaluate via /api/evaluate (LLM-based scoring) ───────────────
            reward_score = 0.0
            breakdown = {}
            eval_source = "api"

            try:
                eval_resp = httpx.post(
                    "http://localhost:8000/api/evaluate",
                    json={"response": model_response},
                    timeout=30.0
                )
                eval_resp.raise_for_status()
                eval_data = eval_resp.json()
                reward_score = float(eval_data.get("score", 0)) / 2.0  # Scale 1-10 → 0.5-5
                breakdown = {
                    "store":      eval_data.get("store", False),
                    "score":      eval_data.get("score", 0),
                    "type":       eval_data.get("type", "factual"),
                    "confidence": eval_data.get("confidence", 0.5),
                    "reason":     eval_data.get("reason", ""),
                }
                eval_source = "api_evaluate"
                logger.info(f"API evaluation: score={eval_data.get('score')}/10, store={eval_data.get('store')}")
            except Exception as e:
                # Fallback to keyword-based reward if evaluate endpoint isn't reachable
                logger.warning(f"⚠️ /api/evaluate unavailable, falling back to keyword scorer: {e}")
                reward_score, breakdown = self.reward_fn.calculate_reward_with_breakdown(
                    question, model_response, ideal_answer
                )
                eval_source = "keyword_fallback"

            result = {
                "success": True,
                "question": question,
                "ideal_answer": ideal_answer,
                "model_response": model_response,
                "reward_score": reward_score,
                "reward_breakdown": breakdown,
                "eval_source": eval_source,
                "timestamp": datetime.now().isoformat(),
                "model": model_name
            }
            
            logger.info(f"Training result: reward={reward_score}/5.0 (via {eval_source})")
            return result
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_training_history_summary(self) -> Dict[str, Any]:
        """Get summary of all training sessions."""
        if not self.training_history:
            return {"total_sessions": 0, "sessions": []}
        
        return {
            "total_sessions": len(self.training_history),
            "sessions": [m.to_dict() for m in sorted(
                self.training_history,
                key=lambda x: x.created_at,
                reverse=True
            )[:20]]  # Last 20 sessions
        }
    
    def get_model_comparison(self) -> Dict[str, Any]:
        """Compare all trained models."""
        comparison = {
            "models": [],
            "best_model": None,
            "best_avg_reward": 0.0
        }
        
        for model_name, metadata in self.models_metadata.items():
            avg_reward = metadata.get("average_reward", 0.0)
            comparison["models"].append({
                "name": model_name,
                "average_reward": avg_reward,
                "total_trainings": metadata.get("total_trainings", 0),
                "created_at": metadata.get("created_at", ""),
            })
            
            if avg_reward > comparison["best_avg_reward"]:
                comparison["best_avg_reward"] = avg_reward
                comparison["best_model"] = model_name
        
        return comparison
    
    def get_reward_analytics(self) -> Dict[str, Any]:
        """Get reward analytics across all trainings."""
        if not self.training_history:
            return {
                "average_reward": 0.0,
                "reward_distribution": {},
                "total_trainings": 0
            }
        
        rewards = [s.average_reward for s in self.training_history if s.average_reward > 0]
        
        if not rewards:
            return {
                "average_reward": 0.0,
                "reward_distribution": {},
                "total_trainings": 0
            }
        
        distribution = {}
        for s in self.training_history:
            if s.reward_distribution:
                for bucket, count in s.reward_distribution.items():
                    distribution[bucket] = distribution.get(bucket, 0) + count
        
        return {
            "average_reward": round(sum(rewards) / len(rewards), 2),
            "highest_reward": round(max(rewards), 2),
            "lowest_reward": round(min(rewards), 2),
            "total_trainings": len(self.training_history),
            "reward_distribution": distribution
        }
    
    def list_all_models(self) -> List[str]:
        """List all available models."""
        try:
            # Try to list models from Ollama
            import subprocess
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                models = [line.split()[0] for line in lines if line.strip()]
                return models
        except Exception as e:
            logger.warning(f"Could not list Ollama models: {e}")
        
        # Fallback to known models
        return ["llama3", "llama3_president_rlhf"]
    
    def export_training_data(self, format: str = "json") -> str:
        """Export training history in specified format."""
        if format == "json":
            return json.dumps({
                "sessions": [m.to_dict() for m in self.training_history]
            }, indent=2)
        elif format == "csv":
            # Simple CSV export
            lines = ["session_id,model_name,created_at,total_examples,average_reward,status"]
            for m in self.training_history:
                lines.append(
                    f'"{m.session_id}","{m.model_name}","{m.created_at}",'
                    f'{m.total_examples},{m.average_reward},"{m.status}"'
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global dashboard instance
dashboard = TrainingDashboard()
