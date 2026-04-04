import httpx
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

# Default RSS feeds to monitor for autonomous learning
DEFAULT_RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://news.ycombinator.com/rss",
    "https://techcrunch.com/feed/",
]

class WebScraper:
    """Async web scraper for RSS/HTML content ingestion."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "AZAN-ResearchAgent/1.0"}
        )

    async def scrape_url(self, url: str) -> Dict[str, str]:
        """Fetches and extracts clean text from a URL, stripping HTML markup."""
        try:
            response = await self.client.get(url, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove non-content tags
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                tag.decompose()
            
            # Extract primary content
            main_content = soup.find("article") or soup.find("main") or soup.body
            text = main_content.get_text(separator=" ", strip=True) if main_content else ""
            
            # Normalize whitespace
            text = " ".join(text.split())
            
            return {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "content": text[:8000],  # Cap to avoid overwhelming the LLM
                "success": True
            }
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return {"url": url, "title": "", "content": "", "success": False, "error": str(e)}

    async def fetch_rss_articles(self, feed_url: str, max_articles: int = 10) -> List[Dict]:
        """Fetches and parses articles from an RSS/Atom feed."""
        try:
            response = await self.client.get(feed_url)
            feed = feedparser.parse(response.text)
            
            articles = []
            for entry in feed.entries[:max_articles]:
                summary = BeautifulSoup(
                    getattr(entry, 'summary', ''), "html.parser"
                ).get_text(strip=True)
                
                articles.append({
                    "title": getattr(entry, 'title', ''),
                    "summary": summary[:2000],
                    "url": getattr(entry, 'link', ''),
                    "published": getattr(entry, 'published', ''),
                    "source": feed_url
                })
            
            logger.info(f"Fetched {len(articles)} articles from {feed_url}")
            return articles
        except Exception as e:
            logger.warning(f"Failed to parse RSS feed {feed_url}: {e}")
            return []

    async def fetch_all_feeds(self, feeds: Optional[List[str]] = None) -> List[Dict]:
        """Fetches all configured RSS feeds concurrently."""
        feeds = feeds or DEFAULT_RSS_FEEDS
        tasks = [self.fetch_rss_articles(url) for url in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles
