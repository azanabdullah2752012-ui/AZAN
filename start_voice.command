#!/bin/bash
echo "Initializing JARVIS Real-Time Voice Interface..."
cd /Applications/AZAN
env PYTHONPATH=/Applications/AZAN /Applications/AZAN/.venv-1/bin/python3 src/workers/voice_loop.py
