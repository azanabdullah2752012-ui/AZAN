import ast
import sys
import io
import subprocess
import resource
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Dangerous built-ins that cannot be used in sandboxed execution
BLOCKED_BUILTINS = {
    "__import__", "open", "exec", "eval", "compile",
    "__builtins__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "type", "dir"
}

SAFE_BUILTINS = {
    "print": print, "len": len, "range": range, "str": str,
    "int": int, "float": float, "list": list, "dict": dict,
    "tuple": tuple, "set": set, "bool": bool, "abs": abs,
    "round": round, "min": min, "max": max, "sum": sum,
    "sorted": sorted, "reversed": reversed, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "isinstance": isinstance,
    "issubclass": issubclass, "hasattr": hasattr,
}

class CodeRunner:
    """Secure, sandboxed Python code execution agent.
    
    Uses Python AST analysis to detect and block dangerous patterns
    before execution. Captures stdout/stderr without subprocess overhead.
    """

    def validate_code(self, code: str) -> Dict[str, Any]:
        """Static analysis pass: rejects code with dangerous operations."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"valid": False, "error": f"SyntaxError: {e}"}
        
        for node in ast.walk(tree):
            # Block all import statements
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, 'module', '') or ''
                # Allow safe imports: math, statistics, json, datetime, re
                allowed_top_level = {'math', 'statistics', 'json', 'datetime', 're', 'collections', 'itertools'}
                if isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[0] in allowed_top_level:
                    continue
                if isinstance(node, ast.Import):
                    all_allowed = all(alias.name.split('.')[0] in allowed_top_level for alias in node.names)
                    if all_allowed:
                        continue
                return {"valid": False, "error": f"Import blocked for security: {ast.dump(node)[:80]}"}
            
            # Block dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_BUILTINS:
                    return {"valid": False, "error": f"Blocked call: {node.func.id}()"}
                    
        return {"valid": True, "error": None}

    def execute(self, code: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        """Executes code in a restricted namespace, capturing output."""
        # Run validation first
        validation = self.validate_code(code)
        if not validation["valid"]:
            return {
                "success": False,
                "output": "",
                "error": validation["error"]
            }

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        namespace = {"__builtins__": SAFE_BUILTINS, "_output_": []}
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        try:
            exec(compile(code, "<azan_sandbox>", "exec"), namespace)
            output = stdout_capture.getvalue()
            error = stderr_capture.getvalue()
            return {
                "success": True,
                "output": output,
                "error": error if error else None
            }
        except Exception as e:
            return {
                "success": False,
                "output": stdout_capture.getvalue(),
                "error": f"{type(e).__name__}: {e}"
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
