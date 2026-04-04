import logging
from typing import List, Dict
from pydantic import BaseModel, ValidationError
from src.core.llm_client import LocalLLMClient

logger = logging.getLogger(__name__)

class Claim(BaseModel):
    subject: str
    predicate: str
    object: str
    context: str
    confidence: float

class KnowledgeExtractor:
    """Agent responsible for breaking down raw input into atomic factual claims."""
    
    def __init__(self, llm_client: LocalLLMClient):
        self.llm = llm_client
        self.system_prompt = """
        You are AZAN's highly precise JSON Knowledge Extractor.
        Your sole task is to analyze the user's text and break it down into strict, atomic factual claims.
        Each claim MUST be a standalone fact that is comprehensible without any surrounding context.
        Ignore conversational filler, opinions, or requests. Extract ONLY hard assertions or facts.
        
        Output exact JSON schema matching this format exactly:
        {
          "claims": [
            {
              "subject": "Main Entity (e.g. 'Albert Einstein')",
              "predicate": "Relationship/Action (e.g. 'was born in')",
              "object": "Target Entity/Value (e.g. '1879')",
              "context": "Original source sentence for exact context",
              "confidence": 0.9  // 0.0 to 1.0 based on how explicit the text is
            }
          ]
        }
        
        If no concrete facts are present, return: {"claims": []}
        Return ONLY valid JSON.
        """

    async def extract_claims(self, raw_text: str) -> List[Claim]:
        """Runs the payload through the LLM to get structured atomic claims."""
        if not raw_text or len(raw_text.strip()) < 5:
            return []
            
        prompt = f"Extract atomic factual claims from the following text:\n\n{raw_text}"
        
        logger.debug("Requesting JSON extraction from LLM...")
        result = await self.llm.generate_json(self.system_prompt, prompt)
        
        claims = []
        raw_claims = result.get("claims", [])
        
        for c in raw_claims:
            try:
                # Validate schema
                validated = Claim(**c)
                claims.append(validated)
            except ValidationError as e:
                logger.warning(f"Failed to validate extracted claim '{c}': {e}")
            except Exception as e:
                logger.error(f"Unexpected error validating claim: {e}")
                
        logger.info(f"Successfully extracted {len(claims)} atomic claims.")
        return claims

    def format_claim_for_vector_store(self, claim: Claim) -> str:
        """Flattens a structured claim into a clean string for optimal vector embedding."""
        return f"{claim.subject} {claim.predicate} {claim.object}. Context: {claim.context}"
