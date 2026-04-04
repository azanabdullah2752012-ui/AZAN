"""
JARVIS System Monitor
Tracks CPU, RAM, Disk usage and Ollama model health for the live status panel.
"""
import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Lightweight system metrics collector using only stdlib + optionally psutil."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._last_check: float = 0
        self._cache_ttl: float = 5.0  # seconds

    def _run_cmd(self, cmd: str) -> str:
        try:
            return subprocess.check_output(cmd, shell=True, text=True, timeout=5).strip()
        except Exception:
            return ""

    def _get_cpu(self) -> float:
        """Get CPU usage percentage using top (macOS compatible)."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.2)
        except ImportError:
            # fallback for macOS without psutil
            raw = self._run_cmd("top -l 1 | awk '/CPU usage/ {print $3}' | cut -d'%' -f1")
            return float(raw) if raw else 0.0

    def _get_ram(self) -> Dict[str, Any]:
        """Get RAM usage in MB."""
        try:
            import psutil
            vm = psutil.virtual_memory()
            return {"used_mb": int(vm.used / 1024 / 1024), "total_mb": int(vm.total / 1024 / 1024), "percent": vm.percent}
        except ImportError:
            raw = self._run_cmd("vm_stat | grep 'Pages active'")
            return {"used_mb": 0, "total_mb": 0, "percent": 0.0}

    def _get_disk(self) -> Dict[str, Any]:
        """Get disk usage for the primary volume."""
        try:
            import psutil
            d = psutil.disk_usage('/')
            return {"used_gb": round(d.used / 1e9, 1), "total_gb": round(d.total / 1e9, 1), "percent": d.percent}
        except ImportError:
            raw = self._run_cmd("df -Hl / | tail -1 | awk '{print $5}'").replace('%', '')
            return {"used_gb": 0, "total_gb": 0, "percent": float(raw) if raw else 0}

    def _get_ollama_status(self) -> str:
        """Checks if Ollama is running by querying its local API."""
        try:
            import urllib.request
            req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            return "online" if req.status == 200 else "degraded"
        except Exception:
            return "offline"

    def get_metrics(self) -> Dict[str, Any]:
        """Return current system metrics (cached for 5 seconds)."""
        import time
        now = time.time()
        if now - self._last_check < self._cache_ttl and self._cache:
            return self._cache

        metrics = {
            "cpu_percent": self._get_cpu(),
            "ram": self._get_ram(),
            "disk": self._get_disk(),
            "ollama": self._get_ollama_status(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._cache = metrics
        self._last_check = now
        return metrics


# Global singleton
_monitor: "SystemMonitor | None" = None

def get_system_monitor() -> SystemMonitor:
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor
