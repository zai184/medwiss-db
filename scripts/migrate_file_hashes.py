"""Migration: populate file_hash for entries missing it, archive dead paths.

Scans all entries where source_path IS NOT NULL AND file_hash IS NULL.
- If the file exists: compute SHA-256 and update file_hash
- If the file does NOT exist: set status='archiviert'

Usage:
    python scripts/migrate_file_hashes.py [--dry-run]
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import and_
from api.database import SessionLocal
from database.models import KnowledgeEntry
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CHUNK_SIZE = 8192
BATCH_SIZE = 50


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file, reading in chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def migrate(dry_run: bool = False):
    db = SessionLocal()
    updated = 0
    archived = 0
    errors = 0

    try:
        # Find entries with source_path but no file_hash
        entries = (
            db.query(KnowledgeEntry)
            .filter(
                and_(
                    KnowledgeEntry.source_path.isnot(None),
                    KnowledgeEntry.file_hash.is_(None),
                )
            )
            .all()
        )

        total = len(entries)
        logger.info(f"Found {total} entries with source_path but no file_hash")

        for i, entry in enumerate(entries, 1):
            file_path = Path(entry.source_path)

            if not file_path.exists():
                # File gone
                archived += 1
                if i % 100 == 0 or i == total:
                    logger.info(f"Progress: {i}/{total} (hashed: {updated}, archived: {archived}, errors: {errors})")
                continue

            try:
                file_hash = compute_sha256(file_path)
                if not dry_run:
                    entry.file_hash = file_hash
                updated += 1
            except PermissionError:
                logger.warning(f"Permission denied: {file_path}")
                errors += 1
            except OSError as e:
                logger.warning(f"OS error reading {file_path}: {e}")
                errors += 1

            if i % 100 == 0 or i == total:
                logger.info(f"Progress: {i}/{total} (hashed: {updated}, archived: {archived}, errors: {errors})")

            # Batch commit
            if not dry_run and i % BATCH_SIZE == 0:
                db.commit()

        # Final commit
        if not dry_run:
            db.commit()

        logger.info(f"\n{'=' * 50}")
        logger.info(f"Migration {'(DRY RUN) ' if dry_run else ''}complete:")
        logger.info(f"  Hashed:   {updated}")
        logger.info(f"  Archived: {archived} (dead paths)")
        logger.info(f"  Errors:   {errors}")
        logger.info(f"  Total:    {total}")
        logger.info(f"{'=' * 50}")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        db.rollback()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        logger.info("DRY RUN mode — no changes will be written")
    sys.exit(migrate(dry_run=dry_run))
