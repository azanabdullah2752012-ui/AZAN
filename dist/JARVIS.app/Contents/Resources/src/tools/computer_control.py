import subprocess
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ComputerControlTool:
    """Agent tool for managing the macOS environment directly."""

    def open_app(self, app_name: str) -> str:
        """Opens a macOS application by name."""
        try:
            result = subprocess.run(["open", "-a", app_name], capture_output=True, text=True)
            if result.returncode == 0:
                return f"Successfully opened {app_name}."
            return f"Failed to open {app_name}. Error: {result.stderr}"
        except Exception as e:
            return f"Error opening app: {e}"

    def search_files(self, query: str) -> str:
        """Searches the whole macOS system using Spotlight (mdfind)."""
        try:
            # mdfind is much faster than find for macOS 
            result = subprocess.run(["mdfind", query], capture_output=True, text=True)
            lines = [line.strip() for line in result.stdout.split("\n") if line.strip()]
            
            if not lines:
                return f"No files found matching '{query}'."
            
            # Truncate to avoid context limit issues
            if len(lines) > 20:
                return "Found " + str(len(lines)) + " files. Top 20 results:\n" + "\n".join(lines[:20])
            return "\n".join(lines)
        except Exception as e:
            return f"Error searching files: {e}"

    def run_applescript(self, script: str) -> str:
        """Runs an AppleScript to automate UI interactions, keystrokes, etc."""
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0:
                output = result.stdout.strip()
                return f"AppleScript executed successfully. Output: {output}" if output else "AppleScript executed successfully."
            return f"AppleScript failed with error: {result.stderr}"
        except Exception as e:
            return f"Error executing AppleScript: {e}"

    def take_screenshot(self, filename="screenshot.jpg") -> str:
        """Takes a screenshot of the main macOS display."""
        # Save to Downloads by default to keep sandbox clean
        path = os.path.expanduser(f"~/Downloads/{filename}")
        try:
            result = subprocess.run(["screencapture", "-x", "-c"], capture_output=True) # -c copies to clipboard instead of file if needed
            # For actual file saving without clipboard
            result = subprocess.run(["screencapture", "-x", path], capture_output=True, text=True)
            
            if result.returncode == 0:
                return f"Screenshot successfully taken and saved to {path}."
            return f"Screenshot failed: {result.stderr}"
        except Exception as e:
            return f"Error taking screenshot: {e}"

    def analyze_screen(self, prompt: str = "Analyze the screen entirely and describe the open windows, active text, and context.") -> str:
        """Takes a screenshot and sends it to a local vision model for analysis."""
        import base64
        import requests
        import time
        
        path = os.path.expanduser("~/Downloads/vision_temp.jpg")
        try:
            subprocess.run(["screencapture", "-x", path], capture_output=True, text=True)
            time.sleep(0.5) # ensure file writes
            
            with open(path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            payload = {
                "model": "llama3.2-vision",
                "prompt": prompt,
                "images": [encoded_string],
                "stream": False
            }
            
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            
            # Cleanup temp vision file
            if os.path.exists(path):
                os.remove(path)
            
            return f"Screen Analysis: {response.json().get('response', 'No analysis returned.')}"
        except Exception as e:
            return f"Error analyzing screen: {e} (Note: Llama-Vision may still be downloading in the background)"
