"""
AZAN RL Inference Engine
Strict data-only responses from curated knowledge
No hallucinations, all responses traceable to source
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import re
import httpx

logger = logging.getLogger(__name__)


class DataOnlyInferenceEngine:
    """
    Inference engine that responds ONLY from curated knowledge
    - No hallucinations
    - All responses sourced
    - Semantic search for relevant knowledge
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.knowledge_file = self.data_dir / "azan_knowledge_base.json"
        self.qa_file = self.data_dir / "azan_qa_pairs.json"
        
        self.knowledge_items = []
        self.qa_pairs = []
        
        self._load_data()
        logger.info(f"✓ DataOnlyInferenceEngine initialized: {len(self.knowledge_items)} items")
    
    def _load_data(self):
        """Load knowledge and Q&A pairs"""
        if self.knowledge_file.exists():
            try:
                with open(self.knowledge_file, 'r') as f:
                    self.knowledge_items = json.load(f)
            except Exception as e:
                logger.error(f"Error loading knowledge: {e}")
        
        if self.qa_file.exists():
            try:
                with open(self.qa_file, 'r') as f:
                    self.qa_pairs = json.load(f)
            except Exception as e:
                logger.error(f"Error loading Q&A pairs: {e}")
        
        self._index_data()

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        return text.lower().split()

    def _calculate_similarity(self, query: str, text: str) -> float:
        """Calculate similarity between query and text"""
        query_tokens = set(self._tokenize(query))
        text_tokens = set(self._tokenize(text))
        if not query_tokens or not text_tokens: return 0.0
        intersection = len(query_tokens & text_tokens)
        union = len(query_tokens | text_tokens)
        return intersection / union if union > 0 else 0.0

    def _index_data(self):
        """Create an inverted index for fast keyword lookups"""
        self.keyword_index = {}
        stop_words = {'the', 'a', 'an', 'and', 'or', 'to', 'of', 'in', 'is', 'for', 'with', 'on', 'at', 'by', 'from'}
        
        for idx, item in enumerate(self.knowledge_items):
            text = (item.get('title', '') + ' ' + item.get('content', '')).lower()
            # Clean and tokenize
            words = re.findall(r'\w{3,}', text) # Words with 3+ chars
            for word in words:
                if word not in stop_words:
                    if word not in self.keyword_index:
                        self.keyword_index[word] = set()
                    self.keyword_index[word].add(idx)
        
        logger.info(f"Indexed {len(self.knowledge_items)} items with {len(self.keyword_index)} keywords")

    def search_knowledge(self, query: str, limit: int = 3) -> List[Dict]:
        """Fast keyword-based search using inverted index"""
        query_words = [w for w in re.findall(r'\w{3,}', query.lower())]
        if not query_words: return []
        
        candidate_indices = set()
        for word in query_words:
            if word in self.keyword_index:
                candidate_indices.update(self.keyword_index[word])
        
        if not candidate_indices: return []
        
        scored_results = []
        for idx in candidate_indices:
            item = self.knowledge_items[idx]
            score = self._calculate_similarity(query, item.get('content', ''))
            if score > 0.05:
                scored_results.append((item, score))
        
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in scored_results[:limit]]
    
    def build_system_prompt(self, query: str) -> Tuple[str, List[Dict]]:
        """
        Build system prompt with retrieved knowledge
        Returns: (system_prompt, sources)
        """
        # Search for relevant knowledge
        relevant_knowledge = self.search_knowledge(query, limit=5)
        
        if not relevant_knowledge:
            system_prompt = """You are AZAN, a specialized AI assistant trained on:
- Indian Constitution and Laws
- UN Treaties and International Policies
- Military Strategies and Doctrines
- Political and Economic Definitions

CRITICAL: Respond ONLY with information from your training data.
If you don't know the answer from your training data, say: "I don't have verified information about this in my training data."

Do not hallucinate, guess, or provide unverified information."""
            
            return system_prompt, []
        
        # Build prompt with sources
        sources_text = "\n\n".join([
            f"**Source: {item['source']}** (Category: {item['category']})\n"
            f"**Title:** {item['title']}\n"
            f"**Content:** {item['content']}\n"
            f"**Key Terms:** {', '.join(item.get('key_terms', []))}"
            for item in relevant_knowledge
        ])
        
        system_prompt = f"""You are AZAN, a specialized AI assistant trained on:
- Indian Constitution and Laws
- UN Treaties and International Policies
- Military Strategies and Doctrines
- Political and Economic Definitions

CRITICAL INSTRUCTIONS:
1. Answer ONLY using information from your training data
2. Cite sources: mention which document (Constitution, UN Charter, Military Doctrine, etc.)
3. Do NOT hallucinate or guess
4. If information isn't in your training data, say: "I don't have verified information about this."
5. Be precise and factual

RELEVANT TRAINING DATA FOR THIS QUERY:
{sources_text}

Now answer the user's question using ONLY the above sources."""
        
        return system_prompt, relevant_knowledge
    
    def answer_query(self, query: str, llm_function=None) -> Dict:
        """
        Answer user query using data-only approach
        
        Args:
            query: User question
            llm_function: Optional function to generate answer (signature: func(system_prompt, query) -> str)
        
        Returns:
            Dict with answer, sources, confidence
        """
        system_prompt, sources = self.build_system_prompt(query)
        
        response = {
            'query': query,
            'sources': sources,
            'source_count': len(sources),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        
        if llm_function:
            try:
                # Call LLM with data-only system prompt
                answer = llm_function(system_prompt, query)
                response['answer'] = answer
                response['confidence'] = 'high' if sources else 'low'
            except Exception as e:
                logger.error(f"Error calling LLM: {e}")
                response['answer'] = self._fallback_answer(sources)
                response['confidence'] = 'fallback'
        else:
            response['answer'] = self._fallback_answer(sources)
            response['confidence'] = 'fallback'
        
        return response
    
    def _fallback_answer(self, sources: List[Dict]) -> str:
        """Generate fallback answer from sources"""
        if not sources:
            return "I don't have verified information about this in my training data. Please ask about: Indian Constitution, UN treaties, military strategies, or political definitions."
        
        answer = "Based on my training data:\n\n"
        for i, source in enumerate(sources, 1):
            answer += f"{i}. **{source['source']} - {source['title']}:**\n"
            answer += f"   {source['content']}\n\n"
        
        return answer
    
    def _build_messages(self, prompt: str, system_prompt: str, history: list = None, images: list = None) -> list:
        """Build messages array for Ollama with history and optional images."""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-20:]:  # Last 10 turns
                role = msg.get("role", "user")
                if role == "azan": role = "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        
        user_msg = {"role": "user", "content": prompt}
        if images:
            user_msg["images"] = images
        messages.append(user_msg)
        return messages

    def stream_ollama(self, prompt: str, system_prompt: str, model: str = "llama3",
                      temperature: float = 0.5, top_p: float = 0.9, history: list = None,
                      images: list = None):
        """Stream from Ollama API with optional vision support."""
        import httpx
        url = "http://127.0.0.1:11434/api/chat"
        messages = self._build_messages(prompt, system_prompt, history, images)
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "top_p": top_p}
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line: continue
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk: yield chunk
                        if data.get("done"): break
        except Exception as e:
            yield f"\n[Streaming Error: {e}]"

    def stream_predict(self, query: str, model: str = "llama3", 
                       temperature: float = 0.5, top_p: float = 0.9, history: list = None,
                       images: list = None):
        """Stream response for curated knowledge with multi-turn memory and vision."""
        system_prompt, relevant_knowledge = self.build_system_prompt(query)
        yield from self.stream_ollama(query, system_prompt, model=model, 
                                      temperature=temperature, top_p=top_p, 
                                      history=history, images=images)

    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        categories = {}
        sources = {}
        
        for item in self.knowledge_items:
            cat = item.get('category', 'unknown')
            src = item.get('source', 'unknown')
            
            categories[cat] = categories.get(cat, 0) + 1
            sources[src] = sources.get(src, 0) + 1
        
        return {
            'total_knowledge_items': len(self.knowledge_items),
            'articles': len(self.knowledge_items),  # Compatibility with UI
            'training_pairs': len(self.qa_pairs),    # Compatibility with UI
            'sessions': 0, # Placeholder, filled by app.py
            'categories': categories,
            'sources': sources,
            'avg_terms_per_item': (
                sum(len(item.get('key_terms', [])) for item in self.knowledge_items) /
                max(len(self.knowledge_items), 1)
            )
        }


# Global instance
_inference_engine = None


def initialize_inference_engine() -> DataOnlyInferenceEngine:
    """Initialize global inference engine"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = DataOnlyInferenceEngine()
    return _inference_engine


def get_inference_engine() -> DataOnlyInferenceEngine:
    """Get inference engine"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = DataOnlyInferenceEngine()
    return _inference_engine
