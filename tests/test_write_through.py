"""Tests for text file write-through helper (api.services.entry_service.write_through)."""

from pathlib import Path

import pytest

from api.services.entry_service import write_through
from pipeline.batch_processor import calculate_file_hash


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_write_through_happy_path(tmp_path):
    root = tmp_path
    f = root / "doc.md"
    _write(f, "old content")

    new_hash = write_through(f, "new content", expected_hash=calculate_file_hash(f), content_root=root)

    assert f.read_text(encoding="utf-8") == "new content"
    assert new_hash == calculate_file_hash(f)
    # tmp sibling cleaned up by os.replace
    assert not f.with_suffix(".md.tmp").exists()


def test_write_through_hash_mismatch_raises(tmp_path):
    root = tmp_path
    f = root / "doc.txt"
    _write(f, "old content")

    with pytest.raises(ValueError, match="File changed on disk since last sync"):
        write_through(f, "new content", expected_hash="deadbeef", content_root=root)

    # untouched on mismatch
    assert f.read_text(encoding="utf-8") == "old content"


def test_write_through_path_escape_raises(tmp_path):
    root = tmp_path
    outside = root / ".." / "outside" / "evil.md"
    outside.parent.mkdir(parents=True, exist_ok=True)
    _write(outside, "old")

    with pytest.raises(ValueError, match="outside content root"):
        write_through(outside, "new", expected_hash=None, content_root=root)

    assert outside.read_text(encoding="utf-8") == "old"
