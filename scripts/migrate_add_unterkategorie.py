#!/usr/bin/env python3
"""Migration: Add unterkategorie column to knowledge_entries table.

Adds a nullable VARCHAR(100) column 'unterkategorie' to store subfolder names
(e.g., 'Notaufnahme', 'Kardio', 'Gyn'). The search view v_entry_search
is a regular view — always current, no refresh needed.
Usage:
    python scripts/migrate_add_unterkategorie.py          # Apply migration
    python scripts/migrate_add_unterkategorie.py --dry-run # Preview only
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings


def check_column_exists(db: Session) -> bool:
    """Check if unterkategorie column already exists."""
    result = db.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'knowledge_entries'
          AND column_name = 'unterkategorie'
    """))
    return result.fetchone() is not None


def run_migration(db: Session, dry_run: bool = False) -> None:
    """Add unterkategorie column."""
    if check_column_exists(db):
        print("Column 'unterkategorie' already exists in knowledge_entries. Skipping.")
        return

    alter_sql = text("""
        ALTER TABLE knowledge_entries
        ADD COLUMN unterkategorie VARCHAR(100)
    """)

    index_sql = text("""
        CREATE INDEX idx_knowledge_entries_unterkategorie
        ON knowledge_entries(unterkategorie)
    """)

    if dry_run:
        print("[DRY RUN] Would execute:")
        print(f"  {alter_sql.text.strip()}")
        print(f"  {index_sql.text.strip()}")
    else:
        print("Adding unterkategorie column...")
        db.execute(alter_sql)
        print("Creating index idx_knowledge_entries_unterkategorie...")
        db.execute(index_sql)
        db.commit()
        print("Migration complete. (v_entry_search is a regular view — always current, no refresh needed.)")


def main():
    parser = argparse.ArgumentParser(
        description="Add unterkategorie column to knowledge_entries"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )
    args = parser.parse_args()

    engine = create_engine(settings.database_url)

    print("=" * 60)
    print("Migration: Add unterkategorie to knowledge_entries")
    print("=" * 60)
    print(f"Dry run: {'ENABLED' if args.dry_run else 'DISABLED'}")
    print()

    with Session(engine) as db:
        run_migration(db, dry_run=args.dry_run)

    print()
    print("=" * 60)
    if args.dry_run:
        print("DRY RUN complete. No changes were made.")
        print("Run without --dry-run to apply the migration.")
    else:
        print("Migration applied successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
