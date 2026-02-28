"""
Semantic Search with Embeddings for AZAN
Uses Ollama embeddings for vector similarity search
"""

import json
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Manages embeddings using Ollama's nomic-embed-text model
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """
        Initialize embedding service
        
        Args:
            ollama_url: URL to Ollama server
        """
        self.ollama_url = ollama_url
        self.model = "nomic-embed-text"
        self.embedding_cache = {}
        
        # Test connection
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info("✓ Connected to Ollama embedding service")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector or None if failed
        """
        # Check cache first
        text_hash = hash(text) % ((2 ** 31) - 1)
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=10
            )
            
            if response.status_code == 200:
                embedding = response.json().get("embedding")
                self.embedding_cache[text_hash] = embedding
                return embedding
            else:
                logger.error(f"Embedding failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None
    
    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
        
        Returns:
            Similarity score (0-1)
        """
        if not vec1 or not vec2:
            return 0.0
        
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


class SemanticSearchEngine:
    """
    Semantic search across articles and training data
    """
    
    def __init__(self, data_dir: str = "data", embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize semantic search
        
        Args:
            data_dir: Directory containing data files
            embedding_service: Optional custom embedding service
        """
        self.data_dir = Path(data_dir)
        self.embedding_service = embedding_service or EmbeddingService()
        self.embeddings_file = self.data_dir / "embeddings.json"
        
        self.embeddings = {}
        self._load_embeddings()
        
        logger.info("✓ SemanticSearchEngine initialized")
    
    def _load_embeddings(self):
        """Load cached embeddings"""
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, 'r') as f:
                    self.embeddings = json.load(f)
                logger.info(f"Loaded {len(self.embeddings)} cached embeddings")
            except Exception as e:
                logger.error(f"Error loading embeddings: {e}")
    
    def _save_embeddings(self):
        """Save embeddings to cache"""
        try:
            with open(self.embeddings_file, 'w') as f:
                json.dump(self.embeddings, f)
        except Exception as e:
            logger.error(f"Error saving embeddings: {e}")
    
    def index_articles(self, articles: Dict[str, Dict]) -> Dict:
        """
        Index articles for semantic search
        
        Args:
            articles: Dictionary of articles {id: article_data}
        
        Returns:
            Indexing results
        """
        indexed = 0
        failed = 0
        
        for article_id, article in articles.items():
            if article_id in self.embeddings:
                continue  # Skip already indexed
            
            # Combine headline and body for embedding
            text = f"{article.get('headline', '')} {article.get('body', '')}"
            embedding = self.embedding_service.get_embedding(text)
            
            if embedding:
                self.embeddings[article_id] = {
                    "embedding": embedding,
                    "headline": article.get('headline'),
                    "source": article.get('source'),
                    "category": article.get('category'),
                    "timestamp": datetime.now().isoformat()
                }
                indexed += 1
            else:
                failed += 1
        
        self._save_embeddings()
        
        result = {
            "indexed": indexed,
            "failed": failed,
            "total": len(self.embeddings)
        }
        
        logger.info(f"✓ Indexed {indexed} articles, {failed} failed")
        return result
    
    def search(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Semantic search across indexed content
        
        Args:
            query: Search query
            limit: Maximum results
            category: Optional category filter
        
        Returns:
            List of relevant articles with similarity scores
        """
        query_embedding = self.embedding_service.get_embedding(query)
        
        if not query_embedding:
            logger.error("Failed to embed query")
            return []
        
        results = []
        
        for doc_id, doc_info in self.embeddings.items():
            doc_embedding = doc_info.get("embedding")
            
            if not doc_embedding:
                continue
            
            # Apply category filter
            if category and doc_info.get("category") != category:
                continue
            
            # Calculate similarity
            similarity = self.embedding_service.similarity(query_embedding, doc_embedding)
            
            results.append({
                "id": doc_id,
                "headline": doc_info.get("headline"),
                "source": doc_info.get("source"),
                "category": doc_info.get("category"),
                "similarity": round(similarity, 3),
                "timestamp": doc_info.get("timestamp")
            })
        
        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:limit]
    
    def search_by_category(self, query: str, category: str, limit: int = 5) -> List[Dict]:
        """Search within specific category"""
        return self.search(query, limit=limit, category=category)
    
    def find_similar(self, doc_id: str, limit: int = 5) -> List[Dict]:
        """
        Find documents similar to a given document
        
        Args:
            doc_id: Document ID to find similarities for
            limit: Maximum results
        
        Returns:
            List of similar documents
        """
        if doc_id not in self.embeddings:
            return []
        
        doc_embedding = self.embeddings[doc_id]["embedding"]
        results = []
        
        for other_id, other_info in self.embeddings.items():
            if other_id == doc_id:
                continue
            
            other_embedding = other_info.get("embedding")
            if not other_embedding:
                continue
            
            similarity = self.embedding_service.similarity(doc_embedding, other_embedding)
            results.append({
                "id": other_id,
                "headline": other_info.get("headline"),
                "similarity": round(similarity, 3)
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]
    
    def get_stats(self) -> Dict:
        """Get indexing statistics"""
        by_category = {}
        for doc_info in self.embeddings.values():
            cat = doc_info.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
        
        return {
            "total_documents": len(self.embeddings),
            "by_category": by_category
        }


# Global search engine instance
_semantic_search = None


def initialize_semantic_search(data_dir: str = "data") -> SemanticSearchEngine:
    """Initialize global semantic search engine"""
    global _semantic_search
    if _semantic_search is None:
        _semantic_search = SemanticSearchEngine(data_dir=data_dir)
    return _semantic_search


def get_semantic_search() -> SemanticSearchEngine:
    """Get global semantic search engine"""
    global _semantic_search
    if _semantic_search is None:
        initialize_semantic_search()
    return _semantic_search
