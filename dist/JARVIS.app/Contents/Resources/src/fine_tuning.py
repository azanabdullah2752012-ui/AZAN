"""
Model Fine-tuning Module for AZAN
Continuous fine-tuning on domain-specific knowledge and user feedback
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import threading
import time

logger = logging.getLogger(__name__)


class FineTuningData:
    """
    Prepares training data for Llama3 fine-tuning
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize fine-tuning data manager
        
        Args:
            data_dir: Data directory
        """
        self.data_dir = Path(data_dir)
        self.training_file = self.data_dir / "finetune_training.jsonl"
        self.validation_file = self.data_dir / "finetune_validation.jsonl"
        
        logger.info("✓ FineTuningData initialized")
    
    def prepare_training_corpus(self, 
                               training_pairs: List[Dict],
                               high_rated_ratio: float = 0.7) -> Dict:
        """
        Prepare training corpus from Q&A pairs
        
        Args:
            training_pairs: List of Q&A pairs
            high_rated_ratio: Ratio of high-rated examples to use
        
        Returns:
            Preparation statistics
        """
        logger.info("📊 Preparing fine-tuning corpus...")
        
        # Separate high and low rated
        high_rated = [p for p in training_pairs if p.get("reward", 0) >= 3.5]
        low_rated = [p for p in training_pairs if p.get("reward", 0) < 3.5]
        
        # Create training corpus with weighted sampling
        corpus = []
        
        # Add all high-rated examples
        for pair in high_rated:
            corpus.append({
                "role": "user",
                "content": pair.get("question", ""),
                "response": pair.get("answer", ""),
                "rating": pair.get("reward", 3.5),
                "type": "high_quality"
            })
        
        # Add subset of low-rated for balance
        num_low = int(len(high_rated) * (1 - high_rated_ratio) / high_rated_ratio)
        for pair in low_rated[:num_low]:
            corpus.append({
                "role": "user",
                "content": pair.get("question", ""),
                "response": pair.get("answer", ""),
                "rating": pair.get("reward", 2.5),
                "type": "learning_example"
            })
        
        # Write JSONL format
        try:
            with open(self.training_file, 'w') as f:
                for item in corpus:
                    f.write(json.dumps(item) + '\n')
            
            logger.info(f"✓ Created training corpus: {len(corpus)} examples")
            
        except Exception as e:
            logger.error(f"Error writing training file: {e}")
            return {"error": str(e)}
        
        return {
            "total_examples": len(corpus),
            "high_rated": len(high_rated),
            "learning_examples": num_low,
            "file": str(self.training_file)
        }
    
    def prepare_validation_set(self, 
                              training_pairs: List[Dict],
                              validation_ratio: float = 0.1) -> Dict:
        """
        Prepare validation set for model evaluation
        
        Args:
            training_pairs: List of Q&A pairs
            validation_ratio: Ratio of data for validation
        
        Returns:
            Validation set statistics
        """
        import random
        
        # Sample for validation
        num_validation = max(1, int(len(training_pairs) * validation_ratio))
        validation_pairs = random.sample(training_pairs, num_validation)
        
        try:
            with open(self.validation_file, 'w') as f:
                for pair in validation_pairs:
                    item = {
                        "role": "user",
                        "content": pair.get("question", ""),
                        "response": pair.get("answer", ""),
                        "rating": pair.get("reward", 3.0)
                    }
                    f.write(json.dumps(item) + '\n')
            
            logger.info(f"✓ Created validation set: {len(validation_pairs)} examples")
            
        except Exception as e:
            logger.error(f"Error writing validation file: {e}")
            return {"error": str(e)}
        
        return {
            "validation_examples": num_validation,
            "file": str(self.validation_file)
        }


class FineTuneManager:
    """
    Manages fine-tuning of Llama3 model
    """
    
    def __init__(self, 
                 model_name: str = "llama3",
                 data_dir: str = "data"):
        """
        Initialize fine-tune manager
        
        Args:
            model_name: Name of model to fine-tune
            data_dir: Data directory
        """
        self.model_name = model_name
        self.data_dir = Path(data_dir)
        self.checkpoint_dir = self.data_dir / "finetuned_models"
        self.history_file = self.data_dir / "finetuning_history.json"
        
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.history = {}
        self._load_history()
        
        logger.info(f"✓ FineTuneManager initialized for {model_name}")
    
    def _load_history(self):
        """Load fine-tuning history"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                logger.info(f"Loaded {len(self.history)} fine-tuning events")
            except Exception as e:
                logger.error(f"Error loading history: {e}")
    
    def _save_history(self):
        """Save fine-tuning history"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def start_finetuning(self, 
                        training_file: str,
                        epochs: int = 3,
                        batch_size: int = 8,
                        learning_rate: float = 1e-5) -> Dict:
        """
        Start fine-tuning process
        
        Args:
            training_file: Path to training data file
            epochs: Number of training epochs
            batch_size: Batch size for training
            learning_rate: Learning rate
        
        Returns:
            Fine-tuning job info
        """
        logger.info(f"🚀 Starting fine-tuning on {self.model_name}...")
        
        job_id = f"finetune_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        job_info = {
            "id": job_id,
            "model": self.model_name,
            "training_file": training_file,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "progress": 0
        }
        
        self.history[job_id] = job_info
        self._save_history()
        
        logger.info(f"✓ Fine-tuning job created: {job_id}")
        
        # In a real scenario, this would call the fine-tuning API
        # For now, we'll simulate it
        return job_info
    
    def simulate_finetuning(self, job_id: str, duration: int = 10) -> Dict:
        """
        Simulate fine-tuning process (for demo)
        
        Args:
            job_id: Job ID
            duration: Duration in seconds
        
        Returns:
            Final results
        """
        if job_id not in self.history:
            return {"error": "Job not found"}
        
        job = self.history[job_id]
        
        for epoch in range(1, job["epochs"] + 1):
            job["current_epoch"] = epoch
            job["progress"] = int((epoch / job["epochs"]) * 100)
            job["status"] = f"training_epoch_{epoch}"
            self._save_history()
            
            logger.info(f"  📈 Epoch {epoch}/{job['epochs']} - {job['progress']}%")
            time.sleep(duration / job["epochs"])
        
        # Mark as complete
        checkpoint_path = self.checkpoint_dir / f"{job_id}_model"
        checkpoint_path.mkdir(exist_ok=True)
        
        job["status"] = "completed"
        job["progress"] = 100
        job["completed_at"] = datetime.now().isoformat()
        job["checkpoint"] = str(checkpoint_path)
        job["metrics"] = {
            "final_loss": round(0.15 + (5 - job["epochs"]) * 0.01, 3),
            "validation_accuracy": round(0.85 + (job["epochs"] * 0.03), 3)
        }
        
        self._save_history()
        
        logger.info(f"✓ Fine-tuning completed: {job_id}")
        
        return job
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of fine-tuning job"""
        return self.history.get(job_id)
    
    def get_recent_checkpoints(self, limit: int = 5) -> List[Dict]:
        """Get recent fine-tuned checkpoints"""
        completed = [j for j in self.history.values() if j.get("status") == "completed"]
        completed.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
        
        return completed[:limit]
    
    def get_finetuning_stats(self) -> Dict:
        """Get fine-tuning statistics"""
        total = len(self.history)
        completed = sum(1 for j in self.history.values() if j.get("status") == "completed")
        running = sum(1 for j in self.history.values() if j.get("status") == "running")
        
        return {
            "total_jobs": total,
            "completed": completed,
            "running": running,
            "success_rate": round(completed / max(total, 1) * 100, 1),
            "last_checkpoint": self.get_recent_checkpoints(1)
        }


class AutomatedFineTuningScheduler:
    """
    Automatically triggers fine-tuning on schedule
    """
    
    def __init__(self, finetune_manager: FineTuneManager, 
                 training_data_source,
                 check_interval: int = 86400):
        """
        Initialize scheduler
        
        Args:
            finetune_manager: FineTuneManager instance
            training_data_source: Source for training data
            check_interval: Seconds between fine-tuning checks (default: 1 day)
        """
        self.finetune_manager = finetune_manager
        self.training_data_source = training_data_source
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        
        logger.info(f"✓ AutomatedFineTuningScheduler initialized (interval: {check_interval}s)")
    
    def start(self):
        """Start automatic fine-tuning scheduler"""
        if self.running:
            logger.warning("Fine-tuning scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.thread.start()
        logger.info("✓ Fine-tuning scheduler started")
    
    def stop(self):
        """Stop scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("✓ Fine-tuning scheduler stopped")
    
    def _schedule_loop(self):
        """Background scheduling loop"""
        while self.running:
            try:
                # Check if we have new training data
                new_pairs = self.training_data_source.get("new_training_pairs", 0)
                
                if new_pairs >= 50:  # Fine-tune if 50+ new pairs
                    logger.info(f"🔄 Triggering fine-tuning with {new_pairs} new pairs...")
                    
                    # Prepare data
                    finetuning_data = FineTuningData()
                    # In real scenario, would load actual training data here
                    
                    logger.info("✓ Fine-tuning scheduled")
                
            except Exception as e:
                logger.error(f"Error in fine-tuning scheduler: {e}")
            
            time.sleep(self.check_interval)


# Global fine-tuning instances
_finetune_manager = None
_finetune_scheduler = None


def initialize_finetuning() -> FineTuneManager:
    """Initialize global fine-tune manager"""
    global _finetune_manager
    if _finetune_manager is None:
        _finetune_manager = FineTuneManager()
    return _finetune_manager


def initialize_finetuning_scheduler(training_data_source: Dict = None,
                                    check_interval: int = 86400) -> AutomatedFineTuningScheduler:
    """Initialize and start fine-tuning scheduler"""
    global _finetune_scheduler
    if _finetune_scheduler is None:
        manager = initialize_finetuning()
        _finetune_scheduler = AutomatedFineTuningScheduler(
            manager, 
            training_data_source or {},
            check_interval=check_interval
        )
        _finetune_scheduler.start()
    return _finetune_scheduler


def get_finetuning() -> FineTuneManager:
    """Get global fine-tune manager"""
    global _finetune_manager
    if _finetune_manager is None:
        initialize_finetuning()
    return _finetune_manager


def get_finetuning_scheduler() -> AutomatedFineTuningScheduler:
    """Get global fine-tuning scheduler"""
    global _finetune_scheduler
    if _finetune_scheduler is None:
        initialize_finetuning_scheduler()
    return _finetune_scheduler
