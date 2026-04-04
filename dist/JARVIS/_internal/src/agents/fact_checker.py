import logging
from typing import List, Dict, Tuple
from src.core.llm_client import LocalLLMClient
from src.memory.vector_store import KnowledgeMemory

logger = logging.getLogger(__name__)

class FactChecker:
    """Verification agent that cross-references new claims against existing memory.
    
    Prevents hallucinated information from polluting the knowledge base by:
    1. Searching for semantically similar existing claims
    2. Using the LLM to detect contradictions
    3. Assigning a final confidence delta based on consistency
    """

    def __init__(self, llm: LocalLLMClient, memory: KnowledgeMemory):
        self.llm = llm
        self.memory = memory
        self.system_prompt = """
        You are a rigorous Fact-Checking agent for the AZAN knowledge base.
        You will be given:
        1. A NEW CLAIM to evaluate
        2. EXISTING KNOWLEDGE from our verified database

        Your task: Determine if the new claim is CONSISTENT, CONTRADICTS, or is UNRELATED to our existing knowledge.
        
        Respond with exact JSON:
        {
          "verdict": "consistent" | "contradiction" | "new_info",
          "confidence_adjustment": -0.5 to 0.5,  // Positive if it reinforces, negative if it contradicts
          "reason": "Brief explanation"
        }
        """

    async def verify_claim(self, claim_text: str) -> Tuple[bool, float, str]:
        """Verifies a single claim against memory. Returns (should_store, confidence, reason)."""
        
        # Search for semantically related existing knowledge
        existing = self.memory.search_claims(claim_text, top_k=3, require_verified=False)
        
        if not existing:
            # No conflicting knowledge exists — store as new info with slight conservatism
            return True, 0.6, "No existing knowledge to compare — treating as new info."

        # Build context for LLM evaluation
        existing_context = "\n".join([f"- {c['claim']}" for c in existing])
        
        prompt = f"""NEW CLAIM: {claim_text}

EXISTING KNOWLEDGE:
{existing_context}

Evaluate this claim against existing knowledge."""

        result = await self.llm.generate_json(self.system_prompt, prompt)
        
        verdict = result.get("verdict", "new_info")
        adjustment = float(result.get("confidence_adjustment", 0.0))
        reason = result.get("reason", "")

        if verdict == "contradiction":
            logger.warning(f"Claim rejected (contradiction): {claim_text[:60]}... Reason: {reason}")
            return False, 0.0, reason
        elif verdict == "consistent":
            # Reinforce confidence slightly
            return True, min(1.0, 0.8 + adjustment), reason
        else:
            # New information — store conservatively
            return True, max(0.0, 0.65 + adjustment), reason

    async def filter_claims(self, claims: List[str], source: str) -> List[Dict]:
        """Runs a batch of claims through fact-checking and filters the valid ones."""
        verified = []
        for claim in claims:
            should_store, confidence, reason = await self.verify_claim(claim)
            if should_store:
                verified.append({
                    "claim": claim,
                    "confidence": confidence,
                    "source": source,
                    "reason": reason
                })
        logger.info(f"Fact-check: {len(verified)}/{len(claims)} claims passed verification.")
        return verified
