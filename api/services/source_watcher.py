"""Source folder watcher for automatic file synchronization.

This module provides automatic monitoring of the canonical content root
(``config.get_content_root()``) and triggers file synchronization when files
are created, modified, moved, or deleted.

The handler owns one database session per event (watchdog dispatches events
from a thread pool, so sharing a Session across events is unsafe).

rsync lands changed files as a hidden temp file plus ``rename()`` into place,
which watchdog reports as ``FileMovedEvent`` — hence ``on_moved`` is treated
exactly like create/modify on the destination.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Set

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
)

from api.database import SessionLocal
from api.services.file_sync import FileSyncService
from config import _resolve_content_path, load_sources
from database.models import KnowledgeEntry

logger = logging.getLogger(__name__)

# Supported file extensions for monitoring
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".md",
    ".txt",
    ".docx",
    ".pptx",
    ".mp3",
    ".wav",
    ".m4a",
}

# Seconds to wait for the writer (or the rsync temp→rename dance) to settle.
SETTLE_SECONDS = 0.5
# Grace period before a delete is applied, so a rename (delete+create pair)
# can be adopted as a move instead of losing the entry and its manual tags.
DELETE_GRACE_SECONDS = 2.0


def _is_supported_file(file_path: Path) -> bool:
    """Check if file has a supported extension and is not a hidden/temp file."""
    if any(part.startswith(".") for part in file_path.parts):
        return False
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


class SourceFolderEventHandler(FileSystemEventHandler):
    """Watchdog event handler for source folder file events.

    Automatically syncs files to the database when they are created,
    modified, moved, or deleted in source folders. Each event runs with its
    own database session.
    """

    def __init__(self):
        super().__init__()
        self._processed_files: Set[str] = set()

    def _should_process(self, file_path: Path) -> bool:
        """Skip files processed within the last few seconds (event storms)."""
        file_id = str(file_path.resolve())
        if file_id in self._processed_files:
            logger.debug(f"Recently processed, skipping: {file_path}")
            return False
        return True

    def _mark_processed(self, file_path: Path) -> None:
        file_id = str(file_path.resolve())
        self._processed_files.add(file_id)
        if len(self._processed_files) > 1000:
            self._processed_files = set(list(self._processed_files)[-500:])

    # -- event plumbing ---------------------------------------------------

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if not _is_supported_file(file_path):
            return
        if not self._should_process(file_path):
            return
        logger.info(f"File created in source folder: {file_path}")
        self._upsert(file_path)

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if not _is_supported_file(file_path):
            return
        logger.info(f"File modified in source folder: {file_path}")
        self._upsert(file_path)

    def on_moved(self, event: FileMovedEvent) -> None:
        """Handle moves.

        rsync lands updated files as a hidden temp file plus rename() into
        place — the source is an ignored temp file and the destination holds
        the new content, so upserting the destination covers both that and a
        genuine rename onto an existing tracked path.
        """
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if not _is_supported_file(dest):
            return
        logger.info(f"File moved into place: {event.src_path} → {dest}")
        self._upsert(dest)

    def on_deleted(self, event: FileDeletedEvent) -> None:
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        logger.info(f"File deleted from source folder: {file_path}")
        time.sleep(DELETE_GRACE_SECONDS)
        self._delete_entry(file_path)

    # -- database work (one session per event) -----------------------------

    def _upsert(self, file_path: Path) -> None:
        """Create or update the entry for a new/modified file."""
        time.sleep(SETTLE_SECONDS)
        if not file_path.exists():
            logger.debug(f"File vanished before processing: {file_path}")
            return
        db = SessionLocal()
        try:
            sync_service = FileSyncService(db)
            entry = (
                db.query(KnowledgeEntry)
                .filter(KnowledgeEntry.source_path == str(file_path))
                .first()
            )
            if entry:
                updated = sync_service.sync_modified_file(entry, file_path)
                if updated:
                    logger.info(f"Updated entry {updated.id} for {file_path}")
                else:
                    logger.error(f"Failed to update entry for {file_path}")
            else:
                created = sync_service.sync_new_file(file_path)
                if created:
                    logger.info(f"Created entry {created.id} for {file_path}")
                    self._mark_processed(file_path)
                else:
                    logger.error(f"Failed to sync new file: {file_path}")
        except Exception as e:
            logger.error(f"Error syncing {file_path}: {e}", exc_info=True)
        finally:
            db.close()

    def _delete_entry(self, file_path: Path) -> None:
        """Delete the entry whose source file was removed."""
        db = SessionLocal()
        try:
            entry = (
                db.query(KnowledgeEntry)
                .filter(KnowledgeEntry.source_path == str(file_path))
                .first()
            )
            if not entry:
                logger.debug(f"No entry found for deleted file: {file_path}")
                return
            # The file may be back (rsync re-created it during the grace wait).
            if file_path.exists():
                logger.info(f"File reappeared during grace period: {file_path}")
                return
            if FileSyncService(db).delete_entry(entry):
                logger.info(f"Deleted entry {entry.id} for removed file: {file_path}")
            else:
                logger.error(f"Failed to delete entry for removed file: {file_path}")
        except Exception as e:
            logger.error(f"Error handling deleted file {file_path}: {e}", exc_info=True)
        finally:
            db.close()


class SourceWatcher:
    """Watchdog-based file watcher for source folders.

    Monitors all configured source folders and automatically syncs
    file changes to the database. Observers run in separate threads.
    """

    def __init__(self, db: Optional[object] = None, max_workers: int = 4):
        """Initialize the source watcher.

        Args:
            db: Unused legacy parameter (kept for backwards compatibility);
                each event uses its own session.
            max_workers: Maximum number of thread pool workers.
        """
        self.max_workers = max_workers
        self.watch_paths: list[Path] = []
        self.observers: list[Observer] = []
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running = False

        self._load_watch_paths()

    def _load_watch_paths(self) -> None:
        """Load all source folder paths from configuration."""
        for source in load_sources():
            main_path = _resolve_content_path(source.path)
            if main_path.exists() and main_path.is_dir():
                self.watch_paths.append(main_path)
                logger.debug(f"Added watch path: {main_path}")
            else:
                logger.warning(f"Source folder does not exist: {main_path}")

            if source.additional_paths:
                for additional_path_str in source.additional_paths:
                    additional_path = _resolve_content_path(additional_path_str)
                    if additional_path.exists() and additional_path.is_dir():
                        self.watch_paths.append(additional_path)
                        logger.debug(f"Added watch path: {additional_path}")
                    else:
                        logger.warning(
                            f"Additional source folder does not exist: {additional_path}"
                        )

        logger.info(f"Loaded {len(self.watch_paths)} watch paths from configuration")

    def start(self) -> None:
        """Start watching all source folders."""
        if self._running:
            logger.warning("SourceWatcher is already running")
            return

        logger.info("Starting source folder watcher...")

        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        for path in self.watch_paths:
            try:
                observer = Observer()
                handler = SourceFolderEventHandler()
                observer.schedule(handler, str(path), recursive=True)
                observer.start()
                self.observers.append(observer)
                logger.info(f"Started watching: {path}")
            except Exception as e:
                logger.error(f"Failed to start observer for {path}: {e}")

        self._running = True
        logger.info(f"SourceWatcher started with {len(self.observers)} observers")

    def stop(self) -> None:
        """Stop all observers and clean up resources."""
        if not self._running:
            return

        logger.info("Stopping source folder watcher...")

        for observer in self.observers:
            try:
                observer.stop()
            except Exception as e:
                logger.error(f"Error stopping observer: {e}")

        for observer in self.observers:
            try:
                observer.join(timeout=5.0)
            except Exception as e:
                logger.error(f"Error joining observer: {e}")

        self.observers = []

        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        self._running = False
        logger.info("SourceWatcher stopped")

    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._running

    def get_watch_paths(self) -> list[Path]:
        """Get the list of paths being watched."""
        return self.watch_paths.copy()
