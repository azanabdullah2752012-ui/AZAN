"""
Scheduler for automatic training on political topics.

Runs training jobs automatically on a schedule to keep the model
updated with current world political knowledge.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
import threading

from src.political_trainer import get_auto_trainer, AutoTrainer
from src.training_dashboard import dashboard

logger = logging.getLogger(__name__)

# Configuration
AUTO_TRAINING_CONFIG_PATH = Path("data") / "auto_training_config.json"
DEFAULT_CONFIG = {
    "enabled": True,
    "schedule_interval_minutes": 30,
    "examples_per_session": 5,
    "quick_mode": True,
    "topics_to_focus": [
        "Global Trade Relationships",
        "Climate Policy and International Action",
        "Democratic Institutions and Elections",
        "International Security and Conflicts"
    ]
}


class AutoTrainingScheduler:
    """Manages automatic scheduled training on political topics."""
    
    def __init__(self):
        self.trainer = get_auto_trainer()
        self.config = self._load_config()
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_training_time: Optional[datetime] = None
        self.training_count = 0
        self.next_training_time: Optional[datetime] = None
    
    def _load_config(self) -> dict:
        """Load auto-training configuration."""
        if AUTO_TRAINING_CONFIG_PATH.exists():
            try:
                with open(AUTO_TRAINING_CONFIG_PATH, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load auto-training config, using defaults")
                return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()
    
    def save_config(self, config: dict) -> None:
        """Save auto-training configuration."""
        AUTO_TRAINING_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUTO_TRAINING_CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        self.config = config
    
    def get_config(self) -> dict:
        """Get current auto-training configuration."""
        return self.config.copy()
    
    def update_config(self, updates: dict) -> dict:
        """Update auto-training configuration."""
        self.config.update(updates)
        self.save_config(self.config)
        return self.config
    
    def start(self) -> dict:
        """Start automatic training scheduler."""
        if self.is_running:
            return {
                "status": "already_running",
                "message": "Auto-training scheduler is already running"
            }
        
        if not self.config.get("enabled", True):
            return {
                "status": "disabled",
                "message": "Auto-training is disabled in configuration"
            }
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="AutoTrainingScheduler"
        )
        self.scheduler_thread.start()
        
        logger.info("Auto-training scheduler started")
        return {
            "status": "started",
            "message": "Auto-training scheduler has been started",
            "config": self.config
        }
    
    def stop(self) -> dict:
        """Stop automatic training scheduler."""
        if not self.is_running:
            return {
                "status": "not_running",
                "message": "Auto-training scheduler is not running"
            }
        
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Auto-training scheduler stopped")
        return {
            "status": "stopped",
            "message": "Auto-training scheduler has been stopped"
        }
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop running in background thread."""
        while self.is_running:
            try:
                self.next_training_time = datetime.now() + timedelta(
                    minutes=self.config.get("schedule_interval_minutes", 30)
                )
                
                # Perform training
                self._run_training_session()
                
                # Sleep until next scheduled time
                while self.is_running:
                    now = datetime.now()
                    if now >= self.next_training_time:
                        break
                    sleep_seconds = min(
                        (self.next_training_time - now).total_seconds(),
                        5  # Check every 5 seconds
                    )
                    if sleep_seconds > 0:
                        threading.Event().wait(sleep_seconds)
            
            except Exception as e:
                logger.error(f"Auto-training scheduler error: {e}")
                # Sleep before retrying
                threading.Event().wait(60)
    
    def _run_training_session(self) -> None:
        """Run a single training session by acquiring news and perfecting knowledge."""
        try:
            from src.inshorts_scraper import InshortsScraper
            from src.database import get_database
            
            scraper = InshortsScraper()
            db = get_database()
            
            # 1. Fetch latest news (knowledge acquisition)
            logger.info("AutoTraining: Scraping latest news...")
            new_articles_count = scraper.scrape_all_categories()
            
            # 2. Sync with SQLite and ChromaDB
            latest_articles = scraper.get_latest_articles(limit=new_articles_count or 10)
            for art in latest_articles:
                db.insert_article(art) # This triggers ChromaDB indexing as of Phase 3
                
            # 3. Generate training pairs from real news
            logger.info("AutoTraining: Generating training pairs...")
            new_pairs = scraper.convert_to_training_data(latest_articles)
            
            # 4. Perform RL training on a sample of new knowledge
            trained_count = 0
            total_reward = 0.0
            
            # Sample up to 5 pairs for this session
            sample_size = self.config.get("examples_per_session", 5)
            sample_pairs = random.sample(new_pairs, min(sample_size, len(new_pairs))) if new_pairs else []
            
            start_time = datetime.now()
            for pair in sample_pairs:
                try:
                    result = dashboard.train_single_example(
                        question=pair["question"],
                        ideal_answer=pair["ideal_answer"],
                        model_name="llama3",
                        quick_mode=self.config.get("quick_mode", True)
                    )
                    
                    if result.get("success"):
                        trained_count += 1
                        total_reward += result.get("reward_score", 0.0)
                except Exception as e:
                    logger.warning(f"Training failed on pair: {e}")
            
            # Log session results
            duration = (datetime.now() - start_time).total_seconds()
            avg_reward = round(total_reward / trained_count, 3) if trained_count > 0 else 0
            
            session_data = {
                "auto_training": True,
                "new_news_acquired": new_articles_count,
                "examples_trained": trained_count,
                "avg_reward": avg_reward,
                "duration_seconds": duration
            }
            
            self.trainer.log_training_session(session_data)
            self.training_count += 1
            self.last_training_time = datetime.now()
            
            logger.info(f"✓ Auto-training session #{self.training_count} complete. Avg Reward: {avg_reward}")
        
        except Exception as e:
            logger.error(f"Error during auto-training session: {e}")
    
    def get_status(self) -> dict:
        """Get current status of auto-training scheduler."""
        return {
            "is_running": self.is_running,
            "enabled": self.config.get("enabled", True),
            "total_sessions": self.training_count,
            "last_training": self.last_training_time.isoformat() if self.last_training_time else None,
            "next_training": self.next_training_time.isoformat() if self.next_training_time else None,
            "schedule_interval_minutes": self.config.get("schedule_interval_minutes", 30),
            "examples_per_session": self.config.get("examples_per_session", 5),
            "quick_mode": self.config.get("quick_mode", True),
            "focused_topics": self.config.get("topics_to_focus", [])
        }
    
    def trigger_manual_training(self, num_examples: Optional[int] = None) -> dict:
        """Trigger a manual auto-training session immediately."""
        try:
            num_examples = num_examples or self.config.get("examples_per_session", 5)
            
            start_time = datetime.now()
            all_pairs = self.trainer.get_training_pairs()
            
            # Filter by focused topics
            focused_topics = self.config.get("topics_to_focus", [])
            if focused_topics:
                pairs = [p for p in all_pairs if p.get("topic") in focused_topics]
            else:
                pairs = all_pairs
            
            sample_pairs = random.sample(pairs, min(num_examples, len(pairs)))
            
            trained_count = 0
            total_reward = 0.0
            
            for pair in sample_pairs:
                try:
                    result = dashboard.train_single_example(
                        question=pair["question"],
                        ideal_answer=pair["ideal_answer"],
                        model_name="llama3",
                        quick_mode=self.config.get("quick_mode", True)
                    )
                    
                    if result.get("success"):
                        trained_count += 1
                        total_reward += result.get("reward_score", 0.0)
                
                except Exception as e:
                    logger.warning(f"Training failed: {e}")
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "examples_trained": trained_count,
                "avg_reward": round(total_reward / trained_count, 3) if trained_count > 0 else 0,
                "duration_seconds": round(duration, 2)
            }
        
        except Exception as e:
            logger.error(f"Manual training error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
scheduler = AutoTrainingScheduler()


def get_scheduler() -> AutoTrainingScheduler:
    """Get the auto-training scheduler instance."""
    return scheduler
