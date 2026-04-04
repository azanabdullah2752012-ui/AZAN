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
        """Fetches a URL and extracts the clean text content (Synchronous compatibility wrapper)."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.aread_webpage(url))

    async def asearch(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Asynchronous wrapper for the search tool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search, query, max_results)

    async def aread_webpage(self, url: str) -> str:
        """Uses Headless Playwright to fully render JavaScript and read dynamic websites."""
        from playwright.async_api import async_playwright
        try:
            logger.info(f"Opening headless browser to read: '{url}'")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Block heavy media resources to massively speed up loading
                await page.route("**/*.png", lambda route: route.abort())
                await page.route("**/*.jpg", lambda route: route.abort())
                await page.route("**/*.jpeg", lambda route: route.abort())
                await page.route("**/*.webp", lambda route: route.abort())
                await page.route("**/*.gif", lambda route: route.abort())
                await page.route("**/*.css", lambda route: route.abort())
                
                await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(1000) # Give dynamic text a second to settle
                
                text = await page.evaluate("document.body.innerText")
                await browser.close()
                
                if not text:
                    text = "No readable text found on body."
                    
                if len(text) > 10000:
                    text = text[:10000] + "\n...[Content Truncated]..."
                    
                return text.strip()
        except Exception as e:
            logger.error(f"Failed to read webpage '{url}': {e}")
            return f"Error reading webpage: {e}"
