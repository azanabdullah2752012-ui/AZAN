import subprocess
import logging

logger = logging.getLogger(__name__)

class AppleNotesTool:
    """Seamless integration with the native macOS Notes application using AppleScript."""

    def create_note(self, title: str, content: str) -> str:
        """Creates a new note in the native Notes.app."""
        safe_title = title.replace('"', '\\"')
        safe_content = content.replace('"', '\\"').replace('\n', '<br>') # Notes uses HTML-lite
        
        script = f"""
        tell application "Notes"
            activate
            set theNote to make new note with properties {{name:"{safe_title}", body:"{safe_content}"}}
            return "Successfully created note: '{safe_title}'"
        end tell
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception as e:
            return f"Failed to create note: {e}"

    def search_notes(self, query: str) -> str:
        """Searches for notes containing the query string."""
        safe_query = query.replace('"', '\\"')
        script = f"""
        set output to ""
        tell application "Notes"
            set matchingNotes to (every note whose name contains "{safe_query}" or body contains "{safe_query}")
            repeat with n in matchingNotes
                set output to output & "- " & name of n & "\\n"
            end repeat
        end tell
        return output
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            output = result.stdout.strip()
            if not output:
                return f"No notes found matching '{query}'."
            return f"Search results for '{query}':\n{output}"
        except Exception as e:
            return f"Failed to search notes: {e}"
