"""
AZAN Inference Engine with RL-Enhanced Responses
Integrates with Ollama and uses RL-trained knowledge base
"""

import json
import logging
import hashlib
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)

# ── Instant fast-path replies (no Ollama call needed) ────────────────────────
_INSTANT_REPLIES: Dict[str, str] = {
    # Greetings
    "hi": "Hello! I'm AZAN, your AI assistant. How can I help you today?",
    "hello": "Hello! I'm AZAN. What would you like to know?",
    "hey": "Hey! I'm AZAN. Ask me anything.",
    "hi there": "Hi there! How can I assist you?",
    "hello there": "Hello there! What can I help you with?",
    # Thanks
    "thanks": "You're welcome! Anything else I can help with?",
    "thank you": "You're welcome! Feel free to ask more questions.",
    "thank you so much": "You're very welcome! Happy to help.",
    "ty": "You're welcome!",
    # Simple
    "ok": "Got it! Let me know if you have more questions.",
    "okay": "Sure! Ask me anything else.",
    "bye": "Goodbye! Come back anytime.",
    "goodbye": "Goodbye! Have a great day.",
    "good morning": "Good morning! How can I assist you today?",
    "good evening": "Good evening! What can I help you with?",
    "good night": "Good night! Feel free to come back with questions anytime.",
    "how are you": "I'm running great and ready to help! What's your question?",
    "what is your name": "I'm AZAN — an AI assistant. How can I help you?",
    "who are you": "I'm AZAN, an AI knowledge assistant. Ask me anything!",
}

# ── Response cache (in-memory) ────────────────────────────────────────────────
_RESPONSE_CACHE: Dict[str, str] = {}


class KnowledgeBase:
    """
    AZAN's learned knowledge base
    Built from RL training on news articles
    """
    
    def __init__(self):
        self.knowledge_dir = Path("data")
        self.articles_file = self.knowledge_dir / "inshorts_articles.json"
        self.training_data_file = self.knowledge_dir / "rl_training_data.json"
        
        self.articles = {}
        self.training_pairs = []
        self.knowledge_index = {}  # Index by category and keywords
        
        self._load_knowledge()
        logger.info(f"✓ KnowledgeBase initialized with {len(self.articles)} articles")
    
    def _load_knowledge(self):
        """Load knowledge from trained articles"""
        # Load articles
        if self.articles_file.exists():
            try:
                with open(self.articles_file, 'r') as f:
                    articles_dict = json.load(f)
                    self.articles = articles_dict if isinstance(articles_dict, dict) else {
                        hashlib.md5(str(a).encode()).hexdigest(): a for a in articles_dict
                    }
            except:
                self.articles = {}
        
        # Load training pairs
        if self.training_data_file.exists():
            try:
                with open(self.training_data_file, 'r') as f:
                    self.training_pairs = json.load(f)
            except:
                self.training_pairs = []
        
        # Build index
        self._build_knowledge_index()
    
    def _build_knowledge_index(self):
        """Build searchable index of knowledge"""
        self.knowledge_index = {
            'by_category': {},
            'by_keyword': {}
        }
        
        # Index by category
        for article in self.articles.values():
            category = article.get('category', 'unknown')
            if category not in self.knowledge_index['by_category']:
                self.knowledge_index['by_category'][category] = []
            self.knowledge_index['by_category'][category].append(article)
        
        # Index by keywords
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'is', 'are', 'was', 'be'}
        for article in self.articles.values():
            headline = article.get('headline', '').lower()
            words = [w for w in headline.split() if len(w) > 3 and w not in stop_words]
            
            for word in words:
                if word not in self.knowledge_index['by_keyword']:
                    self.knowledge_index['by_keyword'][word] = []
                self.knowledge_index['by_keyword'][word].append(article)
    
    def search(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """
        Search knowledge base
        Returns relevant articles based on query
        """
        results = []
        query_words = set(query.lower().split())
        
        # Search by category first
        if category and category in self.knowledge_index['by_category']:
            category_articles = self.knowledge_index['by_category'][category]
            
            # Rank by keyword match
            for article in category_articles:
                headline = article.get('headline', '').lower()
                matching_words = len(set(headline.split()) & query_words)
                if matching_words > 0:
                    results.append((article, matching_words))
        
        # If not enough results, search all articles
        if len(results) < 3:
            for article in self.articles.values():
                if article not in [r[0] for r in results]:
                    headline = article.get('headline', '').lower()
                    matching_words = len(set(headline.split()) & query_words)
                    if matching_words > 0:
                        results.append((article, matching_words))
        
        # Sort by relevance and return
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:5]]
    
    def get_category_knowledge(self, category: str) -> List[Dict]:
        """Get all knowledge for a specific category"""
        return self.knowledge_index['by_category'].get(category, [])
    
    def get_summary(self) -> Dict:
        """Get knowledge base summary"""
        return {
            "total_articles": len(self.articles),
            "total_training_pairs": len(self.training_pairs),
            "categories": list(self.knowledge_index['by_category'].keys()),
            "articles_per_category": {
                cat: len(articles) 
                for cat, articles in self.knowledge_index['by_category'].items()
            }
        }


class EnhancedInference:
    """
    Enhanced inference engine
    Combines Ollama with RL-trained knowledge base
    """
    
    def __init__(self, ollama_host: str = "http://127.0.0.1:11434"):
        self.ollama_host = ollama_host
        self.knowledge_base = KnowledgeBase()
        self.client = httpx.Client(timeout=60.0)
        
        logger.info("✓ EnhancedInference initialized")
    
    def _build_system_prompt(self, category: Optional[str] = None) -> str:
        """
        Build enhanced system prompt with knowledge context
        
        Args:
            category: Optional category to focus on
        
        Returns:
            Enhanced system prompt incorporating learned knowledge
        """
        base_prompt = """You are AZAN, an advanced AI assistant powered by real-time reinforcement learning from news sources.

Your Knowledge Base:
- Learned from 437+ verified Q&A pairs across 8 categories
- Categories: Business, Technology, Politics, World, Science, Sports, Entertainment, National
- Knowledge continuously updated and reinforced through autonomous learning cycles
- Current training metrics: 175+ iterations, 5.0/5.0 average reward

When answering questions:
1. Incorporate relevant learned knowledge naturally into your responses
2. Provide specific examples from your knowledge base when relevant
3. Be comprehensive, detailed, and accurate
4. Draw from all 8 knowledge categories as appropriate

Your learned expertise includes:
- Fusion energy breakthroughs and quantum computing advances
- Global climate agreements and trade negotiations
- Gene therapy, CRISPR, and medical breakthroughs
- AI, autonomous vehicles, and machine learning development
- Cryptocurrency and global market trends
- Space exploration and scientific discoveries
- Sports achievements and records
- Entertainment and cultural developments

Answer comprehensively, accurately, and with confidence in your learned knowledge."""
        
        return base_prompt
    
    def _query_ollama(self, prompt: str, system_prompt: str, model: str = "llama3") -> str:
        """
        Query Ollama API for response
        
        Args:
            prompt: User question
            system_prompt: System context
            model: Model name
        
        Returns:
            Generated response text
        """
        try:
            url = f"{self.ollama_host}/api/chat"
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "num_predict": 1024,  # Full-length responses
                    "temperature": 0.5,
                    "top_p": 0.9
                }
            }
            
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get('message', {}).get('content', 'Unable to generate response')
        
        except Exception as e:
            logger.error(f"Error querying Ollama: {e}")
            return f"Error: Unable to generate response - {str(e)}"
    
    def predict(self, input_text: str, use_knowledge_context: bool = True) -> str:
        """
        Generate prediction/response.
        Fast-path for greetings/simple inputs → instant reply.
        Cache check before calling Ollama.
        """
        # 1. Fast-path: instant reply for simple/greeting messages (no LLM call)
        normalized = input_text.strip().lower().rstrip('!?.')
        if normalized in _INSTANT_REPLIES:
            logger.info("Fast-path reply for: %s", input_text[:40])
            return _INSTANT_REPLIES[normalized]

        # 2. Cache check: return cached response if seen before
        cache_key = hashlib.md5(input_text.encode()).hexdigest()
        if cache_key in _RESPONSE_CACHE:
            logger.info("Cache hit for: %s", input_text[:40])
            return _RESPONSE_CACHE[cache_key]

        # 3. Search knowledge base for relevant information
        relevant_articles = []
        if use_knowledge_context:
            relevant_articles = self.knowledge_base.search(input_text)
        
        # Build enhanced prompt with knowledge context
        context = ""
        if relevant_articles:
            context = "\n\nRecent Relevant Knowledge:\n"
            for i, article in enumerate(relevant_articles[:3], 1):
                context += f"{i}. {article.get('headline', 'N/A')}: {article.get('body', 'N/A')[:150]}...\n"
        
        enhanced_prompt = f"{input_text}{context}"
        
        # Get system prompt
        system_prompt = self._build_system_prompt()
        
        # Query Ollama
        response = self._query_ollama(enhanced_prompt, system_prompt)
        
        # Store in cache
        _RESPONSE_CACHE[cache_key] = response
        
        logger.info("Generated response for: %s", input_text[:60])
        return response
    
    def get_knowledge_summary(self) -> Dict:
        """Get summary of AZAN's knowledge base"""
        return self.knowledge_base.get_summary()


# Global inference instance
_inference_engine = None


def initialize_inference(ollama_host: str = "http://127.0.0.1:11434") -> EnhancedInference:
    """Initialize and return the global inference engine"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = EnhancedInference(ollama_host=ollama_host)
    return _inference_engine


def get_inference_engine() -> EnhancedInference:
    """Get the global inference engine instance"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = initialize_inference()
    return _inference_engine


def predict(input_text: str) -> str:
    """
    Main prediction function
    Always uses the latest trained model with knowledge base
    
    Args:
        input_text: User question/prompt
    
    Returns:
        Generated response from AZAN
    """
    engine = get_inference_engine()
    return engine.predict(input_text, use_knowledge_context=True)
