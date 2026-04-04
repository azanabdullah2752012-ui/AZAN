"""
SQLite Database Integration for AZAN
Local, zero-setup persistence for training data, articles, feedback, and history.
Keeps AZAN 100% private and offline.
"""

import sqlite3
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite connections and database operations for local persistence.
    """

    def __init__(self, db_path: str = "data/azan_local.db"):
        """
        Initialize database manager

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.initialized = False
        self._initialize_db()

    def _get_connection(self):
        """Get a direct connection to the SQLite database"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Allows dictionary-like access
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize_db(self):
        """Initialize database tables"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            # 1. Sessions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT DEFAULT 'New Chat',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Training pairs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS training_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT,
                    reward REAL DEFAULT 0.0,
                    iterations INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Articles table (Knowledge base storage)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    headline TEXT NOT NULL,
                    body TEXT,
                    source TEXT,
                    category TEXT,
                    link TEXT,
                    published_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. User feedback table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id TEXT PRIMARY KEY,
                    interaction_id TEXT,
                    rating INTEGER,
                    comment TEXT,
                    user_id TEXT,
                    helpful BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. Model checkpoints table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS model_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT,
                    iteration INTEGER,
                    avg_reward REAL,
                    pairs_count INTEGER,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 6. Conversation History
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    model TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            conn.commit()
            conn.close()
            self.initialized = True
            logger.info(f"✓ SQLite database initialized at {self.db_path}")

            # Run data migration for articles and training pairs
            self._migrate_legacy_data()

        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            self.initialized = False

    def _migrate_legacy_data(self):
        """Import legacy JSON articles and training pairs into SQLite."""
        import json
        # 1. Articles
        articles_file = self.db_path.parent / "inshorts_articles.json"
        if articles_file.exists():
            try:
                with open(articles_file, "r") as f:
                    articles = json.load(f)
                count = 0
                if isinstance(articles, list):
                    for art in articles:
                        if self.insert_article(art): count += 1
                elif isinstance(articles, dict):
                    for aid, art in articles.items():
                        if "id" not in art: art["id"] = aid
                        if self.insert_article(art): count += 1
                if count > 0:
                    articles_file.rename(articles_file.with_suffix(".json.migrated"))
                    logger.info(f"✓ Migrated {count} articles to SQLite")
            except Exception as e:
                logger.warning(f"Failed to migrate articles: {e}")

        # 2. Training Pairs
        pairs_file = self.db_path.parent / "rl_training_data.json"
        if pairs_file.exists():
            try:
                with open(pairs_file, "r") as f:
                    pairs = json.load(f)
                count = 0
                if isinstance(pairs, list):
                    for p in pairs:
                        q, a, cat = p.get("question"), p.get("answer"), p.get("category")
                        rew, its = p.get("reward", 0.0), p.get("iterations", 0)
                        if q and a:
                            pid = self.insert_training_pair(q, a, cat)
                            if pid: self.update_pair_reward(pid, rew, its); count += 1
                if count > 0:
                    pairs_file.rename(pairs_file.with_suffix(".json.migrated"))
                    logger.info(f"✓ Migrated {count} training pairs to SQLite")
            except Exception as e:
                logger.warning(f"Failed to migrate training pairs: {e}")

    # =========================================================================
    # Session Methods
    # =========================================================================

    def ensure_session(self, session_id: str, first_message: str = "") -> None:
        """Create a session if it doesn't already exist. Title is derived from first message."""
        if not self.initialized:
            return
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            # Check if session exists
            cur.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
            if cur.fetchone() is None:
                title = (first_message[:60] + "...") if len(first_message) > 60 else first_message
                title = title or "New Chat"
                cur.execute(
                    "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
                    (session_id, title),
                )
            else:
                cur.execute(
                    "UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?",
                    (session_id,),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error ensuring session: {e}")

    def get_all_sessions(self, limit: int = 50) -> List[Dict]:
        """Return all sessions with message count, ordered by last activity."""
        if not self.initialized:
            return []
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT s.session_id, s.title, s.created_at, s.last_activity,
                       COUNT(ch.id) as message_count
                FROM sessions s
                LEFT JOIN chat_history ch ON s.session_id = ch.session_id
                GROUP BY s.session_id
                ORDER BY s.last_activity DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its chat history (cascade)."""
        if not self.initialized:
            return False
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
            cur.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            deleted = cur.rowcount > 0
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    # =========================================================================
    # Chat History Methods
    # =========================================================================

    def add_chat_message(self, session_id: str, role: str, content: str, model: str = "azan"):
        """Add a message and auto-create session if needed."""
        if not self.initialized:
            return
        try:
            self.ensure_session(session_id, first_message=content if role == "user" else "")
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_history (session_id, role, content, model)
                VALUES (?, ?, ?, ?)
            """, (session_id, role, content, model))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error adding chat message: {e}")

    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        if not self.initialized:
            return []
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM chat_history
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (session_id, limit))
            rows = cur.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}")
            return []

    # =========================================================================
    # Training Pairs Methods
    # =========================================================================

    def insert_training_pair(self, question: str, answer: str, category: str) -> Optional[int]:
        if not self.initialized:
            return None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO training_pairs (question, answer, category)
                VALUES (?, ?, ?)
            """, (question, answer, category))
            pair_id = cur.lastrowid
            conn.commit()
            conn.close()
            return pair_id
        except Exception as e:
            logger.error(f"Error inserting training pair: {e}")
            return None

    def update_pair_reward(self, pair_id: int, reward: float, iterations: int) -> bool:
        if not self.initialized:
            return False
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE training_pairs
                SET reward = ?, iterations = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (reward, iterations, pair_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating pair reward: {e}")
            return False

    def get_training_pairs(self, category: Optional[str] = None, limit: int = 100) -> List[Dict]:
        if not self.initialized:
            return []
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            if category:
                cur.execute("SELECT * FROM training_pairs WHERE category = ? ORDER BY updated_at DESC LIMIT ?", (category, limit))
            else:
                cur.execute("SELECT * FROM training_pairs ORDER BY updated_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching training pairs: {e}")
            return []

    # =========================================================================
    # Article Methods
    # =========================================================================

    def insert_article(self, article_data: Dict) -> bool:
        if not self.initialized:
            return False
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO articles (id, headline, body, source, category, link, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
            conn.close()
            
            # Phase 3: Auto-index to Vector Store (ChromaDB)
            try:
                from src.semantic_search import get_vector_store
                vs = get_vector_store()
                vs.add_article(article_data)
            except Exception as ve:
                logger.warning(f"Failed to vector-index article: {ve}")

            return True
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
            return False

    def get_articles(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        if not self.initialized:
            return []
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            if category:
                cur.execute("SELECT * FROM articles WHERE category = ? ORDER BY created_at DESC LIMIT ?", (category, limit))
            else:
                cur.execute("SELECT * FROM articles ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching articles: {e}")
            return []

    # =========================================================================
    # Feedback Methods (replaces JSON storage)
    # =========================================================================

    def insert_feedback(self, feedback_id: str, interaction_id: str, rating: int,
                        comment: str = "", user_id: str = "anonymous") -> bool:
        """Insert a feedback record into SQLite."""
        if not self.initialized:
            return False
        try:
            helpful = rating >= 4
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO user_feedback (id, interaction_id, rating, comment, user_id, helpful)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (feedback_id, interaction_id, rating, comment, user_id, helpful))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error inserting feedback: {e}")
            return False

    def get_feedback_for_interaction(self, interaction_id: str) -> List[Dict]:
        """Get all feedback entries for a given interaction."""
        if not self.initialized:
            return []
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM user_feedback WHERE interaction_id = ?", (interaction_id,))
            rows = cur.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching feedback: {e}")
            return []

    def get_feedback_stats(self) -> Dict:
        """Get overall feedback statistics from SQLite."""
        if not self.initialized:
            return {"total_ratings": 0, "average_rating": 0, "helpful_percentage": 0, "by_rating": {}}
        try:
            conn = self._get_connection()
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) as total, AVG(rating) as avg_rating FROM user_feedback")
            row = cur.fetchone()
            total = row["total"] or 0
            avg_rating = round(row["avg_rating"] or 0, 2)

            cur.execute("SELECT COUNT(*) as cnt FROM user_feedback WHERE helpful = 1")
            helpful_count = cur.fetchone()["cnt"] or 0

            by_rating = {}
            for i in range(1, 6):
                cur.execute("SELECT COUNT(*) as cnt FROM user_feedback WHERE rating = ?", (i,))
                by_rating[str(i)] = cur.fetchone()["cnt"] or 0

            conn.close()
            return {
                "total_ratings": total,
                "average_rating": avg_rating,
                "helpful_percentage": round((helpful_count / total * 100), 1) if total > 0 else 0,
                "by_rating": by_rating,
                "recommendation": "good" if avg_rating >= 4 else "needs_improvement"
            }
        except Exception as e:
            logger.error(f"Error getting feedback stats: {e}")
            return {"total_ratings": 0, "average_rating": 0, "helpful_percentage": 0, "by_rating": {}}

    # =========================================================================
    # Database Summary
    # =========================================================================

    def get_db_summary(self) -> Dict:
        """Return row counts for all tables."""
        if not self.initialized:
            return {}
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            summary = {}
            for table in ["sessions", "chat_history", "training_pairs", "articles", "user_feedback", "model_checkpoints"]:
                cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                summary[table] = cur.fetchone()["cnt"]
            summary["db_path"] = str(self.db_path)
            summary["db_size_kb"] = round(self.db_path.stat().st_size / 1024, 1) if self.db_path.exists() else 0
            conn.close()
            return summary
        except Exception as e:
            logger.error(f"Error getting db summary: {e}")
            return {}


# Global database instance
_db_manager = None


def get_database() -> DatabaseManager:
    """Get global database manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
