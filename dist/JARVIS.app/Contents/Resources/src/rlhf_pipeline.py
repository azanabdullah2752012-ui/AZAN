"""
Reinforcement Learning from Human Feedback (RLHF) Pipeline
Retrains model based on user ratings and feedback
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import random
import threading
import time

logger = logging.getLogger(__name__)


class RLHFPipeline:
    """
    RLHF pipeline for continuous model improvement from user feedback
    """
    
    def __init__(self, 
                 data_dir: str = "data",
                 rl_pipeline = None,
                 user_feedback = None):
        """
        Initialize RLHF pipeline
        
        Args:
            data_dir: Data directory
            rl_pipeline: RLPipeline instance
            user_feedback: UserFeedback instance
        """
        self.data_dir = Path(data_dir)
        self.rl_pipeline = rl_pipeline
        self.user_feedback = user_feedback
        self.history_file = self.data_dir / "rlhf_history.json"
        
        self.history = {}
        self._load_history()
        
        logger.info("✓ RLHF Pipeline initialized")
    
    def _load_history(self):
        """Load RLHF training history"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                logger.info(f"Loaded RLHF history with {len(self.history)} entries")
            except Exception as e:
                logger.error(f"Error loading history: {e}")
    
    def _save_history(self):
        """Save RLHF history"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def collect_training_pairs_from_feedback(self) -> List[Dict]:
        """
        Collect high-quality training pairs from user feedback
        
        Returns:
            List of positive training examples from highly-rated responses
        """
        if not self.user_feedback:
            logger.warning("UserFeedback not available")
            return []
        
        training_pairs = []
        high_rated = self.user_feedback.get_high_rated_responses(min_rating=4)
        
        for item in high_rated:
            interaction_id = item["interaction_id"]
            
            # Try to find original Q&A pair
            # This would come from knowledge base or training data
            training_pairs.append({
                "interaction_id": interaction_id,
                "rating": item["average_adjustment"],
                "feedback_count": item["count"],
                "quality": "positive"
            })
        
        logger.info(f"✓ Collected {len(training_pairs)} positive training pairs from feedback")
        return training_pairs
    
    def identify_weak_responses(self) -> List[Dict]:
        """
        Identify responses with low ratings for targeted improvement
        
        Returns:
            List of responses needing improvement
        """
        if not self.user_feedback:
            return []
        
        low_rated = self.user_feedback.get_low_rated_responses(max_rating=2)
        
        weak_responses = []
        for item in low_rated:
            weak_responses.append({
                "interaction_id": item["interaction_id"],
                "rating": item["average_adjustment"],
                "feedback_count": item["count"],
                "quality": "negative"
            })
        
        logger.info(f"✓ Identified {len(weak_responses)} weak responses for improvement")
        return weak_responses
    
    def calculate_reward_adjustment(self, interaction_id: str) -> float:
        """
        Calculate final reward adjustment for interaction
        
        Args:
            interaction_id: ID of interaction
        
        Returns:
            Adjusted reward value
        """
        if not self.user_feedback:
            return 0.0
        
        adjustment_data = self.user_feedback.get_reward_adjustment(interaction_id)
        
        if adjustment_data:
            return adjustment_data["average"]
        
        return 0.0
    
    def ready_for_retraining(self) -> bool:
        """Check if enough feedback collected for retraining"""
        if not self.user_feedback:
            return False
        
        stats = self.user_feedback.get_feedback_stats()
        
        # Ready if we have enough ratings and sufficient feedback
        return (stats["total_ratings"] >= 10 and 
                stats["helpful_percentage"] >= 50)
    
    def prepare_retraining_data(self) -> Dict:
        """
        Prepare data for model retraining
        
        Returns:
            Dictionary with positive and negative examples
        """
        positive_examples = self.collect_training_pairs_from_feedback()
        negative_examples = self.identify_weak_responses()
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "positive_examples": positive_examples,
            "negative_examples": negative_examples,
            "total_examples": len(positive_examples) + len(negative_examples),
            "positive_ratio": len(positive_examples) / max(len(positive_examples) + len(negative_examples), 1)
        }
        
        return data
    
    def apply_feedback_to_training(self) -> Dict:
        """
        Apply user feedback to retrain RL model
        
        Returns:
            Retraining results
        """
        if not self.rl_pipeline or not self.user_feedback:
            return {"error": "RL Pipeline or UserFeedback not available"}
        
        logger.info("🔄 Starting RLHF retraining...")
        
        # Prepare data
        retraining_data = self.prepare_retraining_data()
        
        if retraining_data["total_examples"] < 5:
            logger.warning("Not enough feedback examples for retraining")
            return {"message": "Insufficient feedback", "examples": retraining_data["total_examples"]}
        
        # Get feedback adjustments
        feedback_stats = self.user_feedback.get_feedback_stats()
        
        # Create retraining event
        event = {
            "timestamp": datetime.now().isoformat(),
            "positive_examples": len(retraining_data["positive_examples"]),
            "negative_examples": len(retraining_data["negative_examples"]),
            "user_satisfaction": feedback_stats["helpful_percentage"],
            "avg_rating": feedback_stats["average_rating"]
        }
        
        # Store in history
        event_id = f"rlhf_{datetime.now().timestamp()}"
        self.history[event_id] = event
        self._save_history()
        
        logger.info(f"✓ RLHF retraining logged: {event_id}")
        
        return {
            "status": "success",
            "event_id": event_id,
            "training_data": retraining_data,
            "feedback_stats": feedback_stats
        }
    
    def get_improvement_metrics(self) -> Dict:
        """
        Get metrics showing model improvement from RLHF
        
        Returns:
            Improvement metrics
        """
        if not self.history:
            return {
                "total_retrainings": 0,
                "improvement_trend": "none"
            }
        
        events = sorted(self.history.values(), key=lambda x: x["timestamp"])
        
        metrics = {
            "total_retrainings": len(events),
            "last_retraining": events[-1]["timestamp"] if events else None,
            "user_satisfaction_trend": [],
            "average_rating_trend": []
        }
        
        for event in events[-10:]:  # Last 10 retrainings
            metrics["user_satisfaction_trend"].append(event["user_satisfaction"])
            metrics["average_rating_trend"].append(event["avg_rating"])
        
        # Calculate trend
        if len(metrics["user_satisfaction_trend"]) > 1:
            first = metrics["user_satisfaction_trend"][0]
            last = metrics["user_satisfaction_trend"][-1]
            trend = "improving" if last > first else "declining" if last < first else "stable"
            metrics["improvement_trend"] = trend
        
        return metrics
    
    def get_rlhf_status(self) -> Dict:
        """Get current RLHF status"""
        if not self.user_feedback:
            return {"status": "unavailable"}
        
        feedback_stats = self.user_feedback.get_feedback_stats()
        rlhf_data = self.user_feedback.get_rlhf_training_data()
        improvement = self.get_improvement_metrics()
        
        return {
            "status": "ready" if self.ready_for_retraining() else "collecting",
            "total_ratings": feedback_stats["total_ratings"],
            "average_rating": feedback_stats["average_rating"],
            "helpful_percentage": feedback_stats["helpful_percentage"],
            "ready_for_retraining": rlhf_data["ready_for_retraining"],
            "high_rated_count": len(rlhf_data["high_rated"]),
            "low_rated_count": len(rlhf_data["low_rated"]),
            "improvement_metrics": improvement
        }


class AutomatedRLHFScheduler:
    """
    Automatically triggers RLHF retraining on schedule
    """
    
    def __init__(self, rlhf_pipeline: RLHFPipeline, check_interval: int = 3600):
        """
        Initialize scheduler
        
        Args:
            rlhf_pipeline: RLHFPipeline instance
            check_interval: Seconds between retraining checks (default: 1 hour)
        """
        self.rlhf_pipeline = rlhf_pipeline
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        
        logger.info(f"✓ AutomatedRLHFScheduler initialized (interval: {check_interval}s)")
    
    def start(self):
        """Start automatic retraining scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.thread.start()
        logger.info("✓ RLHF scheduler started")
    
    def stop(self):
        """Stop scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ RLHF scheduler stopped")
    
    def _schedule_loop(self):
        """Background scheduling loop"""
        while self.running:
            try:
                if self.rlhf_pipeline.ready_for_retraining():
                    logger.info("📈 Triggering automatic RLHF retraining...")
                    result = self.rlhf_pipeline.apply_feedback_to_training()
                    logger.info(f"✓ RLHF retraining complete: {result}")
                
            except Exception as e:
                logger.error(f"Error in RLHF scheduler: {e}")
            
            time.sleep(self.check_interval)


# Global RLHF instances
_rlhf_pipeline = None
_rlhf_scheduler = None


def initialize_rlhf(rl_pipeline = None, user_feedback = None) -> RLHFPipeline:
    """Initialize global RLHF pipeline"""
    global _rlhf_pipeline
    if _rlhf_pipeline is None:
        _rlhf_pipeline = RLHFPipeline(rl_pipeline=rl_pipeline, user_feedback=user_feedback)
    return _rlhf_pipeline


def initialize_rlhf_scheduler(check_interval: int = 3600) -> AutomatedRLHFScheduler:
    """Initialize and start RLHF scheduler"""
    global _rlhf_scheduler
    if _rlhf_scheduler is None:
        rlhf = initialize_rlhf()
        _rlhf_scheduler = AutomatedRLHFScheduler(rlhf, check_interval=check_interval)
        _rlhf_scheduler.start()
    return _rlhf_scheduler


def get_rlhf() -> RLHFPipeline:
    """Get global RLHF pipeline"""
    global _rlhf_pipeline
    if _rlhf_pipeline is None:
        initialize_rlhf()
    return _rlhf_pipeline


def get_rlhf_scheduler() -> AutomatedRLHFScheduler:
    """Get global RLHF scheduler"""
    global _rlhf_scheduler
    if _rlhf_scheduler is None:
        initialize_rlhf_scheduler()
    return _rlhf_scheduler
