import httpx
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LocalLLMClient:
    """Async wrapper for local Ollama inference."""
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Forces the LLM to output valid JSON for agent tasks."""
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "top_p": 0.9}
        }
        try:
            response = await self.client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return json.loads(data["response"])
        except Exception as e:
            logger.error(f"LLM JSON extraction failed: {e}")
            return {"error": str(e)}

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Synchronous text generation for background tasks."""
        import httpx
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.1, "top_p": 0.9}
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            logger.error(f"LLM Text generation failed: {e}")
            return ""

    async def generate_stream(self, system_prompt: str, user_prompt: str):
        """Yields chunks for UI streaming."""
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "options": {"temperature": 0.4}
        }
        async with self.client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line)
                        if "response" in chunk_data:
                            yield chunk_data["response"]
                    except:
                        continue
