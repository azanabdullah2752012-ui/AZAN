"""
Inshorts Continuous Trainer - Automatically trains AZAN with news data
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging
import threading
import time
from src.inshorts_scraper import InshortsScraper
from src.training_dashboard import dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InShortsTrainer:
    """Continuously trains AZAN with Inshorts news data"""
    
    def __init__(self):
        self.scraper = InshortsScraper()
        self.training_log_file = "data/inshorts_training_log.json"
        self.training_enabled = False
        self.training_thread = None
        self.scrape_interval = 300  # 5 minutes
        self.training_interval = 600  # 10 minutes
        self.last_scrape_time = None
        self.last_training_time = None
        self._load_training_log()
    
    def _load_training_log(self):
        """Load previous training sessions"""
        self.training_log = []
        if os.path.exists(self.training_log_file):
            try:
                with open(self.training_log_file, 'r') as f:
                    self.training_log = json.load(f)
            except:
                self.training_log = []
    
    def _save_training_log(self):
        """Save training session logs"""
        os.makedirs("data", exist_ok=True)
        with open(self.training_log_file, 'w') as f:
            json.dump(self.training_log, f, indent=2)
    
    def start_continuous_training(self, scrape_interval: int = 300, training_interval: int = 600):
        """Start continuous scraping and training in background"""
        
        if self.training_enabled:
            logger.warning("Training already enabled")
            return {"status": "error", "message": "Training already running"}
        
        self.scrape_interval = scrape_interval
        self.training_interval = training_interval
        self.training_enabled = True
        
        # Start background thread
        self.training_thread = threading.Thread(
            target=self._training_loop,
            daemon=True,
            name="InShortsTrainer"
        )
        self.training_thread.start()
        
        logger.info(f"✓ Started Inshorts training (scrape: {scrape_interval}s, train: {training_interval}s)")
        return {
            "status": "success",
            "message": "Continuous Inshorts training started",
            "scrape_interval": scrape_interval,
            "training_interval": training_interval
        }
    
    def stop_continuous_training(self):
        """Stop continuous training"""
        self.training_enabled = False
        logger.info("✓ Stopped continuous training")
        return {"status": "success", "message": "Training stopped"}
    
    def _training_loop(self):
        """Main training loop running in background"""
        scrape_counter = 0
        train_counter = 0
        
        logger.info("Starting Inshorts training loop...")
        
        while self.training_enabled:
            try:
                # Scrape news periodically
                if scrape_counter >= self.scrape_interval:
                    logger.info("🔄 Scraping Inshorts...")
                    try:
                        articles_count = self.scraper.scrape_all_categories()
                        self.last_scrape_time = datetime.now().isoformat()
                        logger.info(f"✓ Scrape complete: {len(self.scraper.scraped_articles)} total articles")
                    except Exception as e:
                        logger.error(f"Scraping error: {e}")
                    
                    scrape_counter = 0
                
                # Train on new data periodically
                if train_counter >= self.training_interval:
                    if len(self.scraper.scraped_articles) > 0:
                        logger.info("🎓 Training AZAN with latest news...")
                        trained_count = self.train_on_latest_news(max_articles=5)
                        
                        if trained_count > 0:
                            log_entry = {
                                "timestamp": datetime.now().isoformat(),
                                "articles_trained": trained_count,
                                "total_articles": len(self.scraper.scraped_articles),
                                "total_training_pairs": len(self.scraper.training_data)
                            }
                            self.training_log.append(log_entry)
                            self._save_training_log()
                            self.last_training_time = datetime.now().isoformat()
                            
                            logger.info(f"✓ Training complete: {trained_count} Q&A pairs trained")
                    
                    train_counter = 0
                
                scrape_counter += 10
                train_counter += 10
                time.sleep(10)  # Check every 10 seconds
            
            except Exception as e:
                logger.error(f"Error in training loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(30)
    
    def train_on_latest_news(self, max_articles: int = 3) -> int:
        """Train AZAN on latest news articles"""
        
        # Get latest articles
        articles = self.scraper.get_latest_articles(limit=max_articles)
        trained_count = 0
        
        for article in articles:
            try:
                # Generate training Q&A from article
                qa_pairs = self.scraper._generate_qa_from_article(article)
                
                for qa in qa_pairs:
                    try:
                        # Train with each Q&A pair
                        result = dashboard.train_single_example(
                            question=qa['question'],
                            ideal_answer=qa['ideal_answer'],
                            model_name="llama3",
                            quick_mode=True
                        )
                        
                        if result.get("success"):
                            trained_count += 1
                            logger.info(f"✓ Trained: {qa['question'][:50]}...")
                    
                    except Exception as e:
                        logger.warning(f"Failed to train Q&A: {e}")
                        continue
            
            except Exception as e:
                logger.warning(f"Failed to train news: {e}")
        
        # PERSIST updated knowledge base (with new claims and pairs)
        self.scraper._save_data()
        return trained_count
    
    def manual_scrape(self, category: Optional[str] = None) -> Dict:
        """Manually trigger a scrape"""
        if category:
            articles = self.scraper.scrape_category(category)
        else:
            articles_count = self.scraper.scrape_all_categories()
            articles = self.scraper.get_latest_articles(limit=10)
        
        # Convert to training data
        training_pairs = self.scraper.convert_to_training_data(articles)
        
        return {
            "status": "success",
            "articles_scraped": len(articles),
            "training_pairs_generated": len(training_pairs),
            "total_articles": len(self.scraper.scraped_articles),
            "total_training_pairs": len(self.scraper.training_data)
        }
    
    def get_training_status(self) -> Dict:
        """Get current training status"""
        return {
            "training_enabled": self.training_enabled,
            "scrape_interval_seconds": self.scrape_interval,
            "training_interval_seconds": self.training_interval,
            "total_articles_scraped": len(self.scraper.scraped_articles),
            "total_training_pairs": len(self.scraper.training_data),
            "training_sessions": len(self.training_log),
            "last_scrape": self.last_scrape_time,
            "last_training": self.last_training_time,
            "categories": self.scraper.categories,
            "articles_by_category": {
                cat: len(self.scraper.get_articles_by_category(cat))
                for cat in self.scraper.categories
            }
        }
    
    def get_latest_articles(self, limit: int = 10) -> List[Dict]:
        """Get latest scraped articles"""
        return self.scraper.get_latest_articles(limit=limit)
    
    def get_articles_by_category(self, category: str) -> List[Dict]:
        """Get articles from specific category"""
        return self.scraper.get_articles_by_category(category)


# Global instance
inshorts_trainer = InShortsTrainer()

def get_inshorts_trainer() -> InShortsTrainer:
    """Get the Inshorts trainer instance"""
    return inshorts_trainer
