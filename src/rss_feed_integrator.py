"""
Live RSS Feed Integrator for AZAN
Pulls real-time news from multiple sources and updates knowledge base
"""

import feedparser
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import threading
import time

logger = logging.getLogger(__name__)

# News sources configuration
RSS_FEEDS = {
    "business": [
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.cnbc.com/cnbc/intl_business/",
        "https://feeds.finance.yahoo.com/rss/business.xml"
    ],
    "technology": [
        "https://feeds.techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/feed/"
    ],
    "science": [
        "https://feeds.nature.com/nature/rss/current",
        "https://www.sciencenews.org/feed/",
        "https://phys.org/feeds/physics-news/"
    ],
    "politics": [
        "https://feeds.politico.com/playbook-pm.xml",
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://feeds.theguardian.com/theguardian/politics/rss"
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.theguardian.com/theguardian/world/rss",
        "https://feeds.reuters.com/reuters/worldNews"
    ],
    "sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://feeds.espn.com/espn/headlines",
        "https://sports.yahoo.com/rss/"
    ],
    "entertainment": [
        "https://feeds.bbci.co.uk/entertainment/rss.xml",
        "https://feeds.theguardian.com/theguardian/culture/rss",
        "https://variety.com/feed/"
    ],
    "national": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.theguardian.com/theguardian/uk/rss",
        "https://feeds.reuters.com/reuters/domesticNews"
    ]
}


class RSSFeedIntegrator:
    """
    Integrates live RSS feeds into AZAN's knowledge base
    """
    
    def __init__(self, data_dir: str = "data", max_articles_per_feed: int = 5):
        """
        Initialize RSS feed integrator
        
        Args:
            data_dir: Directory to store articles
            max_articles_per_feed: Maximum articles per feed per pull
        """
        self.data_dir = Path(data_dir)
        self.articles_file = self.data_dir / "live_articles.json"
        self.feed_cache_file = self.data_dir / "feed_cache.json"
        self.max_articles = max_articles_per_feed
        
        self.articles = {}
        self.feed_cache = {}
        self._load_cache()
        
        logger.info("✓ RSSFeedIntegrator initialized")
    
    def _load_cache(self):
        """Load existing articles and cache"""
        if self.articles_file.exists():
            try:
                with open(self.articles_file, 'r') as f:
                    self.articles = json.load(f)
                logger.info(f"Loaded {len(self.articles)} existing articles")
            except Exception as e:
                logger.error(f"Error loading articles: {e}")
        
        if self.feed_cache_file.exists():
            try:
                with open(self.feed_cache_file, 'r') as f:
                    self.feed_cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.feed_cache = {}
        else:
            self._save_cache()  # Initialize cache file on first run
    
    def _save_articles(self):
        """Save articles to file"""
        try:
            with open(self.articles_file, 'w') as f:
                json.dump(self.articles, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving articles: {e}")
    
    def _save_cache(self):
        """Save feed cache"""
        try:
            with open(self.feed_cache_file, 'w') as f:
                json.dump(self.feed_cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def fetch_feed(self, feed_url: str, category: str) -> List[Dict]:
        """
        Fetch articles from single RSS feed
        
        Args:
            feed_url: URL of RSS feed
            category: Article category
        
        Returns:
            List of articles
        """
        articles = []
        try:
            # Parse feed with timeout
            feed = feedparser.parse(feed_url)
            
            if feed.status != 200 or feed.bozo != 0:
                logger.warning(f"Feed returned status {feed.status}")
                return articles
            
            # Extract articles
            for entry in feed.entries[:self.max_articles]:
                article = {
                    "id": entry.get('id', entry.get('link', f"{feed_url}-{len(articles)}")),
                    "headline": entry.get('title', 'Untitled'),
                    "body": entry.get('summary', '')[:500],
                    "source": feed.feed.get('title', 'Unknown Source'),
                    "category": category,
                    "published": entry.get('published', datetime.now().isoformat()),
                    "link": entry.get('link', ''),
                    "timestamp": datetime.now().isoformat()
                }
                articles.append(article)
            
            logger.info(f"✓ Fetched {len(articles)} articles from {feed_url[:50]}...")
            
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
        
        return articles
    
    def update_all_feeds(self) -> Dict[str, int]:
        """
        Update all RSS feeds
        
        Returns:
            Dictionary with counts of new articles per category
        """
        results = {}
        
        for category, feed_urls in RSS_FEEDS.items():
            new_count = 0
            
            for feed_url in feed_urls:
                articles = self.fetch_feed(feed_url, category)
                
                for article in articles:
                    article_id = article['id']
                    if article_id not in self.articles:
                        self.articles[article_id] = article
                        new_count += 1
            
            results[category] = new_count
            logger.info(f"Category '{category}': Added {new_count} new articles")
        
        # Save to file
        self._save_articles()
        self._save_cache()
        
        return results
    
    def get_recent_articles(self, category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get recent articles, optionally filtered by category
        
        Args:
            category: Optional category filter
            limit: Maximum articles to return
        
        Returns:
            List of recent articles
        """
        articles = list(self.articles.values())
        
        # Filter by category
        if category:
            articles = [a for a in articles if a.get('category') == category]
        
        # Sort by timestamp (newest first)
        articles.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return articles[:limit]
    
    def get_articles_summary(self) -> Dict:
        """Get summary of loaded articles"""
        by_category = {}
        for article in self.articles.values():
            cat = article.get('category', 'unknown')
            by_category[cat] = by_category.get(cat, 0) + 1
        
        return {
            "total_articles": len(self.articles),
            "by_category": by_category,
            "last_updated": max([a.get('timestamp', '') for a in self.articles.values()]) if self.articles else None
        }


class AutomatedFeedUpdater:
    """
    Automatically updates feeds on a schedule
    """
    
    def __init__(self, integrator: RSSFeedIntegrator, update_interval: int = 900):
        """
        Initialize feed updater
        
        Args:
            integrator: RSSFeedIntegrator instance
            update_interval: Seconds between updates (default: 15 minutes)
        """
        self.integrator = integrator
        self.update_interval = update_interval
        self.updating = False
        self.thread = None
        
        logger.info(f"✓ AutomatedFeedUpdater initialized (interval: {update_interval}s)")
    
    def start_updates(self):
        """Start automatic feed updates"""
        if self.updating:
            logger.warning("Feed updater already running")
            return
        
        self.updating = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info("✓ Feed updater started")
    
    def stop_updates(self):
        """Stop automatic feed updates"""
        self.updating = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ Feed updater stopped")
    
    def _update_loop(self):
        """Background update loop"""
        while self.updating:
            try:
                logger.info("🔄 Updating all RSS feeds...")
                results = self.integrator.update_all_feeds()
                
                total_new = sum(results.values())
                logger.info(f"✓ Feed update complete: {total_new} new articles added")
                
                # Log per category
                for cat, count in results.items():
                    if count > 0:
                        logger.info(f"  • {cat}: +{count} articles")
                
            except Exception as e:
                logger.error(f"Error in feed update loop: {e}")
            
            # Wait for next update
            time.sleep(self.update_interval)


# Global integrator instance
_feed_integrator = None
_feed_updater = None


def initialize_feed_integrator(data_dir: str = "data") -> RSSFeedIntegrator:
    """Initialize and return global feed integrator"""
    global _feed_integrator
    if _feed_integrator is None:
        _feed_integrator = RSSFeedIntegrator(data_dir=data_dir)
    return _feed_integrator


def initialize_feed_updater(update_interval: int = 900) -> AutomatedFeedUpdater:
    """Initialize and return global feed updater"""
    global _feed_updater
    if _feed_updater is None:
        integrator = initialize_feed_integrator()
        _feed_updater = AutomatedFeedUpdater(integrator, update_interval=update_interval)
        _feed_updater.start_updates()
    return _feed_updater


def get_feed_integrator() -> RSSFeedIntegrator:
    """Get global feed integrator"""
    global _feed_integrator
    if _feed_integrator is None:
        initialize_feed_integrator()
    return _feed_integrator


def get_feed_updater() -> AutomatedFeedUpdater:
    """Get global feed updater"""
    global _feed_updater
    if _feed_updater is None:
        initialize_feed_updater()
    return _feed_updater
