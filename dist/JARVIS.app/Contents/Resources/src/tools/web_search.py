import logging
from typing import List, Dict, Optional
import asyncio
import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS  # New package name as of 2024
except ImportError:
    from duckduckgo_search import DDGS  # Legacy fallback

logger = logging.getLogger(__name__)

class WebSearchTool:
    """Provides free live web search capabilities and deep page scraping."""
    
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Executes a synchronous DuckDuckGo text search."""
        try:
            logger.info(f"Executing web search for: '{query}'")
            results = list(self.ddgs.text(query, max_results=max_results))
            
            if not results:
                logger.warning(f"Web search returned 0 results for: '{query}'")
                return [{"title": "No results", "url": "", "snippet": "The search returned no results. Try a different query."}]

            formatted = []
            for r in results:
                formatted.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
            return formatted
        except Exception as e:
            logger.error(f"Web search failed for query '{query}': {e}")
            return [{"error": f"Search failed: {e}"}]

    def read_webpage(self, url: str) -> str:
        """Fetches a URL and extracts the clean text content using BeautifulSoup."""
        try:
            logger.info(f"Scraping deep webpage: '{url}'")
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Kill javascript and CSS
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
                
            text = soup.get_text(separator=' ', strip=True)
            
            # Limit the text to roughly 10,000 chars to avoid blowing up the context window
            if len(text) > 10000:
                text = text[:10000] + "\n...[Content Truncated]..."
                
            return text
        except Exception as e:
            logger.error(f"Failed to read webpage '{url}': {e}")
            return f"Error reading webpage: {e}"

    async def asearch(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Asynchronous wrapper for the search tool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search, query, max_results)

    async def aread_webpage(self, url: str) -> str:
        """Asynchronous wrapper for reading a webpage."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read_webpage, url)
