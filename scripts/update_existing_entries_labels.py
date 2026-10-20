#!/usr/bin/env python3
"""Update existing entries' unterkategorie values based on source_path.

This script migrates existing entries to have correct unterkategorie values
by parsing their source_path and applying the same CATEGORY_LABELS mapping
used in batch import. For faecher entries, it also links the subfolder as
a Fachgebiet.

Usage:
    python scripts/update_existing_entries_labels.py          # Dry-run (shows what would change)
    python scripts/update_existing_entries_labels.py --dry-run  # Same as above
    python scripts/update_existing_entries_labels.py --apply    # Actually apply changes
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from api.database import get_db_context
from database.models import KnowledgeEntry, Fachgebiet
from pipeline.classification_resolver import resolve_fachgebiet, ResolutionResult

# Mapping from source category to human-readable unterkategorie labels
# Must match CATEGORY_LABELS in api/services/hierarchy_labels.py
CATEGORY_LABELS = {
    "sop": "SOP",
    "leitlinien": "Leitlinie",
    "studien": "Studie",
    "faecher": "Fachgebiet",
    "pharma": "Pharma",
    "frageboegen": "Fragebogen",
    "infoblaetter": "Infoblatt",
    "red_flags": "Red Flags",
    "pruefungen": "Prüfung",
    "fortbildung": "Fortbildung",
}

# Regex patterns to detect category from source_path
# Order matters - more specific patterns first
CATEGORY_PATTERNS = [
    (r"/1_SOPs/", "sop"),
    (r"/2_Leitlinien/", "leitlinien"),
    (r"/3_Studien/", "studien"),
    (r"/4_Red Flags/", "red_flags"),
    (r"/5_Fächer/", "faecher"),
    (r"/6_Pharma/", "pharma"),
    (r"/7_Fragebögen/", "frageboegen"),
    (r"/8_Infoblätter/", "infoblaetter"),
    (r"/9_Prüfungen/", "pruefungen"),
    (r"/Fortbildung", "fortbildung"),  # Must be after specific folders
]

logger = logging.getLogger(__name__)


def detect_category_from_path(source_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Detect category and subfolder from source_path."""
    if not source_path:
        return None, None

    category = None
    subfolder = None

    for pattern, cat in CATEGORY_PATTERNS:
        if re.search(pattern, source_path, re.IGNORECASE):
            category = cat
            break

    if category == "faecher" and source_path:
        match = re.search(r"/5_Fächer/([^/]+)/", source_path, re.IGNORECASE)
        if match:
            subfolder = match.group(1)
            subfolder = subfolder[0].upper() + subfolder[1:].lower() if len(subfolder) > 1 else subfolder.upper()

    return category, subfolder


def get_expected_unterkategorie(category: Optional[str], subfolder: Optional[str]) -> Optional[str]:
    if category is None:
        return None
    if category == "faecher" and subfolder:
        return subfolder
    return CATEGORY_LABELS.get(category)


def update_entry_labels(
    db: Session,
    entry: KnowledgeEntry,
    dry_run: bool = True,
) -> dict:
    result = {
        "changed": False,
        "skipped": False,
        "error": None,
        "action_taken": None,
        "old_unterkategorie": entry.unterkategorie,
        "new_unterkategorie": None,
    }

    try:
        category, subfolder = detect_category_from_path(entry.source_path or "")

        if category is None:
            result["skipped"] = True
            result["action_taken"] = "no_matching_category"
            result["new_unterkategorie"] = entry.unterkategorie
            return result

        expected_unterkategorie = get_expected_unterkategorie(category, subfolder)

        if entry.unterkategorie == expected_unterkategorie:
            result["skipped"] = True
            result["action_taken"] = "already_correct"
            result["new_unterkategorie"] = expected_unterkategorie
            return result

        result["changed"] = True
        result["new_unterkategorie"] = expected_unterkategorie

        if dry_run:
            result["action_taken"] = "would_update"
            return result

        entry.unterkategorie = expected_unterkategorie
        result["action_taken"] = "updated"

        if category == "faecher" and subfolder:
            try:
                fg_result: ResolutionResult = resolve_fachgebiet(db, subfolder)
                if fg_result and fg_result.id:
                    existing_ids = [f.id for f in entry.fachgebiete]
                    if fg_result.id not in existing_ids:
                        fach = db.query(Fachgebiet).filter(Fachgebiet.id == fg_result.id).first()
                        if fach:
                            entry.fachgebiete.append(fach)
                            result["action_taken"] = "updated_with_fachgebiet"
                            logger.info(
                                f"Linked entry {entry.id} to Fachgebiet '{subfolder}' (ID: {fg_result.id})"
                            )
            except Exception as e:
                logger.warning(f"Could not resolve Fachgebiet '{subfolder}' for entry {entry.id}: {e}")

        db.flush()

    except Exception as e:
        result["error"] = str(e)
        result["action_taken"] = "error"
        logger.error(f"Error updating entry {entry.id}: {e}", exc_info=True)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update existing entries' unterkategorie values based on source_path",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run          Show what would be updated (default)
  %(prog)s --apply            Actually apply the changes

The script detects entries with missing or incorrect unterkategorie values,
parses their source_path to determine the correct category, and updates
the unterkategorie field. For faecher entries, it also links the subfolder
as a Fachgebiet.
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be changed without making changes (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the changes (default is dry-run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of entries to process (for testing)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    dry_run = not args.apply

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be applied")
        print("=" * 60)
    else:
        print("=" * 60)
        print("APPLY MODE - Changes will be committed to database")
        print("=" * 60)

    entries_needing_update = []
    entries_with_errors = []
    entries_skipped = []

    with get_db_context() as db:
        query = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.source_path.isnot(None),
            KnowledgeEntry.source_path != "",
        )

        if args.limit:
            query = query.limit(args.limit)

        all_entries = query.all()
        total = len(all_entries)

        print(f"\nFound {total} entries with source_path")

        for entry in all_entries:
            result = update_entry_labels(db, entry, dry_run=dry_run)

            if result["action_taken"] == "error":
                entries_with_errors.append((entry, result))
            elif result["action_taken"] == "already_correct":
                entries_skipped.append((entry, result))
            elif result["action_taken"] == "no_matching_category":
                entries_skipped.append((entry, result))
            elif result["changed"]:
                entries_needing_update.append((entry, result))
            else:
                entries_skipped.append((entry, result))

        # Summary before commit
        print("\n" + "-" * 60)
        print("ANALYSIS RESULTS")
        print("-" * 60)
        print(f"  Total entries scanned:        {total}")
        print(f"  Would update / updated:        {len(entries_needing_update)}")
        print(f"  Already correct / skipped:    {len(entries_skipped)}")
        print(f"  Errors:                       {len(entries_with_errors)}")

        # Show detailed changes
        if entries_needing_update:
            print("\n" + "-" * 60)
            print("ENTRIES THAT WOULD BE UPDATED" if dry_run else "ENTRIES UPDATED")
            print("-" * 60)

            for entry, result in entries_needing_update:
                print(f"\n  Entry #{entry.id}: {entry.titel[:50]}...")
                print(f"    Old unterkategorie: {result['old_unterkategorie'] or '(none)'}")
                print(f"    New unterkategorie: {result['new_unterkategorie']}")
                print(f"    Source: {entry.source_path[:60]}..." if len(entry.source_path or "") > 60 else f"    Source: {entry.source_path}")
                if "with_fachgebiet" in (result["action_taken"] or ""):
                    print("    Action: Updated with Fachgebiet link")

        if entries_skipped and args.verbose:
            print("\n" + "-" * 60)
            print("ENTRIES SKIPPED (already correct or no match)")
            print("-" * 60)
            for entry, result in entries_skipped[:10]:  # Show first 10
                print(f"  #{entry.id}: unterkategorie={entry.unterkategorie or '(none)'} - {result['action_taken']}")
            if len(entries_skipped) > 10:
                print(f"  ... and {len(entries_skipped) - 10} more")

        if entries_with_errors:
            print("\n" + "-" * 60)
            print("ENTRIES WITH ERRORS")
            print("-" * 60)
            for entry, result in entries_with_errors:
                print(f"  #{entry.id}: {result['error']}")

        # Commit if applying
        if not dry_run:
            if entries_needing_update:
                print("\n" + "-" * 60)
                print("COMMITTING CHANGES")
                print("-" * 60)
                db.commit()
                print(f"  Committed {len(entries_needing_update)} updates")
            else:
                print("\n  No changes to commit")

    print("\n" + "=" * 60)
    if dry_run:
        print("Dry run complete. Run with --apply to make changes.")
    else:
        print("Update complete.")
    print("=" * 60)

    return 0 if not entries_with_errors else 1


if __name__ == "__main__":
    sys.exit(main())