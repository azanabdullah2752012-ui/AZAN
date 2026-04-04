import os
import sys
import rumps
import subprocess
import requests

# Set rumps debug mode off
rumps.debug_mode(False)

class JarvisMenuBarApp(rumps.App):
    def __init__(self):
        super(JarvisMenuBarApp, self).__init__("JARVIS", quit_button=None)
        self.menu = [
            rumps.MenuItem("Status: Online", callback=None),
            None,
            rumps.MenuItem("Open Web Dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Force Listen", callback=self.trigger_listen),
            None,
            rumps.MenuItem("Quit JARVIS", callback=self.quit_app)
        ]

    def open_dashboard(self, _):
        """Open the FastAPI web dashboard."""
        subprocess.run(["open", "http://127.0.0.1:8000"])

    def trigger_listen(self, _):
        """Manual override to trigger a voice command if wake word fails."""
        pass

    def quit_app(self, _):
        """Cleanup processes and quit."""
        # Stop everything
        subprocess.run(["pkill", "-f", "webui/app.py"])
        subprocess.run(["pkill", "-f", "jarvis_ears.py"])
        rumps.quit_application()

if __name__ == "__main__":
    # Start the Wake Word daemon implicitly linked to the RUMPS AppKit environment
    import threading
    def launch_ears():
        import subprocess
        # We use the absolute path to ensure no version mismatch
        python_bin = "/Applications/AZAN/.venv-1/bin/python3"
        script_path = "/Applications/AZAN/src/workers/jarvis_ears.py"
        env = os.environ.copy()
        env["PYTHONPATH"] = "/Applications/AZAN"
        subprocess.run([python_bin, "-u", script_path], env=env)
    
    t = threading.Thread(target=launch_ears, daemon=True)
    t.start()

    app = JarvisMenuBarApp()
    app.run()
