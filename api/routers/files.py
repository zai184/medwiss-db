"""File serving endpoints for knowledge entry source files."""

import mimetypes
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.services.file_sync import FileSyncService
from api.services.hierarchy_labels import CATEGORY_LABELS
from config import (
    load_sources,
    _get_workspace_root,
    _resolve_content_path,
    get_content_root,
)
from database.models import Chunk, KnowledgeEntry

router = APIRouter(prefix="/files", tags=["files"])

def _content_disposition(file_path: Path, disposition: str) -> str:
    """RFC 5987/6266 Content-Disposition value.

    Raw filenames (e.g. "… 2021 – die BIG-FIVE.pdf") contain non-latin-1
    characters that crash Starlette's header encoding. Provide an
    ASCII-sanitized fallback plus a percent-encoded UTF-8 filename*.
    """
    name = file_path.name
    ascii_name = name.encode("ascii", "ignore").decode().replace('"', "").replace("\\", "") or "file"
    encoded = urllib.parse.quote(name, safe="")
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"



# Security: serve files only from the canonical content root (plus the legacy
# workspace parent for old entries whose source_path predates the switch).
_WORKSPACE_PARENT = str(_get_workspace_root().resolve().parent)
_CONTENT_ROOT = str(get_content_root())
ALLOWED_ROOTS = [_CONTENT_ROOT, _WORKSPACE_PARENT]

def _is_path_allowed(path: Path | str) -> bool:
    """Check if a path is within allowed directories (real containment,
    not a string prefix — rejects sibling dirs sharing the prefix)."""
    resolved = Path(path).resolve()
    return any(resolved.is_relative_to(Path(root).resolve()) for root in ALLOWED_ROOTS)


# AWMF corpus root — all chunk source_paths live under this (verified 2026-08-25).
# Derived from the canonical content root.
AWMF_ROOT = str(get_content_root() / "3_Leitlinien")


def _is_awmf_path_allowed(path: Path | str) -> bool:
    """Check a path is inside the AWMF PDF corpus root."""
    return Path(path).resolve().is_relative_to(Path(AWMF_ROOT).resolve())


def _get_chunk_file_path(chunk: Chunk) -> Optional[Path]:
    """File path from a chunk's source_path."""
    if not chunk.source_path:
        return None
    return Path(chunk.source_path)


def _get_entry_file_path(entry: KnowledgeEntry) -> Optional[Path]:
    """Get the file path from a knowledge entry.

    Args:
        entry: KnowledgeEntry ORM object

    Returns:
        Path object if source_path exists, None otherwise
    """
    if not entry.source_path:
        return None
    return Path(entry.source_path)


class FileInfoResponse(BaseModel):
    """Response model for file info endpoint."""

    exists: bool
    mime_type: Optional[str] = None
    size: Optional[int] = None
    can_inline: bool


@router.get("/entries/{entry_id}/view")
async def view_file(
    entry_id: int,
    db: Session = Depends(get_db),
):
    """Serve a file inline with proper MIME type detection.

    Returns the file with Content-Disposition: inline for browser viewing.
    """
    # Get the entry
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge entry with ID {entry_id} not found",
        )

    # Get file path
    file_path = _get_entry_file_path(entry)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No source file associated with this entry",
        )

    # Security check
    if not _is_path_allowed(file_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this path is not allowed",
        )

    # Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Detect MIME type dynamically
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
        headers={"Content-Disposition": _content_disposition(file_path, "inline")},
    )


@router.get("/chunks/{chunk_id}/view")
async def view_chunk_file(
    chunk_id: int,
    db: Session = Depends(get_db),
):
    """Serve an AWMF chunk's source PDF inline (scoped to the AWMF corpus root)."""
    chunk = db.query(Chunk).filter(Chunk.id == chunk_id).first()
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")

    file_path = _get_chunk_file_path(chunk)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No source file associated")
    if not _is_awmf_path_allowed(file_path):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access to this path is not allowed")
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
        headers={"Content-Disposition": _content_disposition(file_path, "inline")},
    )


@router.get("/entries/{entry_id}/download")
async def download_file(
    entry_id: int,
    db: Session = Depends(get_db),
):
    """Force download a file with proper filename.

    Returns the file with Content-Disposition: attachment for downloading.
    """
    # Get the entry
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge entry with ID {entry_id} not found",
        )

    # Get file path
    file_path = _get_entry_file_path(entry)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No source file associated with this entry",
        )

    # Security check
    if not _is_path_allowed(file_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this path is not allowed",
        )

    # Check file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Detect MIME type dynamically
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
        headers={"Content-Disposition": _content_disposition(file_path, "attachment")},
    )


@router.get("/entries/{entry_id}/info", response_model=FileInfoResponse)
async def get_file_info(
    entry_id: int,
    db: Session = Depends(get_db),
):
    """Return metadata about the entry's source file.

    Returns: exists, mime_type, size, can_inline
    """
    # Get the entry
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge entry with ID {entry_id} not found",
        )

    # Get file path
    file_path = _get_entry_file_path(entry)
    if not file_path:
        return FileInfoResponse(
            exists=False,
            mime_type=None,
            size=None,
            can_inline=False,
        )

    # Security check
    if not _is_path_allowed(file_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this path is not allowed",
        )

    # Check file exists
    if not file_path.exists():
        return FileInfoResponse(
            exists=False,
            mime_type=None,
            size=None,
            can_inline=False,
        )

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    # Determine if can inline (browser-displayable types)
    can_inline = bool(mime_type) and (
        mime_type.startswith("image/")
        or mime_type.startswith("audio/")
        or mime_type.startswith("video/")
        or mime_type == "application/pdf"
        or mime_type.startswith("text/")
    )

    # Get file size
    size = file_path.stat().st_size if file_path.exists() else None

    return FileInfoResponse(
        exists=True,
        mime_type=mime_type,
        size=size,
        can_inline=can_inline,
    )


class SyncStatusResponse(BaseModel):
    """Response model for sync status (cheap — no filesystem hashing)."""

    total_files: int
    files_waiting: int
    last_change: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    running: bool = False
    imported: int = 0
    updated: int = 0
    deleted: int = 0
    sync_errors: list[str]
    source_folders: list[dict]


class SyncTriggerResponse(BaseModel):
    """Response model for manual sync trigger."""

    success: bool
    message: str
    changes_detected: dict


@router.get("/admin/sync-status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: Session = Depends(get_db),
):
    """Get file synchronization status — cheap enough for 10 s UI polling.

    Served from the in-memory sync state (updated by the watcher and by
    reconcile passes); never re-hashes the source tree.
    """
    from api.services.sync_state import sync_state

    total_files = (
        db.query(KnowledgeEntry.id)
        .filter(KnowledgeEntry.source_path.isnot(None))
        .count()
    )

    state = sync_state.snapshot()
    source_folders = []
    for source in load_sources():
        main_path = _resolve_content_path(source.path)
        source_folders.append(
            {
                "name": source.name,
                "path": str(main_path),
                "category": source.category,
                "exists": main_path.exists(),
            }
        )

    return SyncStatusResponse(
        total_files=total_files,
        files_waiting=0,
        last_change=state["last_change_at"],
        last_sync=state["last_sync_at"],
        running=bool(state["running"]),
        imported=int(state["imported"]),
        updated=int(state["updated"]),
        deleted=int(state["deleted"]),
        sync_errors=list(state["errors"]),
        source_folders=source_folders,
    )


@router.post("/admin/sync", response_model=SyncTriggerResponse)
async def trigger_manual_sync(
    db: Session = Depends(get_db),
):
    """Trigger manual file synchronization (admin only).

    Runs a full sync operation:
    - Imports new files
    - Updates modified files
    - Archives entries for deleted files
    """
    sync_service = FileSyncService(db)

    try:
        result = sync_service.run_sync(dry_run=False)

        changes_detected = {
            "new_files": len(result.changes.new_files),
            "modified_files": len(result.changes.modified_files),
            "deleted_entries": len(result.changes.deleted_entries),
            "imported": result.imported,
            "updated": result.updated,
            "deleted": result.deleted,
        }

        if result.errors:
            return SyncTriggerResponse(
                success=False,
                message=f"Sync completed with {len(result.errors)} errors",
                changes_detected=changes_detected,
            )

        total_processed = result.imported + result.updated + result.deleted
        return SyncTriggerResponse(
            success=True,
            message=f"Sync erfolgreich: {total_processed} Dateien verarbeitet",
            changes_detected=changes_detected,
        )

    except Exception as e:
        return SyncTriggerResponse(
            success=False,
            message=f"Sync fehlgeschlagen: {str(e)}",
            changes_detected={},
        )


@router.post("/sync", response_model=SyncTriggerResponse)
async def trigger_lightweight_sync(
    db: Session = Depends(get_db),
):
    """Lightweight file sync — link new files without running AI pipeline.

    Scans source folders and creates database entries for files not yet
    tracked. Uses link-only import (no OCR/classification), which is fast
    and doesn't require Llamaserver.

    Safe for any user to trigger. For full AI processing, use Admin sync.
    """
    from pathlib import Path
    from config import load_sources, _resolve_content_path
    from api.services.hierarchy_labels import apply_hierarchy_labels, find_source_for_file
    from database.models import KnowledgeEntry

    SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg", ".md", ".txt", ".docx", ".pptx", ".mp3", ".wav", ".m4a"}
    sources = load_sources()
    imported = 0
    skipped = 0
    errors = []

    # Get all existing source_paths from DB for fast lookup
    existing_paths = set()
    for row in db.query(KnowledgeEntry.source_path).filter(KnowledgeEntry.source_path.isnot(None)).all():
        existing_paths.add(row[0])

    for source in sources:
        paths_to_scan = [source.path]
        if source.additional_paths:
            paths_to_scan.extend(source.additional_paths)

        for path_str in paths_to_scan:
            abs_path = _resolve_content_path(path_str)
            if not abs_path.exists():
                continue

            for file_path in abs_path.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in SUPPORTED:
                    continue
                if str(file_path) in existing_paths:
                    skipped += 1
                    continue

                try:
                    entry = KnowledgeEntry(
                        titel=file_path.stem,
                        zusammenfassung=f"Dokument aus {source.name}",
                        inhalt=f"# {file_path.stem}\n\nQuelle: {source.name}\nPfad: {file_path}",
                        quelle=source.name,
                        dokumenttyp=CATEGORY_LABELS.get(source.category, source.category),
                        source_path=str(file_path),
                    )
                    db.add(entry)
                    db.flush()
                    source_match = find_source_for_file(file_path)
                    if source_match:
                        matched_source, source_root = source_match
                        apply_hierarchy_labels(db, entry, file_path, matched_source, source_root)
                    imported += 1
                except Exception as e:
                    errors.append(f"{file_path.name}: {e}")

    deleted = 0
    live_entries = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.source_path.isnot(None))
        .all()
    )
    for entry in live_entries:
        if not Path(entry.source_path).exists():
            db.delete(entry)
            deleted += 1

    if imported > 0 or deleted > 0:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            return SyncTriggerResponse(
                success=False,
                message=f"Sync fehlgeschlagen: {str(e)}",
                changes_detected={"new_files": imported, "modified_files": 0, "deleted_entries": deleted, "imported": 0, "updated": 0, "deleted": 0},
            )

    parts = []
    if imported > 0:
        parts.append(f"{imported} neue Dateien verlinkt")
    if deleted > 0:
        parts.append(f"{deleted} verwaiste Einträge gelöscht")
    msg = ", ".join(parts) if parts else "Keine Änderungen"
    if errors:
        msg += f" ({len(errors)} Fehler)"

    return SyncTriggerResponse(
        success=len(errors) == 0,
        message=msg,
        changes_detected={"new_files": imported, "modified_files": 0, "deleted_entries": deleted, "imported": imported, "updated": 0, "deleted": deleted},
    )
