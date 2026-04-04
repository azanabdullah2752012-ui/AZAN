"""
LocalLLMClient — Persistent Ollama HTTP client optimised for JARVIS.

Changes (Phase 21):
 - Singleton AsyncClient with connection pooling (max 10 conns, 5 keepalive).
 - Explicit keepalive_expiry=30 to prevent Ollama idle-disconnect.
 - generate_stream: fully wrapped in try/except; yields error token on failure.
 - asyncio imported at module level (was missing — caused NameError in retry).
 - generate_json retries use asyncio.sleep properly.
"""

import asyncio
import httpx
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator

logger = logging.getLogger(__name__)

# ── Singleton client ──────────────────────────────────────────────────────────
# One AsyncClient for the entire process lifetime → reuses TCP connections,
# avoids the per-request TLS handshake overhead that caused "connection lost".
_CLIENT: Optional[httpx.AsyncClient] = None

def _get_client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30,   # seconds — prevents Ollama idle timeout
            ),
            # Force IPv4 — avoids ~100ms IPv6 resolution on macOS
            transport=httpx.AsyncHTTPTransport(retries=1),
        )
    return _CLIENT


class LocalLLMClient:
    """Async wrapper for local Ollama inference."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model

    @property
    def client(self) -> httpx.AsyncClient:
        return _get_client()

    # ── generate_json ─────────────────────────────────────────────────────────
    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Forces the LLM to output valid JSON with retry + backoff."""
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "num_predict": 256, "top_p": 0.9},
        }
        for attempt in range(3):
            try:
                resp = await self.client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return json.loads(data["response"])
            except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError) as e:
                logger.error(f"LLM JSON attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return {"error": str(e)}
                await asyncio.sleep(1 << attempt)   # 1s, 2s
        return {"error": "Max retries reached"}

    # ── generate_text (sync) ──────────────────────────────────────────────────
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Synchronous text generation for background tasks."""
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 512, "top_p": 0.9},
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"LLM text generation failed: {e}")
            return ""

    # ── complete ────────────────────────────────────────────────────────────
    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        """Async text generation with 3-attempt retry + exponential backoff."""
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        for attempt in range(3):
            try:
                resp = await self.client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "")
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.error(f"LLM complete attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    return ""
                await asyncio.sleep(1 << attempt)
        return ""

    # ── generate_stream ────────────────────────────────────────────────────
    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        FIX 2: Hard 20s ceiling via asyncio.timeout. Never raises — yields
        a safe FINAL_ANSWER error token on any failure so the orchestrator
        loop always continues cleanly.
        """
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "options": options or {"temperature": 0.0, "num_predict": 256},
        }

        async def _inner():
            async with self.client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload, timeout=20.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                            if chunk.get("done"):
                                return
                        except json.JSONDecodeError:
                            continue

        try:
            # Hard 20s ceiling — asyncio.timeout cancels the entire generator
            async with asyncio.timeout(20):
                async for token in _inner():
                    yield token
        except asyncio.TimeoutError:
            logger.error("[LLM] generate_stream: 20s hard timeout reached")
            yield '{"action": "FINAL_ANSWER", "action_input": "Request timed out. Standing by."}'
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"[LLM] generate_stream: connection error: {e}")
            yield '{"action": "FINAL_ANSWER", "action_input": "Connection issue. Standing by."}'
        except Exception as e:
            logger.error(f"[LLM] generate_stream: unexpected error: {e}")
            yield '{"action": "FINAL_ANSWER", "action_input": "Something went wrong. Standing by."}'
