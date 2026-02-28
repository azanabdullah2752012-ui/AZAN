"""
RSS Feed Integration with Inference Engine
Automatically injects real-time news into AZAN's context
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FeedContextInjector:
    """
    Injects relevant RSS feed articles into inference context
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize feed context injector
        
        Args:
            data_dir: Data directory
        """
        self.data_dir = Path(data_dir)
        logger.info("✓ FeedContextInjector initialized")
    
    def get_relevant_articles(self, 
                             query: str,
                             category: Optional[str] = None,
                             max_articles: int = 3,
                             hours_back: int = 24) -> List[Dict]:
        """
        Get articles relevant to a query
        
        Args:
            query: User query
            category: Optional category filter
            max_articles: Maximum articles to return
            hours_back: Only include articles from last N hours
        
        Returns:
            List of relevant articles
        """
        try:
            from src.semantic_search import get_semantic_search
            from src.rss_feed_integrator import get_feed_integrator
            
            # Try semantic search first
            search_engine = get_semantic_search()
            articles = search_engine.search(query, limit=max_articles*2, category=category)
            
            if articles:
                logger.info(f"✓ Found {len(articles)} articles via semantic search")
                return articles[:max_articles]
            
            # Fallback to recent articles
            feed_integrator = get_feed_integrator()
            recent = feed_integrator.get_recent_articles(category=category, limit=max_articles)
            
            if recent:
                logger.info(f"✓ Got {len(recent)} recent articles")
                return recent
            
            return []
        
        except Exception as e:
            logger.error(f"Error getting relevant articles: {e}")
            return []
    
    def build_context(self, 
                     query: str,
                     category: Optional[str] = None) -> str:
        """
        Build enhanced context with recent articles
        
        Args:
            query: User query
            category: Optional category filter
        
        Returns:
            Context string with article summaries
        """
        articles = self.get_relevant_articles(query, category=category, max_articles=3)
        
        if not articles:
            return ""
        
        context = "\n🔔 Recent News Context:\n"
        context += "=" * 50 + "\n"
        
        for i, article in enumerate(articles, 1):
            headline = article.get("headline", "Untitled")
            source = article.get("source", "Unknown")
            similarity = article.get("similarity", 0)
            
            context += f"\n{i}. [{source}] {headline}\n"
            context += f"   Relevance: {similarity*100:.0f}%\n"
        
        context += "\n" + "=" * 50 + "\n"
        
        return context
    
    def should_include_news_context(self, query: str) -> bool:
        """
        Determine if query should include news context
        
        Args:
            query: User query
        
        Returns:
            True if should include news context
        """
        # Keywords that suggest news context would be helpful
        news_keywords = [
            "news", "today", "recent", "latest", "current",
            "happening", "breaking", "update", "report", "says",
            "business", "tech", "science", "politics", "world",
            "sports", "entertainment", "national", "market", "stock"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in news_keywords)


class EnhancedContextManager:
    """
    Manages enhanced context combining knowledge base + feeds
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize enhanced context manager
        
        Args:
            data_dir: Data directory
        """
        self.data_dir = Path(data_dir)
        self.injector = FeedContextInjector(data_dir=data_dir)
        logger.info("✓ EnhancedContextManager initialized")
    
    def prepare_inference_context(self,
                                 query: str,
                                 knowledge_base: Optional[Dict] = None) -> Dict:
        """
        Prepare enhanced context for inference
        
        Args:
            query: User query
            knowledge_base: Optional base knowledge to include
        
        Returns:
            Dictionary with enhanced context
        """
        context = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "sources": []
        }
        
        # Add knowledge base if provided
        if knowledge_base:
            context["knowledge_base"] = knowledge_base
            context["sources"].append("knowledge_base")
        
        # Check if we should add news context
        if self.injector.should_include_news_context(query):
            news_context = self.injector.build_context(query)
            if news_context:
                context["news_context"] = news_context
                context["sources"].append("rss_feeds")
        
        # Add metadata
        context["has_news"] = "news_context" in context
        context["context_quality"] = "enhanced" if len(context["sources"]) > 1 else "base"
        
        return context
    
    def get_context_summary(self) -> Dict:
        """Get summary of available context sources"""
        try:
            from src.rss_feed_integrator import get_feed_integrator
            from src.rl_inference import get_inference
            
            feed_summary = get_feed_integrator().get_articles_summary()
            
            return {
                "articles_available": feed_summary["total_articles"],
                "by_category": feed_summary["by_category"],
                "last_updated": feed_summary["last_updated"],
                "context_sources": ["knowledge_base", "rss_feeds"]
            }
        except Exception as e:
            logger.error(f"Error getting context summary: {e}")
            return {"error": str(e)}


# Global injector instance
_context_injector = None
_context_manager = None


def initialize_feed_context_injector(data_dir: str = "data") -> FeedContextInjector:
    """Initialize global feed context injector"""
    global _context_injector
    if _context_injector is None:
        _context_injector = FeedContextInjector(data_dir=data_dir)
    return _context_injector


def initialize_context_manager(data_dir: str = "data") -> EnhancedContextManager:
    """Initialize global context manager"""
    global _context_manager
    if _context_manager is None:
        _context_manager = EnhancedContextManager(data_dir=data_dir)
    return _context_manager


def get_feed_context_injector() -> FeedContextInjector:
    """Get global feed context injector"""
    global _context_injector
    if _context_injector is None:
        initialize_feed_context_injector()
    return _context_injector


def get_context_manager() -> EnhancedContextManager:
    """Get global context manager"""
    global _context_manager
    if _context_manager is None:
        initialize_context_manager()
    return _context_manager
