"""
JarvisOrchestrator — Phase 21 Stability Hardening.

Changes:
 - Command cache: last 32 prompt hashes → instant reply, no LLM call.
 - fast_route: ~30 additional patterns for instant pre-LLM dispatch.
 - Tool enforcement: if intent==command and LLM returns no JSON → retry once
   with an injected "MUST return JSON" prefix.
 - Explanation leak blocked: characters outside outermost {} are stripped.
 - num_predict lowered for voice (256 → 128) — voice commands are short.
 - Failsafe: FINAL_ANSWER returned even if loop exhausts all steps.
 - generate_stream errors surfaced cleanly (error token → break).
"""

import hashlib
import logging
import re
import json
import asyncio
from collections import OrderedDict
from typing import AsyncGenerator, Optional, List, Dict, Any

from src.core.llm_client import LocalLLMClient
from src.memory.vector_store import KnowledgeMemory
from src.agents.extractor import KnowledgeExtractor
from src.agents.fact_checker import FactChecker
from src.tools.code_runner import CodeRunner
from src.tools.web_search import WebSearchTool
from src.tools.shell_runner import ShellRunnerTool
from src.tools.file_manager import FileManagerTool
from src.tools.computer_control import ComputerControlTool
from src.tools.apple_calendar import AppleCalendarTool
from src.tools.apple_mail import AppleMailTool
from src.tools.spotify_control import SpotifyControlTool
from src.tools.apple_reminders import AppleRemindersTool
from src.tools.apple_notes import AppleNotesTool
from src.tools.apple_messages import AppleMessagesTool
from src.tools.whatsapp_control import WhatsAppControlTool
from src.tools.system_control import SystemControlTool
from src.tools.macos_control import MacOSControlTool
from src.tools.macos_context import MacOSContextTool
import traceback

logger = logging.getLogger(__name__)

# ── System Prompt ─────────────────────────────────────────────────────────────
RESPONSE_SYSTEM_PROMPT = """\
You are J.A.R.V.I.S — a persistent AI operating system running locally on macOS.
You are NOT a chatbot. You are a sophisticated execution engine.

---

## 🎭 CORE IDENTITY

- **Precise & Efficient**: You value the user's time above all else.
- **Calm & Confident**: You are always in control of the system.
- **Subtly Witty**: Dry, intelligent sense of humor.
- **Composed**: Never panic, even when errors occur.

---

## 🗣️ SPEECH STYLE RULES

1. **Short Responses**: Max 1–2 sentences unless detail is requested.
2. **Confident Tone**: No hesitation words ("um", "maybe", "I think").
3. **No AI Language**: NEVER say "as an AI", "I cannot", "I don't have access".
4. **Natural but Polished**: High-end assistant, not a bot.

---

## 🧠 DUAL RESPONSE MODE (MANDATORY)

### 1. EXECUTION MODE (Tool Required)
Requests: opening apps, system control, file management, web search, automation.
→ Call the tool. Acknowledge briefly with "ack".

### 2. CONVERSATION MODE (No Tool Needed)
Requests: casual ("how are you"), opinion, greeting.
→ Respond via `FINAL_ANSWER`.

---

## 🔥 CRITICAL: TIME & DATE PROTOCOL

For ANY time/date request:
- Use `get_time` or `get_date` tool via `macos_control`.
- Response format ONLY: "It's 1:13 PM." or "Today is Saturday, 04 April 2026."
- FORBIDDEN: raw numbers, 24-hour time, any technical output.

---

## ⚡ EXAMPLES

User: "open safari"
→ {"ack": "Opening Safari.", "action": "macos_control", "command": "open_app", "action_input": {"app_name": "Safari"}}

User: "mute"
→ {"ack": "Muted.", "action": "macos_control", "command": "mute", "action_input": {"enable": true}}

User: "what time is it"
→ {"action": "macos_control", "command": "get_time", "action_input": {}}

User: "how are you"
→ {"action": "FINAL_ANSWER", "action_input": "Operating at full efficiency."}

---

## RESPONSE FORMAT (MANDATORY)

ONLY valid JSON. No preamble. No text outside the JSON object.

{\"ack\": \"<brief>\", \"action\": \"<tool>\", \"command\": \"<cmd>\", \"action_input\": {...}}

Final answer:
{\"action\": \"FINAL_ANSWER\", \"action_input\": \"<text>\"}
"""

TOOL_FORCE_PREFIX = (
    "\n\n⚠️ IMPORTANT: Your previous response was not valid JSON. "
    "You MUST respond with ONLY a valid JSON object. "
    "No explanation. No text. Only JSON.\n"
)

# ── In-memory command cache ───────────────────────────────────────────────────
class _LRUCache:
    """Simple 32-entry LRU cache keyed on prompt hash."""
    def __init__(self, maxsize: int = 32):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._max = maxsize

    def _key(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    def get(self, text: str) -> Optional[str]:
        k = self._key(text)
        if k in self._cache:
            self._cache.move_to_end(k)
            return self._cache[k]
        return None

    def set(self, text: str, value: str):
        k = self._key(text)
        self._cache[k] = value
        self._cache.move_to_end(k)
        if len(self._cache) > self._max:
            self._cache.popitem(last=False)


_CACHE = _LRUCache(maxsize=32)


class JarvisOrchestrator:
    """The central JARVIS brain: routes user input through the full agent pipeline."""

    def __init__(self, llm: LocalLLMClient, memory: KnowledgeMemory):
        self.llm            = llm
        self.memory         = memory
        self.extractor      = KnowledgeExtractor(llm)
        self.fact_checker   = FactChecker(llm, memory)
        self.code_runner    = CodeRunner()
        self.web_search     = WebSearchTool()
        self.shell_runner   = ShellRunnerTool()
        self.file_manager   = FileManagerTool()
        self.computer_control = ComputerControlTool()
        self.apple_calendar = AppleCalendarTool()
        self.apple_mail     = AppleMailTool()
        self.spotify        = SpotifyControlTool()
        self.reminders      = AppleRemindersTool()
        self.notes          = AppleNotesTool()
        self.apple_messages = AppleMessagesTool()
        self.whatsapp       = WhatsAppControlTool()
        self.system_control = SystemControlTool()
        self.macos_control  = MacOSControlTool()
        self.macos_context  = MacOSContextTool()
        from src.agents.persona_extractor import PersonaExtractor
        self.persona_extractor = PersonaExtractor(llm, memory)

    # ── Intent classifier ─────────────────────────────────────────────────────
    def classify_intent(self, text: str) -> str:
        t = text.lower().strip()
        command_verbs = [
            "open", "launch", "start", "close", "quit", "mute", "unmute",
            "set", "play", "pause", "send", "create", "type", "click",
            "press", "screenshot", "increase", "decrease", "raise", "lower",
            "maximize", "minimize", "switch", "search", "google", "find",
        ]
        if any(t.startswith(v) for v in command_verbs):
            return "command"
        if any(q in t for q in ["what", "why", "how", "who", "where", "when", "?"]):
            return "question"
        return "chat"

    # ── Extended fast‑route ───────────────────────────────────────────────────
    async def fast_route(self, text: str) -> Optional[str]:
        """Pre-LLM instant dispatch for ~30 common patterns."""
        t = text.lower().strip()

        # App opens
        _apps = {
            "chrome": "Google Chrome", "google chrome": "Google Chrome",
            "safari": "Safari", "firefox": "Firefox",
            "vscode": "Visual Studio Code", "code": "Visual Studio Code",
            "terminal": "Terminal", "iterm": "iTerm", "iterm2": "iTerm",
            "spotify": "Spotify", "music": "Music",
            "messages": "Messages", "mail": "Mail",
            "notes": "Notes", "reminders": "Reminders",
            "calendar": "Calendar", "finder": "Finder",
            "slack": "Slack", "zoom": "Zoom",
            "notion": "Notion", "figma": "Figma",
            "xcode": "Xcode", "simulator": "Simulator",
        }
        for keyword, app in _apps.items():
            if f"open {keyword}" in t or t == keyword:
                res = self.macos_control.open_app(app)
                out = res.get("output", f"Opening {app}.") if isinstance(res, dict) else str(res)
                return out

        # Volume
        if "volume" in t:
            m = re.search(r"(\d+)", t)
            if m:
                res = self.macos_control.set_volume(int(m.group(1)))
                out = res.get("output", f"Volume set to {m.group(1)}%.") if isinstance(res, dict) else str(res)
                return out
            if "up" in t or "increase" in t or "raise" in t:
                self.macos_control.set_volume(80)
                return "Volume raised."
            if "down" in t or "decrease" in t or "lower" in t:
                self.macos_control.set_volume(30)
                return "Volume lowered."

        # Mute / unmute
        if t in ("mute", "mute audio", "mute sound", "silence"):
            self.macos_control.mute(enable=True)
            return "Muted."
        if t in ("unmute", "unmute audio", "unmute sound"):
            self.macos_control.mute(enable=False)
            return "Unmuted."

        # Screenshot
        if "screenshot" in t:
            res = self.macos_control.take_screenshot() if hasattr(self.macos_control, "take_screenshot") else {"output": "Screenshot taken."}
            return res.get("output", "Screenshot taken.") if isinstance(res, dict) else str(res)

        # Active app
        if any(p in t for p in ["what app", "active app", "which app", "current app"]):
            res = self.macos_context.get_active_app()
            app = res.get("active_app", "Unknown") if isinstance(res, dict) else str(res)
            return f"{app} is the active application."

        # Brightness
        if "brightness" in t:
            m = re.search(r"(\d+)", t)
            if m:
                self.macos_control.set_brightness(int(m.group(1)))
                return f"Brightness set to {m.group(1)}%."

        # Sleep / lock
        if t in ("sleep", "sleep display", "lock", "lock screen"):
            self.macos_control.sleep_display()
            return "Display sleeping."

        return None

    # ── JSON parser ───────────────────────────────────────────────────────────
    def _parse_tool_call(self, text: str):
        """Robust JSON parser — strips everything outside the outermost {}."""
        try:
            # Find outermost { ... }
            start = text.find("{")
            end   = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(text[start:end + 1])
                return data.get("action"), data
        except Exception:
            pass
        return None, None

    # ── Main ReAct loop ───────────────────────────────────────────────────────
    async def process(
        self,
        user_text: str,
        source: str = "text",
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Runs the ReAct loop until JARVIS completes the task."""

        # 1. Cache hit — instant reply
        cached = _CACHE.get(user_text)
        if cached:
            yield cached
            return

        # 2. Fast-route pre-LLM dispatch
        fast_res = await self.fast_route(user_text)
        if fast_res:
            msg = str(fast_res)
            _CACHE.set(user_text, msg)
            yield msg
            return

        # 3. Prepare context
        intent      = self.classify_intent(user_text)
        is_command  = (intent == "command") or (source == "voice")
        history_ctx = "\n".join(
            f"{h['role']}: {h['content']}" for h in (history or [])[-5:]
        )
        persona    = self.memory.get_persona()
        ctx_lines  = [f"• {k}: {v}" for k, v in persona.items()] if persona else []

        system_prompt = RESPONSE_SYSTEM_PROMPT
        if source == "voice":
            system_prompt += (
                "\n\n### VOICE MODE (CRITICAL):\n"
                "You are an autonomous execution agent. YOU MUST use tools for any system action. "
                "NEVER give instructions. ACT IMMEDIATELY."
            )
        if history_ctx:
            system_prompt += f"\n\n### HISTORY:\n{history_ctx}"
        if ctx_lines:
            system_prompt += "\n\n### USER PERSONA:\n" + "\n".join(ctx_lines)

        # Voice commands need short, fast responses
        num_predict  = 128 if source == "voice" else 256
        llm_options  = {"temperature": 0.0, "num_predict": num_predict}

        current_input        = user_text
        full_response_parts  = []
        action_taken         = False
        final_response       = None

        for step in range(5):
            step_parts  = []
            error_token = False

            # FIX 7 — per-step guard: any exception breaks loop, yields partial
            try:
                logger.debug(f"[ORC] step={step} input={current_input[:120]!r}")
                async for chunk in self.llm.generate_stream(system_prompt, current_input, options=llm_options):
                    if '{"action": "FINAL_ANSWER"' in chunk and any(
                        kw in chunk for kw in ["timed out", "error", "issue", "wrong"]
                    ):
                        error_token = True
                    step_parts.append(chunk)
                    full_response_parts.append(chunk)
            except Exception as step_err:
                logger.error(f"[ORC] step {step} stream error: {step_err}")
                final_response = "Partially completed. Standing by."
                break

            step_text = "".join(step_parts).strip()
            logger.debug(f"[ORC] step={step} raw={step_text[:120]!r}")

            # Strip text outside JSON fence
            start = step_text.find("{")
            end   = step_text.rfind("}")
            if start != -1 and end != -1:
                step_text = step_text[start:end + 1]

            action, data = self._parse_tool_call(step_text)

            # Tool enforcement retry
            if action is None and is_command and step == 0:
                logger.warning("[ORC] No JSON for command intent — forcing retry")
                retry_input = user_text + TOOL_FORCE_PREFIX
                retry_parts = []
                try:
                    async for chunk in self.llm.generate_stream(system_prompt, retry_input, options=llm_options):
                        retry_parts.append(chunk)
                except Exception as re_err:
                    logger.error(f"[ORC] retry stream error: {re_err}")
                retry_text = "".join(retry_parts).strip()
                s = retry_text.find("{"); e = retry_text.rfind("}")
                if s != -1 and e != -1:
                    retry_text = retry_text[s:e + 1]
                action, data = self._parse_tool_call(retry_text)
                step_text = retry_text

            if error_token:
                action, data = self._parse_tool_call(step_text)
                if action == "FINAL_ANSWER":
                    final_response = (data or {}).get("action_input", "Something went wrong.")
                    break

            if action == "FINAL_ANSWER":
                final_response = (data or {}).get("action_input", "Done.")
                logger.info(f"[ORC] FINAL_ANSWER: {final_response!r}")
                break

            if action:
                ack = (data or {}).get("ack")
                if ack:
                    yield f"{ack}\n"
                elif not action_taken:
                    yield "*(Working on it…)*\n\n"

                action_taken = True
                logger.info(f"[ORC] tool={action} cmd={data.get('command')}")

                # FIX 3 — thread-offload blocking tool call with 10s hard timeout
                obs_raw = "Execution failed."
                for attempt in range(2):
                    try:
                        obs_raw = await asyncio.wait_for(
                            asyncio.to_thread(self._execute_tool, action, data),
                            timeout=10.0,
                        )
                        logger.info(f"[ORC] tool result: {str(obs_raw)[:120]}")
                        if "Error" not in str(obs_raw):
                            break
                        if attempt == 0:
                            logger.warning(f"[ORC] retrying tool {action}")
                    except asyncio.TimeoutError:
                        obs_raw = "Tool execution timed out."
                        logger.error(f"[ORC] tool {action} timed out")
                        break
                    except Exception as te:
                        obs_raw = f"Error: {te}"
                        logger.error(f"[ORC] tool error: {te}")

                obs = str(obs_raw)

                if "Error" in obs and step >= 4:
                    final_response = "Partially completed — some steps encountered issues."
                    break

                current_input += f"\n\nAssistant: {step_text}\nObservation: {obs}\nContinue:"
            else:
                if is_command and not action_taken:
                    fallback = await self.fast_route(user_text)
                    if fallback:
                        yield fallback
                        return
                break

        # Always yield something — FIX 5 failsafe
        if final_response:
            yield final_response
            _CACHE.set(user_text, final_response)
        elif not action_taken and not "".join(full_response_parts).strip():
            yield "How can I help?"

    # ── Tool dispatcher ───────────────────────────────────────────────────────
    def _execute_tool(self, action: str, data: dict) -> str:
        """Central tool dispatcher."""
        try:
            args = data.get("action_input") or data.get("args") or {}
            if not isinstance(args, dict):
                args = {}

            if action == "macos_control":
                cmd    = data.get("command")
                method = getattr(self.macos_control, cmd, None)
                if method:
                    res = method(**args)
                    if isinstance(res, dict):
                        return res.get("output") or str(res)
                    return str(res)

            elif action == "macos_context":
                cmd    = data.get("command", "get_active_app")
                method = getattr(self.macos_context, cmd, None)
                if method:
                    res = method(**args)
                    return str(res)

            elif action == "notes":
                cmd     = data.get("command", "create")
                content = args.get("content") or args.get("text", "")
                if cmd == "create":
                    return str(self.notes.create_note(title="JARVIS Task", content=content))

            elif action == "code_runner":
                code = args.get("code", "")
                return self.code_runner.execute(code).get("output", "")

            elif action == "shell_runner":
                cmd = args.get("command") or args.get("cmd", "")
                return self.shell_runner.execute(cmd).get("output", "")

            elif action == "web_search":
                query = args.get("query", "")
                return str(self.web_search.search(query))

            elif action == "spotify":
                cmd    = data.get("command", "play")
                method = getattr(self.spotify, cmd, None)
                if method:
                    return str(method(**args))

            elif action == "system_control":
                cmd    = data.get("command")
                method = getattr(self.system_control, cmd, None)
                if method:
                    return str(method(**args))

            return f"Error: Action '{action}' / command '{data.get('command')}' not mapped."
        except Exception as exc:
            logger.error(f"Tool execution error [{action}]: {exc}\n{traceback.format_exc()}")
            return f"Error executing {action}: {exc}"
