#!/usr/bin/env python3
"""Backfill folder-hierarchy Fachgebiet labels for existing entries.

Derives tags from source_path subfolders (up to 4 levels) and sets
unterkategorie to the deepest folder name.

Usage:
    python scripts/backfill_hierarchy_labels.py
    python scripts/backfill_hierarchy_labels.py --dry-run
    python scripts/backfill_hierarchy_labels.py --limit 100
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import joinedload

from api.database import SessionLocal
from api.services.hierarchy_labels import (
    _raw_folder_parts,
    apply_hierarchy_labels_for_path,
    consolidate_fachgebiet_aliases,
    find_source_for_file,
    remove_stale_folder_tags,
)
from database.models import KnowledgeEntry

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def backfill(
    dry_run: bool = False,
    limit: int | None = None,
    replace_stale_tags: bool = False,
) -> dict:
    db = SessionLocal()
    stats = {
        "processed": 0,
        "updated": 0,
        "labels_added": 0,
        "tags_removed": 0,
        "skipped_no_path": 0,
        "skipped_no_source": 0,
        "errors": 0,
    }

    try:
        query = (
            db.query(KnowledgeEntry)
            .options(joinedload(KnowledgeEntry.fachgebiete))
            .filter(KnowledgeEntry.source_path.isnot(None))
            .order_by(KnowledgeEntry.id)
        )
        if limit:
            query = query.limit(limit)

        entries = query.all()
        logger.info("Processing %s entries with source_path", len(entries))

        for entry in entries:
            stats["processed"] += 1
            if not entry.source_path:
                stats["skipped_no_path"] += 1
                continue

            if not find_source_for_file(entry.source_path):
                stats["skipped_no_source"] += 1
                continue

            before_count = len(entry.fachgebiete)
            before_unter = entry.unterkategorie

            try:
                match = find_source_for_file(entry.source_path)
                if replace_stale_tags and match:
                    _, source_root = match
                    raw_parts = _raw_folder_parts(Path(entry.source_path), source_root)
                    stats["tags_removed"] += remove_stale_folder_tags(entry, raw_parts)

                apply_hierarchy_labels_for_path(db, entry)
            except Exception as e:
                stats["errors"] += 1
                logger.error("Entry %s failed: %s", entry.id, e)
                db.rollback()
                continue

            if len(entry.fachgebiete) > before_count or entry.unterkategorie != before_unter:
                stats["updated"] += 1
                stats["labels_added"] += max(0, len(entry.fachgebiete) - before_count)
                logger.info(
                    "Entry %s: +%s fachgebiete, unterkategorie=%s",
                    entry.id,
                    len(entry.fachgebiete) - before_count,
                    entry.unterkategorie,
                )

            if not dry_run:
                db.commit()
            else:
                db.rollback()

        return stats
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill hierarchy labels from source_path")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without committing")
    parser.add_argument("--limit", type=int, default=None, help="Max entries to process")
    parser.add_argument(
        "--replace-stale-tags",
        action="store_true",
        help="Remove old raw folder tags (e.g. DRG_Radiologie) before applying humanized labels",
    )
    parser.add_argument(
        "--consolidate-aliases",
        action="store_true",
        help="Merge/rename prefixed Fachgebiet records (e.g. AWMF_Leitlinien → Leitlinien)",
    )
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN — no changes will be saved")

    if args.consolidate_aliases and not args.dry_run:
        db = SessionLocal()
        try:
            alias_stats = consolidate_fachgebiet_aliases(db)
            db.commit()
            logger.info("Consolidated Fachgebiet aliases: %s", alias_stats)
        finally:
            db.close()

    stats = backfill(
        dry_run=args.dry_run,
        limit=args.limit,
        replace_stale_tags=args.replace_stale_tags,
    )

    logger.info("Done: %s", stats)
    return 1 if stats["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
