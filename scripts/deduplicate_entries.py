"""Migration: deduplicate entries by source_path.

Finds entries sharing the same source_path and keeps only the best one:
1. Longest inhalt (most content)
2. Has file_hash (pipeline-imported > link-only)
3. Highest id (newest)

Usage:
    python scripts/deduplicate_entries.py [--dry-run]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from api.database import SessionLocal
from database.models import KnowledgeEntry
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def deduplicate(dry_run: bool = False):
    db = SessionLocal()
    groups_found = 0
    entries_removed = 0

    try:
        # Find source_paths with more than one entry
        dupes = (
            db.query(
                KnowledgeEntry.source_path,
                func.count(KnowledgeEntry.id).label("cnt"),
            )
            .filter(KnowledgeEntry.source_path.isnot(None))
            .group_by(KnowledgeEntry.source_path)
            .having(func.count(KnowledgeEntry.id) > 1)
            .all()
        )

        groups_found = len(dupes)
        logger.info(f"Found {groups_found} source_paths with duplicate entries")

        for source_path, count in dupes:
            entries = (
                db.query(KnowledgeEntry)
                .filter(KnowledgeEntry.source_path == source_path)
                .all()
            )

            # Score each entry: (has_hash, content_length, id)
            def score(e):
                has_hash = 1 if e.file_hash else 0
                content_len = len(e.inhalt) if e.inhalt else 0
                return (has_hash, content_len, e.id)

            entries.sort(key=score, reverse=True)
            keep = entries[0]
            remove = entries[1:]

            logger.info(
                f"  {source_path}: {count} entries → keeping id={keep.id} "
                f"(hash={'yes' if keep.file_hash else 'no'}, content={len(keep.inhalt or '')}), "
                f"removing {[e.id for e in remove]}"
            )

            for entry in remove:
                if not dry_run:
                    db.delete(entry)
                entries_removed += 1

        if not dry_run:
            db.commit()

        logger.info(f"\n{'=' * 50}")
        logger.info(f"Deduplication {'(DRY RUN) ' if dry_run else ''}complete:")
        logger.info(f"  Duplicate groups: {groups_found}")
        logger.info(f"  Entries removed:  {entries_removed}")
        logger.info(f"{'=' * 50}")

    except Exception as e:
        logger.error(f"Deduplication failed: {e}", exc_info=True)
        db.rollback()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        logger.info("DRY RUN mode — no changes will be written")
    sys.exit(deduplicate(dry_run=dry_run))
