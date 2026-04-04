import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class FileManagerTool:
    """Agent tool for managing the local file system."""

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            self.base_dir = os.path.expanduser("~/Downloads")
        else:
            self.base_dir = base_dir

    def list_dir(self, path: str = ".") -> str:
        """List contents of a directory."""
        safe_path = path.lstrip("/\\")
        target_path = os.path.abspath(os.path.join(self.base_dir, safe_path))
        try:
            items = os.listdir(target_path)
            # Format output
            output = []
            for item in items:
                item_path = os.path.join(target_path, item)
                if os.path.isdir(item_path):
                    output.append(f"[DIR]  {item}/")
                else:
                    size = os.path.getsize(item_path)
                    output.append(f"[FILE] {item} ({size} bytes)")
            return "\n".join(output) if output else "(Empty directory)"
        except Exception as e:
            return f"Error listing directory: {e}"

    def read_file(self, path: str) -> str:
        """Reads a file's contents."""
        safe_path = path.lstrip("/\\")
        target_path = os.path.abspath(os.path.join(self.base_dir, safe_path))
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Truncate if too long to save LLM context
                if len(content) > 4000:
                    return content[:4000] + "\n...(truncated due to length)..."
                return content
        except Exception as e:
            return f"Error reading file '{path}': {e}"

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file."""
        safe_path = path.lstrip("/\\")
        target_path = os.path.abspath(os.path.join(self.base_dir, safe_path))
        try:
            # Ensure directories exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file '{path}': {e}"
