"""
AZAN Live News Scraper — True Unsupervised Learning via RSS Feeds
Fetches real articles from global RSS feeds, deduplicates, and generates
Q&A training pairs automatically. No human input required.
"""

import json
import os
import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

try:
    import httpx
except ImportError:
    import urllib.request
    httpx = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Real RSS feed sources ────────────────────────────────────────────────────
RSS_FEEDS = {
    "technology": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.wired.com/feed/rss",
    ],
    "science": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "world": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
    "business": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "politics": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
    ],
    "sports": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ],
    "entertainment": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
    ],
    "national": [
        "https://feeds.bbci.co.uk/news/rss.xml",
    ],
}


class InshortsScraper:
    """
    Live RSS News Scraper — fetches real articles from the internet
    and converts them into training data for AZAN's knowledge base.
    """

    def __init__(self):
        self.categories = list(RSS_FEEDS.keys())
        self.scraped_articles_file = "data/inshorts_articles.json"
        self.training_data_file = "data/inshorts_training_data.json"
        self.scrape_history_file = "data/inshorts_scrape_history.json"

        self._http = httpx.Client(timeout=15.0, follow_redirects=True,
                                  headers={"User-Agent": "AZAN-AI/2.1"}) if httpx else None
        self._load_existing_data()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load_existing_data(self):
        self.scraped_articles: Dict[str, Dict] = {}
        self.training_data: List[Dict] = []
        self.scrape_history: List[Dict] = []

        if os.path.exists(self.scraped_articles_file):
            try:
                with open(self.scraped_articles_file, "r") as f:
                    self.scraped_articles = json.load(f)
                logger.info(f"Loaded {len(self.scraped_articles)} existing articles")
            except Exception:
                self.scraped_articles = {}

        if os.path.exists(self.training_data_file):
            try:
                with open(self.training_data_file, "r") as f:
                    self.training_data = json.load(f)
                logger.info(f"Loaded {len(self.training_data)} existing training pairs")
            except Exception:
                self.training_data = []

        if os.path.exists(self.scrape_history_file):
            try:
                with open(self.scrape_history_file, "r") as f:
                    self.scrape_history = json.load(f)
            except Exception:
                self.scrape_history = []

    def _save_data(self):
        os.makedirs("data", exist_ok=True)
        with open(self.scraped_articles_file, "w") as f:
            json.dump(self.scraped_articles, f, indent=2)
        with open(self.training_data_file, "w") as f:
            json.dump(self.training_data, f, indent=2)
        with open(self.scrape_history_file, "w") as f:
            json.dump(self.scrape_history, f, indent=2)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _article_hash(headline: str, body: str) -> str:
        return hashlib.md5(f"{headline}:{body}".encode()).hexdigest()

    def _get_article_hash(self, headline: str, body: str) -> str:
        return self._article_hash(headline, body)

    def _fetch_xml(self, url: str) -> Optional[str]:
        """Fetch raw XML from a URL."""
        try:
            if self._http:
                resp = self._http.get(url)
                resp.raise_for_status()
                return resp.text
            else:
                req = urllib.request.Request(url,
                    headers={"User-Agent": "AZAN-AI/2.1"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _parse_rss(self, xml_text: str, category: str) -> List[Dict]:
        """Parse RSS XML into article dicts."""
        articles = []
        try:
            root = ET.fromstring(xml_text)
            # Handle both RSS 2.0 and Atom
            items = root.findall(".//item") or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry")

            for item in items[:10]:  # Cap at 10 per feed
                headline = ""
                body = ""

                # RSS 2.0
                title_el = item.find("title")
                desc_el = item.find("description")
                # Atom fallback
                if title_el is None:
                    title_el = item.find("{http://www.w3.org/2005/Atom}title")
                if desc_el is None:
                    desc_el = item.find("{http://www.w3.org/2005/Atom}summary")

                if title_el is not None and title_el.text:
                    headline = title_el.text.strip()
                if desc_el is not None and desc_el.text:
                    # Strip HTML tags simply
                    import re
                    body = re.sub(r"<[^>]+>", "", desc_el.text).strip()

                if not headline or len(headline) < 10:
                    continue

                if not body or len(body) < 20:
                    body = headline  # Use headline as body if no description

                h = self._article_hash(headline, body)
                if h in self.scraped_articles:
                    continue  # Skip duplicates

                articles.append({
                    "headline": headline,
                    "body": body[:500],  # Cap body length
                    "category": category,
                    "timestamp": datetime.now().isoformat(),
                    "hash": h,
                })
        except ET.ParseError as e:
            logger.warning(f"XML parse error: {e}")
        return articles

    # ── Public API ───────────────────────────────────────────────────────────

    def scrape_category(self, category: str) -> List[Dict]:
        """Scrape real RSS articles for one category."""
        feeds = RSS_FEEDS.get(category, [])
        new_articles: List[Dict] = []

        for feed_url in feeds:
            xml = self._fetch_xml(feed_url)
            if not xml:
                continue
            parsed = self._parse_rss(xml, category)
            for article in parsed:
                self.scraped_articles[article["hash"]] = article
                new_articles.append(article)
                logger.info(f"📰 NEW ({category}): {article['headline'][:60]}…")
            time.sleep(1)  # Rate limiting between feeds

        return new_articles

    def scrape_all_categories(self) -> int:
        """Scrape all RSS categories. Returns count of new articles."""
        total = 0
        logger.info(f"🌐 Scraping {len(self.categories)} live RSS categories…")

        for category in self.categories:
            try:
                articles = self.scrape_category(category)
                total += len(articles)
            except Exception as e:
                logger.error(f"Error scraping {category}: {e}")
            time.sleep(2)

        if total > 0:
            self._save_data()
            self.scrape_history.append({
                "timestamp": datetime.now().isoformat(),
                "articles_scraped": total,
                "total_articles": len(self.scraped_articles),
            })
            self._save_data()

        logger.info(f"✅ Scraped {total} new articles (total: {len(self.scraped_articles)})")
        return total

    def convert_to_training_data(self, articles: List[Dict]) -> List[Dict]:
        """Convert articles to training Q&A pairs."""
        pairs = []
        for article in articles:
            qa = self._generate_qa_from_article(article)
            pairs.extend(qa)
        self.training_data.extend(pairs)
        self._save_data()
        return pairs

    def _extract_claims(self, text: str) -> List[Dict]:
        """Call the backend API to extract atomic factual claims."""
        try:
            if not self._http:
                return []
            
            resp = self._http.post(
                "http://localhost:8000/api/extract-claims",
                json={"text": text},
                timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("claims", [])
        except Exception as e:
            logger.warning(f"Claims extraction failed: {e}")
            return []

    def _generate_qa_from_article(self, article: Dict) -> List[Dict]:
        """Generate Q&A training pairs from one article, incorporating deterministic claims."""
        headline = article.get("headline", "")
        body = article.get("body", "")
        category = article.get("category", "")
        qa: List[Dict] = []

        # 1. 🧬 Atomic Claim Extraction (The new "True Unsupervised" path)
        claims = self._extract_claims(f"{headline}. {body}")
        
        if claims:
            article["claims"] = claims # Store claims back in the article record
            for claim in claims:
                # Filter for high confidence claims
                if claim.get("confidence", 0) >= 0.7:
                    # Generate a question for this specific claim
                    question = f"What factual detail can you provide about {headline}?"
                    if claim.get("entities"):
                        entities_str = ", ".join(claim["entities"])
                        question = f"What is the role of {entities_str} in context of: {headline}?"

                    qa.append({
                        "question": question,
                        "ideal_answer": claim["text"],
                        "source": "deterministic_claim",
                        "category": category,
                        "timestamp": article.get("timestamp"),
                        "metadata": {
                            "type": claim.get("type"),
                            "entities": claim.get("entities"),
                            "time": claim.get("time_reference"),
                            "confidence": claim.get("confidence")
                        }
                    })

        # 2. 🗞️ Standard Contextual Q&A (Fallback/Complementary)
        # Q1: Basic Fact
        qa.append({
            "question": f"Summarize the latest news on {headline}.",
            "ideal_answer": body,
            "source": "rss_live",
            "category": category,
            "timestamp": article.get("timestamp"),
        })

        # Q2: Category Context
        qa.append({
            "question": f"How does the news about '{headline}' affect {category}?",
            "ideal_answer": f"This affects {category} by introducing the following: {body}",
            "source": "rss_live",
            "category": category,
            "timestamp": article.get("timestamp"),
        })

        return qa

    # ── Accessors ────────────────────────────────────────────────────────────

    def get_latest_articles(self, limit: int = 10) -> List[Dict]:
        articles = list(self.scraped_articles.values())
        articles.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return articles[:limit]

    def get_articles_by_category(self, category: str) -> List[Dict]:
        articles = [a for a in self.scraped_articles.values()
                    if a.get("category") == category]
        articles.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return articles

    def get_training_data_count(self) -> Dict:
        return {
            "total_articles": len(self.scraped_articles),
            "total_training_pairs": len(self.training_data),
            "categories": list(set(
                a.get("category") for a in self.scraped_articles.values()
            )),
            "last_scrape": self.scrape_history[-1] if self.scrape_history else None,
        }
