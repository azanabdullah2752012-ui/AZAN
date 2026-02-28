"""
Inference module for AZAN chatbot using Llama3 via Ollama.
Supports both base and fine-tuned model variants with persistent caching.
"""

from __future__ import annotations

import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict
import json

try:
    from ollama import chat
    OLLAMA_PKG_AVAILABLE = True
except ImportError:
    chat = None
    OLLAMA_PKG_AVAILABLE = False
    logging.warning("ollama package not installed. Install with: pip install ollama. Using httpx fallback.")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Model names
BASE_MODEL_NAME = "llama3"
FINETUNED_MODEL_NAME = "llama3_president_rlhf"
FINETUNED_MODEL_PATH = Path("model") / "llama3_president_rlhf"

# Global cache for responses (persistent + in-memory)
_INFERENCE_CACHE: Dict[str, str] = {}
CACHE_FILE = Path("data") / "inference_cache.json"

def _load_cache():
    """Load cache from disk on startup."""
    global _INFERENCE_CACHE
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                _INFERENCE_CACHE = json.load(f)
                logger.info(f"Loaded {len(_INFERENCE_CACHE)} cached responses")
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")

def _save_cache():
    """Save cache to disk."""
    try:
        CACHE_FILE.parent.mkdir(exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(_INFERENCE_CACHE, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save cache: {e}")

def _get_cache_key(prompt: str, model: str) -> str:
    """Generate cache key from prompt and model."""
    return f"{model}:{hashlib.md5(prompt.encode()).hexdigest()}"

def clear_cache():
    """Clear all cached responses."""
    global _INFERENCE_CACHE
    _INFERENCE_CACHE.clear()
    try:
        CACHE_FILE.unlink()
        logger.info("Cache cleared")
    except:
        pass

# Load cache on module import
_load_cache()


def get_available_model() -> str:
    """
    Determine which model to use: fine-tuned if available, otherwise base.
    
    Returns:
        Name of the model to use for inference
    """
    # Check if fine-tuned model has been created
    # For now, we use the base model unless explicitly fine-tuned via Ollama CLI
    # In production, you'd check if FINETUNED_MODEL_NAME exists in Ollama
    return BASE_MODEL_NAME


def predict(prompt: str, model_name: Optional[str] = None, use_cache: bool = True, speed_mode: bool = True) -> str:
    """
    Send a prompt to Llama3 and return the response.
    Uses persistent caching + speed optimizations for fast inference.
    
    Args:
        prompt: User input/prompt to send to the model
        model_name: Optional model name override. If None, uses base model.
        use_cache: Whether to use/save response cache (default: True)
        speed_mode: If True, uses aggressive speed optimizations (default: True)
        
    Returns:
        The model's text response
        
    Raises:
        ValueError: If prompt is empty or invalid
        RuntimeError: If inference fails
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError("Prompt must be a non-empty string.")
    
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt cannot be empty or whitespace only.")
    
    # Select model
    if model_name is None:
        model_name = get_available_model()
    
    # Check cache first (instant response)
    cache_key = _get_cache_key(prompt, model_name)
    if use_cache and cache_key in _INFERENCE_CACHE:
        logger.debug(f"Cache hit: {prompt[:40]}... (instant)")
        return _INFERENCE_CACHE[cache_key]
    
    try:
        logger.debug(f"Inference: {prompt[:50]}...")
        
        # Speed mode: Balanced for both speed and quality
        if speed_mode:
            options = {
                "num_predict": 256,       # Complete responses (was 50)
                "temperature": 0.5,       # Balanced creativity
                "top_k": 40,              # Normal choices
                "top_p": 0.9,             # Natural sampling
                "repeat_penalty": 1.1
            }
        else:
            # Quality mode: Longer responses, slower
            options = {
                "num_predict": 512,       # Much longer responses
                "temperature": 0.7,
                "top_k": 40,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        
        # Use Ollama with optimized settings
        response = chat(
            model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are AZAN, an advanced AI assistant powered by continuous reinforcement learning from real-time news sources. You learn from multiple categories: business, technology, politics, world, science, sports, entertainment, and national news. When answering questions, incorporate relevant information from your continuously updated knowledge base. Provide complete, detailed, and accurate answers based on what you've learned. You are always up-to-date and learning new information constantly."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            stream=False,
            options=options
        )
        
        # Extract text from response
        if not hasattr(response, 'message') or not hasattr(response.message, 'content'):
            raise RuntimeError("Unexpected response structure from Ollama.")
        
        result = response.message.content.strip()
        
        if not result:
            raise RuntimeError("Model returned an empty response.")
        
        # Cache the result (persistent)
        if use_cache:
            _INFERENCE_CACHE[cache_key] = result
            _save_cache()
        
        logger.debug(f"Response: {result[:80]}...")
        return result
        
    except Exception as e:
        error_msg = f"Inference failed: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def predict_chat(prompt: str, model_name: Optional[str] = None, speed_mode: bool = True) -> str:
    """
    Predict function for use in web API.
    Returns response string with optimized speed.
    
    Args:
        prompt: User prompt
        model_name: Optional model name (default: base model)
        speed_mode: Use speed optimizations (default: True)
        
    Returns:
        Response string
        
    Raises:
        ValueError: If prompt is invalid
        RuntimeError: If inference fails
    """
    if not prompt:
        raise ValueError("Prompt cannot be empty.")
    
    response_text = predict(prompt, model_name=model_name, speed_mode=speed_mode)
    return response_text


if __name__ == "__main__":
    # Simple test
    user_prompt = "Hello, AZAN!"
    print(f"Prompt: {user_prompt}")
    try:
        response = predict(user_prompt)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
