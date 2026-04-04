import json
import re
import logging

logger = logging.getLogger(__name__)

class OutputParser:
    """Strict JSON enforcement parser for the ReAct loop."""

    @staticmethod
    def parse_tool_call(text: str):
        """
        Extract ONLY the FIRST valid JSON object from the text.
        Discards everything after the closing brace to prevent chained outputs.
        """
        # Block invalid trailing or malformed structures
        if "Observation:" in text or "JARVIS:" in text:
            text = text.split("Observation:")[0].split("JARVIS:")[0]

        # Strip markdown fences
        clean = re.sub(r'```(?:json)?\s*', '', text).strip()

        # Extract only the first JSON matching the structure
        match = re.search(r'\{[^{}]*\}', clean)  # Basic non-nested first pass
        if not match:
            # Try deeper parser for nested JSON
            start = clean.find('{')
            if start == -1:
                return None, None
            
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
                        except json.JSONDecodeError:
                            break
            return None, None
            
        try:
            candidate = match.group(0)
            data = json.loads(candidate)
            if 'action' in data:
                return data.get('action'), data
        except json.JSONDecodeError:
            pass
            
        return None, None
