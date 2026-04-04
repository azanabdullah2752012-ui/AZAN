import subprocess
import logging

logger = logging.getLogger(__name__)

class AppleMailTool:
    """Seamless integration with the native macOS Mail application using AppleScript."""

    def draft_email(self, subject: str, recipient: str, body: str) -> str:
        """Opens a new Mail draft window with the specified fields physically rendered on the user's screen."""
        # Sanitize strings for AppleScript
        safe_subject = subject.replace('"', '\\"')
        safe_recipient = recipient.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        
        script = f"""
        tell application "Mail"
            -- Bring Mail to front so the user sees the draft
            activate
            set theMessage to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:true}}
            tell theMessage
                make new to recipient at end of to recipients with properties {{address:"{safe_recipient}"}}
            end tell
            return "Successfully launched Apple Mail composer draft for {safe_recipient}."
        end tell
        """
        
        try:
            logger.info(f"Drafting Apple Mail to: {recipient}")
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                err = result.stderr.strip()
                if "Not authorized" in err:
                    return "Error: macOS Mail access denied. Please grant Terminal/Python access in System Settings > Privacy & Security > Automation."
                return f"AppleScript Mail Error: {err}"
                
            return result.stdout.strip()
        except Exception as e:
            return f"Failed to execute Mail formatting: {e}"

    def get_recent_unread(self, limit: int = 5) -> str:
        """Retrieves snippets of the most recent unread emails from the native macOS Mail Inbox."""
        script = f"""
        set output to ""
        tell application "Mail"
            set unreadMessages to (messages of inbox whose read status is false)
            set countToRead to {limit}
            if (count of unreadMessages) < countToRead then
                set countToRead to count of unreadMessages
            end if
            
            if countToRead is 0 then
                return "No unread emails."
            end if
            
            repeat with i from 1 to countToRead
                set msg to item i of unreadMessages
                set msgSender to sender of msg
                set msgSub to subject of msg
                -- Limit content to first 150 chars roughly to avoid massive blobs
                set msgContent to text 1 thru 150 of (content of msg as string) & "..."
                set output to output & "- From: " & msgSender & " | Subject: " & msgSub & "\\nSnippet: " & msgContent & "\\n\\n"
            end repeat
        end tell
        return output
        """
        
        try:
            logger.info("Reading unread Apple Mail inbox")
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                err = result.stderr.strip()
                return f"AppleScript Mail Error: {err}"
                
            output = result.stdout.strip()
            return f"Recent Unread Emails:\n{output}"
        except Exception as e:
            return f"Failed to fetch Apple Mail messages: {e}"
