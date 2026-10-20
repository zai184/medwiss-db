"""File synchronization service for syncing filesystem with database.

This module provides functionality to:
- Scan source folders for files
- Compare filesystem state with database state (by source_path + SHA-256)
- Detect new files, modified files (hash changed), renamed files (same hash,
  new path), and deleted files
- Ingest new/modified files through the pipeline (extract → classify → save)
- Remove database entries for deleted files

The filesystem is the source of truth; this service only ever READS it.
The content root is the canonical Medizin tree (see config.get_content_root).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from config import (
    SourceConfig,
    _resolve_content_path,
    load_sources,
)
from database.models import KnowledgeEntry
from pipeline.batch_processor import BatchProcessor, calculate_file_hash
from pipeline.classification_resolver import resolve_classifications
from pipeline.embeddings import generate_embedding

from api.services.hierarchy_labels import (
    CATEGORY_LABELS,
    apply_hierarchy_labels,
    extract_hierarchical_labels,
    find_source_for_file,
)
from api.services.sync_state import sync_state

logger = logging.getLogger(__name__)

# Extensions considered for sync (mirrors SourceWatcher.SUPPORTED_EXTENSIONS)
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

# Files whose extraction needs OCR (PDF/images) or office parsers
# (pptx/docx); audio is link-only playable. Ingest indexes these
# metadata-only — extraction is on-demand (summarize / process-file).
EXTRACTION_DEPENDENT_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".mp3",
    ".wav",
    ".m4a",
    ".pptx",
    ".docx",
}

@dataclass
class FileChangeSet:
    """Container for detected file changes.

    Attributes:
        new_files: List of paths to new files (not in database)
        modified_files: List of tuples (entry, path) for files with changed hashes
        deleted_entries: List of KnowledgeEntry objects for deleted files
    """
    new_files: List[Path] = field(default_factory=list)
    modified_files: List[Tuple[KnowledgeEntry, Path]] = field(default_factory=list)
    deleted_entries: List[KnowledgeEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "new_files": [str(p) for p in self.new_files],
            "modified_files": [
                {"entry_id": e.id, "str_path": str(p)}
                for e, p in self.modified_files
            ],
            "deleted_entries": [
                {"entry_id": e.id, "source_path": e.source_path}
                for e in self.deleted_entries
            ],
        }


@dataclass
class SyncResult:
    """Result of a sync operation."""
    changes: FileChangeSet
    imported: int = 0
    updated: int = 0
    deleted: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if no errors occurred."""
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "changes": self.changes.to_dict(),
            "imported": self.imported,
            "updated": self.updated,
            "deleted": self.deleted,
            "errors": self.errors,
            "success": self.success,
        }


class FileSyncService:
    """Service for synchronizing filesystem with database.

    This service scans configured source folders, compares the filesystem
    state with the database (source_path + SHA-256), and handles new,
    modified, renamed, and deleted files. New/modified files are ingested
    directly through the pipeline — no import jobs.
    """

    def __init__(self, db: Session):
        """Initialize the file sync service.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db
        self._processor = BatchProcessor()

    # ------------------------------------------------------------------
    # Source discovery
    # ------------------------------------------------------------------

    def _get_all_source_paths(self) -> list[Tuple[SourceConfig, Path]]:
        """Get all configured source folders with their configurations.

        Returns:
            List of (SourceConfig, Path) tuples for all configured sources.
        """
        result: list[Tuple[SourceConfig, Path]] = []
        for source in load_sources():
            main_path = _resolve_content_path(source.path)
            if main_path.exists() and main_path.is_dir():
                result.append((source, main_path))
            else:
                logger.warning(f"Source folder does not exist: {main_path}")

            # Additional paths (for aggregated sources like Fortbildung)
            if source.additional_paths:
                for additional_path_str in source.additional_paths:
                    additional_path = _resolve_content_path(additional_path_str)
                    if additional_path.exists() and additional_path.is_dir():
                        result.append((source, additional_path))
                    else:
                        logger.warning(
                            f"Additional source folder does not exist: {additional_path}"
                        )
        return result

    def _find_source_for_path(self, file_path: Path) -> Optional[SourceConfig]:
        """Find the source configuration for a given file path."""
        match = find_source_for_file(file_path)
        return match[0] if match else None

    # ------------------------------------------------------------------
    # Change detection
    # ------------------------------------------------------------------

    def scan_source_folders(self) -> dict[Path, str]:
        """Scan all source folders and compute file hashes.

        Skips dot-directories (Syncthing/OS metadata, editor temp files) and
        unsupported extensions.

        Returns:
            Dictionary mapping file paths to their SHA-256 hashes.
        """
        logger.info("Scanning source folders...")
        file_hashes: dict[Path, str] = {}

        for _, source_path in self._get_all_source_paths():
            try:
                for path in source_path.rglob("*"):
                    if not path.is_file():
                        continue
                    if any(part.startswith(".") for part in path.parts):
                        continue
                    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                        continue
                    try:
                        file_hashes[path] = calculate_file_hash(path)
                    except Exception as e:
                        logger.error(f"Error calculating hash for {path}: {e}")
            except Exception as e:
                logger.error(f"Error scanning folder {source_path}: {e}")

        logger.info(f"Scanned {len(file_hashes)} files in source folders")
        return file_hashes

    def detect_changes(self) -> FileChangeSet:
        """Detect changes between filesystem and database.

        Returns:
            FileChangeSet containing lists of new, modified, and deleted items.
        """
        logger.info("Detecting changes between filesystem and database...")
        changes = FileChangeSet()

        # Get all files from source folders with their hashes
        fs_hashes = self.scan_source_folders()

        # Get all entries from the database that have source paths
        db_entries = (
            self.db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.source_path.isnot(None))
            .all()
        )

        db_entries_by_path: dict[str, KnowledgeEntry] = {}
        for entry in db_entries:
            if entry.source_path:
                db_entries_by_path[entry.source_path] = entry

        # Check for modified and deleted files
        for entry in db_entries:
            path = Path(entry.source_path)
            if not path.exists():
                logger.info(f"Detected deleted file: {entry.source_path}")
                changes.deleted_entries.append(entry)
                continue

            # File exists in both — check hash
            fs_hash = fs_hashes.pop(path, None)
            if fs_hash is None:
                continue
            if entry.file_hash != fs_hash:
                logger.info(f"Detected modified file: {entry.source_path}")
                changes.modified_files.append((entry, path))

        # Find new files (in filesystem but not in database)
        for path in fs_hashes:
            if str(path) not in db_entries_by_path:
                logger.info(f"Detected new file: {path}")
                changes.new_files.append(path)

        return changes

    # ------------------------------------------------------------------
    # Ingest (extract → classify → save) — the single-file pipeline
    # ------------------------------------------------------------------

    def ingest_file(
        self,
        file_path: Union[str, Path],
        entry: Optional[KnowledgeEntry] = None,
    ) -> Optional[KnowledgeEntry]:
        """Ingest a single file through the pipeline.

        New files are extracted, classified (regex/folder-derived; LLM
        optional), and saved with fresh tags. Existing entries are updated
        in place: content, hash, and folder-derived hierarchy labels only —
        manual tag edits are never overwritten.

        Args:
            file_path: Path to the file.
            entry: Existing entry to update, or None to create a new one.

        Returns:
            The saved KnowledgeEntry, or None on failure.
        """
        path = Path(file_path)
        source = self._find_source_for_path(path)
        if not source:
            logger.error(f"Could not find source configuration for {path}")
            return None

        suffix = path.suffix.lower()
        try:
            # Extraction-dependent files (image/PDF/audio/office) are indexed
            # metadata-only — title/hierarchy/hash, no content. OCR runs
            # ONLY on demand (summarize / /pipeline/process-file), never at
            # ingest; audio has no extraction at all.
            if suffix in EXTRACTION_DEPENDENT_SUFFIXES:
                file_hash = calculate_file_hash(path)
                entry = self._link_only_index(path, source, file_hash, entry)
                if entry is not None:
                    self.db.commit()
                    self.db.refresh(entry)
                    logger.info(
                        f"Link-only indexed (metadata only, on-demand extraction): {path}"
                    )
                    return entry
                logger.error(f"Link-only indexing failed for {path}")
                return None

            # Text files (.md/.txt/...): cheap direct read, no OCR.
            result = self._processor.process_file(path)
            if result.error:
                logger.error(f"Pipeline error for {path}: {result.error}")
                return None

            file_hash = calculate_file_hash(path)

            if entry is None:
                entry = self._create_entry_from_result(result, source, file_hash)
            else:
                self._update_entry_from_result(entry, result, source, file_hash)

            self._generate_embedding(entry)
            self.db.commit()
            self.db.refresh(entry)
            logger.info(f"Successfully ingested {path} → entry {entry.id}")
            return entry
        except Exception as e:
            logger.error(f"Error ingesting {path}: {e}", exc_info=True)
            self.db.rollback()
            return None

    def _link_only_index(
        self,
        path: Path,
        source: SourceConfig,
        file_hash: str,
        entry: Optional[KnowledgeEntry],
    ) -> Optional[KnowledgeEntry]:
        """Index a file without extraction (title/hierarchy from path only)."""
        try:
            if entry is None:
                source_match = find_source_for_file(path)
                unterkategorie = (
                    CATEGORY_LABELS.get(source.category, source.category)
                    if not source_match
                    else extract_hierarchical_labels(path, *source_match)[1]
                )
                entry = KnowledgeEntry(
                    titel=path.stem.replace("_", " ").replace("-", " ").title()[:500],
                    inhalt=(
                        f"# {path.stem}\n\nQuelle: {source.name}\n"
                        f"Pfad: {path}\n\n"
                        "[Inhalt nicht extrahiert — Volltext-Verarbeitung auf "
                        "diesem Host deaktiviert.]"
                    ),
                    quelle=f"{source.category}: {source.name}",
                    dokumenttyp=CATEGORY_LABELS.get(source.category, source.category),
                    schwierigkeit="fortgeschritten",
                    source_path=str(path),
                    file_hash=file_hash,
                    unterkategorie=unterkategorie,
                )
                self.db.add(entry)

            # Stamp first: the hash must survive even if folder-tag derivation
            # below hits a TaggingService edge case (duplicate label links,
            # FK races on auto-created lookup rows).
            self.db.commit()
            self.db.refresh(entry)

            try:
                with self.db.begin_nested():
                    source_match = find_source_for_file(path)
                    if source_match:
                        matched_source, source_root = source_match
                        apply_hierarchy_labels(
                            self.db, entry, path, matched_source, source_root
                        )
                    self.db.flush()
                self.db.commit()
            except Exception as e:
                logger.warning(f"Link-only: hierarchy labels skipped for {path}: {e}")
                self.db.rollback()
            return entry
        except Exception as e:
            logger.error(f"Link-only indexing failed for {path}: {e}", exc_info=True)
            self.db.rollback()
            return None

    def _resolve_classifications_for_result(
        self,
        processing_result,
        source: SourceConfig,
    ) -> dict:
        """Resolve the source's configured default Fachgebiet to a tag ID."""
        result = {
            "fachgebiet_id": None,
            "diagnose_ids": [],
            "symptom_ids": [],
        }

        fachgebiet = source.default_fachgebiete[0] if source.default_fachgebiete else ""
        if not fachgebiet:
            return result

        try:
            fach_result = resolve_classifications(
                self.db, fachgebiet=fachgebiet, diagnosen=[], symptome=[]
            )
            if fach_result.get("fachgebiet"):
                result["fachgebiet_id"] = fach_result["fachgebiet"].id
        except Exception as e:
            logger.error(f"Error resolving fachgebiet '{fachgebiet}': {e}")

        return result

    def _create_entry_from_result(
        self,
        processing_result,
        source: SourceConfig,
        file_hash: str,
    ) -> KnowledgeEntry:
        """Create a knowledge entry from a pipeline result."""
        titel = Path(processing_result.file_path).stem.replace("_", " ").replace("-", " ")
        titel = titel.title()

        inhalt = processing_result.extracted_text or ""
        if not inhalt.strip():
            inhalt = f"[Kein Text extrahiert aus {Path(processing_result.file_path).name}]"

        source_match = find_source_for_file(processing_result.file_path)
        if source_match:
            matched_source, source_root = source_match
            _, unterkategorie = extract_hierarchical_labels(
                processing_result.file_path, matched_source, source_root
            )
        else:
            unterkategorie = CATEGORY_LABELS.get(source.category, source.category)

        entry = KnowledgeEntry(
            titel=titel[:500],
            inhalt=inhalt,
            quelle=f"{source.category}: {source.name}",
            dokumenttyp=CATEGORY_LABELS.get(source.category, source.category),
            schwierigkeit="fortgeschritten",
            source_path=str(processing_result.file_path),
            file_hash=file_hash,
            unterkategorie=unterkategorie,
        )

        self.db.add(entry)
        self.db.flush()

        resolved = self._resolve_classifications_for_result(processing_result, source)

        fach_id = resolved.get("fachgebiet_id")
        if fach_id:
            from database.models import Fachgebiet

            fach = self.db.query(Fachgebiet).filter(Fachgebiet.id == fach_id).first()
            if fach:
                entry.fachgebiete.append(fach)

        diagnose_ids = resolved.get("diagnose_ids", [])
        if diagnose_ids:
            from database.models import Diagnose

            entry.diagnosen.extend(
                self.db.query(Diagnose).filter(Diagnose.id.in_(diagnose_ids)).all()
            )

        symptom_ids = resolved.get("symptom_ids", [])
        if symptom_ids:
            from database.models import Symptom

            entry.symptome.extend(
                self.db.query(Symptom).filter(Symptom.id.in_(symptom_ids)).all()
            )

        if source_match:
            apply_hierarchy_labels(
                self.db, entry, processing_result.file_path, matched_source, source_root
            )

        self.db.flush()
        return entry

    def _update_entry_from_result(
        self,
        entry: KnowledgeEntry,
        processing_result,
        source: SourceConfig,
        file_hash: str,
    ) -> None:
        """Update an existing entry after a file change.

        Content, hash, and folder-derived hierarchy labels are refreshed;
        manually edited tags (Fachgebiete, Diagnosen, Symptome, ...) are
        never touched.
        """
        entry.inhalt = processing_result.extracted_text or entry.inhalt
        entry.file_hash = file_hash

        source_match = find_source_for_file(processing_result.file_path)
        if source_match:
            matched_source, source_root = source_match
            apply_hierarchy_labels(
                self.db, entry, processing_result.file_path, matched_source, source_root
            )

        self.db.flush()

    def _generate_embedding(self, entry: KnowledgeEntry) -> None:
        """Generate and store the vector embedding for an entry (best effort)."""
        try:
            text_to_embed = f"{entry.titel}\n\n{entry.inhalt[:4000]}"
            entry.embedding = generate_embedding(text_to_embed)
            self.db.flush()
        except Exception as e:
            logger.error(f"Failed to generate embedding for entry {entry.id}: {e}")

    # ------------------------------------------------------------------
    # Single-file operations (watcher entry points)
    # ------------------------------------------------------------------

    def sync_new_file(self, file_path: Union[str, Path]) -> Optional[KnowledgeEntry]:
        """Ingest a new file, or adopt an existing entry after a rename.

        If an entry with the same file hash points at a path that no longer
        exists on disk, this is treated as a rename: the existing entry (with
        its ID and manual tags) is moved to the new path instead of creating
        a duplicate.
        """
        path = Path(file_path)
        try:
            # Rename adoption: same hash, stale source_path elsewhere.
            file_hash = calculate_file_hash(path)
            stale = (
                self.db.query(KnowledgeEntry)
                .filter(
                    KnowledgeEntry.file_hash == file_hash,
                    KnowledgeEntry.source_path.isnot(None),
                    KnowledgeEntry.source_path != str(path),
                )
                .all()
            )
            for candidate in stale:
                if not Path(candidate.source_path).exists():
                    logger.info(
                        f"Detected rename: {candidate.source_path} → {path} "
                        f"(entry {candidate.id})"
                    )
                    self._move_entry(candidate, path, file_hash)
                    return candidate

            entry = self.ingest_file(path)
            if entry:
                sync_state.record_change()
            return entry
        except Exception as e:
            logger.error(f"Error syncing new file {path}: {e}", exc_info=True)
            return None

    def sync_modified_file(
        self, entry: KnowledgeEntry, file_path: Union[str, Path]
    ) -> Optional[KnowledgeEntry]:
        """Re-process a modified file, updating the existing entry."""
        path = Path(file_path)
        try:
            updated = self.ingest_file(path, entry=entry)
            if updated:
                sync_state.record_change()
            return updated
        except Exception as e:
            logger.error(f"Error syncing modified file {path}: {e}", exc_info=True)
            return None

    def _move_entry(
        self, entry: KnowledgeEntry, new_path: Path, file_hash: str
    ) -> None:
        """Point an existing entry at a renamed file; refresh folder-derived tags."""
        entry.source_path = str(new_path)
        entry.file_hash = file_hash
        source_match = find_source_for_file(new_path)
        if source_match:
            matched_source, source_root = source_match
            apply_hierarchy_labels(self.db, entry, new_path, matched_source, source_root)
        self.db.commit()
        self.db.refresh(entry)
        sync_state.record_change()

    def delete_entry(self, entry: KnowledgeEntry) -> bool:
        """Delete a database entry whose source file no longer exists.

        Only the database row is removed — files are never touched.
        """
        try:
            entry_id = entry.id
            self.db.delete(entry)
            self.db.commit()
            logger.info(f"Successfully deleted entry {entry_id}")
            sync_state.record_change()
            return True
        except Exception as e:
            logger.error(f"Error deleting entry {entry.id}: {e}", exc_info=True)
            self.db.rollback()
            return False

    # ------------------------------------------------------------------
    # Full reconcile
    # ------------------------------------------------------------------

    def run_sync(self, dry_run: bool = False) -> SyncResult:
        """Run a full synchronization between filesystem and database.

        Detects all changes and processes them:
        - New files are ingested
        - Modified files are re-processed (content/hash/hierarchy only)
        - Renames (delete+create with matching hash) move the existing entry
        - Deleted files result in deleted database entries

        Args:
            dry_run: If True, only detect changes without applying them.

        Returns:
            SyncResult with details of what was done.
        """
        logger.info(f"Starting full sync (dry_run={dry_run})...")
        sync_state.set_running(True)
        try:
            changes = self.detect_changes()
            result = SyncResult(changes=changes)

            if dry_run:
                logger.info("Dry run mode: no changes applied")
                return result

            # Pair renames first: deleted entry ↔ new file with matching hash.
            new_hashes = {path: calculate_file_hash(path) for path in changes.new_files}
            for entry in list(changes.deleted_entries):
                matched_path = None
                for path, file_hash in new_hashes.items():
                    if file_hash == entry.file_hash:
                        matched_path = path
                        break
                if matched_path is not None:
                    logger.info(
                        f"Detected rename: {entry.source_path} → {matched_path} "
                        f"(entry {entry.id})"
                    )
                    self._move_entry(entry, matched_path, entry.file_hash)
                    changes.deleted_entries.remove(entry)
                    changes.new_files.remove(matched_path)
                    result.updated += 1
                    del new_hashes[matched_path]

            for file_path in changes.new_files:
                try:
                    entry = self.sync_new_file(file_path)
                    if entry is not None:
                        result.imported += 1
                    else:
                        result.errors.append(f"Failed to import file: {file_path}")
                except Exception as e:
                    error_msg = f"Error importing {file_path}: {e}"
                    logger.error(error_msg, exc_info=True)
                    result.errors.append(error_msg)

            for entry, file_path in changes.modified_files:
                try:
                    updated_entry = self.sync_modified_file(entry, file_path)
                    if updated_entry is not None:
                        result.updated += 1
                    else:
                        result.errors.append(f"Failed to update file: {file_path}")
                except Exception as e:
                    error_msg = f"Error updating {file_path}: {e}"
                    logger.error(error_msg, exc_info=True)
                    result.errors.append(error_msg)

            for entry in changes.deleted_entries:
                try:
                    if self.delete_entry(entry):
                        result.deleted += 1
                    else:
                        result.errors.append(f"Failed to delete entry {entry.id}")
                except Exception as e:
                    error_msg = f"Error deleting entry {entry.id}: {e}"
                    logger.error(error_msg, exc_info=True)
                    result.errors.append(error_msg)

            sync_state.record_sync(
                imported=result.imported,
                updated=result.updated,
                deleted=result.deleted,
                errors=result.errors,
            )
            logger.info(
                f"Sync completed — Imported: {result.imported}, "
                f"Updated: {result.updated}, Deleted: {result.deleted}, "
                f"Errors: {len(result.errors)}"
            )
            return result
        finally:
            sync_state.set_running(False)

