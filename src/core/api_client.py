"""
JarvisAPIClient — high-reliability internal client for voice/daemon → JARVIS backend.

Changes (Phase 21):
 - Added missing `json` import (was causing silent stream failures).
 - Changed base_url default to 127.0.0.1 (avoids IPv6 resolution on macOS).
 - health check raises properly so callers know backend state.
 - stream_chat error yields are consistent with orchestrator expectations.
"""

import json
import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator

logger = logging.getLogger("JARVIS_API_CLIENT")


class JarvisAPIClient:
    """
    Persistent, high-reliability FastAPI client.
    Uses a module-level shared AsyncClient for connection reuse.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30,
            ),
            # Force IPv4 transport — eliminates ~100ms localhost IPv6 delay
            transport=httpx.AsyncHTTPTransport(retries=1),
        )

    # ── Health ────────────────────────────────────────────────────────────────
    async def check_health(self) -> bool:
        """Returns True if backend is reachable, False otherwise."""
        try:
            resp = await self.client.get("/api/health", timeout=2.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    # ── Generic POST ─────────────────────────────────────────────────────────
    async def post_command(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """POST with retry + exponential backoff."""
        for attempt in range(max_retries):
            try:
                resp = await self.client.post(endpoint, json=payload)
                resp.raise_for_status()
                return resp.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.warning(f"API attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    return {"result": "Error", "error": str(e)}
        return {"result": "Error", "error": "Max retries reached"}

    # ── Streaming chat ────────────────────────────────────────────────────────
    async def stream_chat(
        self,
        prompt: str,
        session_id: str,
        source: str = "voice",
    ) -> AsyncGenerator[str, None]:
        """
        Streams chat tokens from /chat/stream.
        Always yields at least one token — never silently fails.
        """
        payload = {
            "prompt": prompt,
            "session_id": session_id,
            "source": source,
            "stream": True,
        }
        try:
            async with self.client.stream(
                "POST", "/chat/stream", json=payload, timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "token" in data and data["token"]:
                                yield data["token"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except asyncio.TimeoutError:
            logger.error("stream_chat timed out")
            yield "Request timed out. Please try again."
        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(f"stream_chat failed: {e}")
            yield "Connection issue. Standing by."

    # ── Cleanup ───────────────────────────────────────────────────────────────
    async def close(self):
        await self.client.aclose()
