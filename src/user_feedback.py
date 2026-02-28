"""
User Feedback System for AZAN
Collects user ratings, stores feedback, and adjusts RLHF rewards
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import statistics

logger = logging.getLogger(__name__)


class UserFeedback:
    """
    Manages user feedback, ratings, and RLHF reward adjustments
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize feedback system
        
        Args:
            data_dir: Directory to store feedback
        """
        self.data_dir = Path(data_dir)
        self.feedback_file = self.data_dir / "user_feedback.json"
        self.rewards_file = self.data_dir / "feedback_rewards.json"
        
        self.feedback = {}
        self.reward_adjustments = {}
        self._load_feedback()
        
        logger.info("✓ UserFeedback system initialized")
    
    def _load_feedback(self):
        """Load existing feedback"""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r') as f:
                    self.feedback = json.load(f)
                logger.info(f"Loaded {len(self.feedback)} feedback entries")
            except Exception as e:
                logger.error(f"Error loading feedback: {e}")
        
        if self.rewards_file.exists():
            try:
                with open(self.rewards_file, 'r') as f:
                    self.reward_adjustments = json.load(f)
            except:
                self.reward_adjustments = {}
    
    def _save_feedback(self):
        """Save feedback to file"""
        try:
            with open(self.feedback_file, 'w') as f:
                json.dump(self.feedback, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
    
    def _save_rewards(self):
        """Save reward adjustments"""
        try:
            with open(self.rewards_file, 'w') as f:
                json.dump(self.reward_adjustments, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving rewards: {e}")
    
    def submit_rating(self, 
                     interaction_id: str,
                     rating: int,
                     comment: str = "",
                     user_id: str = "anonymous") -> Dict:
        """
        Submit user rating for an interaction
        
        Args:
            interaction_id: Unique ID of the Q&A interaction
            rating: Rating 1-5 (1=bad, 5=excellent)
            comment: Optional user comment
            user_id: Optional user identifier
        
        Returns:
            Feedback record with ID
        """
        if not (1 <= rating <= 5):
            logger.error(f"Invalid rating: {rating}")
            return {"error": "Rating must be 1-5"}
        
        feedback_id = f"{interaction_id}_{datetime.now().timestamp()}"
        
        feedback_record = {
            "id": feedback_id,
            "interaction_id": interaction_id,
            "rating": rating,
            "comment": comment,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "helpful": rating >= 4
        }
        
        self.feedback[feedback_id] = feedback_record
        self._save_feedback()
        
        # Calculate reward adjustment
        self._calculate_reward_adjustment(interaction_id, rating)
        
        logger.info(f"✓ Feedback recorded: {interaction_id} rated {rating}/5")
        
        return feedback_record
    
    def _calculate_reward_adjustment(self, interaction_id: str, rating: int):
        """Calculate and store reward adjustment based on rating"""
        
        # Rating to reward mapping
        reward_map = {
            1: -0.5,  # Bad response
            2: -0.2,  # Poor
            3: 0.0,   # Neutral
            4: 0.5,   # Good
            5: 1.0    # Excellent
        }
        
        adjustment = reward_map.get(rating, 0.0)
        
        if interaction_id not in self.reward_adjustments:
            self.reward_adjustments[interaction_id] = {
                "adjustments": [],
                "average": 0.0,
                "count": 0
            }
        
        self.reward_adjustments[interaction_id]["adjustments"].append({
            "value": adjustment,
            "timestamp": datetime.now().isoformat()
        })
        
        # Calculate average
        adjustments = self.reward_adjustments[interaction_id]["adjustments"]
        average = statistics.mean([a["value"] for a in adjustments])
        self.reward_adjustments[interaction_id]["average"] = round(average, 3)
        self.reward_adjustments[interaction_id]["count"] = len(adjustments)
        
        self._save_rewards()
    
    def thumbs_up(self, interaction_id: str, user_id: str = "anonymous") -> Dict:
        """Quick thumbs-up rating"""
        return self.submit_rating(
            interaction_id=interaction_id,
            rating=5,
            comment="Thumbs up!",
            user_id=user_id
        )
    
    def thumbs_down(self, interaction_id: str, user_id: str = "anonymous") -> Dict:
        """Quick thumbs-down rating"""
        return self.submit_rating(
            interaction_id=interaction_id,
            rating=1,
            comment="Thumbs down",
            user_id=user_id
        )
    
    def get_feedback_for_interaction(self, interaction_id: str) -> List[Dict]:
        """Get all feedback for an interaction"""
        return [
            f for f in self.feedback.values()
            if f["interaction_id"] == interaction_id
        ]
    
    def get_reward_adjustment(self, interaction_id: str) -> Optional[Dict]:
        """Get reward adjustment for an interaction"""
        return self.reward_adjustments.get(interaction_id)
    
    def get_high_rated_responses(self, min_rating: int = 4) -> List[Dict]:
        """Get interactions with high average ratings for RLHF training"""
        high_rated = []
        
        for interaction_id, adjustments in self.reward_adjustments.items():
            if adjustments["average"] >= (min_rating - 1):  # Convert rating to adjustment scale
                high_rated.append({
                    "interaction_id": interaction_id,
                    "average_adjustment": adjustments["average"],
                    "count": adjustments["count"]
                })
        
        return sorted(high_rated, key=lambda x: x["average_adjustment"], reverse=True)
    
    def get_low_rated_responses(self, max_rating: int = 2) -> List[Dict]:
        """Get interactions with low ratings for improvement"""
        low_rated = []
        
        for interaction_id, adjustments in self.reward_adjustments.items():
            if adjustments["average"] <= -(max_rating - 1):
                low_rated.append({
                    "interaction_id": interaction_id,
                    "average_adjustment": adjustments["average"],
                    "count": adjustments["count"]
                })
        
        return sorted(low_rated, key=lambda x: x["average_adjustment"])
    
    def get_feedback_stats(self) -> Dict:
        """Get overall feedback statistics"""
        if not self.feedback:
            return {
                "total_ratings": 0,
                "average_rating": 0,
                "helpful_percentage": 0,
                "by_rating": {}
            }
        
        ratings = [f["rating"] for f in self.feedback.values()]
        helpful = sum(1 for f in self.feedback.values() if f["helpful"])
        
        by_rating = {}
        for i in range(1, 6):
            by_rating[i] = len([r for r in ratings if r == i])
        
        return {
            "total_ratings": len(ratings),
            "average_rating": round(statistics.mean(ratings), 2),
            "helpful_percentage": round((helpful / len(ratings) * 100), 1),
            "by_rating": by_rating,
            "recommendation": "good" if statistics.mean(ratings) >= 4 else "needs_improvement"
        }
    
    def get_rlhf_training_data(self, min_count: int = 2) -> Dict:
        """
        Prepare data for RLHF retraining
        Returns high and low-rated interactions
        """
        high_rated = self.get_high_rated_responses()
        low_rated = self.get_low_rated_responses()
        
        return {
            "high_rated": [h for h in high_rated if h["count"] >= min_count],
            "low_rated": [l for l in low_rated if l["count"] >= min_count],
            "ready_for_retraining": len(high_rated) >= 5 or len(low_rated) >= 5,
            "timestamp": datetime.now().isoformat()
        }


# Global feedback instance
_user_feedback = None


def initialize_feedback() -> UserFeedback:
    """Initialize and return global feedback system"""
    global _user_feedback
    if _user_feedback is None:
        _user_feedback = UserFeedback()
    return _user_feedback


def get_feedback() -> UserFeedback:
    """Get global feedback system"""
    global _user_feedback
    if _user_feedback is None:
        initialize_feedback()
    return _user_feedback
