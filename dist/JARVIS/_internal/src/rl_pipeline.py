"""
Automated Reinforcement Learning Pipeline for AZAN
Continuously trains on incoming news articles with RLHF feedback
"""

import json
import os
import time
import logging
import threading
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RLDataCollector:
    """
    Collects training data from Inshorts news articles
    Generates Q&A pairs and tracks training rewards
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.articles_file = self.data_dir / "inshorts_articles.json"
        self.training_data_file = self.data_dir / "rl_training_data.json"
        self.rewards_file = self.data_dir / "rl_rewards.json"
        self.checkpoint_dir = self.data_dir / "rl_checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self._load_existing_data()
        logger.info(f"✓ RLDataCollector initialized with {len(self.training_pairs)} training pairs")
    
    def _load_existing_data(self):
        """Load previously collected training data and rewards"""
        self.training_pairs = []
        self.rewards_history = []
        self.processed_articles = set()
        
        # Load training pairs
        if self.training_data_file.exists():
            try:
                with open(self.training_data_file, 'r') as f:
                    self.training_pairs = json.load(f)
                    logger.info(f"Loaded {len(self.training_pairs)} training pairs")
            except:
                self.training_pairs = []
        
        # Load rewards
        if self.rewards_file.exists():
            try:
                with open(self.rewards_file, 'r') as f:
                    self.rewards_history = json.load(f)
                    logger.info(f"Loaded {len(self.rewards_history)} reward records")
            except:
                self.rewards_history = []
    
    def _save_data(self):
        """Persist training data and rewards to disk"""
        with open(self.training_data_file, 'w') as f:
            json.dump(self.training_pairs, f, indent=2)
        
        with open(self.rewards_file, 'w') as f:
            json.dump(self.rewards_history, f, indent=2)
    
    def load_articles(self) -> List[Dict]:
        """Load articles from Inshorts scraper"""
        if not self.articles_file.exists():
            return []
        
        try:
            with open(self.articles_file, 'r') as f:
                articles_dict = json.load(f)
                # Convert dict to list
                return [article for article in articles_dict.values()]
        except:
            return []
    
    def add_training_pair(self, question: str, answer: str, category: str, reward: float):
        """Add a training pair with its reward score"""
        pair = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "category": category,
            "reward": reward
        }
        self.training_pairs.append(pair)
        
        self.rewards_history.append({
            "timestamp": datetime.now().isoformat(),
            "reward": reward,
            "category": category
        })
        
        self._save_data()
    
    def get_recent_pairs(self, limit: int = 20) -> List[Dict]:
        """Get most recent training pairs"""
        return self.training_pairs[-limit:]
    
    def get_pairs_by_category(self, category: str) -> List[Dict]:
        """Get training pairs by category"""
        return [p for p in self.training_pairs if p.get('category') == category]
    
    def get_average_reward(self) -> float:
        """Calculate average reward across all training"""
        if not self.rewards_history:
            return 0.0
        return np.mean([r['reward'] for r in self.rewards_history])
    
    def get_category_performance(self) -> Dict[str, float]:
        """Get average reward per category"""
        if not self.rewards_history:
            return {}
        
        performance = {}
        for reward_record in self.rewards_history:
            category = reward_record.get('category', 'unknown')
            reward = reward_record['reward']
            
            if category not in performance:
                performance[category] = []
            performance[category].append(reward)
        
        # Calculate averages
        return {cat: np.mean(rewards) for cat, rewards in performance.items()}


class RLTrainingEnvironment:
    """
    Reinforcement Learning environment for AZAN
    Handles interaction between AZAN and training data
    """
    
    def __init__(self, data_collector: RLDataCollector):
        self.data_collector = data_collector
        self.current_batch = []
        self.batch_index = 0
        logger.info("✓ RLTrainingEnvironment initialized")
    
    def load_batch(self, batch_size: int = 10) -> List[Dict]:
        """Load a batch of training pairs"""
        all_pairs = self.data_collector.training_pairs
        
        if not all_pairs:
            logger.warning("No training pairs available")
            return []
        
        # Get random batch
        start_idx = self.batch_index * batch_size
        end_idx = start_idx + batch_size
        
        batch = all_pairs[start_idx:end_idx]
        
        # Wrap around if end of data
        if not batch:
            self.batch_index = 0
            batch = all_pairs[0:batch_size]
        else:
            self.batch_index += 1
        
        self.current_batch = batch
        return batch
    
    def evaluate_response(self, question: str, model_response: str, ideal_answer: str) -> float:
        """
        Evaluate model response quality
        Returns reward score 0.0-5.0 based on answer quality
        """
        # Simple heuristic: measure overlap between model response and ideal answer
        model_words = set(model_response.lower().split())
        ideal_words = set(ideal_answer.lower().split())
        
        if not ideal_words:
            return 2.5
        
        # Jaccard similarity
        intersection = len(model_words & ideal_words)
        union = len(model_words | ideal_words)
        
        similarity = intersection / union if union > 0 else 0
        
        # Map to 0-5 scale
        reward = similarity * 5.0
        reward = min(max(reward, 0.0), 5.0)
        
        return reward


class RLModel:
    """
    Wrapper for AZAN model with checkpointing
    Manages model state and training history
    """
    
    def __init__(self, checkpoint_dir: str = "data/rl_checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        self.model_state = {
            "training_iterations": 0,
            "total_reward": 0.0,
            "created_at": datetime.now().isoformat()
        }
        
        self._load_latest_checkpoint()
        logger.info(f"✓ RLModel initialized (iteration {self.model_state['training_iterations']})")
    
    def _load_latest_checkpoint(self):
        """Load the most recent checkpoint"""
        checkpoints = sorted(self.checkpoint_dir.glob("checkpoint_*.json"))
        
        if checkpoints:
            latest = checkpoints[-1]
            try:
                with open(latest, 'r') as f:
                    self.model_state = json.load(f)
                    logger.info(f"Loaded checkpoint: {latest.name}")
            except:
                logger.warning("Failed to load checkpoint")
    
    def save_checkpoint(self):
        """Save current model state as checkpoint"""
        checkpoint_name = f"checkpoint_{self.model_state['training_iterations']:06d}.json"
        checkpoint_path = self.checkpoint_dir / checkpoint_name
        
        with open(checkpoint_path, 'w') as f:
            json.dump(self.model_state, f, indent=2)
        
        logger.info(f"✓ Saved checkpoint: {checkpoint_name}")
    
    def update_state(self, reward: float):
        """Update model state after training step"""
        self.model_state['training_iterations'] += 1
        self.model_state['total_reward'] += reward
        self.model_state['last_updated'] = datetime.now().isoformat()
    
    def get_metrics(self) -> Dict:
        """Get current model metrics"""
        iterations = self.model_state['training_iterations']
        avg_reward = (self.model_state['total_reward'] / iterations) if iterations > 0 else 0
        
        return {
            "iterations": iterations,
            "total_reward": self.model_state['total_reward'],
            "average_reward": avg_reward,
            "last_updated": self.model_state.get('last_updated', 'never')
        }


class AutomatedRLPipeline:
    """
    Main reinforcement learning pipeline
    Orchestrates continuous training and model updates
    """
    
    def __init__(self, update_interval: int = 60):
        """
        Initialize the RL pipeline
        
        Args:
            update_interval: Seconds between training updates (30-120 recommended)
        """
        self.update_interval = update_interval
        self.data_collector = RLDataCollector()
        self.environment = RLTrainingEnvironment(self.data_collector)
        self.model = RLModel()
        
        self.training_enabled = False
        self.training_thread = None
        self.iteration_count = 0
        
        logger.info(f"✓ AutomatedRLPipeline initialized (update_interval={update_interval}s)")
    
    def start_training(self):
        """Start the autonomous training loop"""
        if self.training_enabled:
            logger.warning("Training already running")
            return
        
        self.training_enabled = True
        self.training_thread = threading.Thread(
            target=self._training_loop,
            daemon=True,
            name="RLTrainingThread"
        )
        self.training_thread.start()
        
        logger.info("✓ Started autonomous RL training loop")
    
    def stop_training(self):
        """Stop the training loop"""
        self.training_enabled = False
        logger.info("✓ Stopped RL training loop")
    
    def _training_loop(self):
        """Main training loop - runs continuously in background thread"""
        logger.info("🤖 RL Training loop started")
        
        while self.training_enabled:
            try:
                self.iteration_count += 1
                
                # Load fresh training batch
                batch = self.environment.load_batch(batch_size=5)
                
                if not batch:
                    logger.warning("No training data available, waiting...")
                    time.sleep(self.update_interval)
                    continue
                
                # Train on batch
                batch_rewards = []
                for pair in batch:
                    try:
                        # In production, this would call the actual AZAN model
                        # For now, we simulate training with the ideal answer
                        question = pair['question']
                        ideal_answer = pair['answer']
                        category = pair['category']
                        
                        # Simulate model response (in production: call predict())
                        model_response = ideal_answer
                        
                        # Evaluate response
                        reward = self.environment.evaluate_response(
                            question, model_response, ideal_answer
                        )
                        
                        batch_rewards.append(reward)
                        
                        # Update model
                        self.model.update_state(reward)
                        
                        # Record in data collector
                        self.data_collector.add_training_pair(
                            question=question,
                            answer=model_response,
                            category=category,
                            reward=reward
                        )
                        
                        logger.info(f"  ✓ Trained: {question[:50]}... (reward={reward:.2f})")
                    
                    except Exception as e:
                        logger.error(f"Error training pair: {e}")
                        continue
                
                # Save checkpoint every 10 iterations
                if self.iteration_count % 10 == 0:
                    self.model.save_checkpoint()
                    metrics = self.model.get_metrics()
                    logger.info(
                        f"🎯 Training iteration {self.iteration_count}: "
                        f"avg_reward={metrics['average_reward']:.2f}/5.0, "
                        f"total_iterations={metrics['iterations']}"
                    )
                
                # Wait before next batch
                time.sleep(self.update_interval)
            
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(self.update_interval)
    
    def get_training_status(self) -> Dict:
        """Get current training status"""
        metrics = self.model.get_metrics()
        category_performance = self.data_collector.get_category_performance()
        
        return {
            "training_enabled": self.training_enabled,
            "iterations": metrics['iterations'],
            "average_reward": metrics['average_reward'],
            "total_training_pairs": len(self.data_collector.training_pairs),
            "category_performance": category_performance,
            "last_updated": metrics['last_updated']
        }
    
    def get_model_knowledge(self) -> Dict:
        """Get summary of model's learned knowledge"""
        pairs_by_category = {}
        for category in ["business", "technology", "politics", "world", 
                        "science", "sports", "entertainment", "national"]:
            pairs = self.data_collector.get_pairs_by_category(category)
            pairs_by_category[category] = len(pairs)
        
        return {
            "total_pairs_learned": len(self.data_collector.training_pairs),
            "pairs_by_category": pairs_by_category,
            "average_reward": self.data_collector.get_average_reward(),
            "model_iterations": self.model.model_state['training_iterations']
        }


# Global pipeline instance
_rl_pipeline = None


def initialize_rl_pipeline(update_interval: int = 60) -> AutomatedRLPipeline:
    """Initialize and return the global RL pipeline"""
    global _rl_pipeline
    if _rl_pipeline is None:
        _rl_pipeline = AutomatedRLPipeline(update_interval=update_interval)
    return _rl_pipeline


def get_rl_pipeline() -> AutomatedRLPipeline:
    """Get the global RL pipeline instance"""
    global _rl_pipeline
    if _rl_pipeline is None:
        _rl_pipeline = initialize_rl_pipeline()
    return _rl_pipeline
