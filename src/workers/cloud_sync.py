import os
import shutil
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class CloudSyncWorker:
    """
    Autonomously backs up the JARVIS neural memory (ChromaDB + SQLite) 
    to the user's native macOS iCloud Drive for cross-device persistence.
    """
    
    def __init__(self, backup_interval_hours: int = 24):
        self.backup_interval_hours = backup_interval_hours
        self.is_running = False
        self._thread = None
        self.local_data_dir = os.path.join(os.getcwd(), "data")
        
        # Native macOS iCloud Drive Path
        self.icloud_base = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/JARVIS_Neural_Backup")

    def start(self):
        """Starts the background sync daemon."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
        logger.info(f"☁️ JARVIS iCloud Sync Daemon started (Interval: {self.backup_interval_hours}h)")

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _sync_loop(self):
        # Do an initial backup on boot if it's been a while, or just wait for the first cycle.
        # We will do a backup 5 minutes after boot to ensure systems are settled.
        time.sleep(300) 
        
        while self.is_running:
            try:
                self.perform_backup()
            except Exception as e:
                logger.error(f"iCloud sync failed: {e}")
                
            # Sleep for the interval
            sleep_seconds = self.backup_interval_hours * 3600
            for _ in range(int(sleep_seconds)):
                if not self.is_running:
                    break
                time.sleep(1)

    def perform_backup(self):
        """Zips the local data directory and copies it to iCloud Drive."""
        if not os.path.exists(self.local_data_dir):
            logger.warning("No local data directory found to backup.")
            return

        # Ensure iCloud JARVIS folder exists
        os.makedirs(self.icloud_base, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"JARVIS_memory_{timestamp}"
        temp_zip_path = os.path.join("/tmp", archive_name)
        
        logger.info(f"Compressing neural memory to {archive_name}.zip...")
        
        # Compress the data folder
        shutil.make_archive(temp_zip_path, 'zip', self.local_data_dir)
        
        zip_file = f"{temp_zip_path}.zip"
        dest_file = os.path.join(self.icloud_base, f"{archive_name}.zip")
        
        # Move to iCloud
        shutil.move(zip_file, dest_file)
        logger.info(f"✅ Neural Memory successfully synced to iCloud: {dest_file}")
        
        # Prune old backups (keep last 5)
        self._prune_old_backups()

    def _prune_old_backups(self):
        """Maintains only the specified number of recent backups in iCloud to save space."""
        try:
            backups = []
            for f in os.listdir(self.icloud_base):
                if f.startswith("JARVIS_memory_") and f.endswith(".zip"):
                    full_path = os.path.join(self.icloud_base, f)
                    backups.append((full_path, os.path.getmtime(full_path)))
            
            # Sort by modification time, newest first
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Keep the 5 most recent
            max_backups = 5
            if len(backups) > max_backups:
                for old_backup in backups[max_backups:]:
                    os.remove(old_backup[0])
                    logger.info(f"Pruned old iCloud backup: {os.path.basename(old_backup[0])}")
        except Exception as e:
            logger.error(f"Failed to prune old backups: {e}")

# Singleton instance
_cloud_sync_worker = None

def get_cloud_sync_worker() -> CloudSyncWorker:
    global _cloud_sync_worker
    if _cloud_sync_worker is None:
        _cloud_sync_worker = CloudSyncWorker()
    return _cloud_sync_worker
