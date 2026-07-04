import sqlite3
import datetime
import asyncio
from typing import List, Dict, Any, Callable, Optional

class Scheduler:
    """
    Manages persistent timers, alarms, and reminders using SQLite.
    Runs a background checker that fires notifications.
    """
    def __init__(self, db_path: str = "friday_memory.db"):
        self.db_path = db_path
        self._init_db()
        self.running = False
        self._check_task = None
        self.on_trigger_callback: Optional[Callable[[Dict[str, Any]], Any]] = None

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduler_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    target_time DATETIME NOT NULL,
                    completed INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_reminder(self, title: str, delay_seconds: int) -> int:
        """Adds a reminder to fire after delay_seconds."""
        now = datetime.datetime.now()
        target = now + datetime.timedelta(seconds=delay_seconds)
        target_str = target.strftime("%Y-%m-%d %H:%M:%S")
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO scheduler_events (title, target_time)
                VALUES (?, ?)
            """, (title, target_str))
            conn.commit()
            return cursor.lastrowid

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """Gets all reminders that are due and not completed."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, title, target_time FROM scheduler_events
                WHERE completed = 0 AND target_time <= ?
            """, (now_str,))
            rows = cursor.fetchall()
            return [{"id": r["id"], "title": r["title"], "target_time": r["target_time"]} for r in rows]

    def mark_completed(self, event_id: int):
        """Marks a reminder as completed."""
        with self._get_connection() as conn:
            conn.execute("UPDATE scheduler_events SET completed = 1 WHERE id = ?", (event_id,))
            conn.commit()

    def start(self, callback: Callable[[Dict[str, Any]], Any]):
        """Starts the background scheduler loop."""
        self.on_trigger_callback = callback
        self.running = True
        self._check_task = asyncio.create_task(self._scheduler_loop())

    def stop(self):
        """Stops the scheduler."""
        self.running = False
        if self._check_task:
            self._check_task.cancel()

    async def _scheduler_loop(self):
        while self.running:
            try:
                due_reminders = self.get_pending_reminders()
                for reminder in due_reminders:
                    # Mark completed first to avoid duplicate firing
                    self.mark_completed(reminder["id"])
                    
                    # Trigger callback
                    if self.on_trigger_callback:
                        # Make sure callback runs inside try-except
                        try:
                            if asyncio.iscoroutinefunction(self.on_trigger_callback):
                                await self.on_trigger_callback(reminder)
                            else:
                                self.on_trigger_callback(reminder)
                        except Exception as cb_err:
                            print(f"Error in scheduler callback: {str(cb_err)}")
                            
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(10)
