import chromadb
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)

class KnowledgeMemory:
    """Manages both SQLite (Graph/Relational) and ChromaDB (Vector) memory for AZAN.
    
    This ensures that claims can be semantically searched (Chroma) while maintaining
    strict, reliable tracking of source, confidence, and verification status (SQLite).
    """
    
    def __init__(self, persist_dir: str = "data/memory"):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # 1. Vector Store via ChromaDB
        # We use the default local persistent client. It will download the default
        # sentence-transformers model (all-MiniLM-L6-v2) automatically if not configured.
        try:
            self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.chroma_client.get_or_create_collection("atomic_claims")
            logger.info("ChromaDB persistent vector store initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

        # 2. Provenance Database
        db_path = os.path.join(self.persist_dir, "claims.sqlite")
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite schema for tracking graph relations and metadata."""
        try:
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    claim_text TEXT,
                    source TEXT,
                    timestamp DATETIME,
                    confidence REAL,
                    verified BOOLEAN
                )
            ''')
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS user_persona (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    timestamp DATETIME
                )
            ''')
            self.db.commit()
            logger.info("SQLite claims provenance DB & persona store initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite structure: {e}")

    def add_claim(self, claim_text: str, source: str, confidence: float, verified: bool = False) -> bool:
        """Adds a new atomic factual claim to memory. Deduplicates via SHA256 of text."""
        claim_id = hashlib.sha256(claim_text.encode('utf-8')).hexdigest()
        
        # 1. Check Relational DB to deduplicate
        cursor = self.db.cursor()
        cursor.execute("SELECT id FROM knowledge WHERE id=?", (claim_id,))
        if cursor.fetchone():
            logger.debug(f"Claim already exists, skipping: {claim_text[:50]}...")
            return False
            
        now = datetime.now().isoformat()
        
        try:
            # 2. Store Relational
            self.db.execute(
                "INSERT INTO knowledge VALUES (?, ?, ?, ?, ?, ?)",
                (claim_id, claim_text, source, now, confidence, verified)
            )
            self.db.commit()
            
            # 3. Store Vector (Chroma handles the embedding natively on CPU/MPS)
            self.collection.add(
                documents=[claim_text],
                metadatas=[{
                    "source": source, 
                    "confidence": confidence, 
                    "verified": verified,
                    "timestamp": now
                }],
                ids=[claim_id]
            )
            logger.info(f"Ingested new claim: {claim_text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to store claim '{claim_text[:30]}': {e}")
            self.db.rollback()
            return False

    def search_claims(self, query: str, top_k: int = 5, require_verified: bool = False) -> List[Dict]:
        """Semantically searches the vector memory for the most relevant known claims."""
        try:
            # Add dynamic filtering if requested
            where_clause = {"verified": True} if require_verified else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause
            )
            
            retrieved = []
            if results and "documents" in results and results["documents"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
                dists = results["distances"][0] if "distances" in results else [0.0] * len(docs)
                
                for doc, meta, dist in zip(docs, metas, dists):
                    retrieved.append({
                        "claim": doc,
                        "metadata": meta,
                        "distance": dist  # Lower distance means higher similarity
                    })
            return retrieved
        except Exception as e:
            logger.error(f"Vector search failed for query '{query}': {e}")
            return []
            
    def get_all_claims(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Fetch claims strictly from relational DB for UI/Admin views."""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM knowledge ORDER BY timestamp DESC LIMIT ? OFFSET ?", 
            (limit, offset)
        )
        return [dict(row) for row in cursor.fetchall()]

    # --- Phase 9: Cross-Session User Persona Memory ---
    
    def set_persona_trait(self, key: str, value: str):
        """Upsert a specific user persona trait or preference."""
        now = datetime.now().isoformat()
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO user_persona (key, value, timestamp) VALUES (?, ?, ?)",
                (key, value, now)
            )
            self.db.commit()
            logger.info(f"Updated persona trait: {key} = {value}")
        except Exception as e:
            logger.error(f"Failed to set persona trait {key}: {e}")
            self.db.rollback()

    def get_persona(self) -> Dict[str, str]:
        """Retrieve the entire stored user persona."""
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT key, value FROM user_persona")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Failed to get persona: {e}")
            return {}
