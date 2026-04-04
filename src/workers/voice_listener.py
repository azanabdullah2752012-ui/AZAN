import os
import sys
import json
import time
import uuid
import requests
import threading
import logging
import speech_recognition as sr
from PyQt6.QtCore import pyqtSignal, QObject
# Trying to use a built-in macOS TTS first for the fastest feedback
import subprocess

logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/chat/stream"

class VoiceAgent:
    """An autonomous agent that perpetually listens for 'Azan' or 'JARVIS'."""
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjusting ambient noise initially
        with self.microphone as source:
            print("Calibrating microphone for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("Listening for wake word: 'Hey Azan' or 'JARVIS'...")
            self.speak("JARVIS is now online and listening.")

    def speak(self, text):
        """Use native macOS Siri voice to respond instantly."""
        # Using AppleScript/say ensures no delays from external API pings
        try:
            subprocess.run(["say", "-v", "Samantha", text])
        except Exception as e:
            logger.error(f"Speech failed: {e}")

    def query_jarvis(self, prompt: str):
        """Send the transcribed speech to the JARVIS backend and fetch the final answer to speak."""
        session_id = f"voice_{uuid.uuid4().hex[:8]}"
        payload = {
            "prompt": prompt,
            "session_id": session_id,
            "model": "llama3", # Assuming text logic first
            "temperature": 0.5
        }
        
        print(f"\n[Voice] Thinking about: {prompt}")
        final_answer = ""
        try:
            with requests.post(API_URL, json=payload, stream=True, timeout=300) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if "token" in data:
                                    final_answer += data["token"]
                            except json.JSONDecodeError:
                                pass
                                
            # We want to speak the final synthesized answer, but it typically contains the thinking trace
            # if we stream. So we just strip out any markdown blocks if any exist.
            import re
            spoken_text = re.sub(r'```.*?```', '', final_answer, flags=re.DOTALL)
            spoken_text = spoken_text.replace('*', '').replace('_', '').strip()
            
            print(f"[Voice] Reply: {spoken_text}")
            self.speak(spoken_text)
            
        except Exception as e:
            print(f"[Voice] API Error: {e}")
            self.speak("I'm sorry, my core backend is currently unreachable.")

    def run_loop(self):
        """Perpetually listen in the background."""
        while True:
            try:
                with self.microphone as source:
                    # Listen in short chunks to catch the wake word quickly
                    audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=5.0)
                
                # Transcribe whatever was heard
                text = self.recognizer.recognize_google(audio).lower()
                print(f"[MIC TRACE] Heard: '{text}'", flush=True)
                
                if "azan" in text or "jarvis" in text:
                    self.speak("Yes, Azan?")
                    print(f"\n[Detected Wake Word in text: '{text}']", flush=True)
                    print("Listening for command...")
                    with self.microphone as source:
                        command_audio = self.recognizer.listen(source, timeout=5.0, phrase_time_limit=15.0)
                    
                    command_text = self.recognizer.recognize_google(command_audio)
                    print(f"Heard Command: {command_text}")
                    self.query_jarvis(command_text)
                    print("\nListening for wake word again...")
                    
            except sr.WaitTimeoutError:
                pass # Normal timeout, loop again
            except sr.UnknownValueError:
                pass # Heard noise but couldn't parse it
            except sr.RequestError as e:
                print(f"[MIC ERROR] Could not request results from Google Speech Recognition service; {e}", flush=True)
                time.sleep(5)
            except Exception as e:
                print(f"[MIC ERROR] Unexpected error in background voice loop: {e}", flush=True)
                time.sleep(2)


if __name__ == "__main__":
    agent = VoiceAgent()
    agent.run_loop()
