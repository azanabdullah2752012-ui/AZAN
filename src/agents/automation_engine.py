import asyncio
import sqlite3
import logging
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.tools.macos_control import MacOSControlTool
from src.tools.macos_context import MacOSContextTool

logger = logging.getLogger(__name__)

class AutomationEngine:
    """
    Proactive automation engine for JARVIS.
    Evaluates rules periodically and triggers macos_control actions.
    """

    def __init__(self, db_path: str = "/Applications/AZAN/data/automation_rules.db"):
        self.db_path = db_path
        self.macos_control = MacOSControlTool()
        self.macos_context = MacOSContextTool()
        self._init_db()
        self.is_running = False

    def _init_db(self):
        """Initializes the SQLite database for rules."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                condition_type TEXT NOT NULL, -- "time", "active_app", "system_state"
                condition_value TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_args TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_triggered INTEGER DEFAULT 0
            )
        ''')
        # Add some initial demo rules if database is empty
        cursor.execute("SELECT count(*) FROM rules")
        if cursor.fetchone()[0] == 0:
            demo_rules = [
                ("Morning Ritual", "time", "07:00", "open_app", json.dumps({"app_name": "Safari"})),
                ("Focus Suggestion", "active_app", "Safari", "notify", json.dumps({"text": "Suggesting Focus Mode for Safari."})),
                ("Low Brightness", "time", "22:00", "set_brightness", json.dumps({"level": 20}))
            ]
            cursor.executemany(
                "INSERT INTO rules (name, condition_type, condition_value, action_type, action_args) VALUES (?, ?, ?, ?, ?)",
                demo_rules
            )
        conn.commit()
        conn.close()

    async def start(self):
        """Starts the automation loop."""
        if self.is_running:
            return
        self.is_running = True
        logger.info("[Automation] Engine started.")
        while self.is_running:
            try:
                await self.evaluate_rules()
            except Exception as e:
                logger.error(f"[Automation] Evaluation error: {e}")
            await asyncio.sleep(10) # Evaluate every 10 seconds

    def stop(self):
        """Stops the automation loop."""
        self.is_running = False
        logger.info("[Automation] Engine stopped.")

    async def evaluate_rules(self):
        """Fetches enabled rules and triggers actions if conditions are met."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, condition_type, condition_value, action_type, action_args, last_triggered FROM rules WHERE enabled = 1")
        rules = cursor.fetchall()

        now = int(time.time())
        current_time = datetime.now().strftime("%H:%M")
        context = self.macos_context.get_screen_summary() # Combined context

        for r_id, name, c_type, c_val, a_type, a_args, last_t in rules:
            triggered = False
            
            # 1. Evaluate Condition
            if c_type == "time" and current_time == c_val:
                # Prevent multiple triggers within the same minute
                if now - last_t > 60:
                    triggered = True
            elif c_type == "active_app" and c_val.lower() in context["active_app"].lower():
                # Allow re-trigger if context changed but stay throttled (e.g. once every 10 mins)
                if now - last_t > 600:
                    triggered = True
            
            # 2. Trigger Action
            if triggered:
                logger.info(f"[Automation] Triggering rule: {name}")
                args = json.loads(a_args)
                try:
                    if a_type == "notify":
                        # We could send a notification to the HUD via an event system
                        logger.info(f"[Automation] Notification: {args.get('text')}")
                    else:
                        self.macos_control.execute(a_type, args)
                except Exception as e:
                    logger.error(f"[Automation] Action error for rule {name}: {e}")
                
                cursor.execute("UPDATE rules SET last_triggered = ? WHERE id = ?", (now, r_id))
        
        conn.commit()
        conn.close()

    def add_rule(self, name: str, c_type: str, c_val: str, a_type: str, a_args: Dict[str, Any]):
        """Adds a new automation rule."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rules (name, condition_type, condition_value, action_type, action_args) VALUES (?, ?, ?, ?, ?)",
            (name, c_type, c_val, a_type, json.dumps(a_args))
        )
        conn.commit()
        conn.close()
        logger.info(f"[Automation] Added new rule: {name}")

import os
