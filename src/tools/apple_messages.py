import subprocess
import logging

logger = logging.getLogger(__name__)

class AppleMessagesTool:
    """Automates sending messages via macOS Messages.app using AppleScript."""

    def send_message(self, contact: str, text: str) -> str:
        """Sends an iMessage/SMS to a contact or phone number."""
        safe_contact = contact.replace('"', '\\"')
        safe_text = text.replace('"', '\\"')
        
        # Native AppleScript for Messages
        script = f"""
        tell application "Messages"
            set targetBuddy to participant "{safe_contact}" of account "iMessage"
            try
                send "{safe_text}" to targetBuddy
                return "Successfully sent message to {safe_contact}."
            on error
                return "Failed to find contact '{safe_contact}' or send message."
            end try
        end tell
        """
        try:
            logger.info(f"Apple Messages: Sending to {contact}")
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception as e:
            return f"Error sending Apple Message: {e}"
