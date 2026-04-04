"""
Semantic Search with ChromaDB for AZAN
Uses ChromaDB for vector persistence and semantic retrieval.
Keeps AZAN's knowledge base intelligent and fast.
"""

import logging
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Optional
import requests
import hashlib

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
        """
        # Simple in-memory cache for speed
        text_hash = hashlib.md5(text.encode()).hexdigest()
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


class VectorStore:
    """
    ChromaDB wrapper for persistent vector storage.
    """
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize Persistent Client
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # Create or Get Collections
        # Using a default distance function "l2" (squared L2 distance)
        # Cosine similarity is "cosine"
        self.articles_collection = self.client.get_or_create_collection(
            name="azan_articles",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.embedding_service = EmbeddingService()
        logger.info(f"✓ ChromaDB VectorStore initialized at {self.persist_directory}")

    def add_article(self, article: Dict) -> bool:
        """
        Add an article to the vector store.
        """
        article_id = article.get("id")
        headline = article.get("headline", "")
        body = article.get("body", "")
        
        if not article_id:
            article_id = hashlib.md5((headline + body).encode()).hexdigest()
        
        text = f"{headline}\n\n{body}"
        embedding = self.embedding_service.get_embedding(text)
        
        if embedding:
            try:
                # Sanitize metadata to ensure all values are valid types (str, int, float, bool)
                metadata = {
                    "headline": str(headline) if headline else "Unknown",
                    "source": str(article.get("source")) if article.get("source") else "Unknown",
                    "category": str(article.get("category")) if article.get("category") else "General",
                    "published_at": str(article.get("published_at")) if article.get("published_at") else "Unknown"
                }

                self.articles_collection.add(
                    ids=[article_id],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    documents=[text]
                )
                return True
            except Exception as e:
                logger.error(f"Error adding to ChromaDB: {e}")
                return False
        return False

    def search(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Semantic search using vector similarity.
        """
        query_embedding = self.embedding_service.get_embedding(query)
        
        if not query_embedding:
            return []
        
        where_filter = {}
        if category:
            where_filter = {"category": category}
            
        try:
            results = self.articles_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter if where_filter else None,
                include=["metadatas", "documents", "distances"]
            )
            
            output = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    output.append({
                        "id": results["ids"][0][i],
                        "headline": results["metadatas"][0][i]["headline"],
                        "body": results["documents"][0][i],
                        "source": results["metadatas"][0][i]["source"],
                        "category": results["metadatas"][0][i]["category"],
                        "similarity": 1.0 - results["distances"][0][i]  # Convert distance to similarity
                    })
            return output
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get vector store statistics."""
        return {
            "total_vectors": self.articles_collection.count(),
            "collection_name": "azan_articles"
        }


# Global instances
_vector_store = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def initialize_semantic_search():
    """Proxy for legacy compatibility if needed."""
    return get_vector_store()
