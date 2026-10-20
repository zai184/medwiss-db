#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings

CATEGORY_MAP = {
    "sop": "sop",
    "leitlinien": "leitlinien",
    "studien": "studien",
    "red_flags": "red_flags",
    "frageboegen": "frageboegen",
    "nachschlagen": "nachschlagen",
    "infoblaetter": "infoblaetter",
    "faecher": "faecher",
    "faelle": "faelle",
    "pharma": "pharma",
    "fortbildung": "fortbildung",
}

QUELLE_PREFIX_MAP = {
    "1_": "sop",
    "2_": "leitlinien",
    "3_": "studien",
    "4_": "red_flags",
    "5_": "faecher",
    "6_": "pharma",
    "7_": "frageboegen",
    "8_": "infoblaetter",
    "9_": "pruefungen",
}


def parse_quelle_category(quelle: str | None) -> str | None:
    if not quelle:
        return None
    if ": " in quelle:
        return quelle.split(": ", 1)[0].lower().strip()
    for prefix, category in QUELLE_PREFIX_MAP.items():
        if quelle.startswith(prefix):
            return category
    return None


def get_entries_needing_migration(db: Session, batch_size: int = 100):
    offset = 0
    while True:
        query = text("""
            SELECT id, titel, quelle, falltyp
            FROM knowledge_entries
            WHERE quelle IS NOT NULL
            LIMIT :batch_size OFFSET :offset
        """)
        result = db.execute(query, {"batch_size": batch_size, "offset": offset})
        rows = result.fetchall()
        if not rows:
            break
        yield rows
        offset += batch_size


LEGACY_CLEANUP_MAP = {
    "forschung": "studie",
}

DEMO_CATEGORIES = ["lehrfall", "fall", "nachschlagen"]


def run_legacy_cleanup(db: Session, args, stats, changes_preview):
    print("\n" + "=" * 60)
    print("PHASE 2: Legacy falltyp cleanup")
    print("=" * 60)

    for old_falltyp, new_falltyp in LEGACY_CLEANUP_MAP.items():
        query = text("""
            SELECT id, titel, quelle, falltyp
            FROM knowledge_entries
            WHERE falltyp = :old_falltyp
        """)
        result = db.execute(query, {"old_falltyp": old_falltyp})
        rows = result.fetchall()

        if not rows:
            print(f"  No entries with falltyp='{old_falltyp}' found.")
            continue

        print(f"  Found {len(rows)} entries with falltyp='{old_falltyp}' → '{new_falltyp}'")

        for row in rows:
            entry_id, titel, quelle, current_falltyp = row
            stats["total_processed"] += 1
            stats["updated"] += 1
            changes_preview.append({
                "id": entry_id,
                "quelle": quelle,
                "current_falltyp": current_falltyp,
                "new_falltyp": new_falltyp,
            })

            if not args.dry_run:
                try:
                    db.execute(
                        text("UPDATE knowledge_entries SET falltyp = :new_falltyp, updated_at = NOW() WHERE id = :id"),
                        {"new_falltyp": new_falltyp, "id": entry_id}
                    )
                except Exception as e:
                    stats["errors"] += 1
                    print(f"    ERROR updating entry {entry_id}: {e}")

        if not args.dry_run:
            db.commit()

    # Phase 3: Delete demo categories
    print("\n" + "=" * 60)
    print("PHASE 3: Delete demo categories")
    print("=" * 60)

    for demo_category in DEMO_CATEGORIES:
        query = text("""
            SELECT id, titel, quelle, falltyp
            FROM knowledge_entries
            WHERE falltyp = :demo_category
        """)
        result = db.execute(query, {"demo_category": demo_category})
        rows = result.fetchall()

        if not rows:
            print(f"  No entries with falltyp='{demo_category}' found.")
            continue

        print(f"  Found {len(rows)} demo entries with falltyp='{demo_category}' - DELETING")

        for row in rows:
            entry_id, titel, quelle, current_falltyp = row
            stats["total_processed"] += 1
            changes_preview.append({
                "id": entry_id,
                "quelle": quelle,
                "current_falltyp": current_falltyp,
                "new_falltyp": "DELETED",
            })

            if not args.dry_run:
                try:
                    db.execute(
                        text("DELETE FROM knowledge_entries WHERE id = :id"),
                        {"id": entry_id}
                    )
                except Exception as e:
                    stats["errors"] += 1
                    print(f"    ERROR deleting entry {entry_id}: {e}")

        if not args.dry_run:
            db.commit()

    # Phase 4: Fix old singular forms to plural
    print("\n" + "=" * 60)
    print("PHASE 4: Fix singular → plural categories")
    print("=" * 60)

    SINGULAR_TO_PLURAL = {
        "richtlinien": "leitlinien",
        "studie": "studien",
        "redflag": "red_flags",
        "infoblatt": "infoblaetter",
        "fragebogen": "frageboegen",
        "fach": "faecher",
        "fall": "faelle",
    }

    for old_cat, new_cat in SINGULAR_TO_PLURAL.items():
        query = text("""
            SELECT id, titel, quelle, falltyp
            FROM knowledge_entries
            WHERE falltyp = :old_cat
        """)
        result = db.execute(query, {"old_cat": old_cat})
        rows = result.fetchall()

        if not rows:
            continue

        print(f"  Found {len(rows)} entries with falltyp='{old_cat}' → '{new_cat}'")

        for row in rows:
            entry_id, titel, quelle, current_falltyp = row
            stats["total_processed"] += 1
            stats["updated"] += 1
            changes_preview.append({
                "id": entry_id,
                "quelle": quelle,
                "current_falltyp": current_falltyp,
                "new_falltyp": new_cat,
            })

            if not args.dry_run:
                try:
                    db.execute(
                        text("UPDATE knowledge_entries SET falltyp = :new_cat, updated_at = NOW() WHERE id = :id"),
                        {"new_cat": new_cat, "id": entry_id}
                    )
                except Exception as e:
                    stats["errors"] += 1
                    print(f"    ERROR updating entry {entry_id}: {e}")

        if not args.dry_run:
            db.commit()


def main():
    parser = argparse.ArgumentParser(description="Migrate falltyp from quelle field")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without making them")
    args = parser.parse_args()

    engine = create_engine(settings.database_url)

    stats = {
        "total_processed": 0,
        "updated": 0,
        "no_change_needed": 0,
        "unmatched": 0,
        "errors": 0,
    }

    changes_preview = []

    print(f"{'='*60}")
    print("Migration: Fix falltyp from quelle field")
    print(f"{'='*60}")
    print(f"Dry run mode: {'ENABLED' if args.dry_run else 'DISABLED'}")
    print(f"{'='*60}\n")

    with Session(engine) as db:
        batch_num = 0
        for batch in get_entries_needing_migration(db):
            batch_num += 1
            print(f"Processing batch {batch_num} ({len(batch)} entries)...")

            for row in batch:
                stats["total_processed"] += 1
                entry_id, titel, quelle, current_falltyp = row

                category = parse_quelle_category(quelle)
                if category is None:
                    stats["unmatched"] += 1
                    changes_preview.append({
                        "id": entry_id,
                        "quelle": quelle,
                        "current_falltyp": current_falltyp,
                        "new_falltyp": "UNMATCHED",
                    })
                    continue

                new_falltyp = CATEGORY_MAP.get(category, category)
                if current_falltyp == new_falltyp:
                    stats["no_change_needed"] += 1
                    continue

                stats["updated"] += 1
                changes_preview.append({
                    "id": entry_id,
                    "quelle": quelle,
                    "current_falltyp": current_falltyp,
                    "new_falltyp": new_falltyp,
                })

                if not args.dry_run:
                    try:
                        db.execute(
                            text("UPDATE knowledge_entries SET falltyp = :new_falltyp, updated_at = NOW() WHERE id = :id"),
                            {"new_falltyp": new_falltyp, "id": entry_id}
                        )
                    except Exception as e:
                        stats["errors"] += 1
                        print(f"  ERROR updating entry {entry_id}: {e}")

            if not args.dry_run:
                db.commit()

        run_legacy_cleanup(db, args, stats, changes_preview)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total processed:   {stats['total_processed']}")
    print(f"  - Updated:      {stats['updated']}")
    print(f"  - No change:   {stats['no_change_needed']}")
    print(f"  - Unmatched:   {stats['unmatched']}")
    print(f"  - Errors:      {stats['errors']}")

    if changes_preview:
        print(f"\n{'='*60}")
        print("CHANGES" + (" (DRY RUN - NOT APPLIED)" if args.dry_run else ""))
        print(f"{'='*60}")
        print(f"{'ID':<8} {'Current':<15} {'New':<15} {'Quelle':<30}")
        print("-" * 70)
        for change in changes_preview[:50]:
            print(f"{change['id']:<8} {change['current_falltyp'] or '(null)':<15} "
                  f"{change['new_falltyp']:<15} {change['quelle'][:28]:<30}")
        if len(changes_preview) > 50:
            print(f"\n... and {len(changes_preview) - 50} more changes")

    print(f"\n{'='*60}")
    if args.dry_run:
        if stats['updated'] > 0:
            print(f"DRY RUN: {stats['updated']} updates would be made.")
            print("Run without --dry-run to apply these changes.")
        else:
            print("No updates needed.")
    else:
        if stats['errors'] == 0:
            print(f"SUCCESS: {stats['updated']} entries updated.")
        else:
            print(f"COMPLETED with {stats['errors']} errors.")
    print(f"{'='*60}")
    sys.exit(0 if stats['errors'] == 0 else 1)


if __name__ == "__main__":
    main()