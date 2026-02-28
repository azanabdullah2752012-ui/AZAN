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
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        return text.lower().split()
    
    def _calculate_similarity(self, query: str, text: str) -> float:
        """Calculate similarity between query and text"""
        query_tokens = set(self._tokenize(query))
        text_tokens = set(self._tokenize(text))
        
        if not query_tokens or not text_tokens:
            return 0.0
        
        intersection = len(query_tokens & text_tokens)
        union = len(query_tokens | text_tokens)
        
        return intersection / union if union > 0 else 0.0
    
    def search_knowledge(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Search knowledge base for relevant items
        Returns scored and ranked results
        """
        results = []
        
        for item in self.knowledge_items:
            # Score based on multiple fields
            title_score = self._calculate_similarity(query, item.get('title', ''))
            content_score = self._calculate_similarity(query, item.get('content', ''))
            terms_score = sum(
                self._calculate_similarity(query, term) 
                for term in item.get('key_terms', [])
            ) / max(len(item.get('key_terms', [])), 1)
            
            # Weighted average (content is most important)
            final_score = (title_score * 0.2 + content_score * 0.6 + terms_score * 0.2)
            
            if final_score > 0.1:  # Only include if minimum relevance
                results.append({
                    'item': item,
                    'score': final_score
                })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return [r['item'] for r in results[:limit]]
    
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
    
    def search_by_category(self, category: str, query: Optional[str] = None) -> List[Dict]:
        """Search knowledge by category"""
        results = [item for item in self.knowledge_items if item.get('category') == category]
        
        if query:
            # Score by relevance to query
            scored = []
            for item in results:
                score = self._calculate_similarity(query, item.get('content', ''))
                scored.append((item, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [item for item, score in scored]
        
        return results
    
    def get_categories(self) -> List[str]:
        """Get all knowledge categories"""
        categories = set()
        for item in self.knowledge_items:
            cat = item.get('category')
            if cat:
                categories.add(cat)
        return sorted(list(categories))
    
    def get_sources(self) -> List[str]:
        """Get all knowledge sources"""
        sources = set()
        for item in self.knowledge_items:
            src = item.get('source')
            if src:
                sources.add(src)
        return sorted(list(sources))
    
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
            'total_qa_pairs': len(self.qa_pairs),
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
