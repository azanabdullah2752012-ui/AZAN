import subprocess
import logging
import urllib.parse
import time

logger = logging.getLogger(__name__)

class WhatsAppControlTool:
    """Automates WhatsApp Desktop using URI deep links and AppleScript UI actions."""

    def send_message(self, phone: str, text: str) -> str:
        """Sends a message via the native WhatsApp Desktop application."""
        # 1. Open the deep link
        encoded_text = urllib.parse.quote(text)
        # Phone number should ideally be clean (e.g., +1234567890 or 1234567890)
        clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        uri = f"whatsapp://send?phone={clean_phone}&text={encoded_text}"
        
        try:
            # Tell macOS to open the URI (this opens WhatsApp Desktop)
            logger.info(f"Opening WhatsApp URI for {clean_phone}")
            subprocess.run(["open", uri], check=True)
            
            # 2. Use AppleScript to wait and press Enter
            # The UI needs a moment to load the chat and populate the text field
            time.sleep(2)  # Wait for WhatsApp to come to the foreground and load the chat
            
            script = '''
            tell application "System Events"
                tell process "WhatsApp"
                    set frontmost to true
                    -- Press Return to send the pre-filled message
                    key code 36
                end tell
            end tell
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"UI Scripting failed (might need Accessibility permissions): {result.stderr}")
                return "Opened WhatsApp and pre-filled the message, but could not auto-send (Accessibility permission required). Please press Enter."
            
            return f"Successfully sent WhatsApp message to {clean_phone}."
            
        except Exception as e:
            logger.error(f"WhatsApp automation failed: {e}")
            return f"Failed to send WhatsApp message: {e}"
