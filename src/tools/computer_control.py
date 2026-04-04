import subprocess
import os
import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ComputerControlTool:
    """Agent tool for managing the macOS environment directly."""

    def _screen_capture_hint(self) -> str:
        return (
            "Hint: On macOS this usually means Screen Recording permission is missing. "
            "Enable it for the terminal/python running AZAN in System Settings > Privacy & Security > Screen Recording, "
            "then restart the backend."
        )

    def open_app(self, app_name: str) -> str:
        """Opens a macOS application by name."""
        try:
            raw_name = (app_name or "").strip()
            if not raw_name:
                return "Failed to open app: empty app name."

            def _try_open_a(name: str) -> Optional[str]:
                result = subprocess.run(["open", "-a", name], capture_output=True, text=True)
                if result.returncode == 0:
                    return f"Successfully opened {name}."
                err = (result.stderr or "").strip()
                return None if not err else err

            def _try_open_b(bundle_id: str) -> Optional[str]:
                result = subprocess.run(["open", "-b", bundle_id], capture_output=True, text=True)
                if result.returncode == 0:
                    return f"Successfully opened {bundle_id}."
                err = (result.stderr or "").strip()
                return None if not err else err

            # Common alias normalization: users say "Chrome", but macOS app is usually "Google Chrome".
            lowered = raw_name.lower()
            candidates: List[str] = [raw_name]
            bundle_candidates: List[str] = []

            if lowered in {"chrome", "google chrome"} or " chrome" in lowered or lowered.endswith("chrome"):
                # Prefer stable names first.
                candidates = ["Google Chrome", raw_name, "Google Chrome Canary", "Chromium"]
                bundle_candidates = ["com.google.Chrome", "com.google.Chrome.canary", "org.chromium.Chromium"]

            # 1) Try opening by app name.
            last_err = ""
            for name in candidates:
                if not name:
                    continue
                ok = _try_open_a(name)
                if ok and ok.startswith("Successfully opened"):
                    return ok
                if ok:
                    last_err = ok

            # 2) Try bundle id fallback (more reliable than display name).
            for bid in bundle_candidates:
                ok = _try_open_b(bid)
                if ok and ok.startswith("Successfully opened"):
                    # Return a user-friendly success message if we know the human app name.
                    if bid == "com.google.Chrome":
                        return "Successfully opened Google Chrome."
                    return ok
                if ok:
                    last_err = ok

            return f"Failed to open {raw_name}. Error: {last_err or 'application not found'}"
        except Exception as e:
            return f"Error opening app: {e}"

    def open_url(self, url: str) -> str:
        """Opens a URL in the default web browser."""
        try:
            if not url.startswith("http"):
                url = "https://" + url
            
            subprocess.run(["open", url], check=True, capture_output=True)
            return f"Successfully opened {url} in your default browser."
        except Exception as e:
            return f"Failed to open URL {url}: {e}"

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
        try:
            # Prefer a temp path that always exists; avoid clipboard mode.
            target = os.path.join("/tmp", filename if filename else f"screenshot_{int(time.time())}.png")
            if not os.path.splitext(target)[1]:
                target += ".png"

            result = subprocess.run(["screencapture", "-x", target], capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(target):
                return f"Screenshot successfully taken and saved to {target}."

            err = (result.stderr or result.stdout or "").strip()
            if not err:
                err = "unknown screencapture error"
            if "could not create image from display" in err.lower():
                err = f"{err}\n{self._screen_capture_hint()}"
            return f"Screenshot failed: {err}"
        except Exception as e:
            return f"Error taking screenshot: {e}"

    def analyze_screen(self, prompt: str = "Analyze the screen entirely and describe the open windows, active text, and context.") -> str:
        """Takes a screenshot and sends it to a local vision model for analysis."""
        import base64
        import requests

        path = os.path.join("/tmp", f"vision_temp_{int(time.time())}.jpg")
        try:
            cap = subprocess.run(["screencapture", "-x", path], capture_output=True, text=True)
            if cap.returncode != 0 or not os.path.exists(path):
                err = (cap.stderr or cap.stdout or "").strip()
                if not err:
                    err = "screencapture failed (no output)"
                if "could not create image from display" in err.lower():
                    err = f"{err}\n{self._screen_capture_hint()}"
                return f"Error analyzing screen: {err}"

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
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
            
            return f"Screen Analysis: {response.json().get('response', 'No analysis returned.')}"
        except Exception as e:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
            return f"Error analyzing screen: {e} (Note: Llama-Vision may still be downloading in the background)"
