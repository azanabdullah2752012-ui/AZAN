import subprocess
import logging
import time
import os
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MacOSContextTool:
    """
    Context awareness tool for JARVIS to understand the current macOS state.
    Always returns structured JSON.
    """

    def _run_osascript(self, script: str) -> str:
        """Executes an AppleScript and returns the raw output."""
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr.strip()}"
        except Exception as e:
            return f"Exception: {str(e)}"

    def get_active_app(self) -> Dict[str, str]:
        """Returns the name of the frontmost application."""
        script = 'tell application "System Events" to get name of first process whose frontmost is true'
        app_name = self._run_osascript(script)
        return {"active_app": app_name}

    def get_front_window_title(self) -> Dict[str, str]:
        """Returns the title of the frontmost window."""
        script = '''
        tell application "System Events"
            set frontmostProcess to first process whose frontmost is true
            tell frontmostProcess
                if (count of windows) > 0 then
                    return name of window 1
                else
                    return "No active window"
                end if
            end tell
        end tell
        '''
        title = self._run_osascript(script)
        return {"front_window_title": title}

    def get_screen_summary(self) -> Dict[str, Any]:
        """Combines active app and window information for a quick summary."""
        app = self.get_active_app()["active_app"]
        window = self.get_front_window_title()["front_window_title"]
        return {
            "summary": f"User is currently using {app} with window '{window}' focused.",
            "active_app": app,
            "front_window": window,
            "timestamp": time.time()
        }

    def take_screenshot(self, filename: str = "screenshot.png") -> Dict[str, str]:
        """Takes a screenshot and returns the path."""
        path = os.path.join("/tmp", filename)
        try:
            subprocess.run(["screencapture", "-x", path], check=True, timeout=5)
            return {"status": "success", "screenshot_path": path}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_context(self) -> Dict[str, Any]:
        """Returns a full context summary object."""
        return self.get_screen_summary()
