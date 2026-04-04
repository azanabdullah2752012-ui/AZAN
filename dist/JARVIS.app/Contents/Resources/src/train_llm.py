"""
Training pipeline for fine-tuning Llama3 locally using Ollama.
Loads conversation data from CSV and creates JSONL format for training.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import csv
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH = Path("data") / "chat_data.csv"
TRAINING_JSONL_PATH = Path("data") / "chat_data_training.jsonl"
MODEL_PATH = Path("model") / "llama3_finetuned"


def load_data(data_path: Path = DATA_PATH) -> list[dict[str, str]]:
    """
    Load conversation data from CSV file with columns: input, response.
    
    Args:
        data_path: Path to CSV file containing training data
        
    Returns:
        List of dictionaries with 'input' and 'response' keys
        
    Raises:
        FileNotFoundError: If data file doesn't exist
        ValueError: If CSV doesn't have required columns
    """
    if not data_path.exists():
        raise FileNotFoundError(f"Training data not found at '{data_path}'.")
    
    conversations = []
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or set(reader.fieldnames) != {'input', 'response'}:
                raise ValueError("CSV must have exactly two columns: 'input' and 'response'")
            
            for row in reader:
                if row['input'].strip() and row['response'].strip():
                    conversations.append({
                        'input': row['input'].strip(),
                        'response': row['response'].strip()
                    })
    except csv.Error as e:
        raise ValueError(f"Error parsing CSV file: {e}")
    
    if not conversations:
        raise ValueError("No valid conversation pairs found in data file.")
    
    logger.info(f"Loaded {len(conversations)} conversation pairs from '{data_path}'")
    return conversations


def preprocess_data(conversations: list[dict[str, str]]) -> list[dict[str, Any]]:
    """
    Preprocess conversation data into training format.
    Converts to message-based format compatible with LLM training.
    
    Args:
        conversations: List of input-response pairs
        
    Returns:
        List of conversation dictionaries with 'messages' field
    """
    processed = []
    for conv in conversations:
        # Create a conversation with system context and user-assistant exchange
        conversation = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are AZAN, a helpful AI assistant built with Llama3. Respond helpfully and concisely."
                },
                {
                    "role": "user",
                    "content": conv['input']
                },
                {
                    "role": "assistant",
                    "content": conv['response']
                }
            ]
        }
        processed.append(conversation)
    
    logger.info(f"Preprocessed {len(processed)} conversation samples")
    return processed


def save_training_data_jsonl(
    conversations: list[dict[str, str]], 
    output_path: Path = TRAINING_JSONL_PATH
) -> None:
    """
    Save preprocessed data in JSONL format for training.
    
    Args:
        conversations: List of preprocessed conversations
        output_path: Path to save JSONL file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for conv in conversations:
            f.write(json.dumps(conv) + '\n')
    
    logger.info(f"Saved {len(conversations)} samples to '{output_path}'")


def train_model(data_path: Path = DATA_PATH) -> dict[str, Any]:
    """
    Train/fine-tune Llama3 model using local conversation data.
    
    NOTE: Ollama doesn't support direct fine-tuning through Python bindings yet.
    This function prepares data in the correct format for manual fine-tuning.
    For actual fine-tuning, use Ollama's CLI:
        ollama create llama3_finetuned -f Modelfile
    
    Where Modelfile contains your training data and parameters.
    
    Args:
        data_path: Path to CSV training data
        
    Returns:
        Dictionary with training metrics and status
    """
    try:
        # Load and preprocess data
        conversations = load_data(data_path=data_path)
        processed = preprocess_data(conversations)
        save_training_data_jsonl(processed)
        
        metrics = {
            "status": "success",
            "samples_processed": len(conversations),
            "training_data_saved": str(TRAINING_JSONL_PATH),
            "message": (
                f"Prepared {len(conversations)} samples for training. "
                "To complete fine-tuning, use Ollama's create command with a Modelfile."
            )
        }
        logger.info("Training data preparation complete!")
        return metrics
        
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Training failed: {e}")
        raise


def main() -> None:
    """Run training pipeline."""
    try:
        metrics = train_model()
        logger.info(f"✓ Training Status: {metrics['status']}")
        logger.info(f"✓ Samples Processed: {metrics['samples_processed']}")
        logger.info(f"✓ Training Data: {metrics['training_data_saved']}")
        logger.info(f"✓ Note: {metrics['message']}")
    except Exception as e:
        logger.error(f"Training pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
