"""
data_only_inference.py — Strict retrieval-grounded response engine.

Anti-hallucination pipeline:
  1. Embed user query
  2. FAISS top-k retrieval
  3. If max cosine score < SIMILARITY_THRESHOLD → hard refusal (no LLM call)
  4. Otherwise → build context-only prompt → call Ollama Llama3
  5. Return response + source attributions + similarity score

The system prompt explicitly forbids Llama3 from using any knowledge
outside the retrieved context. Zero speculation, zero hallucination.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a strict factual assistant. You ONLY answer based on the context provided below.

CRITICAL RULES:
- NEVER use knowledge from your training data.
- NEVER speculate, guess, or infer beyond what is explicitly stated in the context.
- NEVER make up facts, names, dates, or laws.
- If the context does not fully answer the question, say so clearly.
- Always cite the source title from the context in your response.
- Respond in clear, academic, policy-grade language.
- Keep responses concise and factual.

Context from verified knowledge base:
{context}
"""

REFUSAL = "No verified data available in the local knowledge base."


class DataOnlyInference:
    """
    Retrieval-grounded inference engine with hard anti-hallucination guardrails.
    """

    def __init__(
        self,
        vector_store,
        embedding_engine,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "llama3",
        ollama_timeout: int = 60,
        top_k: int = 5,
        similarity_threshold: float = 0.35,
    ):
        self.vector_store = vector_store
        self.embedding_engine = embedding_engine
        self.ollama_host = ollama_host
        self.ollama_model = ollama_model
        self.ollama_timeout = ollama_timeout
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(self, query: str) -> Dict[str, Any]:
        """
        Full chat pipeline: retrieve → check threshold → call Llama3.
        Returns dict with keys: answer, sources, similarity_score, latency_ms, refused.
        """
        t0 = time.monotonic()

        # Step 1: Retrieve relevant chunks
        results = self.search(query)

        if not results or results["max_score"] < self.similarity_threshold:
            return {
                "answer": REFUSAL,
                "sources": [],
                "similarity_score": results["max_score"] if results else 0.0,
                "latency_ms": int((time.monotonic() - t0) * 1000),
                "refused": True,
            }

        # Step 2: Build context string
        context_blocks = []
        for chunk in results["chunks"]:
            block = (
                f"[SOURCE: {chunk['source']} | TITLE: {chunk['title']}]\n"
                f"{chunk['content']}"
            )
            context_blocks.append(block)
        context = "\n\n---\n\n".join(context_blocks)

        # Step 3: Call Ollama Llama3
        try:
            answer = self._call_ollama(query, context)
        except Exception as e:
            logger.error("Ollama call failed: %s", e)
            answer = (
                f"(Ollama unavailable: {e})\n\n"
                "Retrieved context:\n" + context
            )

        return {
            "answer": answer,
            "sources": [
                {"title": c["title"], "source": c["source"], "category": c["category"]}
                for c in results["chunks"]
            ],
            "similarity_score": results["max_score"],
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "refused": False,
        }

    def search(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Pure semantic search: embed query → FAISS top-k.
        Returns dict with chunks and max_score.
        """
        if self.vector_store.count() == 0:
            return {"chunks": [], "max_score": 0.0}

        query_vec = self.embedding_engine.embed_single(query)
        raw_results: List[Tuple[float, Dict]] = self.vector_store.search(
            query_vec, top_k=self.top_k
        )

        if not raw_results:
            return {"chunks": [], "max_score": 0.0}

        max_score = max(score for score, _ in raw_results)
        chunks = []
        for score, meta in raw_results:
            chunks.append({
                "title": meta.get("title", "Unknown"),
                "source": meta.get("source", "Unknown"),
                "category": meta.get("category", "Unknown"),
                "content": meta.get("content", ""),
                "score": round(float(score), 4),
            })

        return {"chunks": chunks, "max_score": round(float(max_score), 4)}

    # ── Internal ──────────────────────────────────────────────────────────────

    def _call_ollama(self, query: str, context: str) -> str:
        """Send grounded prompt to Ollama Llama3. Raises on failure."""
        system = SYSTEM_PROMPT.format(context=context)
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": query},
            ],
            "stream": False,
            "options": {"num_predict": 512, "temperature": 0.1},
        }
        url = f"{self.ollama_host}/api/chat"
        with httpx.Client(timeout=self.ollama_timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
