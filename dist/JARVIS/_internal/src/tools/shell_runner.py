import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ShellRunnerTool:
    """Execute bash shell commands with safety boundaries."""
    
    def __init__(self):
        # Prevent completely destructive commands
        self.blocked_commands = ['rm -rf /', 'mkfs', 'dd ', 'shutdown', 'reboot']

    def execute(self, command: str, timeout: int = 15) -> Dict[str, Any]:
        """Runs a bash command and returns stdout/stderr."""
        if any(bad_cmd in command for bad_cmd in self.blocked_commands):
            return {"success": False, "output": f"Security Error: Command blocked. Did you try to run '{command}'?"}

        logger.info(f"Executing shell command: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode == 0:
                # Success
                return {
                    "success": True, 
                    "output": output if output else "Command executed successfully with no output."
                }
            else:
                # Failure
                return {
                    "success": False,
                    "output": f"Exit Code {result.returncode}\nSTDOUT:\n{output}\nSTDERR:\n{error}"
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": f"Command timed out after {timeout} seconds."}
        except Exception as e:
            return {"success": False, "output": f"Execution error: {e}"}
