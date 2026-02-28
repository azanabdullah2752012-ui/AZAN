"""
Restricted Inference Engine - Uses ONLY Training Data
No external knowledge, only responses from rl_training_data.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RestrictedKnowledgeBase:
    """
    Knowledge base restricted to only training data
    No external sources or generated content
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.training_data_file = self.data_dir / "rl_training_data.json"
        
        self.training_pairs = []
        self.by_category = {}
        self.by_question = {}
        
        self._load_training_data()
        logger.info(f"✓ RestrictedKnowledgeBase initialized with {len(self.training_pairs)} training pairs")
    
    def _load_training_data(self):
        """Load ONLY training data from JSON file"""
        if not self.training_data_file.exists():
            logger.warning(f"Training data file not found: {self.training_data_file}")
            return
        
        try:
            with open(self.training_data_file, 'r') as f:
                self.training_pairs = json.load(f)
            
            # Index by category
            for pair in self.training_pairs:
                category = pair.get('category', 'unknown')
                if category not in self.by_category:
                    self.by_category[category] = []
                self.by_category[category].append(pair)
                
                # Index by question
                question = pair.get('question', '').lower()
                self.by_question[question] = pair
            
            logger.info(f"Loaded {len(self.training_pairs)} training pairs")
            
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            self.training_pairs = []
    
    def find_answer(self, query: str, category: Optional[str] = None) -> Optional[Dict]:
        """
        Find answer from training data
        Returns exact or similar training pair
        """
        query_lower = query.lower()
        
        # Try exact match first
        if query_lower in self.by_question:
            return self.by_question[query_lower]
        
        # Search by category if specified
        if category and category in self.by_category:
            candidates = self.by_category[category]
        else:
            candidates = self.training_pairs
        
        # Find best matching question
        best_match = None
        best_score = 0
        
        for pair in candidates:
            question = pair.get('question', '').lower()
            score = self._similarity_score(query_lower, question)
            
            if score > best_score:
                best_score = score
                best_match = pair
        
        # Only return if there's a reasonable match (> 30% similarity)
        if best_score > 0.3:
            return best_match
        
        return None
    
    def _similarity_score(self, query: str, question: str) -> float:
        """
        Calculate similarity between query and question
        Simple word overlap score
        """
        query_words = set(query.split())
        question_words = set(question.split())
        
        if not question_words:
            return 0.0
        
        overlap = len(query_words & question_words)
        return overlap / len(question_words)
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Get all training pairs for a category"""
        return self.by_category.get(category, [])
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        return list(self.by_category.keys())
    
    def get_random_from_category(self, category: str) -> Optional[Dict]:
        """Get a random training pair from category"""
        import random
        pairs = self.get_by_category(category)
        if pairs:
            return random.choice(pairs)
        return None
    
    def get_stats(self) -> Dict:
        """Get statistics about training data"""
        return {
            "total_pairs": len(self.training_pairs),
            "categories": self.get_categories(),
            "by_category": {cat: len(pairs) for cat, pairs in self.by_category.items()},
            "avg_reward": sum(p.get('reward', 0) for p in self.training_pairs) / max(len(self.training_pairs), 1)
        }


class RestrictedInference:
    """
    Inference engine that ONLY uses training data
    No Ollama, no external knowledge, no generation
    """
    
    def __init__(self, data_dir: str = "data"):
        self.kb = RestrictedKnowledgeBase(data_dir=data_dir)
        self.interaction_count = 0
        logger.info("✓ RestrictedInference initialized")
    
    def predict(self, query: str, category: Optional[str] = None) -> Dict:
        """
        Get response ONLY from training data
        Returns answer from training pair or fallback
        """
        self.interaction_count += 1
        
        # Try to find answer in training data
        answer_pair = self.kb.find_answer(query, category=category)
        
        if answer_pair:
            return {
                "query": query,
                "answer": answer_pair.get('answer', 'No answer found'),
                "source": "training_data",
                "category": answer_pair.get('category'),
                "confidence": 1.0,
                "training_pair": True,
                "reward": answer_pair.get('reward', 0),
                "timestamp": datetime.now().isoformat()
            }
        
        # Fallback: suggest asking something from training data
        categories = self.kb.get_categories()
        available_categories = ", ".join(categories) if categories else "unknown"
        
        return {
            "query": query,
            "answer": f"I can only answer questions from my training data. Available categories: {available_categories}",
            "source": "fallback",
            "category": None,
            "confidence": 0.0,
            "training_pair": False,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_info(self, category: Optional[str] = None) -> Dict:
        """Get available training data for category"""
        if category:
            return {
                "category": category,
                "pairs": self.kb.get_by_category(category),
                "count": len(self.kb.get_by_category(category))
            }
        
        return {
            "available_categories": self.kb.get_categories(),
            "stats": self.kb.get_stats(),
            "total_interactions": self.interaction_count
        }
    
    def get_response_from_training(self, question_index: int) -> Optional[Dict]:
        """Get specific response by training pair index"""
        if 0 <= question_index < len(self.kb.training_pairs):
            return self.kb.training_pairs[question_index]
        return None


# Global instance
_restricted_inference = None


def initialize_restricted_inference(data_dir: str = "data") -> RestrictedInference:
    """Initialize global restricted inference engine"""
    global _restricted_inference
    if _restricted_inference is None:
        _restricted_inference = RestrictedInference(data_dir=data_dir)
    return _restricted_inference


def get_restricted_inference() -> RestrictedInference:
    """Get global restricted inference engine"""
    global _restricted_inference
    if _restricted_inference is None:
        initialize_restricted_inference()
    return _restricted_inference
