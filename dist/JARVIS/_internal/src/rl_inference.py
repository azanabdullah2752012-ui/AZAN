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
    "what does azan mean": "Azan is an Arabic word meaning 'to listen' or 'to inform', most commonly known as the Islamic call to prayer. As an AI assistant, the name AZAN reflects my purpose of listening to user needs and informing them with accurate, real-time knowledge.",
    "what is azan": "Azan is an Arabic word meaning 'to listen' or 'to inform', most commonly known as the Islamic call to prayer. As an AI assistant, the name AZAN reflects my purpose of listening to user needs and informing them with accurate, real-time knowledge.",
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
        Search knowledge base with relevance filtering.
        """
        results = []
        # Filter query words to remove common stop words for better search quality
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'is', 'are', 'was', 'be', 'what', 'does', 'mean', 'how', 'me', 'tell'}
        query_words = {w for w in query.lower().split() if w not in stop_words and len(w) > 2}
        
        if not query_words:
            return []

        # All articles search
        for article in self.articles.values():
            headline = article.get('headline', '').lower()
            h_words = set(headline.split())
            matching_words = len(query_words & h_words)
            
            # Require at least 2 matching words for relevance (or 1 if query is very short)
            if matching_words >= 2 or (len(query_words) == 1 and matching_words == 1):
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
        self.client = httpx.Client(timeout=30.0)
        
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
1. ONLY use the provided context if it is directly relevant to the user's question. 
2. If the context is not related to the user's query, ignore it completely and answer using your general knowledge.
3. NEVER state "Based on the provided snippets" or list irrelevant summaries.
4. If you use context, incorporate it naturally into your response.
5. Be concise but complete. Do not trail off or cut your response short.

Answer comprehensively, accurately, and prioritize relevant information. Use your learned expertise where appropriate. """
        
        return base_prompt
    
    def _build_messages(self, prompt: str, system_prompt: str, 
                         history: list = None) -> list:
        """
        Build the messages array for Ollama, prepending conversation history.
        
        Args:
            prompt: Current user message (may include context appended)
            system_prompt: System context string
            history: List of prior messages [{"role": "user"|"azan"|"assistant", "content": "..."}]
        
        Returns:
            List of message dicts formatted for Ollama
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Inject up to last 10 turns of history (20 messages)
        if history:
            for msg in history[-20:]:
                role = msg.get("role", "user")
                # Normalize 'azan' role to 'assistant' for Ollama
                if role == "azan":
                    role = "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        
        # Final user message
        messages.append({"role": "user", "content": prompt})
        return messages

    def _query_ollama(self, prompt: str, system_prompt: str, model: str = "llama3",
                       temperature: float = 0.5, top_p: float = 0.9,
                       history: list = None) -> str:
        """
        Query Ollama API for a complete (non-streaming) response.
        
        Args:
            prompt: User question (may include RAG context)
            system_prompt: System context
            model: Model name
            temperature: Sampling temperature (0.0–1.0)
            top_p: Top-p nucleus sampling (0.0–1.0)
            history: Prior conversation messages for multi-turn memory
        
        Returns:
            Generated response text
        """
        try:
            url = f"{self.ollama_host}/api/chat"
            messages = self._build_messages(prompt, system_prompt, history)
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": 512,
                    "temperature": temperature,
                    "top_p": top_p,
                    "repeat_penalty": 1.1
                }
            }
            
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get('message', {}).get('content', 'Unable to generate response')
        
        except Exception as e:
            logger.error(f"Error querying Ollama: {e}")
            return f"Error: Unable to generate response - {str(e)}"

    def stream_ollama(self, prompt: str, system_prompt: str, model: str = "llama3",
                      temperature: float = 0.5, top_p: float = 0.9,
                      history: list = None):
        """
        Stream tokens from Ollama line-by-line as a generator.
        Yields string chunks as they arrive.
        """
        import json as _json
        url = f"{self.ollama_host}/api/chat"
        messages = self._build_messages(prompt, system_prompt, history)
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "num_predict": 512,
                "temperature": temperature,
                "top_p": top_p,
                "repeat_penalty": 1.1
            }
        }
        try:
            with httpx.Client(timeout=60.0) as stream_client:
                with stream_client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            data = _json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                yield chunk
                            if data.get("done"):
                                break
                        except Exception:
                            continue
        except Exception as e:
            yield f"\n[Error: {e}]"

    def predict(self, input_text: str, use_knowledge_context: bool = True,
                model: str = "llama3", temperature: float = 0.5, top_p: float = 0.9,
                history: list = None) -> str:
        """
        Generate prediction/response with Semantic RAG + multi-turn memory.
        
        Args:
            input_text: User message
            use_knowledge_context: Whether to inject RAG context
            model: Ollama model name
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            history: Prior conversation messages for multi-turn memory
        """
        # 1. Fast-path: instant reply for simple/greeting messages (skip if history present)
        if not history:
            normalized = input_text.strip().lower().rstrip('!?.')
            if normalized in _INSTANT_REPLIES:
                return _INSTANT_REPLIES[normalized]

        # 2. Semantic Vector Search (ChromaDB RAG)
        relevant_articles = []
        if use_knowledge_context:
            try:
                from src.semantic_search import get_vector_store
                vs = get_vector_store()
                relevant_articles = vs.search(input_text, limit=3)
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back: {e}")
                relevant_articles = self.knowledge_base.search(input_text)
        
        # Build context from semantic matches
        context = ""
        if relevant_articles:
            context = "\n\nRecent Relevant Knowledge:\n"
            for i, article in enumerate(relevant_articles, 1):
                headline = article.get('headline', 'N/A')
                body = article.get('body', 'N/A')
                context += f"{i}. {headline}: {body[:200]}...\n"
        
        enhanced_prompt = f"{input_text}{context}"
        system_prompt = self._build_system_prompt()
        
        # Query Ollama with multi-turn history
        response = self._query_ollama(enhanced_prompt, system_prompt,
                                       model=model, temperature=temperature, top_p=top_p,
                                       history=history)
        
        logger.info("Generated response for: %s", input_text[:60])
        return response

    def stream_predict(self, input_text: str, use_knowledge_context: bool = True,
                       model: str = "llama3", temperature: float = 0.5, top_p: float = 0.9,
                       history: list = None):
        """
        Stream tokens for input_text, injecting RAG context + conversation history.
        Yields string chunks.
        """
        relevant_articles = []
        if use_knowledge_context:
            try:
                from src.semantic_search import get_vector_store
                vs = get_vector_store()
                relevant_articles = vs.search(input_text, limit=3)
            except Exception:
                relevant_articles = self.knowledge_base.search(input_text)
        
        context = ""
        if relevant_articles:
            context = "\n\nRecent Relevant Knowledge:\n"
            for i, article in enumerate(relevant_articles, 1):
                headline = article.get('headline', 'N/A')
                body = article.get('body', 'N/A')
                context += f"{i}. {headline}: {body[:200]}...\n"
        
        enhanced_prompt = f"{input_text}{context}"
        system_prompt = self._build_system_prompt()
        
        yield from self.stream_ollama(enhanced_prompt, system_prompt,
                                      model=model, temperature=temperature, top_p=top_p,
                                      history=history)
    
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
