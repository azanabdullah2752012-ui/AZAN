#!/bin/bash
set -euo pipefail
cd /Applications/AZAN

# Stop anything already listening on port 8000 (covers uvicorn, flask, etc.)
PIDS="$(lsof -t -i :8000 2>/dev/null || true)"
if [ -n "${PIDS}" ]; then
  echo "Stopping existing process(es) on port 8000: ${PIDS}"
  kill -9 ${PIDS} 2>/dev/null || true
  sleep 1
fi

# ── PART 6: PRELOAD MODEL ───────────────────────────────────────────
echo "🚀 Warming up Ollama (llama3)..."
ollama run llama3 "/exit"

# ── START BACKEND WITH WATCHDOG ────────────────────────────────────
# Run in a background loop that auto-restarts if the server crashes
echo "Starting JARVIS backend with Auto-Restart watchdog (logs: /tmp/jarvis_backend.log)"

cat << 'EOF' > /tmp/jarvis_backend_watchdog.sh
#!/bin/bash
while true; do
  echo "[$(date)] Starting JARVIS Backend..." >> /tmp/jarvis_backend.log
  env PYTHONPATH=/Applications/AZAN arch -arm64 /Applications/AZAN/.venv-1/bin/python3 webui/app.py --port 8000 --host 0.0.0.0 >> /tmp/jarvis_backend.log 2>&1
  echo "[$(date)] Backend crashed! Restarting in 2s..." >> /tmp/jarvis_backend.log
  sleep 2
done
EOF

chmod +x /tmp/jarvis_backend_watchdog.sh
nohup /tmp/jarvis_backend_watchdog.sh > /dev/null 2>&1 &
BACKEND_PID=$!
echo "${BACKEND_PID}" > /tmp/jarvis_backend.pid

sleep 2

# Start the Native Rumps Menu Bar UI in the background
echo "Starting JARVIS Mac Menu Bar UI (logs: /tmp/jarvis_ui.log)"
nohup env PYTHONPATH=/Applications/AZAN arch -arm64 /Applications/AZAN/.venv-1/bin/python3 src/ui/menubar.py > /tmp/jarvis_ui.log 2>&1 &
UI_PID=$!
echo "${UI_PID}" > /tmp/jarvis_ui.pid

echo "Started successfully with 24/7 Watchdog. Watchdog PID=${BACKEND_PID}"
