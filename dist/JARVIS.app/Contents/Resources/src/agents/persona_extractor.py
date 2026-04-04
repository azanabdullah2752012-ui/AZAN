import logging
from typing import Dict, Optional, Any
import json
from src.core.llm_client import LocalLLMClient
from src.memory.vector_store import KnowledgeMemory

logger = logging.getLogger(__name__)

PERSONA_SYSTEM_PROMPT = """
You are JARVIS's background persona extraction engine.
Analyze the user's latest statement. Extract ONLY new, permanent facts about the user's identity, preferences, or environment.

Examples of things to extract:
- "My name is John" -> {"name": "John"}
- "I prefer dark mode" -> {"ui_preference": "dark mode"}
- "I code in Python" -> {"primary_language": "Python"}
- "I live in New York" -> {"location": "New York"}

Examples of things to IGNORE (temporary or irrelevant):
- "Turn on the lights" -> {}
- "What is the weather?" -> {}
- "I am tired right now" -> {}

Output ONLY a JSON dictionary of new traits. If none are found, output {}. Do not narrate.
"""

class PersonaExtractor:
    """
    Background worker that analyzes user inputs to deduce and store long-term persona traits.
    """
    
    def __init__(self, llm: LocalLLMClient, memory: KnowledgeMemory):
        self.llm = llm
        self.memory = memory

    def analyze_and_store(self, user_message: str):
        """Analyze a user message and store any deduced persona traits."""
        if len(user_message.strip()) < 5:
            return  # Too short to contain meaningful persona data
            
        try:
            response = self.llm.generate_text(
                system_prompt=PERSONA_SYSTEM_PROMPT,
                user_prompt=f"Extract persona traits from this user message:\n\"{user_message}\""
            )
            
            # Clean and parse JSON
            clean = response.strip()
            if clean.startswith('```json'):
                clean = clean[7:]
            if clean.startswith('```'):
                clean = clean[3:]
            if clean.endswith('```'):
                clean = clean[:-3]
            clean = clean.strip()
            
            if not clean or clean == "{}":
                return
                
            traits: Dict[str, str] = json.loads(clean)
            
            # Store in SQLite
            for key, value in traits.items():
                if isinstance(value, str):
                    self.memory.set_persona_trait(key, value)
                    logger.info(f"🧠 Deduced persona trait: {key} = {value}")
                    
        except json.JSONDecodeError:
            logger.debug(f"PersonaExtractor failed to parse JSON: {response}")
        except Exception as e:
            logger.error(f"PersonaExtractor error: {e}")
