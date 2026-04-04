import asyncio
import logging
from datetime import datetime
from src.core.llm_client import LocalLLMClient
from src.memory.vector_store import KnowledgeMemory
from src.agents.extractor import KnowledgeExtractor
from src.agents.fact_checker import FactChecker
from src.tools.web_scraper import WebScraper, DEFAULT_RSS_FEEDS

logger = logging.getLogger(__name__)

# How many seconds to wait between ingestion cycles when idle
IDLE_INTERVAL_SECONDS = 300  # Run every 5 minutes

class ContinuousLearner:
    """The AZAN 'Subconscious' — an async background worker that autonomously
    ingests RSS feeds, extracts atomic claims, verifies them, and stores
    them in the knowledge base without blocking the FastAPI server.
    """

    def __init__(self, llm: LocalLLMClient, memory: KnowledgeMemory):
        self.llm = llm
        self.memory = memory
        self.scraper = WebScraper()
        self.extractor = KnowledgeExtractor(llm)
        self.fact_checker = FactChecker(llm, memory)
        self._running = False
        self._cycle_count = 0

    async def run_once(self):
        """Execute a single ingestion cycle: fetch → extract → verify → store."""
        self._cycle_count += 1
        logger.info(f"[ContinuousLearner] Starting ingestion cycle #{self._cycle_count}...")
        
        # 1. Fetch articles from all RSS feeds
        articles = await self.scraper.fetch_all_feeds(DEFAULT_RSS_FEEDS)
        if not articles:
            logger.warning("[ContinuousLearner] No articles fetched this cycle.")
            return

        total_stored = 0

        for article in articles:
            # Build a compact representation for the LLM
            raw_text = f"{article.get('title', '')}\n{article.get('summary', '')}"
            source_url = article.get("url", article.get("source", "rss_feed"))
            
            if len(raw_text.strip()) < 30:
                continue

            # 2. Extract atomic claims from article
            try:
                claims = await self.extractor.extract_claims(raw_text)
            except Exception as e:
                logger.error(f"Extraction failed for article '{article.get('title', '')}': {e}")
                continue

            if not claims:
                continue

            # 3. Format claims for vector embedding
            claim_texts = [
                self.extractor.format_claim_for_vector_store(c) for c in claims
            ]

            # 4. Fact-check and filter
            try:
                verified_claims = await self.fact_checker.filter_claims(
                    claim_texts, source=source_url
                )
            except Exception as e:
                logger.error(f"Fact-check failed: {e}")
                continue

            # 5. Store verified claims in memory
            for vc in verified_claims:
                added = self.memory.add_claim(
                    claim_text=vc["claim"],
                    source=vc["source"],
                    confidence=vc["confidence"],
                    verified=True
                )
                if added:
                    total_stored += 1

            # Yield control back to the event loop between articles
            await asyncio.sleep(0.1)

        logger.info(
            f"[ContinuousLearner] Cycle #{self._cycle_count} complete. "
            f"Stored {total_stored} new claims from {len(articles)} articles."
        )

    async def start(self):
        """Starts the infinite background ingestion loop."""
        self._running = True
        logger.info("[ContinuousLearner] Autonomous background learning started.")
        
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"[ContinuousLearner] Cycle failed: {e}")
            
            # Sleep between cycles, yielding the event loop
            logger.info(f"[ContinuousLearner] Sleeping {IDLE_INTERVAL_SECONDS}s until next cycle.")
            await asyncio.sleep(IDLE_INTERVAL_SECONDS)

    def stop(self):
        """Gracefully stops the background loop."""
        self._running = False
        logger.info("[ContinuousLearner] Stopping autonomous learning loop.")
