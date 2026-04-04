"""
User Feedback System for AZAN
Collects user ratings, stores feedback in SQLite, and adjusts RLHF rewards.
Migrated from JSON file storage to SQLite via DatabaseManager.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class UserFeedback:
    """
    Manages user feedback, ratings, and RLHF reward adjustments.
    Stores all data in the local SQLite database.
    """

    # Rating to reward adjustment mapping
    REWARD_MAP = {
        1: -0.5,  # Bad response
        2: -0.2,  # Poor
        3:  0.0,  # Neutral
        4:  0.5,  # Good
        5:  1.0,  # Excellent
    }

    def __init__(self, data_dir: str = "data"):
        """
        Initialize feedback system.
        On first run, migrates any existing JSON feedback into SQLite.
        """
        self.data_dir = Path(data_dir)
        self._legacy_feedback_file = self.data_dir / "user_feedback.json"
        self._legacy_rewards_file = self.data_dir / "feedback_rewards.json"

        # Import database lazily to avoid circular imports
        from src.database import get_database
        self.db = get_database()

        # One-time migration from legacy JSON files
        self._migrate_legacy_data()

        logger.info("✓ UserFeedback system initialized (SQLite backend)")

    def _migrate_legacy_data(self):
        """Migrate legacy JSON feedback data into SQLite (runs once)."""
        if not self._legacy_feedback_file.exists():
            return
        try:
            with open(self._legacy_feedback_file, "r") as f:
                legacy_data = json.load(f)

            migrated = 0
            for feedback_id, record in legacy_data.items():
                self.db.insert_feedback(
                    feedback_id=record.get("id", feedback_id),
                    interaction_id=record.get("interaction_id", ""),
                    rating=record.get("rating", 3),
                    comment=record.get("comment", ""),
                    user_id=record.get("user_id", "anonymous"),
                )
                migrated += 1

            # Rename legacy files so we don't re-migrate
            self._legacy_feedback_file.rename(
                self._legacy_feedback_file.with_suffix(".json.migrated")
            )
            if self._legacy_rewards_file.exists():
                self._legacy_rewards_file.rename(
                    self._legacy_rewards_file.with_suffix(".json.migrated")
                )
            logger.info(f"✓ Migrated {migrated} legacy feedback entries to SQLite")
        except Exception as e:
            logger.warning(f"Could not migrate legacy feedback: {e}")

    def submit_rating(
        self,
        interaction_id: str,
        rating: int,
        comment: str = "",
        user_id: str = "anonymous",
    ) -> Dict:
        """
        Submit user rating for an interaction.

        Args:
            interaction_id: Unique ID of the Q&A interaction
            rating: Rating 1-5 (1=bad, 5=excellent)
            comment: Optional user comment
            user_id: Optional user identifier

        Returns:
            Feedback record dict
        """
        if not (1 <= rating <= 5):
            logger.error(f"Invalid rating: {rating}")
            return {"error": "Rating must be 1-5"}

        feedback_id = f"{interaction_id}_{datetime.now().timestamp()}"

        self.db.insert_feedback(
            feedback_id=feedback_id,
            interaction_id=interaction_id,
            rating=rating,
            comment=comment,
            user_id=user_id,
        )

        logger.info(f"✓ Feedback recorded: {interaction_id} rated {rating}/5")

        return {
            "id": feedback_id,
            "interaction_id": interaction_id,
            "rating": rating,
            "comment": comment,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "helpful": rating >= 4,
        }

    def thumbs_up(self, interaction_id: str, user_id: str = "anonymous") -> Dict:
        """Quick thumbs-up rating"""
        return self.submit_rating(
            interaction_id=interaction_id,
            rating=5,
            comment="Thumbs up!",
            user_id=user_id,
        )

    def thumbs_down(self, interaction_id: str, user_id: str = "anonymous") -> Dict:
        """Quick thumbs-down rating"""
        return self.submit_rating(
            interaction_id=interaction_id,
            rating=1,
            comment="Thumbs down",
            user_id=user_id,
        )

    def get_feedback_for_interaction(self, interaction_id: str) -> List[Dict]:
        """Get all feedback for an interaction"""
        return self.db.get_feedback_for_interaction(interaction_id)

    def get_feedback_stats(self) -> Dict:
        """Get overall feedback statistics"""
        return self.db.get_feedback_stats()

    def get_reward_adjustment(self, interaction_id: str) -> Optional[Dict]:
        """Get reward adjustment for an interaction"""
        feedbacks = self.db.get_feedback_for_interaction(interaction_id)
        if not feedbacks:
            return None
        ratings = [f["rating"] for f in feedbacks]
        adjustments = [self.REWARD_MAP.get(r, 0.0) for r in ratings]
        import statistics
        return {
            "average": round(statistics.mean(adjustments), 3),
            "count": len(adjustments),
        }

    def get_high_rated_responses(self, min_rating: int = 4) -> List[Dict]:
        """Get interactions with high average ratings for RLHF training"""
        stats = self.db.get_feedback_stats()
        # Return summary-level info; detailed per-interaction filtering
        # would require a more complex query.
        return [{"average_rating": stats["average_rating"], "total": stats["total_ratings"]}]

    def get_rlhf_training_data(self, min_count: int = 2) -> Dict:
        """Prepare data summary for RLHF retraining"""
        stats = self.db.get_feedback_stats()
        return {
            "stats": stats,
            "ready_for_retraining": stats["total_ratings"] >= 5,
            "timestamp": datetime.now().isoformat(),
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
