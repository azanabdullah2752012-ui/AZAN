"""
JARVIS High-Accuracy Voice Loop — Phase 21 Stability Hardening.

Changes vs previous version:
 - Q-key activation: press Q in terminal → jump straight to ACTIVE state.
 - Wake-word check window: 1.5s → 0.7s (halves CPU spike during idle listening).
 - Silence limit: 800ms → 1000ms (prevents premature cut-off on natural pauses).
 - stream.read wrapped in IOError guard → recovers without crashing the loop.
 - send_to_backend: 3-retry + backoff, audible "connection issue" on failure.
 - Keyboard thread is daemon so it never blocks process exit.
"""

import os
import sys
import time
import json
import logging
import threading
import collections
import re
import asyncio
import select
import tty
import termios

import numpy as np
import pyaudio
import webrtcvad
from faster_whisper import WhisperModel
from src.core.api_client import JarvisAPIClient

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/jarvis_voice_loop.log"),
    ],
)
logger = logging.getLogger("JARVIS_VOICE")

from enum import Enum
import subprocess

# ── State Machine ─────────────────────────────────────────────────────────────
class VoiceState(Enum):
    IDLE     = 1
    ACTIVE   = 2
    COOLDOWN = 3

# ── Configuration ─────────────────────────────────────────────────────────────
SAMPLE_RATE           = 16000
FRAME_MS              = 20
FRAME_SIZE            = int(SAMPLE_RATE * FRAME_MS / 1000)   # 320 samples
SILENCE_LIMIT_MS      = 1000                                  # ↑ 800→1000ms
SILENCE_FRAMES        = int(SILENCE_LIMIT_MS / FRAME_MS)     # 50 frames
PRE_ROLL_SECONDS      = 1.5
WAKE_WORD_WINDOW_SEC  = 0.7                                   # ↓ 1.5→0.7s
WAKE_WORD_MODEL       = "tiny.en"
COMMAND_MODEL         = "base.en"
VOICE_TIMEOUT_SECONDS = 6
COOLDOWN_SECONDS      = 2
BACKEND_URL           = "http://127.0.0.1:8000"


class HighAccuracyVoiceLoop:
    """JARVIS Phase-21 Voice Pipeline: PyAudio → VAD → Whisper → Backend."""

    def __init__(self):
        logger.info("Initializing Voice Engine...")

        # Models
        self.wake_model = WhisperModel(WAKE_WORD_MODEL, device="cpu", compute_type="int8")
        self.cmd_model  = WhisperModel(COMMAND_MODEL,  device="cpu", compute_type="int8")

        # VAD (3 = most aggressive — good for office/noisy environments)
        self.vad = webrtcvad.Vad(3)

        # Audio
        self.audio  = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAME_SIZE,
        )

        # Buffers / state
        pre_roll_len            = int(SAMPLE_RATE / FRAME_SIZE * PRE_ROLL_SECONDS)
        self.pre_roll_buffer    = collections.deque(maxlen=pre_roll_len)
        self.api_client         = JarvisAPIClient(base_url=BACKEND_URL)

        self.state                = VoiceState.IDLE
        self.is_running           = True
        self.is_speaking          = False
        self.say_process          = None
        self.last_interaction_time = 0

        # Q-key activation flag (set by keyboard thread)
        self._key_activate = threading.Event()

        # Start keyboard listener in background
        self._start_keyboard_thread()

    # ── Keyboard activation ───────────────────────────────────────────────────
    def _start_keyboard_thread(self):
        """Daemon thread: pressing Q instantly activates listening."""
        def _listen():
            old = None
            try:
                fd  = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                tty.setraw(fd)
                while self.is_running:
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        ch = sys.stdin.read(1)
                        if ch.lower() == "q":
                            logger.info("⌨️  Q-key pressed → activating")
                            self._key_activate.set()
                        elif ch == "\x03":   # Ctrl-C
                            self.is_running = False
                            break
            except Exception:
                pass  # Silently ignore if stdin is not a TTY
            finally:
                if old:
                    try:
                        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
                    except Exception:
                        pass

        t = threading.Thread(target=_listen, daemon=True, name="kb-listener")
        t.start()

    # ── TTS ───────────────────────────────────────────────────────────────────
    def speak_native(self, text: str):
        if not text:
            return
        logger.info(f"Speaking: '{text}'")
        if self.say_process and self.say_process.poll() is None:
            self.say_process.terminate()
        self.is_speaking  = True
        self.say_process  = subprocess.Popen(["say", "-v", "Samantha", text])

    def stop_speaking(self):
        if self.say_process and self.say_process.poll() is None:
            self.say_process.terminate()
            self.say_process = None
        self.is_speaking = False

    # ── Wake word ─────────────────────────────────────────────────────────────
    def detect_wake_word(self, audio_data: bytes) -> bool:
        """Narrow 0.7s window check → halves CPU cost vs 1.5s."""
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        segs, _ = self.wake_model.transcribe(audio_np, beam_size=1, language="en")
        text = " ".join(s.text for s in segs).lower()
        return "jarvis" in text

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run_voice_cycle(self):
        logger.info("🎙️  Voice System Active. State: IDLE  |  Press Q to activate.")

        while self.is_running:
            try:
                # Maintain TTS state
                if self.is_speaking and self.say_process and self.say_process.poll() is not None:
                    self.is_speaking = False

                # Read 20ms frame — guard against overflow errors
                try:
                    frame = self.stream.read(FRAME_SIZE, exception_on_overflow=False)
                except IOError as io_err:
                    logger.warning(f"Audio overflow recovered: {io_err}")
                    continue

                self.pre_roll_buffer.append(frame)

                try:
                    is_speech = self.vad.is_speech(frame, SAMPLE_RATE)
                except Exception:
                    is_speech = False

                # Interrupt TTS if user speaks
                if is_speech and self.is_speaking:
                    self.stop_speaking()

                # ── Q-key shortcut ────────────────────────────────────────────
                if self._key_activate.is_set():
                    self._key_activate.clear()
                    if self.state != VoiceState.ACTIVE:
                        logger.info("Activated via Q-key")
                        self.speak_native("Yes?")
                        self.state              = VoiceState.ACTIVE
                        self.last_interaction_time = time.time()

                # ── State transitions ─────────────────────────────────────────
                if self.state == VoiceState.IDLE:
                    if is_speech:
                        window_frames = int(SAMPLE_RATE / FRAME_SIZE * WAKE_WORD_WINDOW_SEC)
                        check_audio   = b"".join(list(self.pre_roll_buffer)[-window_frames:])
                        if self.detect_wake_word(check_audio):
                            logger.info("Wake word detected")
                            self.speak_native("Yes?")
                            self.state              = VoiceState.ACTIVE
                            self.last_interaction_time = time.time()

                elif self.state == VoiceState.ACTIVE:
                    if is_speech:
                        self.process_command()
                        self.last_interaction_time = time.time()

                    if time.time() - self.last_interaction_time > VOICE_TIMEOUT_SECONDS:
                        self.state = VoiceState.COOLDOWN

                elif self.state == VoiceState.COOLDOWN:
                    self.speak_native("Standing by.")
                    time.sleep(COOLDOWN_SECONDS)
                    self.state = VoiceState.IDLE
                    logger.info("→ IDLE")

            except Exception as e:
                logger.error(f"Voice loop error: {e}")
                time.sleep(0.1)

    # ── Command capture ───────────────────────────────────────────────────────
    def process_command(self):
        """FIX 6: Fully guarded capture→transcribe→dispatch. Never crashes."""
        try:
            logger.info("Capturing command...")
            command_frames = list(self.pre_roll_buffer)
            silent_frames  = 0

            while silent_frames < SILENCE_FRAMES:
                try:
                    frame = self.stream.read(FRAME_SIZE, exception_on_overflow=False)
                except IOError:
                    continue
                command_frames.append(frame)
                try:
                    is_sp = self.vad.is_speech(frame, SAMPLE_RATE)
                except Exception:
                    is_sp = False
                silent_frames = 0 if is_sp else silent_frames + 1

                if len(command_frames) > SAMPLE_RATE / FRAME_SIZE * 10:
                    break   # 10s hard cap

            # Transcribe
            logger.info("Transcribing...")
            try:
                audio_np = np.frombuffer(b"".join(command_frames), dtype=np.int16).astype(np.float32) / 32768.0
                segs, _  = self.cmd_model.transcribe(audio_np, beam_size=2)
                text     = " ".join(s.text for s in segs).strip()
            except Exception as te:
                logger.error(f"Transcription failed: {te}")
                return  # Skip this command, continue voice loop

            if text:
                clean = re.sub(r"(hey\s+)?jarvis", "", text, flags=re.IGNORECASE).strip()
                if clean:
                    logger.info(f"[VOICE] command: <{clean}>")
                    threading.Thread(
                        target=self.send_to_backend,
                        args=(clean,),
                        daemon=True,
                        name="backend-dispatch",
                    ).start()
        except Exception as e:
            # FIX 6: Never crash the voice loop — log and return
            logger.error(f"[VOICE] process_command failed: {e}")

    # ── Backend dispatch ──────────────────────────────────────────────────────
    def send_to_backend(self, command: str):
        """3-retry backend call with audible failure notification."""
        import httpx as _httpx

        backoff = 1.0
        for attempt in range(3):
            try:
                with _httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{BACKEND_URL}/chat",
                        json={"prompt": command, "source": "voice"},
                        headers={"X-Jarvis-Source": "voice-daemon"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        reply = data.get("response", "")
                        if reply:
                            self.speak_native(reply)
                        return
                    logger.warning(f"Backend {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Backend attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    self.speak_native(
                        "I'm having trouble reaching the central processor. Please check if the backend is running."
                    )


# ── Entry point ───────────────────────────────────────────────────────────────
def start_voice_system():
    engine = HighAccuracyVoiceLoop()
    engine.run_voice_cycle()


if __name__ == "__main__":
    vt = threading.Thread(target=start_voice_system, daemon=True, name="voice-engine")
    vt.start()
    logger.info("🎙️  High-Accuracy Voice System running  |  Press Q to activate, Ctrl-C to quit")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down.")
