#!/usr/bin/env python3
"""Test script for source_watcher functionality."""

import sys
import time
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import get_db_context
from api.services.source_watcher import SourceWatcher


def test_source_watcher():
    """Test that source watcher can be instantiated and started."""
    print("Testing SourceWatcher...")

    with get_db_context() as db:
        # Create watcher
        watcher = SourceWatcher(db)

        # Check watch paths were loaded
        watch_paths = watcher.get_watch_paths()
        print(f"Loaded {len(watch_paths)} watch paths:")
        for path in watch_paths:
            print(f"  - {path}")

        # Start watcher
        print("\nStarting watcher...")
        watcher.start()

        if watcher.is_running():
            print("✓ Watcher is running")
        else:
            print("✗ Watcher failed to start")
            return False

        # Let it run for a few seconds
        print("\nWatcher running for 3 seconds...")
        time.sleep(3)

        # Stop watcher
        print("\nStopping watcher...")
        watcher.stop()

        if not watcher.is_running():
            print("✓ Watcher stopped successfully")
        else:
            print("✗ Watcher did not stop properly")
            return False

    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_source_watcher()
    sys.exit(0 if success else 1)
