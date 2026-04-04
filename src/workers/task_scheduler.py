"""
JARVIS Proactive Task Scheduler
Supports: one-shot delays, recurring intervals, and named cancellable tasks.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Coroutine, Dict, Optional
import uuid

logger = logging.getLogger(__name__)


class ScheduledTask:
    def __init__(self, task_id: str, name: str, coro_fn: Callable, interval_sec: Optional[float], run_at: Optional[datetime]):
        self.task_id = task_id
        self.name = name
        self.coro_fn = coro_fn
        self.interval_sec = interval_sec  # None = one-shot
        self.run_at = run_at
        self.asyncio_task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.run_count: int = 0
        self.status: str = "pending"


class JarvisScheduler:
    """A lightweight async task scheduler for JARVIS. Runs inside the existing FastAPI event loop."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False

    def start(self):
        self._running = True
        logger.info("⏰ JarvisScheduler started")

    def stop(self):
        self._running = False
        for t in self._tasks.values():
            if t.asyncio_task and not t.asyncio_task.done():
                t.asyncio_task.cancel()
        logger.info("⏰ JarvisScheduler stopped")

    def schedule_once(self, name: str, coro_fn: Callable[[], Coroutine], delay_sec: float) -> str:
        """Run a coroutine once after `delay_sec` seconds."""
        task_id = str(uuid.uuid4())[:8]
        run_at = datetime.utcnow() + timedelta(seconds=delay_sec)
        st = ScheduledTask(task_id, name, coro_fn, interval_sec=None, run_at=run_at)
        self._tasks[task_id] = st
        st.asyncio_task = asyncio.create_task(self._run_once(st, delay_sec))
        logger.info(f"⏰ Scheduled one-shot task '{name}' in {delay_sec}s (id={task_id})")
        return task_id

    def schedule_recurring(self, name: str, coro_fn: Callable[[], Coroutine], interval_sec: float) -> str:
        """Run a coroutine repeatedly every `interval_sec` seconds."""
        task_id = str(uuid.uuid4())[:8]
        st = ScheduledTask(task_id, name, coro_fn, interval_sec=interval_sec, run_at=None)
        self._tasks[task_id] = st
        st.asyncio_task = asyncio.create_task(self._run_recurring(st, interval_sec))
        logger.info(f"⏰ Scheduled recurring task '{name}' every {interval_sec}s (id={task_id})")
        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancel a scheduled task by ID."""
        st = self._tasks.get(task_id)
        if st and st.asyncio_task and not st.asyncio_task.done():
            st.asyncio_task.cancel()
            st.status = "cancelled"
            logger.info(f"⏰ Cancelled task '{st.name}' (id={task_id})")
            return True
        return False

    def list_tasks(self) -> list:
        return [
            {
                "task_id": st.task_id,
                "name": st.name,
                "status": st.status,
                "run_count": st.run_count,
                "last_run": st.last_run.isoformat() if st.last_run else None,
                "interval_sec": st.interval_sec,
            }
            for st in self._tasks.values()
        ]

    async def _run_once(self, st: ScheduledTask, delay_sec: float):
        try:
            st.status = "waiting"
            await asyncio.sleep(delay_sec)
            st.status = "running"
            await st.coro_fn()
            st.run_count += 1
            st.last_run = datetime.utcnow()
            st.status = "done"
        except asyncio.CancelledError:
            st.status = "cancelled"
        except Exception as e:
            st.status = f"error: {e}"
            logger.error(f"Task '{st.name}' failed: {e}")

    async def _run_recurring(self, st: ScheduledTask, interval_sec: float):
        try:
            st.status = "running"
            while self._running:
                await asyncio.sleep(interval_sec)
                await st.coro_fn()
                st.run_count += 1
                st.last_run = datetime.utcnow()
        except asyncio.CancelledError:
            st.status = "cancelled"
        except Exception as e:
            st.status = f"error: {e}"
            logger.error(f"Recurring task '{st.name}' failed: {e}")


# Global singleton
_scheduler: Optional[JarvisScheduler] = None

def get_jarvis_scheduler() -> JarvisScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = JarvisScheduler()
    return _scheduler
