import os
import time
import logging
import threading
from typing import List
from src.memory.vector_store import KnowledgeMemory

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Background worker that semantically indexes local ~/Documents and ~/Desktop files."""
    
    def __init__(self, target_folders: List[str]):
        self.target_folders = [os.path.expanduser(f) for f in target_folders]
        self.memory = KnowledgeMemory()
        self.last_sync = 0
        self.sync_interval = 3600 * 4 # Every 4 hours
        
    def start(self):
        """Starts the background indexing thread."""
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info(f"Document Indexer started for: {self.target_folders}")

    def _run_loop(self):
        while True:
            try:
                self._index_files()
                time.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Indexer loop error: {e}")
                time.sleep(60)

    def _index_files(self):
        """Walks target folders and indexes text/pdf content."""
        logger.info("[Indexer] Starting incremental sync...")
        for folder in self.target_folders:
            if not os.path.exists(folder):
                continue
                
            for root, _, files in os.walk(folder):
                # Skip virtual environments and hidden git folders
                if '.venv' in root or '.git' in root:
                    continue
                    
                for file in files:
                    if file.startswith('.'): continue
                    
                    # Target text-heavy formats
                    if file.endswith(('.txt', '.md', '.py', '.js', '.json', '.pdf')):
                        path = os.path.join(root, file)
                        mtime = os.path.getmtime(path)
                        
                        # Only index if changed recently or new
                        if mtime > self.last_sync:
                            self._process_file(path)
        
        self.last_sync = time.time()
        logger.info("[Indexer] Sync complete.")

    def _process_file(self, path: str):
        """Extracts text and pushes to ChromaDB."""
        try:
            content = ""
            if path.endswith(('.txt', '.md', '.py', '.js', '.json')):
                with open(path, 'r', errors='ignore') as f:
                    content = f.read(10000) # Index first 10k chars
            
            if content:
                # Add to memory with source metadata
                # Correct method name is add_claim(claim_text, source, confidence, verified)
                self.memory.add_claim(
                    claim_text=f"File: {os.path.basename(path)}\nContent: {content[:5000]}",
                    source=f"local_file:{path}",
                    confidence=1.0,
                    verified=True
                )
                logger.info(f"[Indexer] Indexed: {path}")
        except Exception as e:
            logger.error(f"Error processing {path}: {e}")

if __name__ == "__main__":
    indexer = DocumentIndexer(["~/Documents", "~/Desktop"])
    indexer.start()
    while True: time.sleep(1)
