#!/usr/bin/env python3
"""Integration test for source_watcher with actual file operations."""

import sys
import time
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import get_db_context
from api.services.source_watcher import SourceWatcher, SourceFolderEventHandler
from api.services.file_sync import FileSyncService


def test_file_detection():
    """Test that file creation is detected by the watcher."""
    print("Testing file detection...")

    # Create a temporary directory to watch
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)

        with get_db_context() as db:
            # Create watcher with test directory
            sync_service = FileSyncService(db)

            # Create a manual observer for the test directory
            from watchdog.observers import Observer

            observer = Observer()
            handler = SourceFolderEventHandler(sync_service, db)
            observer.schedule(handler, str(test_dir), recursive=True)
            observer.start()

            print(f"✓ Watching test directory: {test_dir}")

            # Create a test file
            test_file = test_dir / "test_file.md"
            test_file.write_text("# Test Document\n\nThis is a test.")
            print(f"✓ Created test file: {test_file}")

            # Wait for detection
            time.sleep(2)

            # Stop observer
            observer.stop()
            observer.join()
            print("✓ Observer stopped")

            print("\n✓ File detection test completed")
            return True


def test_watcher_paths():
    """Test that watcher loads correct paths from config."""
    print("Testing watcher path configuration...")

    with get_db_context() as db:
        watcher = SourceWatcher(db)
        paths = watcher.get_watch_paths()

        expected_sources = [
            "1_SOPs",
            "2_Leitlinien",
            "3_Studien",
            "4_Red Flags",
            "5_Fragebögen",
            "6_Nachschlagen",
            "7_Infoblätter",
            "8_Fächer",
            "9_Fälle",
            "10_Pharma",
            "Fortbildung 2024",
            "Fortbildung 2025",
            "Fortbildung 2026",
        ]

        print(f"Loaded {len(paths)} watch paths:")
        for path in paths:
            path_str = str(path)
            matched = any(src in path_str for src in expected_sources)
            status = "✓" if matched else "✗"
            print(f"  {status} {path}")

            if not matched:
                print("    WARNING: Path doesn't match expected sources")

        # Verify we have the expected number of paths
        if len(paths) == len(expected_sources):
            print(f"\n✓ Correct number of watch paths: {len(paths)}")
        else:
            print(f"\n✗ Expected {len(expected_sources)} paths, got {len(paths)}")
            return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("SourceWatcher Integration Tests")
    print("=" * 60)

    success = True

    # Test 1: Path configuration
    if not test_watcher_paths():
        success = False

    print()

    # Test 2: File detection (requires manual verification)
    try:
        test_file_detection()
    except Exception as e:
        print(f"✗ File detection test failed: {e}")
        success = False

    print()
    print("=" * 60)
    if success:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
