import subprocess
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AppleCalendarTool:
    """Seamless integration with the native macOS Calendar application using AppleScript."""

    def get_upcoming_events(self, days_ahead: int = 7) -> str:
        """Retrieves upcoming calendar events using native AppleScript binding."""
        script = f"""
        set output to ""
        set currentDate to current date
        set futureDate to currentDate + ({days_ahead} * days)
        
        tell application "Calendar"
            -- We query all calendars
            set allCalendars to every calendar
            repeat with cal in allCalendars
                set calEvents to (every event of cal where start date ≥ currentDate and start date ≤ futureDate)
                repeat with ev in calEvents
                    set evSum to summary of ev
                    set evStart to start date of ev as string
                    set evEnd to end date of ev as string
                    set output to output & "- " & evSum & " (From: " & evStart & " To: " & evEnd & ")\\n"
                end repeat
            end repeat
        end tell
        return output
        """
        
        try:
            logger.info(f"Querying macOS Calendar for next {days_ahead} days")
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                err = result.stderr.strip()
                if "Not authorized" in err:
                    return "Error: macOS Calendar access denied. Please grant Terminal/Python access in System Settings > Privacy & Security > Calendars."
                return f"AppleScript Calendar Error: {err}"
                
            output = result.stdout.strip()
            if not output:
                return "Your calendar is empty for this time period."
            return f"Upcoming Events:\n{output}"
            
        except Exception as e:
            return f"Failed to execute Calendar query: {e}"

    def create_event(self, summary: str, start_time_str: str, duration_minutes: int = 60) -> str:
        """
        Creates a new event in the local Apple Calendar.
        start_time_str must be parsable by AppleScript (e.g. "March 26, 2026 at 2:00 PM")
        """
        script = f"""
        try
            set startDate to date "{start_time_str}"
            set endDate to startDate + ({duration_minutes} * minutes)
            
            tell application "Calendar"
                -- Default to the first calendar found
                set targetCal to first calendar whose writable is true
                tell targetCal
                    make new event at end with properties {{summary:"{summary}", start date:startDate, end date:endDate}}
                end tell
                return "Successfully created event: '{summary}' on " & (startDate as string)
            end tell
        on error errMsg
            return "Failed to parse date or create event: " & errMsg
        end try
        """
        
        try:
            logger.info(f"Creating macOS Calendar event: {summary}")
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                err = result.stderr.strip()
                if "Not authorized" in err:
                    return "Error: macOS Calendar access denied."
                return f"AppleScript error: {err}"
                
            return result.stdout.strip()
        except Exception as e:
            return f"Failed to execute Calendar creation: {e}"
