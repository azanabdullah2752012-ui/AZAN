import subprocess
import logging

logger = logging.getLogger(__name__)

class SystemControlTool:
    """Controls core macOS hardware settings (volume, brightness, sleep, focus)."""

    def set_volume(self, level: int) -> str:
        """Sets the system volume (0 to 100)."""
        level = max(0, min(100, level))
        script = f"set volume output volume {level}"
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return f"System volume set to {level}%."
        except Exception as e:
            return f"Failed to set volume: {e}"

    def mute(self, is_muted: bool) -> str:
        """Mutes or unmutes the system volume."""
        state = "true" if is_muted else "false"
        script = f"set volume output muted {state}"
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return "System sound muted." if is_muted else "System sound unmuted."
        except Exception as e:
            return f"Failed to toggle mute: {e}"

    def set_brightness(self, level: int) -> str:
        """Sets the display brightness (0 to 100) using a 3rd party tool if available or applescript."""
        # AppleScript cannot natively set brightness easily without UI scripting 
        # or relying on specific third-party utilities like 'brightness'.
        # For simplicity, we use AppleScript UI scripting on the Control Center if needed.
        # Alternatively, we can use a built-in shell technique if available.
        # Here we approximate it by pressing the brightness keys.
        level = max(0, min(100, level))
        
        # Calculate how many "steps" out of 16 (macOS default increments)
        target_steps = int((level / 100.0) * 16)
        
        # Max it out first, then step down. Or completely lower it, then step up.
        # This is a brute-force approach since macOS lacks a clean CLI brightness tool out of the box.
        script = f"""
        tell application "System Events"
            repeat 16 times
                key code 145 -- brightness down
            end repeat
            repeat {target_steps} times
                key code 144 -- brightness up
            end repeat
        end tell
        """
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return f"System brightness set to approximately {level}%."
        except Exception as e:
            return f"Failed to set brightness (Accessibility permission may be required): {e}"

    def sleep_display(self) -> str:
        """Puts the Mac display to sleep."""
        # pmset requires sudo sometimes, but triggering screen saver or sending sleep works.
        script = 'tell application "Finder" to sleep'
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return "Sent sleep command to the computer."
        except Exception as e:
            return f"Failed to sleep computer: {e}"

    def toggle_focus_mode(self, enable: bool) -> str:
        """Toggles Do Not Disturb / Focus Mode via Shortcuts or UI Scripting."""
        # We can use the native macOS Shortcut for Do Not Disturb if it exists,
        # or toggle it using AppleScript defaults. 
        # A common generic way without Shortcuts is using the defaults command (requires killall SystemUIServer).
        state = 1 if enable else 0
        cmd = f"defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean {'YES' if enable else 'NO'}; killall NotificationCenter"
        try:
            subprocess.run(cmd, shell=True, check=True)
            status = "enabled" if enable else "disabled"
            return f"Do Not Disturb (Focus Mode) {status}."
        except Exception as e:
            return f"Failed to toggle Focus mode: {e}"
