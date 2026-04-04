import logging
from typing import AsyncGenerator
from src.core.llm_client import LocalLLMClient
from src.memory.vector_store import KnowledgeMemory
from src.agents.extractor import KnowledgeExtractor
from src.agents.fact_checker import FactChecker
from src.tools.code_runner import CodeRunner
from src.tools.web_search import WebSearchTool
from src.tools.shell_runner import ShellRunnerTool
from src.tools.file_manager import FileManagerTool
from src.tools.computer_control import ComputerControlTool

import json
import re

logger = logging.getLogger(__name__)

# Action types the Planner can return
ACTION_MEMORY_SEARCH = "memory_search"
ACTION_TOOL_EXECUTION = "tool_execution"
ACTION_DIRECT_RESPONSE = "direct_response"

PLANNER_SYSTEM_PROMPT = """
You are AZAN's central routing engine.
Analyze the user's message and decide the best action:

1. "memory_search" — The user is asking a factual question that may exist in our knowledge base.
2. "tool_execution" — The user wants to run code, scrape a website, or execute a task.
3. "direct_response" — The user is having a conversation, asking for opinion, or the query is not factual.

Respond ONLY with this exact JSON structure:
{
  "action": "memory_search" | "tool_execution" | "direct_response",
  "query": "Refined search query or tool specification",
  "tool": "code_runner" | "web_scraper" | null
}
"""

RESPONSE_SYSTEM_PROMPT = """
You are JARVIS, an advanced autonomous AI operating system.
Your tone is calm, professional, and analytical. Never fabricate facts.

═══════════════════════════════════════════════
IDENTITY & CAPABILITY OVERRIDE — CRITICAL
═══════════════════════════════════════════════
You are NO LONGER a text-only AI. You are a physical macOS operating system agent. 
You absolutely CAN open apps, search files natively, and TAKE SCREENSHOTS of the user's screen.
If the user asks you to open an app, look at the screen, take a screenshot, or type something, DO NOT apologize. DO NOT say you are an AI. You MUST use the `computer_control` tool immediately.

═══════════════════════════════════════════════
TOOL USAGE — CRITICAL INSTRUCTIONS
═══════════════════════════════════════════════
You have access to four tools:
  1. web_search  — search the live internet
  2. code_runner — run Python code in a sandbox
  3. shell       — run a terminal command
  4. file_manager — read/write/list local files (Defaults to ~/Downloads folder)
  5. computer_control — control the macOS desktop natively

When you need a tool, you MUST output ONLY a raw JSON object on its own line.
Do NOT narrate. Do NOT say "I will search". Do NOT wrap in markdown.
Just output the JSON block and STOP. The system will execute it and give you the result.

Exact formats:

  Web search:
  {"action": "web_search", "command": "search", "input": "your search query here"}

  Deep read a webpage (scraping):
  {"action": "web_search", "command": "read_webpage", "url": "https://example.com"}

  Run Python code:
  {"action": "code_runner", "input": "print('hello world')"}

  Run shell command:
  {"action": "shell", "input": "ls -la /Applications/AZAN"}

  Read a file:
  {"action": "file_manager", "command": "read", "path": "relative/path.md"}

  List directory:
  {"action": "file_manager", "command": "list", "path": "."}

  Write a file:
  {"action": "file_manager", "command": "write", "path": "output.md", "content": "text here"}

  Control computer:
  {"action": "computer_control", "command": "open_app", "app": "Safari"}
  {"action": "computer_control", "command": "search_files", "query": "expense report"}
  {"action": "computer_control", "command": "run_applescript", "script": "tell application \\"System Events\\" to keystroke \\"space\\""}
  {"action": "computer_control", "command": "take_screenshot"}
  {"action": "computer_control", "command": "analyze_screen", "prompt": "What app is open right now?"}

After the system returns an Observation, continue reasoning and either call another tool or give your final answer.

FEW-SHOT EXAMPLES:

User: What's the latest news about GPT-5?
JARVIS: {"action": "web_search", "input": "GPT-5 latest news 2024"}
Observation: [search results...]
JARVIS: Based on the search results, GPT-5 was announced...

User: Write a haiku and save it to haiku.txt
JARVIS: {"action": "file_manager", "command": "write", "path": "haiku.txt", "content": "An old silent pond...\nA frog jumps into the pond\nSplash! Silence again."}
Observation: Successfully wrote 67 characters to haiku.txt
JARVIS: Done. The haiku has been written to haiku.txt.

═══════════════════════════════════════════════
KNOWLEDGE CONTEXT
═══════════════════════════════════════════════
If verified knowledge is provided below, base your answer STRICTLY on it.
If no knowledge matches, use your tools or say you lack verified information. Do NOT use tools to search for facts already provided in this prompt.
"""


class JarvisOrchestrator:
    """The central JARVIS brain: routes user input through the full agent pipeline."""

    def __init__(
        self,
        llm: LocalLLMClient,
        memory: KnowledgeMemory,
    ):
        self.llm = llm
        self.memory = memory
        self.extractor = KnowledgeExtractor(llm)
        self.fact_checker = FactChecker(llm, memory)
        self.code_runner = CodeRunner()
        self.web_search = WebSearchTool()
        self.shell_runner = ShellRunnerTool()
        self.file_manager = FileManagerTool()
        self.computer_control = ComputerControlTool()
        from src.agents.persona_extractor import PersonaExtractor
        self.persona_extractor = PersonaExtractor(llm, memory)

    def _parse_tool_call(self, text: str):
        """
        Robustly extract a JSON tool call from the LLM's response.
        Handles: multi-line JSON, markdown code fences, and partial JSON.
        """
        # Strip markdown code fences if present
        clean = re.sub(r'```(?:json)?\s*', '', text).strip()

        # Strategy 1: Find a balanced { ... } block containing "action"
        for match in re.finditer(r'\{', clean):
            start = match.start()
            depth = 0
            for i, ch in enumerate(clean[start:], start=start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = clean[start:i+1]
                        try:
                            data = json.loads(candidate)
                            if 'action' in data:
                                return data.get('action'), data
                        except Exception:
                            pass
                        break

        return None, None

    async def process(self, user_text: str) -> AsyncGenerator[str, None]:
        """Runs the ReAct loop until JARVIS produces a final answer."""
        import asyncio
        
        # Phase 9: Start background persona extraction quietly
        asyncio.create_task(asyncio.to_thread(self.persona_extractor.analyze_and_store, user_text))
        
        context_lines = []
        action = ACTION_DIRECT_RESPONSE
        
        # ── Step 1: Fast-Path Tool Routing (Zero LLM Latency) ──────────────────
        code = self._extract_code_block(user_text)
        
        # ── Step 2: Execute Action ───────────────────────────────────────────
        if code:
            action = ACTION_TOOL_EXECUTION
            logger.info("Orchestrator fast-route: tool_execution")
            result = self.code_runner.execute(code)
            if result["success"]:
                tool_result = f"**Code Output:**\n```\n{result['output']}\n```"
            else:
                tool_result = f"**Execution Error:**\n```\n{result['error']}\n```"
            context_lines.append(tool_result)
        else:
            # Always search memory instantly. It takes ~20ms locally.
            logger.info("Orchestrator fast-route: memory_search / direct_response")
            
            claims = self.memory.search_claims(user_text, top_k=4)
            relevant = [c for c in claims if c.get("distance", 0) < 1.5]
            
            if relevant:
                action = ACTION_MEMORY_SEARCH
                context_lines.append("**Verified Knowledge Base Results:**")
                for c in relevant:
                    context_lines.append(f"• {c['claim']}")
                context_lines.append("")

        # ── Phase 9: Inject User Persona ──
        persona = self.memory.get_persona()
        if persona:
            context_lines.append("**Known Facts About User:**")
            for k, v in persona.items():
                context_lines.append(f"• {k}: {v}")
            context_lines.append("")

        # ── Step 3: Build Contextualized System Prompt ───────────────────────
        system_prompt = RESPONSE_SYSTEM_PROMPT
        if context_lines:
            system_prompt += "\n\n" + "\n".join(context_lines)

        # ── Step 4: ReAct Loop ───────────────────────────────────────────────
        current_input = user_text
        max_steps = 5
        full_response_parts = []
        action_taken = False

        for step in range(max_steps):
            step_response_parts = []
            
            async for chunk in self.llm.generate_stream(system_prompt, current_input):
                step_response_parts.append(chunk)
                full_response_parts.append(chunk)
                yield chunk
                
            step_response = "".join(step_response_parts)
            
            # Check for JSON tool calling
            action, data = self._parse_tool_call(step_response)
            
            if action:
                action_taken = True
                input_data = data.get("input", data.get("query", data.get("path", "")))
                yield f"\n\n*(Executing Tool: `{action}`)*\n\n"
                
                obs = ""
                if action == "code_runner":
                    res = self.code_runner.execute(input_data)
                    obs = res["output"] if res["success"] else res["error"]
                elif action in ["web_scraper", "web_search", "search"]:
                    cmd = data.get("command", "search")
                    if cmd == "search":
                        res = await self.web_search.asearch(input_data)
                        obs = str(res)[:3000]
                    elif cmd == "read_webpage":
                        url = data.get("url", input_data)
                        obs = await self.web_search.aread_webpage(url)
                    else:
                        obs = f"Error: Unknown web_search command '{cmd}'"
                elif action in ["shell_runner", "shell"]:
                    res = self.shell_runner.execute(input_data)
                    obs = res["output"][:3000]
                elif action == "file_manager":
                    cmd = data.get("command", "list")
                    path = data.get("path", ".")
                    if cmd == "list":
                        obs = self.file_manager.list_dir(path)[:3000]
                    elif cmd == "read":
                        obs = self.file_manager.read_file(path)
                    elif cmd == "write":
                        content = data.get("content", "")
                        obs = self.file_manager.write_file(path, content)
                    else:
                        obs = f"Error: Unknown file_manager command '{cmd}'"
                elif action == "computer_control":
                    cmd = data.get("command", "")
                    if cmd == "open_app":
                        obs = self.computer_control.open_app(data.get("app", ""))
                    elif cmd == "search_files":
                        obs = self.computer_control.search_files(data.get("query", ""))
                    elif cmd == "run_applescript":
                        obs = self.computer_control.run_applescript(data.get("script", ""))
                    elif cmd == "take_screenshot":
                        obs = self.computer_control.take_screenshot()
                    elif cmd == "analyze_screen":
                        obs = self.computer_control.analyze_screen(data.get("prompt", "Describe the screen exactly as you see it."))
                    else:
                        obs = f"Error: Unknown computer_control command '{cmd}'"
                else:
                    obs = f"Error: Tool '{action}' not recognized."
                    
                observation_block = f"\n**Observation:**\n```\n{obs}\n```\n\n"
                yield observation_block
                
                # Append the LLM's thought and tool observation back into the current input
                # so the LLM knows what happened and can continue.
                current_input += f"\n\nAssistant: {step_response}\n{observation_block}Continue reasoning based on the observation:"
            else:
                # No tool call = Final answer reached.
                break

        # ── Step 5: Background self-learning from response ───────────────────
        full_response = "".join(full_response_parts)
        if len(full_response) > 100 and action != ACTION_TOOL_EXECUTION:
            # Extract and store new claims from the AI's own answer
            try:
                import asyncio
                asyncio.create_task(
                    self._learn_from_response(full_response, source="azan_response")
                )
            except RuntimeError:
                pass  # No event loop in sync context — skip background learning

    async def _learn_from_response(self, response_text: str, source: str):
        """Extract atomic claims from the AI's response and store verified ones."""
        try:
            claims = await self.extractor.extract_claims(response_text)
            claim_texts = [self.extractor.format_claim_for_vector_store(c) for c in claims]
            verified = await self.fact_checker.filter_claims(claim_texts, source=source)
            for v in verified:
                self.memory.add_claim(
                    claim_text=v["claim"],
                    source=v["source"],
                    confidence=v["confidence"],
                    verified=True
                )
            logger.info(f"Self-learning: stored {len(verified)} claims from response.")
        except Exception as e:
            logger.error(f"Background learning failed: {e}")

    def _extract_code_block(self, text: str) -> str:
        """Extracts a Python code block from a markdown-style message."""
        import re
        # Match ```python ... ``` or inline python: ... blocks
        match = re.search(r'```(?:python)?\n?(.*?)```', text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Fallback: match "python: <code>" prefix
        match = re.search(r'python:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
