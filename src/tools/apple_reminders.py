import subprocess
import logging

logger = logging.getLogger(__name__)

class AppleRemindersTool:
    """Seamless integration with the native macOS Reminders application using AppleScript."""

    def create_reminder(self, name: str, body: str = "", list_name: str = "Reminders") -> str:
        """Creates a new reminder in the specified list."""
        # Sanitize for AppleScript
        safe_name = name.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        safe_list = list_name.replace('"', '\\"')
        
        script = f"""
        tell application "Reminders"
            if not (exists list "{safe_list}") then
                make new list with properties {{name:"{safe_list}"}}
            end if
            tell list "{safe_list}"
                make new reminder with properties {{name:"{safe_name}", body:"{safe_body}"}}
            end tell
            return "Successfully created reminder '{safe_name}' in list '{safe_list}'."
        end tell
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception as e:
            return f"Failed to create reminder: {e}"

    def get_reminders(self, list_name: str = "Reminders") -> str:
        """Lists all incomplete reminders in a specific list."""
        safe_list = list_name.replace('"', '\\"')
        script = f"""
        set output to ""
        tell application "Reminders"
            if exists list "{safe_list}" then
                set todoList to list "{safe_list}"
                set incompleteTasks to (every reminder of todoList whose completed is false)
                repeat with t in incompleteTasks
                    set output to output & "- " & name of t & "\\n"
                end repeat
            else
                return "List '{safe_list}' not found."
            end if
        end tell
        return output
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            output = result.stdout.strip()
            if not output:
                return f"No incomplete reminders found in '{list_name}'."
            return f"Incomplete Reminders in '{list_name}':\n{output}"
        except Exception as e:
            return f"Failed to fetch reminders: {e}"
