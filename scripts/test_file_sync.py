#!/usr/bin/env python3
"""Test script for FileSyncService.

This script demonstrates how to use the FileSyncService to:
1. Detect changes between filesystem and database
2. Run a full sync operation

Usage:
    python test_file_sync.py [--dry-run]

The --dry-run flag will only detect changes without applying them.
"""

import argparse
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    parser = argparse.ArgumentParser(description="Test FileSyncService")
    parser.add_argument("--dry-run", action="store_true", help="Detect changes only")
    args = parser.parse_args()

    print("=" * 60)
    print("FileSyncService Test")
    print("=" * 60)
    print()

    try:
        from api.database import get_db_context
        from api.services.file_sync import FileSyncService

        with get_db_context() as db:
            service = FileSyncService(db)

            print(f"Running sync (dry_run={args.dry_run})...")
            print()

            result = service.run_sync(dry_run=args.dry_run)

            # Display results
            changes = result.changes

            print("-" * 60)
            print("CHANGES DETECTED")
            print("-" * 60)
            print(f"  New files:       {len(changes.new_files)}")
            print(f"  Modified files:  {len(changes.modified_files)}")
            print(f"  Deleted entries: {len(changes.deleted_entries)}")
            print()

            if not args.dry_run:
                print("-" * 60)
                print("SYNC RESULTS")
                print("-" * 60)
                print(f"  Imported:  {result.imported}")
                print(f"  Updated:   {result.updated}")
                print(f"  Deleted:   {result.deleted}")
                print(f"  Errors:    {len(result.errors)}")
                print()

            # List new files
            if changes.new_files:
                print("-" * 60)
                print("NEW FILES (first 10)")
                print("-" * 60)
                for path in changes.new_files[:10]:
                    print(f"  + {path}")
                if len(changes.new_files) > 10:
                    print(f"  ... and {len(changes.new_files) - 10} more")
                print()

            # List modified files
            if changes.modified_files:
                print("-" * 60)
                print("MODIFIED FILES")
                print("-" * 60)
                for entry, path in changes.modified_files[:10]:
                    print(f"  ~ {path} (entry {entry.id})")
                if len(changes.modified_files) > 10:
                    print(f"  ... and {len(changes.modified_files) - 10} more")
                print()

            # List deleted entries
            if changes.deleted_entries:
                print("-" * 60)
                print("DELETED ENTRIES (to be archived)")
                print("-" * 60)
                for entry in changes.deleted_entries[:10]:
                    print(f"  - {entry.source_path} (entry {entry.id})")
                if len(changes.deleted_entries) > 10:
                    print(f"  ... and {len(changes.deleted_entries) - 10} more")
                print()

            # Show errors
            if result.errors:
                print("-" * 60)
                print("ERRORS")
                print("-" * 60)
                for error in result.errors[:5]:
                    print(f"  ! {error}")
                if len(result.errors) > 5:
                    print(f"  ... and {len(result.errors) - 5} more errors")
                print()

            print("-" * 60)
            print("DONE")
            print("-" * 60)

    except ImportError as e:
        print(f"Error: Could not import required modules: {e}")
        print("Make sure you're in the correct directory and dependencies are installed.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
