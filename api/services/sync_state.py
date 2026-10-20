"""In-memory sync state shared between the watcher and the sync endpoints.

Cheap change signal for the UI poll: the watcher records every processed
event here so `GET /admin/sync-status` never has to re-hash the tree.
"""

import threading
from datetime import datetime
from typing import Optional


class SyncState:
    """Process-wide singleton tracking the last watcher/reconcile activity."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_change_at: Optional[datetime] = None
        self._last_sync_at: Optional[datetime] = None
        self._running = False
        self.imported = 0
        self.updated = 0
        self.deleted = 0
        self.errors: list[str] = []

    def record_change(self) -> None:
        """Record a single file-level change processed by the watcher."""
        with self._lock:
            self._last_change_at = datetime.utcnow()

    def record_sync(
        self,
        imported: int = 0,
        updated: int = 0,
        deleted: int = 0,
        errors: Optional[list[str]] = None,
    ) -> None:
        """Record the outcome of a reconcile pass (startup, manual, or timer)."""
        with self._lock:
            self._last_sync_at = datetime.utcnow()
            self._last_change_at = self._last_sync_at
            self.imported = imported
            self.updated = updated
            self.deleted = deleted
            self.errors = list(errors or [])

    def set_running(self, running: bool) -> None:
        with self._lock:
            self._running = running

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "last_change_at": self._last_change_at,
                "last_sync_at": self._last_sync_at,
                "running": self._running,
                "imported": self.imported,
                "updated": self.updated,
                "deleted": self.deleted,
                "errors": list(self.errors),
            }


sync_state = SyncState()
