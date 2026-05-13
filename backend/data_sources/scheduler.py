"""Import scheduler — background thread that triggers imports on schedule.

Uses stdlib threading only. Checks every 60 seconds if any configured
data source needs to run based on its cron expression.

Cron expression support (simplified):
  - Empty string = manual only
  - "@daily" or "0 N * * *" = daily at hour N
  - "@weekly" = weekly on Sunday at 2:00
  - "H M * * *" = at specific time every day
  - "H M * * DOW" = specific day of week (0=Sun)
"""
from __future__ import annotations
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

from .models import DataSourceConfig, ImportLog, now_iso


class CronParser:
    """Lightweight cron expression parser (5-field: M H DOM MON DOW)."""

    def __init__(self, expr: str):
        self.expr = expr.strip()
        self._next_run: Optional[datetime] = None

    def should_run(self, now: datetime, last_run: str) -> bool:
        """Check if the job should run now."""
        if not self.expr:
            return False

        # Parse aliases
        expr = self.expr
        if expr == '@daily':
            expr = '0 2 * * *'
        elif expr == '@weekly':
            expr = '0 2 * * 0'

        parts = expr.split()
        if len(parts) != 5:
            return False

        minute_s, hour_s, dom_s, month_s, dow_s = parts

        # Check if current time matches
        if not self._match_field(minute_s, now.minute, 0, 59):
            return False
        if not self._match_field(hour_s, now.hour, 0, 23):
            return False
        if not self._match_field(dom_s, now.day, 1, 31):
            return False
        if not self._match_field(month_s, now.month, 1, 12):
            return False
        if not self._match_field(dow_s, now.isoweekday() % 7, 0, 6):
            return False

        # Don't re-run within the same hour
        if last_run:
            try:
                lr = datetime.fromisoformat(last_run)
                if (now - lr).total_seconds() < 3600:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    @staticmethod
    def _match_field(pattern: str, value: int, lo: int, hi: int) -> bool:
        if pattern == '*':
            return True
        # Handle */N
        if pattern.startswith('*/'):
            try:
                step = int(pattern[2:])
                return value % step == 0
            except ValueError:
                return False
        # Handle comma-separated values
        for part in pattern.split(','):
            try:
                if int(part) == value:
                    return True
            except ValueError:
                continue
        return False


class ImportScheduler:
    """Background scheduler for auto-import jobs."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._import_fn: Optional[Callable] = None
        self._lock = threading.Lock()
        self._active_jobs: dict[str, str] = {}  # source_id -> status

    def set_import_fn(self, fn: Callable):
        """Set the import function to call: fn(source_id) -> ImportLog."""
        self._import_fn = fn

    def start(self):
        """Start the background scheduler thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name='ImportScheduler')
        self._thread.start()

    def stop(self):
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        """Return scheduler status."""
        return {
            'running': self._running,
            'activeJobs': dict(self._active_jobs),
            'threadAlive': self._thread.is_alive() if self._thread else False,
        }

    def _loop(self):
        """Main scheduler loop — check every 60 seconds."""
        while self._running:
            try:
                self._check_and_run()
            except Exception:
                pass  # don't crash the scheduler
            time.sleep(60)

    def _check_and_run(self):
        """Check all configs and trigger scheduled imports."""
        from .models import load_configs

        configs = load_configs()
        now = datetime.now()

        for config in configs:
            if not config.enabled or not config.schedule:
                continue

            parser = CronParser(config.schedule)
            if parser.should_run(now, config.last_sync):
                self.run_import(config.id)

    def run_import(self, source_id: str) -> Optional[ImportLog]:
        """Run an import for a specific data source (thread-safe)."""
        if not self._import_fn:
            return None

        with self._lock:
            if source_id in self._active_jobs:
                return None  # already running
            self._active_jobs[source_id] = 'running'

        try:
            log = self._import_fn(source_id)
            return log
        finally:
            with self._lock:
                self._active_jobs.pop(source_id, None)

    def run_import_async(self, source_id: str):
        """Trigger import in a background thread."""
        t = threading.Thread(
            target=self.run_import,
            args=(source_id,),
            daemon=True,
            name=f'Import-{source_id}'
        )
        t.start()

    def is_job_running(self, source_id: str) -> bool:
        with self._lock:
            return source_id in self._active_jobs


# Singleton instance
scheduler = ImportScheduler()
