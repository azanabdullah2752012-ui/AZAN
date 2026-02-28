"""
PostgreSQL Database Integration for AZAN
Scalable persistence for training data, articles, feedback, and embeddings
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
    from psycopg2.extras import RealDictCursor
except ImportError:
    # Graceful fallback if psycopg2 not installed
    SimpleConnectionPool = None  # type: ignore
    RealDictCursor = None  # type: ignore

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL connections and database operations
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 5432,
                 database: str = "azan_db",
                 user: str = "azan",
                 password: str = "azan_secure_password",
                 min_connections: int = 2,
                 max_connections: int = 20):
        """
        Initialize database manager
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connection pool size
            max_connections: Maximum connection pool size
        """
        self.config = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        
        self.pool = None
        self.initialized = False
        
        # Try to initialize
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            self.pool = SimpleConnectionPool(
                2, 20,
                **self.config
            )
            self.initialized = True
            self._create_tables()
            logger.info("✓ PostgreSQL connection pool initialized")
        except psycopg2.OperationalError as e:
            logger.warning(f"PostgreSQL unavailable: {e}. Using fallback mode.")
            self.initialized = False
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            self.initialized = False
    
    def _create_tables(self):
        """Create necessary database tables"""
        if not self.initialized:
            return
        
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # Training pairs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS training_pairs (
                    id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category VARCHAR(50),
                    reward FLOAT DEFAULT 0.0,
                    iterations INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Articles table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id VARCHAR(255) PRIMARY KEY,
                    headline TEXT NOT NULL,
                    body TEXT,
                    source VARCHAR(255),
                    category VARCHAR(50),
                    link TEXT,
                    embedding BYTEA,
                    published_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User feedback table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id VARCHAR(255) PRIMARY KEY,
                    interaction_id VARCHAR(255),
                    rating INTEGER,
                    comment TEXT,
                    user_id VARCHAR(255),
                    helpful BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model checkpoints table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS model_checkpoints (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50),
                    iteration INTEGER,
                    avg_reward FLOAT,
                    pairs_count INTEGER,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User sessions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255),
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            """)
            
            # Embeddings table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id VARCHAR(255) PRIMARY KEY,
                    document_id VARCHAR(255),
                    document_type VARCHAR(50),
                    embedding BYTEA,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("✓ Database tables created/verified")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            conn.rollback()
        finally:
            cur.close()
            self.pool.putconn(conn)
    
    def get_connection(self):
        """Get a connection from the pool"""
        if not self.initialized:
            return None
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """Return connection to pool"""
        if self.initialized and conn:
            self.pool.putconn(conn)
    
    # Training Pairs Methods
    
    def insert_training_pair(self, question: str, answer: str, category: str) -> Optional[int]:
        """Insert a training pair"""
        if not self.initialized:
            return None
        
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO training_pairs (question, answer, category, reward)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (question, answer, category, 0.0))
            
            pair_id = cur.fetchone()[0]
            conn.commit()
            return pair_id
            
        except Exception as e:
            logger.error(f"Error inserting training pair: {e}")
            conn.rollback()
            return None
        finally:
            cur.close()
            self.return_connection(conn)
    
    def update_pair_reward(self, pair_id: int, reward: float, iterations: int) -> bool:
        """Update reward for a training pair"""
        if not self.initialized:
            return False
        
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE training_pairs
                SET reward = %s, iterations = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (reward, iterations, pair_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating pair reward: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            self.return_connection(conn)
    
    def get_training_pairs(self, category: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get training pairs from database"""
        if not self.initialized:
            return []
        
        conn = self.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if category:
                cur.execute("""
                    SELECT * FROM training_pairs
                    WHERE category = %s
                    ORDER BY updated_at DESC
                    LIMIT %s
                """, (category, limit))
            else:
                cur.execute("""
                    SELECT * FROM training_pairs
                    ORDER BY updated_at DESC
                    LIMIT %s
                """, (limit,))
            
            return cur.fetchall()
            
        except Exception as e:
            logger.error(f"Error fetching training pairs: {e}")
            return []
        finally:
            cur.close()
            self.return_connection(conn)
    
    # Articles Methods
    
    def insert_article(self, article_data: Dict) -> bool:
        """Insert article"""
        if not self.initialized:
            return False
        
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO articles (id, headline, body, source, category, link, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                article_data.get("id"),
                article_data.get("headline"),
                article_data.get("body"),
                article_data.get("source"),
                article_data.get("category"),
                article_data.get("link"),
                article_data.get("published_at")
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            self.return_connection(conn)
    
    def get_articles(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get recent articles"""
        if not self.initialized:
            return []
        
        conn = self.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if category:
                cur.execute("""
                    SELECT * FROM articles
                    WHERE category = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (category, limit))
            else:
                cur.execute("""
                    SELECT * FROM articles
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
            
            return cur.fetchall()
            
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
            return []
        finally:
            cur.close()
            self.return_connection(conn)
    
    # Feedback Methods
    
    def insert_feedback(self, feedback_data: Dict) -> bool:
        """Insert user feedback"""
        if not self.initialized:
            return False
        
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_feedback (id, interaction_id, rating, comment, user_id, helpful)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                feedback_data.get("id"),
                feedback_data.get("interaction_id"),
                feedback_data.get("rating"),
                feedback_data.get("comment"),
                feedback_data.get("user_id"),
                feedback_data.get("helpful")
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting feedback: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            self.return_connection(conn)
    
    def get_feedback(self, interaction_id: Optional[str] = None) -> List[Dict]:
        """Get feedback"""
        if not self.initialized:
            return []
        
        conn = self.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if interaction_id:
                cur.execute("""
                    SELECT * FROM user_feedback
                    WHERE interaction_id = %s
                """, (interaction_id,))
            else:
                cur.execute("SELECT * FROM user_feedback")
            
            return cur.fetchall()
            
        except Exception as e:
            logger.error(f"Error fetching feedback: {e}")
            return []
        finally:
            cur.close()
            self.return_connection(conn)
    
    # Checkpoint Methods
    
    def save_checkpoint(self, checkpoint_data: Dict) -> bool:
        """Save model checkpoint metadata"""
        if not self.initialized:
            return False
        
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO model_checkpoints (version, iteration, avg_reward, pairs_count, file_path)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                checkpoint_data.get("version"),
                checkpoint_data.get("iteration"),
                checkpoint_data.get("avg_reward"),
                checkpoint_data.get("pairs_count"),
                checkpoint_data.get("file_path")
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            self.return_connection(conn)
    
    def close_pool(self):
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("✓ Database connection pool closed")


# Global database instance
_db_manager = None


def initialize_database(**kwargs) -> DatabaseManager:
    """Initialize global database manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(**kwargs)
    return _db_manager


def get_database() -> DatabaseManager:
    """Get global database manager"""
    global _db_manager
    if _db_manager is None:
        initialize_database()
    return _db_manager
