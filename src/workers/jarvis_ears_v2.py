import os
import sys
import time
import json
import logging
import subprocess
import threading
import collections
import re
import asyncio
import numpy as np
import pyaudio
from faster_whisper import WhisperModel
from src.core.api_client import JarvisAPIClient

# Configure logging to match user's debug requirements
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("/tmp/apple_silicon_jarvis.log")]
)
logger = logging.getLogger("SILICON_JARVIS")

# Configuration (Apple Silicon Optimized)
WAKE_REGEX = r"(hey|hi|yo|hello)?\s*(jarvis|azan)"
SAMPLE_RATE = 16000 # 16kHz is optimal for Whisper
CHUNK_SIZE = 1024 # CoreAudio friendly buffer
PRE_ROLL_SECONDS = 3.0
MAX_COMMAND_SECONDS = 8.0
INTERRUPT_THRESHOLD = 0.08 # Adjusted for M1-M4 mic sensitivity

class AppleSiliconJarvisEars:
    """
    Apple Silicon Optimized Ambient Voice System:
    VAD + Metal-Ready Faster-Whisper + CoreAudio Tuning
    """
    def __init__(self, model_size="tiny.en"):
        logger.info(f"Initializing Silicon-Native STT ({model_size})...")
        # faster-whisper uses CTranslate2 which is highly optimized for Apple Silicon CPU/NPU
        self.stt_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        self.api_client = JarvisAPIClient()
        self.audio = pyaudio.PyAudio()
        
        # Open Stream with CoreAudio optimizations
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        # Audio Buffers
        self.audio_deque = collections.deque(maxlen=int((SAMPLE_RATE / CHUNK_SIZE) * 5.0))
        self.command_queue = asyncio.Queue()
        
        # State
        self.is_running = True
        self.is_speaking = False
        self.say_process = None
        self.last_wake_time = 0
        
        logger.info("Listening...")
        self.speak_offline("Silicon optimizations active. Ready.")

    def speak_offline(self, text):
        """Native macOS 'say' (Fastest native TTS)."""
        if not text: return
        logger.info(f"Speaking...")
        self.is_speaking = True
        try:
            # Samantha is high quality and native to macOS
            self.say_process = subprocess.Popen(["say", "-v", "Samantha", text])
        except Exception as e:
            logger.error(f"Speech error: {e}")
            self.is_speaking = False

    def interrupt(self):
        """Instant interrupt implementation."""
        if self.say_process and self.say_process.poll() is None:
            # logger.info("Interrupting speech...")
            self.say_process.terminate()
            self.say_process = None
        self.is_speaking = False

    def normalize_audio(self, audio_data):
        """Normalize audio energy for better VAD/STT."""
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        peak = np.max(np.abs(audio_np))
        if peak > 0.01: # Avoid amplifying floor noise
            audio_np = audio_np / peak * 0.9
        return audio_np

    async def listener_loop(self):
        """LOOP 1: Continuous Audio Capture + Energy Normalization."""
        while self.is_running:
            try:
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                self.audio_deque.append(data)
                
                # Interrupt check (Silicon mic sensitivity is high; energy check is fast)
                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                energy = np.sqrt(np.mean(audio_np**2))
                
                if self.is_speaking and energy > INTERRUPT_THRESHOLD:
                    self.interrupt()
                
                if self.say_process and self.say_process.poll() is not None:
                    self.is_speaking = False
                    
                await asyncio.sleep(0.001)
            except Exception as e:
                logger.error(f"Listener error: {e}")
                await asyncio.sleep(0.1)

    async def wake_word_detector(self):
        """LOOP 2: Fast Wake Word Detection (Sub-200ms)."""
        while self.is_running:
            try:
                if len(self.audio_deque) >= int((SAMPLE_RATE / CHUNK_SIZE) * 1.5):
                    raw_audio = b"".join(list(self.audio_deque)[-int((SAMPLE_RATE/CHUNK_SIZE)*1.5):])
                    audio_np = self.normalize_audio(raw_audio)
                    
                    # Transcribe current slice with VAD enabled
                    segments, _ = self.stt_model.transcribe(
                        audio_np, 
                        beam_size=1, 
                        vad_filter=True, 
                        vad_parameters=dict(min_silence_duration_ms=500)
                    )
                    text = " ".join([s.text for s in segments]).lower()
                    
                    if re.search(WAKE_REGEX, text) and (time.time() - self.last_wake_time > 2.0):
                        logger.info("Wake word detected")
                        self.last_wake_time = time.time()
                        
                        # Pre-roll capture (last 3s)
                        await self.command_queue.put(b"".join(list(self.audio_deque)))
                        
                await asyncio.sleep(0.15) # Optimized refresh for M1-M4
            except Exception as e:
                logger.error(f"Wake detector error: {e}")
                await asyncio.sleep(0.5)

    async def command_processor(self):
        """LOOP 3: Non-Blocking Command Capture & Execution."""
        while self.is_running:
            try:
                pre_roll = await self.command_queue.get()
                
                # Capture until silence or 5s
                # logger.info("Listening for command...")
                extra = []
                for _ in range(int((SAMPLE_RATE / CHUNK_SIZE) * 5.0)):
                    chunk = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    extra.append(chunk)
                
                total_np = self.normalize_audio(pre_roll + b"".join(extra))
                
                # Full Command STT
                segments, _ = self.stt_model.transcribe(total_np, beam_size=2, vad_filter=True)
                full_text = " ".join([s.text for s in segments]).strip()
                
                if full_text:
                    logger.info(f"Command captured: <{full_text}>")
                    asyncio.create_task(self.execute_and_respond(full_text))
                    
            except Exception as e:
                logger.error(f"Command processing error: {e}")

    async def execute_and_respond(self, command: str):
        """Backend execution loop with retry logic."""
        logger.info("Sending to backend")
        session_id = f"silicon_{int(time.time())}"
        
        # Clean command
        clean_command = re.sub(WAKE_REGEX, "", command.lower(), count=1).strip() or command
        
        for attempt in range(2):
            try:
                response_received = False
                current_sentence = ""
                
                async for token in self.api_client.stream_chat(clean_command, session_id):
                    if not response_received:
                        logger.info("Response received")
                        response_received = True
                    
                    current_sentence += token
                    if any(p in current_sentence for p in [".", "!", "?", "\n"]):
                        self.speak_offline(current_sentence.strip())
                        current_sentence = ""
                
                if current_sentence.strip():
                    self.speak_offline(current_sentence.strip())
                
                if response_received: break
                else: raise Exception("No response")

            except Exception as e:
                logger.warning(f"Backend attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    self.speak_offline("Something went wrong, retrying later.")

    async def start(self):
        self.loop = asyncio.get_event_loop()
        await asyncio.gather(
            self.listener_loop(),
            self.wake_word_detector(),
            self.command_processor()
        )

def start_voice_loop():
    """FIX 3: Run voice listening loop in a separate thread to prevent blocking."""
    ears = AppleSiliconJarvisEars()
    try:
        asyncio.run(ears.start())
    except Exception as e:
        logger.error(f"Voice loop thread died: {e}")

if __name__ == "__main__":
    # Start as a daemon thread exactly as requested
    threading.Thread(target=start_voice_loop, daemon=True).start()
    logger.info("🎙️ Non-blocking voice daemon thread started")
    
    # Keep main thread alive
    while True:
        time.sleep(1)
