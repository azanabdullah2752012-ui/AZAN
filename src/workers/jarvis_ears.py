import os
import sys
import time
import json
import logging
import subprocess
import threading
import collections
import re
import httpx
import speech_recognition as sr
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("JARVIS_EARS")

# Configuration
BASE_URL = "http://127.0.0.1:8000"
QUICK_URL = f"{BASE_URL}/quick_command"
CHAT_URL = f"{BASE_URL}/chat"
STATUS_URL = f"{BASE_URL}/status"
WAKE_WORDS = ["jarvis", "hey jarvis", "azan"]
MAX_COMMAND_DURATION = 6.0
SILENCE_TIMEOUT = 1.2

class JarvisProEars:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Optimizer settings
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = SILENCE_TIMEOUT
        
        self.is_running = True
        self.last_trigger_time = 0
        
        logger.info("Initializing JARVIS Pro Ears (Always-Listening)...")
        self.calibrate()
        self.speak_offline("Voice systems active. Always listening.")

    def calibrate(self):
        with self.microphone as source:
            logger.info("Calibrating for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)

    def speak_offline(self, text):
        """Fast offline feedback."""
        logger.info(f"JARVIS: {text}")
        subprocess.run(["say", "-v", "Daniel", text])

    def normalize_audio(self, audio_data):
        """Normalize audio energy for better STT."""
        try:
            # Convert to numpy array
            data = np.frombuffer(audio_data.get_raw_data(), dtype=np.int16)
            if len(data) == 0: return audio_data
            
            # Normalize
            peak = np.max(np.abs(data))
            if peak > 0:
                data = (data.astype(float) * (32767.0 / peak)).astype(np.int16)
            
            # Create new AudioData object
            return sr.AudioData(data.tobytes(), audio_data.sample_rate, audio_data.sample_width)
        except Exception as e:
            logger.warning(f"Normalization failed: {e}")
            return audio_data

    def check_backend(self):
        """Health check before requests."""
        try:
            with httpx.Client() as client:
                resp = client.get(STATUS_URL, timeout=2.0)
                return resp.status_code == 200
        except Exception:
            return False

    def send_command_to_backend(self, text: str):
        """High-reliability API call with retries and quick-path logic."""
        if not self.check_backend():
            self.speak_offline("JARVIS backend offline.")
            return

        # 1. Command Cleaning & Wake Word Stripping
        clean_text = text.lower()
        for ww in WAKE_WORDS:
            if clean_text.startswith(ww):
                clean_text = clean_text[len(ww):].strip()
                break
        
        if not clean_text:
            return

        logger.info(f"Processing command: '{clean_text}'")

        # 2. Fast Path Execution (Simple Patterns)
        quick_patterns = ["mute", "unmute", "open safari", "what app", "active app", "volume"]
        is_quick = any(p in clean_text for p in quick_patterns)
        
        url = QUICK_URL if is_quick else CHAT_URL
        payload = {
            "command": clean_text,
            "source": "voice"
        } if is_quick else {
            "prompt": clean_text,
            "stream": False,
            "model": "llama3",
            "source": "voice"
        }

        # 3. Request with Retry Logic
        for attempt in range(3): # Initial + 2 retries
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    response_text = data.get("result") or data.get("response", "Success")
                    self.speak_offline(response_text)
                    return
            except Exception as e:
                logger.warning(f"API Attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(0.5)
                else:
                    self.speak_offline("Connection issue, retrying later.")

    def continuous_listen(self):
        """Always-listening loop: Wake word + Command in one pass."""
        logger.info("Continuous listening loop started.")
        
        with self.microphone as source:
            while self.is_running:
                try:
                    # Listen for audio (rolling buffer implicitly handled by SR phrase detection)
                    # We capture up to 6 seconds or until SILENCE_TIMEOUT
                    logger.info("Listening...")
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=MAX_COMMAND_DURATION)
                    
                    # Cooldown check
                    if time.time() - self.last_trigger_time < 2.0:
                        continue

                    # Transcribe
                    try:
                        # Normalize audio before transcription
                        audio = self.normalize_audio(audio)
                        text = self.recognizer.recognize_google(audio).lower()
                        logger.info(f"Heard: '{text}'")

                        # Detect wake word
                        if any(ww in text for ww in WAKE_WORDS):
                            self.last_trigger_time = time.time()
                            # Process entire sentence
                            self.send_command_to_backend(text)
                            
                    except sr.UnknownValueError:
                        # Ignore silence/noise
                        continue
                    except sr.RequestError as e:
                        logger.error(f"STT Error: {e}")
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"Mic loop error: {e}")
                    time.sleep(1)

if __name__ == "__main__":
    try:
        ears = JarvisProEars()
        ears.continuous_listen()
    except KeyboardInterrupt:
        logger.info("Stopping...")
