"""
Migration script to index existing SQLite articles into the ChromaDB vector store.
Part of Phase 3 Intelligence & RAG.
"""

import logging
from src.database import get_database
from src.semantic_search import get_vector_store

logger = logging.getLogger(__name__)


def migrate_articles_to_vector_store():
    """Migrate articles from SQLite to ChromaDB."""
    db = get_database()
    vector_store = get_vector_store()
    
    # Get all articles from SQLite
    articles = db.get_articles(limit=1000)
    
    # Index to ChromaDB
    indexed = 0
    failed = 0
    
    for article in articles:
        try:
            if vector_store.add_article(article):
                indexed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Error migrating article {article.get('id')}: {e}")
            failed += 1
            
    logger.info(f"✓ Migration complete: {indexed} indexed, {failed} failed")
    return indexed, failed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🚀 Starting migration from SQLite to ChromaDB...")
    indexed, failed = migrate_articles_to_vector_store()
    print(f"✅ Migration finished: {indexed} articles indexed to ChromaDB.")
