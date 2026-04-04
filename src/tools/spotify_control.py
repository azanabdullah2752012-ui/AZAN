import subprocess
import logging

logger = logging.getLogger(__name__)

class SpotifyControlTool:
    """Seamless integration with the native macOS Spotify application using AppleScript."""

    def run_command(self, command: str) -> str:
        """Executes a playback command: play, pause, next, back, stop, play_pause."""
        apple_commands = {
            "play": "play",
            "pause": "pause",
            "next": "next track",
            "back": "previous track",
            "stop": "pause",
            "play_pause": "playpause"
        }
        
        cmd = apple_commands.get(command.lower())
        if not cmd:
            return f"Error: Unknown Spotify command '{command}'."
            
        script = f'tell application "Spotify" to activate\ntell application "Spotify" to {cmd}'
        
        try:
            logger.info(f"Spotify Command: {command}")
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                return f"Spotify Error: {result.stderr.strip()} (Is Spotify open?)"
            return f"Successfully executed Spotify {command}."
        except Exception as e:
            return f"Failed to control Spotify: {e}"

    def get_current_track(self) -> str:
        """Retrieves details about the currently playing track."""
        script = """
        tell application "Spotify"
            if player state is playing then
                set track_name to name of current track
                set artist_name to artist of current track
                return "Currently playing: " & track_name & " by " & artist_name
            else
                return "Spotify is currently paused or inactive."
            end if
        end tell
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return result.stdout.strip() or "No track information found."
        except Exception as e:
            return f"Failed to fetch Spotify track: {e}"

    def play_track(self, spotify_uri: str) -> str:
        """Plays a specific Spotify URI (track, album, or playlist)."""
        script = f'tell application "Spotify" to play track "{spotify_uri}"'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return f"Attempting to play Spotify URI: {spotify_uri}"
        except Exception as e:
            return f"Failed to play Spotify URI: {e}"

    def play_search(self, query: str) -> str:
        """Searches for a track/artist/album and plays the first result."""
        # Sanitize query for AppleScript
        safe_query = query.replace('"', '\\"')
        
        # We use 'activate' to ensure Spotify is responsive, then play the search URI.
        script = f'''
        tell application "Spotify"
            activate
            delay 1
            play track "spotify:search:{safe_query}"
            return "Searching Spotify for '{safe_query}'..."
        end tell
        '''
        try:
            logger.info(f"Spotify Search & Play: {query}")
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                 return f"Spotify Search Error: {result.stderr.strip()}"
            return f"Command sent: Searching for '{query}'. Please wait for Spotify to process."
        except Exception as e:
            return f"Failed to search and play on Spotify: {e}"

    def create_playlist(self, name: str) -> str:
        """Creates a new empty playlist in the user's library."""
        script = f"""
        tell application "Spotify"
            make new playlist with properties {{name:"{name}"}}
            return "Created playlist '{name}'."
        end tell
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            return result.stdout.strip() or f"Successfully created playlist '{name}'."
        except Exception as e:
            return f"Failed to create playlist: {e}"

    def add_current_to_playlist(self, playlist_name: str) -> str:
        """Adds the currently playing track to a named playlist."""
        script = f"""
        tell application "Spotify"
            set track_uri to spotify url of current track
            if not (exists playlist "{playlist_name}") then
                make new playlist with properties {{name:"{playlist_name}"}}
            end if
            add track_uri to playlist "{playlist_name}"
            return "Added current track to playlist '{playlist_name}'."
        end tell
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if "error" in result.stdout.lower() or "error" in result.stderr.lower():
                 return f"Spotify Error: {result.stdout.strip() or result.stderr.strip()}"
            return result.stdout.strip() or f"Added current track to '{playlist_name}'."
        except Exception as e:
            return f"Failed to add track to playlist: {e}"
