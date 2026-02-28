#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

source .venv/bin/activate

python -m webbrowser "http://127.0.0.1:8000" >/dev/null 2>&1 || true
exec uvicorn webui.app:app --host 127.0.0.1 --port 8000
