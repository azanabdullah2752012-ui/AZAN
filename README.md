# J.A.R.V.I.S. (AZAN OS) - Autonomous macOS Intelligence

**Status**: ✅ FULLY OPERATIONAL (Phase 16 Complete)  
**Version**: 16.0.0 (The Ecosystem Update)  
**Server**: FastAPI (`http://localhost:8000`) + Native macOS Menu Bar Daemon  

J.A.R.V.I.S. (formerly AZAN) is a fully local, profoundly autonomous artificial intelligence operating system built for macOS Apple Silicon. Powered by **Local LLMs (Ollama/Llama3)**, it goes far beyond a traditional chatbot. JARVIS utilizes a continuous **ReAct (Reason → Act → Observe)** loop to autonomously interact with your Mac, read your files, manage your schedule, control your media, and hold zero-latency voiced conversations.

Everything runs 100% locally and privately on your machine. Zero cloud APIs.

---

## 🌟 The J.A.R.V.I.S. Architecture

JARVIS exists simultaneously as a **Web Dashboard** and a **Native macOS Menu Bar Widget**, unified by a powerful FastAPI backend and a sophisticated PyAudio/TTS daemon.

### 1. The ReAct Orchestrator Core
At the center of JARVIS is the Orchestrator. Instead of answering linearly, JARVIS *thinks*. When asked a complex question, the LLM emits a JSON tool call, the backend executes it natively, and feeds the `Observation` back to JARVIS. It loops autonomously, handling errors and self-correcting until the task is complete.

### 2. Deep Native Expansion (The 16 Phases)
JARVIS has been systematically expanded over 16 core architectural phases to achieve complete ecosystem dominion:
- **Vision & Screen**: JARVIS can take screenshots and analyze your active desktop using local Vision-Language Models.
- **System Control**: Native AppleScript wrappers allow JARVIS to adjust Mac volume, brightness, sleep the display, and toggle Do Not Disturb.
- **Productivity Suite**: Direct integrations with Apple Calendar, Reminders, and Notes. JARVIS can read your agenda, create tasks, and archive notes entirely on its own.
- **Communications**: Automated dispatch of iMessages/SMS through the native macOS Messages app, and WhatsApp Desktop integration using URI schemas.
- **Media Mastery**: Seamless, integrated playback control and deep-library searching for Spotify Desktop.

### 3. The Semantic "Brain" (Knowledge Graph & RAG)
- **Local Document Indexer**: A background daemon continuously crawls your `~/Documents` and `~/Desktop`, reading `.md`, `.txt`, `.pdf`, and `.py` files.
- **ChromaDB Vector Store**: Information is encoded into high-dimensional space.
- **SQLite Provenance Graph**: Every atomic claim JARVIS learns is fact-checked and stored in a graph database, ensuring he remembers context forever.

### 4. Zero-Latency Voice Daemon
JARVIS features a persistent, always-open microphone stream (eliminating macOS TCC permission lag) coupled with a high-performance sentence-boundary TTS buffer using Microsoft Edge neural voices. This provides a sub-second, multi-turn, British-accented spoken dialogue system accessible from anywhere on your Mac.

---

## 🖥️ The Dual Interfaces

### The Web Dashboard Control Center (`http://localhost:8000`)
- **Real-Time ReAct Streaming**: Watch JARVIS think. The UI intercepts internal ReAct loops and elegantly displays "⚙️ Action: web_search" and the resulting terminal outputs before giving you the final conversational answer.
- **System Telemetry**: Live CPU, RAM, and background worker status.
- **Knowledge Visualizer**: See exactly how many articles, documents, and concepts exist in ChromaDB.

### The Native macOS Widget (Menu Bar)
- **Always Available**: A lightweight `rumps` application living in the macOS Menu Bar.
- **Ambient Listening**: Actively listens for the wake word *"Hey JARVIS"* or *"Hey AZAN"*.
- **Floating HUD**: Delivers sleek, non-intrusive chat interfaces that float over your active workspace.

---

## 🧰 The Tool Registry
JARVIS holds an arsenal of specialized tools he can deploy autonomously:
1. `web_search`: Live headless scraping and deep reading of zero-paywall internet.
2. `code_runner`: Sandboxed Python execution.
3. `shell_runner`: Bash script and terminal command execution.
4. `file_manager`: Read, write, and traverse the local SSD.
5. `computer_control`: Open apps, click, type, and analyze screenshots.
6. `spotify`: Play, pause, search, and manage playlists.
7. `apple_calendar` / `apple_reminders` / `apple_notes`: Deep macOS PIM integration.
8. `apple_messages` / `whatsapp`: Automated messaging.
9. `system_control`: Mute, volume, brightness, Focus modes.

---

## 🚀 Getting Started

### Prerequisites
- macOS on Apple Silicon (M1/M2/M3/M4)
- Python 3.9+
- Ollama installed and running (`ollama serve`)

### Booting the System
```bash
# Start the entire JARVIS ecosystem (Backend, WebUI, and Mac Daemon)
cd /Applications/AZAN
./start_jarvis.sh
```

### Communicating
- **Web**: Navigate to `http://localhost:8000`
- **Voice**: Speak *"Hey JARVIS, what's on my schedule today?"*
- **Text**: Click the AI icon in your Mac Menu Bar.

---

## 🛡️ Security & Privacy
Because JARVIS has `shell` and `osascript` access to your machine, he is designed to operate **100% locally**.
- **No API Keys** (uses Local LLMs and generic web scraping).
- **Strict Guardrails**: File deletion and destructive shell commands are restricted. System changes require explicit user prompts or safe-listed pathways.

---
*Built for the ultimate local autonomous productivity experience. Welcome to the future of macOS.*
