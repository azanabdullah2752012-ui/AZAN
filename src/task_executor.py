"""
Task Executor Agent for AZAN — Phase 5 + Phase 6b
Handles agentic commands: URL scraping, text summarization,
math solving, and physics problem solving.
"""

import logging
import hashlib
import re
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


def execute_task(command: str, args: Dict) -> Dict:
    """
    Execute an agentic task.

    Supported commands:
        - scrape: Fetch a URL, extract text, and index into vector store
        - summarize: Summarize text from the knowledge base on a topic
        - solve_math: Solve symbolic math (calculus, algebra, etc.)
        - solve_physics: Solve physics problems (kinematics, forces, etc.)
        - unit_convert: Convert between units

    Args:
        command: The command name
        args: Command arguments

    Returns:
        Dict with execution results
    """
    command = command.lower().strip()

    if command == "scrape":
        return _scrape_url(args.get("url", ""))
    elif command == "summarize":
        return _summarize_topic(args.get("topic", ""))
    elif command == "solve_math":
        return _solve_math_smart(args.get("expression", ""), args.get("task", "auto"))
    elif command == "solve_physics":
        return _solve_physics_task(args.get("problem", ""), args.get("domain", "auto"))
    elif command == "unit_convert":
        return _solve_physics_task(args.get("problem", ""), "unit_convert")
    else:
        return {"success": False, "result": f"Unknown command: {command}. Supported: scrape, summarize, solve_math, solve_physics, unit_convert"}


# ── Smart Math Solver ───────────────────────────────────────────────────────

def _solve_math_smart(expression: str, task: str = "auto") -> Dict:
    """Solve a math task with smart auto-detection."""
    if not expression:
        return {"success": False, "result": "Missing math expression."}

    try:
        from src.math_engine import get_math_engine
        engine = get_math_engine()
        res = engine.solve(expression, task)

        if res.get("success"):
            # Build a readable response
            steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(res.get("steps", [])))
            output = f"📐 Math Solution ({res['task']})\n"
            output += f"Expression: {expression}\n"
            if steps_text:
                output += f"Steps:\n{steps_text}\n"
            output += f"Result: {res['result']}"
            if res.get("latex"):
                output += f"\nLaTeX: {res['latex']}"

            return {"success": True, "result": output, "data": res}
        else:
            return {"success": False, "result": f"Math Error: {res.get('error')}"}
    except Exception as e:
        return {"success": False, "result": f"Execution error: {e}"}


# ── Physics Solver ──────────────────────────────────────────────────────────

def _solve_physics_task(problem: str, domain: str = "auto") -> Dict:
    """Solve a physics problem."""
    if not problem:
        return {"success": False, "result": "Missing physics problem description."}

    try:
        from src.physics_engine import get_physics_engine
        engine = get_physics_engine()
        res = engine.solve(problem, domain)

        if res.get("success"):
            steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(res.get("steps", [])))
            output = f"🔬 Physics Solution ({res.get('domain', domain)})\n"
            if steps_text:
                output += f"Steps:\n{steps_text}\n"
            output += f"Result: {res['result']}"

            return {"success": True, "result": output, "data": res}
        else:
            return {"success": False, "result": f"Physics Error: {res.get('error')}"}
    except Exception as e:
        return {"success": False, "result": f"Execution error: {e}"}


# ── Scraper ─────────────────────────────────────────────────────────────────

def _scrape_url(url: str) -> Dict:
    """Fetch a URL, extract text, and index into vector store."""
    if not url or not url.startswith("http"):
        return {"success": False, "result": "Invalid URL. Must start with http:// or https://"}

    try:
        import httpx
        with httpx.Client(timeout=15.0, follow_redirects=True,
                          headers={"User-Agent": "AZAN-Agent/3.0"}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        return {"success": False, "result": f"Failed to fetch URL: {e}"}

    # Extract text from HTML
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) < 50:
        return {"success": False, "result": "Could not extract meaningful text from the page."}

    # Chunk and index
    chunks = _chunk_text(text, 500)
    doc_id = hashlib.md5(url.encode()).hexdigest()[:12]

    try:
        from src.semantic_search import get_vector_store
        vs = get_vector_store()
        indexed = 0
        for i, chunk in enumerate(chunks[:20]):  # Cap at 20 chunks per URL
            article = {
                "id": f"web_{doc_id}_{i}",
                "headline": f"Scraped: {url[:60]}",
                "body": chunk,
                "source": url,
                "category": "web_scrape",
                "published_at": datetime.now().isoformat()
            }
            if vs.add_article(article):
                indexed += 1

        return {
            "success": True,
            "result": f"✓ Scraped and indexed {indexed} chunks from {url}",
            "url": url,
            "chunks_indexed": indexed,
            "text_length": len(text)
        }
    except Exception as e:
        return {"success": False, "result": f"Indexing failed: {e}"}


# ── Summarizer ──────────────────────────────────────────────────────────────

def _summarize_topic(topic: str) -> Dict:
    """Summarize knowledge on a topic from the vector store."""
    if not topic or len(topic) < 3:
        return {"success": False, "result": "Topic too short. Provide a more specific topic."}

    try:
        from src.semantic_search import get_vector_store
        vs = get_vector_store()
        results = vs.search(topic, limit=5)

        if not results:
            return {"success": False, "result": f"No knowledge found on '{topic}'."}

        context = "\n".join([
            f"- {r.get('headline', 'N/A')}: {(r.get('body', '') or '')[:200]}"
            for r in results
        ])

        # Use Ollama to summarize
        import httpx
        with httpx.Client(timeout=30.0) as client:
            resp = client.post("http://127.0.0.1:11434/api/chat", json={
                "model": "llama3",
                "messages": [
                    {"role": "system", "content": "Summarize the following knowledge concisely in a few paragraphs."},
                    {"role": "user", "content": f"Topic: {topic}\n\nKnowledge:\n{context}"}
                ],
                "stream": False,
                "options": {"num_predict": 300, "temperature": 0.4}
            })
            if resp.status_code == 200:
                summary = resp.json().get("message", {}).get("content", "")
                return {"success": True, "result": summary, "sources": len(results)}

        return {"success": False, "result": "LLM summarization failed."}
    except Exception as e:
        return {"success": False, "result": f"Summarization error: {e}"}


# ── Utilities ───────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 500) -> list:
    """Split text into chunks."""
    words = text.split()
    chunks = []
    current = []
    current_len = 0
    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
    if current:
        chunks.append(" ".join(current))
    return chunks
