import subprocess
import logging
import json
import os
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MacOSControlTool:
    """
    Comprehensive macOS control tool using AppleScript and System Events.
    Returns structured ToolResult (success, output, error, execution_time).
    """

    def _run_osascript(self, script: str, timeout: int = 5) -> Dict[str, Any]:
        """Executes an AppleScript and returns a structured result."""
        start_time = time.time()
        try:
            result = subprocess.run(
                ["osascript", "-e", script], 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            execution_time = time.time() - start_time
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "error": None,
                    "execution_time": execution_time
                }
            else:
                return {
                    "success": False,
                    "output": None,
                    "error": result.stderr.strip(),
                    "execution_time": execution_time
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": None,
                "error": f"Command timed out after {timeout} seconds.",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "output": None,
                "error": str(e),
                "execution_time": time.time() - start_time
            }

    # --- APPLICATION CONTROL ---

    def open_app(self, app_name: str) -> Dict[str, Any]:
        """Opens a macOS application."""
        start_time = time.time()
        try:
            subprocess.run(["open", "-a", app_name], check=True, capture_output=True, timeout=5)
            return {
                "success": True,
                "output": f"Opened {app_name}.",
                "error": None,
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            return {
                "success": False,
                "output": None,
                "error": str(e),
                "execution_time": time.time() - start_time
            }

    def close_app(self, app_name: str) -> Dict[str, Any]:
        """Quits a macOS application."""
        script = f'tell application "{app_name}" to quit'
        return self._run_osascript(script)

    def switch_app(self, app_name: str) -> Dict[str, Any]:
        """Activates/Switches to a macOS application."""
        script = f'tell application "{app_name}" to activate'
        return self._run_osascript(script)

    def list_running_apps(self) -> Dict[str, Any]:
        """Lists currently running applications."""
        script = 'tell application "System Events" to get name of every process whose background only is false'
        return self._run_osascript(script)

    # --- WINDOW MANAGEMENT ---

    def focus_window(self, app_name: str) -> Dict[str, Any]:
        """Brings the application window to front."""
        return self.switch_app(app_name)

    def minimize_window(self, app_name: str = None) -> Dict[str, Any]:
        """Minimizes the front window."""
        if app_name:
            script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    set value of attribute "AXMinimized" of window 1 to true
                end tell
            end tell
            '''
        else:
            script = '''
            tell application "System Events"
                set frontmostProcess to first process whose frontmost is true
                tell frontmostProcess
                    set value of attribute "AXMinimized" of window 1 to true
                end tell
            end tell
            '''
        return self._run_osascript(script)

    def maximize_window(self, app_name: str = None) -> Dict[str, Any]:
        """Maximizes/Zooms the front window."""
        if app_name:
            script = f'''
            tell application "System Events"
                tell process "{app_name}"
                    set value of attribute "AXZoomed" of window 1 to true
                end tell
            end tell
            '''
        else:
            script = '''
            tell application "System Events"
                set frontmostProcess to first process whose frontmost is true
                tell frontmostProcess
                    set value of attribute "AXZoomed" of window 1 to true
                end tell
            end tell
            '''
        return self._run_osascript(script)

    # --- KEYBOARD INPUT ---

    def type_text(self, text: str) -> Dict[str, Any]:
        """Types text using System Events."""
        safe_text = text.replace('"', '\\"')
        script = f'tell application "System Events" to keystroke "{safe_text}"'
        return self._run_osascript(script)

    def press_key(self, key: str) -> Dict[str, Any]:
        """Presses a single key."""
        key_map = {"enter": 36, "return": 36, "space": 49, "escape": 53}
        if key.lower() in key_map:
            script = f'tell application "System Events" to key code {key_map[key.lower()]}'
        else:
            script = f'tell application "System Events" to keystroke "{key}"'
        return self._run_osascript(script)

    def hotkey(self, keys: List[str]) -> Dict[str, Any]:
        """Executes a hotkey combination."""
        modifiers = []
        base_key = ""
        for k in keys:
            k = k.lower()
            if k in ["command", "cmd"]: modifiers.append("command down")
            elif k == "shift": modifiers.append("shift down")
            elif k in ["option", "alt"]: modifiers.append("option down")
            elif k in ["control", "ctrl"]: modifiers.append("control down")
            else: base_key = k
        
        mod_str = " using {" + ", ".join(modifiers) + "}" if modifiers else ""
        script = f'tell application "System Events" to keystroke "{base_key}"{mod_str}'
        return self._run_osascript(script)

    # --- UI AUTOMATION ---

    def click(self, x: int, y: int) -> Dict[str, Any]:
        """Clicks at specific screen coordinates."""
        script = f'tell application "System Events" to click at {{{x}, {y}}}'
        return self._run_osascript(script)

    def scroll(self, direction: str) -> Dict[str, Any]:
        """Scrolls the active window."""
        key_code = 126 if direction.lower() == "up" else 125
        script = f'tell application "System Events" to key code {key_code} using {{command down}}'
        return self._run_osascript(script)

    # --- FINDER INTEGRATION ---

    def open_folder(self, path: str) -> Dict[str, Any]:
        """Opens a folder in Finder."""
        start_time = time.time()
        try:
            subprocess.run(["open", path], check=True, timeout=5)
            return {"success": True, "output": f"Opened {path}", "error": None, "execution_time": time.time() - start_time}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e), "execution_time": time.time() - start_time}

    def reveal_file(self, path: str) -> Dict[str, Any]:
        """Reveals a file in Finder."""
        start_time = time.time()
        try:
            subprocess.run(["open", "-R", path], check=True, timeout=5)
            return {"success": True, "output": f"Revealed {path}", "error": None, "execution_time": time.time() - start_time}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e), "execution_time": time.time() - start_time}

    def search_file(self, query: str) -> Dict[str, Any]:
        """Searches for files using Spotlight."""
        start_time = time.time()
        try:
            result = subprocess.run(["mdfind", query], capture_output=True, text=True, timeout=5)
            files = result.stdout.strip().split("\n")[:10]
            execution_time = time.time() - start_time
            return {"success": True, "output": files, "error": None, "execution_time": execution_time}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e), "execution_time": time.time() - start_time}

    # --- SYSTEM CONTROLS ---

    def set_volume(self, level: int) -> Dict[str, Any]:
        """Sets system volume."""
        script = f"set volume output volume {level}"
        return self._run_osascript(script)

    def mute(self, enable: bool = True) -> Dict[str, Any]:
        """Mutes or unmutes system volume."""
        state = "true" if enable else "false"
        script = f"set volume output muted {state}"
        return self._run_osascript(script)

    def set_brightness(self, level: int) -> Dict[str, Any]:
        """Sets display brightness."""
        target_steps = int((level / 100.0) * 16)
        script = f'''
        tell application "System Events"
            repeat 16 times
                key code 145
            end repeat
            repeat {target_steps} times
                key code 144
            end repeat
        end tell
        '''
        return self._run_osascript(script)

    def sleep_display(self) -> Dict[str, Any]:
        """Puts display to sleep."""
        script = 'tell application "Finder" to sleep'
        return self._run_osascript(script)

    def toggle_focus_mode(self, enable: bool) -> Dict[str, Any]:
        """Toggles Do Not Disturb."""
        start_time = time.time()
        state = "YES" if enable else "NO"
        cmd = f"defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean {state}; killall NotificationCenter"
        try:
            subprocess.run(cmd, shell=True, check=True, timeout=5)
            return {"success": True, "output": f"Focus mode {'enabled' if enable else 'disabled'}", "error": None, "execution_time": time.time() - start_time}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e), "execution_time": time.time() - start_time}

    # --- TIME & DATE ---

    def get_time(self) -> Dict[str, Any]:
        """Returns the current system time in a 12-hour natural format (e.g., 1:13 PM)."""
        from datetime import datetime
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip('0')  # Remove leading zero
        return {
            "success": True,
            "output": time_str,
            "error": None,
            "execution_time": 0
        }

    def get_date(self) -> Dict[str, Any]:
        """Returns the current system date in a natural format."""
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%A, %d %B %Y")
        return {
            "success": True,
            "output": date_str,
            "error": None,
            "execution_time": 0
        }

    # --- APPLE ECOSYSTEM ---

    def send_message(self, contact: str, text: str) -> Dict[str, Any]:
        """Sends a message via Messages.app."""
        safe_contact = contact.replace('"', '\\"')
        safe_text = text.replace('"', '\\"')
        script = f'''
        tell application "Messages"
            try
                set targetBuddy to participant "{safe_contact}" of account "iMessage"
                send "{safe_text}" to targetBuddy
                return "Message sent."
            on error err
                return "Error: " & err
            end try
        end tell
        '''
        return self._run_osascript(script)

    def create_event(self, title: str, datetime_str: str) -> Dict[str, Any]:
        """Creates a Calendar event."""
        # datetime_str example: "March 30, 2026 at 10:00 AM"
        script = f'''
        tell application "Calendar"
            tell calendar "Calendar"
                make new event with properties {{summary:"{title}", start date:date "{datetime_str}"}}
            end tell
        end tell
        '''
        return self._run_osascript(script)

    def create_note(self, content: str) -> Dict[str, Any]:
        """Creates a Note in Notes.app."""
        safe_content = content.replace('"', '\\"')
        script = f'''
        tell application "Notes"
            tell folder "Notes"
                make new note with properties {{body:"{safe_content}"}}
            end tell
        end tell
        '''
        return self._run_osascript(script)

    # --- CENTRAL DISPATCHER ---

    def execute(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches to the appropriate method."""
        method = getattr(self, action, None)
        if not method:
            return {"success": False, "output": None, "error": f"Action '{action}' not implemented.", "execution_time": 0}
        return method(**args)
