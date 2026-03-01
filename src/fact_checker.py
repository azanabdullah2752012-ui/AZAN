"""
Fact-Checker Agent for AZAN — Phase 5
Verifies factual claims against the ChromaDB vector store and optionally queries
Ollama for reasoning chains. Returns verdicts: confirmed, disputed, unverified.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def fact_check(claim: str) -> Dict:
    """
    Check a factual claim against the knowledge base.

    Args:
        claim: A factual statement to verify

    Returns:
        Dict with verdict, confidence, supporting evidence, and reasoning
    """
    if not claim or len(claim.strip()) < 5:
        return {"verdict": "unverified", "confidence": 0, "reasoning": "Claim too short to verify."}

    # 1. Search vector store for supporting/contradicting evidence
    try:
        from src.semantic_search import get_vector_store
        vs = get_vector_store()
        results = vs.search(claim, limit=5)
    except Exception as e:
        logger.error(f"Fact-check vector search failed: {e}")
        return {"verdict": "unverified", "confidence": 0, "reasoning": f"Knowledge base unavailable: {e}"}

    if not results:
        return {
            "verdict": "unverified",
            "confidence": 0.1,
            "reasoning": "No relevant evidence found in the knowledge base for this claim.",
            "evidence": []
        }

    # 2. Score relevance
    top_similarity = results[0].get("similarity", 0)
    evidence_snippets = []
    for r in results[:3]:
        evidence_snippets.append({
            "headline": r.get("headline", ""),
            "excerpt": (r.get("body", "") or "")[:200],
            "similarity": r.get("similarity", 0)
        })

    # 3. Use Ollama for reasoning if we have evidence
    reasoning = ""
    verdict = "unverified"
    confidence = round(top_similarity, 2)

    if top_similarity >= 0.75:
        verdict = "confirmed"
        reasoning = f"High-confidence match found. The claim aligns with {len(results)} sources in the knowledge base."
    elif top_similarity >= 0.5:
        verdict = "partially_confirmed"
        reasoning = f"Moderate evidence found ({len(results)} partial matches). The claim may be partially accurate."
    else:
        verdict = "unverified"
        reasoning = f"Low relevance matches found (best: {top_similarity:.2f}). Cannot confirm or deny this claim."

    # 4. Try Ollama-based reasoning for richer output
    try:
        import httpx
        system_prompt = (
            "You are a fact-checking assistant. Given a claim and supporting evidence, "
            "determine if the claim is TRUE, PARTIALLY TRUE, or UNVERIFIED. "
            "Respond concisely in 2-3 sentences."
        )
        evidence_text = "\n".join([f"- {e['headline']}: {e['excerpt']}" for e in evidence_snippets])
        user_prompt = f"CLAIM: {claim}\n\nEVIDENCE FROM KNOWLEDGE BASE:\n{evidence_text}\n\nVerdict and reasoning:"

        with httpx.Client(timeout=20.0) as client:
            resp = client.post("http://127.0.0.1:11434/api/chat", json={
                "model": "llama3",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"num_predict": 200, "temperature": 0.3}
            })
            if resp.status_code == 200:
                reasoning = resp.json().get("message", {}).get("content", reasoning)
    except Exception as e:
        logger.warning(f"Ollama reasoning failed, using heuristic: {e}")

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
        "evidence": evidence_snippets,
        "claim": claim
    }
