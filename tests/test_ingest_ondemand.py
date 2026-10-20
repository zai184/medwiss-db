"""Ingest routing regression: extraction-dependent files are indexed
metadata-only (never OCR'd at ingest); text files keep direct read.

Pure routing test — stubs the DB session and source lookup; no live Postgres.
"""

from pathlib import Path
from unittest.mock import MagicMock


from config import SourceConfig
from pipeline.batch_processor import BatchProcessor

# A minimal but valid SourceConfig (see config/__init__.py).
SAMPLE_SOURCE = SourceConfig(
    name="test",
    path="1_SOPs",
    category="SOP",
    default_fachgebiete=[],
    description="test source",
)


def _make_service(db=None):
    from api.services.file_sync import FileSyncService

    svc = FileSyncService.__new__(FileSyncService)
    svc.db = db or MagicMock()
    svc._processor = BatchProcessor()
    return svc


def test_image_pdf_audio_routed_to_link_only_never_process_file(tmp_path, monkeypatch):
    """A PDF/PNG/mp3 new file must go metadata-only — process_file never runs."""
    from api.services import file_sync as fs

    svc = _make_service()
    svc._find_source_for_path = lambda p: SAMPLE_SOURCE

    calls = []

    def fake_link_only(path, source, file_hash, entry):
        calls.append(("link_only", path.suffix))
        return MagicMock(id=1)

    def process_file_must_not_run(path):
        raise AssertionError(f"process_file must not run for extraction-dependent {path}")

    monkeypatch.setattr(fs, "calculate_file_hash", lambda p: "abc")
    monkeypatch.setattr(svc, "_link_only_index", fake_link_only)
    monkeypatch.setattr(svc._processor, "process_file", process_file_must_not_run)

    for name in ["scan.pdf", "photo.png", "note.jpg", "rec.mp3"]:
        calls.clear()
        f = tmp_path / name
        f.write_bytes(b"fake")
        entry = svc.ingest_file(f)
        assert calls == [("link_only", Path(name).suffix)], name
        assert entry is not None


def test_text_file_goes_through_processor(tmp_path, monkeypatch):
    """.md/.txt new files keep direct-read extraction (not link-only)."""
    from api.services import file_sync as fs
    from pipeline.orchestrator import ProcessingResult

    svc = _make_service()
    svc._find_source_for_path = lambda p: SAMPLE_SOURCE

    result = ProcessingResult(
        file_path=str(tmp_path / "doc.md"),
        file_type="text",
        extracted_text="# heading",
        processing_time_ms=1,
    )
    monkeypatch.setattr(
        svc._processor, "process_file", lambda p: result
    )
    monkeypatch.setattr(fs, "calculate_file_hash", lambda p: "def")
    monkeypatch.setattr(svc, "_link_only_index", lambda *a, **k: (_ for _ in ()).throw(AssertionError("text file must not be link-only")))
    monkeypatch.setattr(svc, "_create_entry_from_result", lambda r, s, h: MagicMock(id=2))
    monkeypatch.setattr(svc, "_generate_embedding", lambda e: None)

    f = tmp_path / "doc.md"
    f.write_text("# heading", encoding="utf-8")
    entry = svc.ingest_file(f)
    assert entry is not None


def test_extraction_dependent_does_not_require_ocr_backend(tmp_path, monkeypatch):
    """Even with no OCR backend configured, ingest succeeds (metadata-only)."""
    from api.services import file_sync as fs

    svc = _make_service()
    svc._find_source_for_path = lambda p: SAMPLE_SOURCE

    monkeypatch.setattr(fs, "calculate_file_hash", lambda p: "xyz")
    entry_mock = MagicMock(id=3)
    monkeypatch.setattr(svc, "_link_only_index", lambda *a, **k: entry_mock)

    f = tmp_path / "scan.png"
    f.write_bytes(b"fake")
    entry = svc.ingest_file(f)
    assert entry is not None
