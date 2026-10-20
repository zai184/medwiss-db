"""Contract tests for the AI pipeline.

Tests file type detection, supported extensions, and processing result
structure without requiring a live llamaserver or database.
"""

from pathlib import Path

import pytest


class TestFileTypeDetection:
    """detect_file_type() must correctly classify file extensions."""

    @pytest.fixture
    def detect(self):
        from pipeline.orchestrator import detect_file_type

        return detect_file_type

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("scan.png", "image"),
            ("photo.jpg", "image"),
            ("photo.jpeg", "image"),
            ("document.pdf", "image"),  # PDF goes through OCR
            ("xray.bmp", "image"),
            ("slide.tiff", "image"),
            ("scan.tif", "image"),
        ],
    )
    def test_image_types(self, detect, filename, expected):
        assert detect(Path(filename)) == expected

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("lecture.mp3", "audio"),
            ("recording.wav", "audio"),
            ("voice.m4a", "audio"),
            ("podcast.ogg", "audio"),
            ("music.flac", "audio"),
            ("memo.wma", "audio"),
            ("dictation.aac", "audio"),
        ],
    )
    def test_audio_types(self, detect, filename, expected):
        assert detect(Path(filename)) == expected

    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("notes.txt", "text"),
            ("readme.md", "text"),
            ("data.csv", "text"),
            ("config.json", "text"),
            ("schema.xml", "text"),
        ],
    )
    def test_text_types(self, detect, filename, expected):
        assert detect(Path(filename)) == expected

    def test_unknown_extension(self, detect):
        assert detect(Path("file.xyz")) == "unknown"

    def test_no_extension(self, detect):
        assert detect(Path("Makefile")) == "unknown"

    def test_case_insensitive(self, detect):
        assert detect(Path("IMAGE.PNG")) == "image"
        assert detect(Path("Audio.MP3")) == "audio"


class TestSupportedExtensions:
    """Verify extension sets are consistent."""

    def test_image_extensions(self):
        from pipeline.orchestrator import IMAGE_EXTENSIONS

        assert ".png" in IMAGE_EXTENSIONS
        assert ".jpg" in IMAGE_EXTENSIONS
        assert ".pdf" in IMAGE_EXTENSIONS  # Handled by OCR

    def test_audio_extensions(self):
        from pipeline.orchestrator import AUDIO_EXTENSIONS

        assert ".mp3" in AUDIO_EXTENSIONS
        assert ".wav" in AUDIO_EXTENSIONS

    def test_text_extensions(self):
        from pipeline.orchestrator import TEXT_EXTENSIONS

        assert ".txt" in TEXT_EXTENSIONS
        assert ".md" in TEXT_EXTENSIONS

    def test_no_overlap_between_categories(self):
        """No extension should be in multiple categories."""
        from pipeline.orchestrator import IMAGE_EXTENSIONS, AUDIO_EXTENSIONS, TEXT_EXTENSIONS

        overlap_ia = IMAGE_EXTENSIONS & AUDIO_EXTENSIONS
        overlap_it = IMAGE_EXTENSIONS & TEXT_EXTENSIONS
        overlap_at = AUDIO_EXTENSIONS & TEXT_EXTENSIONS

        assert not overlap_ia, f"Overlap image/audio: {overlap_ia}"
        assert not overlap_it, f"Overlap image/text: {overlap_it}"
        assert not overlap_at, f"Overlap audio/text: {overlap_at}"


class TestProcessingResult:
    """ProcessingResult dataclass structure contract."""

    def test_processing_result_fields(self):
        from pipeline.orchestrator import ProcessingResult

        result = ProcessingResult(
            file_path="/tmp/test.pdf",
            file_type="image",
            extracted_text="Sample text",
        )

        d = result.to_dict()
        assert d["file_path"] == "/tmp/test.pdf"
        assert d["file_type"] == "image"
        assert d["extracted_text"] == "Sample text"

    def test_processing_result_error(self):
        from pipeline.orchestrator import ProcessingResult

        result = ProcessingResult(
            file_path="/tmp/bad.xyz",
            file_type="unknown",
            extracted_text="",
            error="Unsupported file type",
        )

        d = result.to_dict()
        assert d["error"] == "Unsupported file type"

    def test_processing_result_json_serializable(self):
        import json

        from pipeline.orchestrator import ProcessingResult

        result = ProcessingResult(
            file_path="/tmp/test.txt",
            file_type="text",
            extracted_text="hello",
        )

        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["file_path"] == "/tmp/test.txt"


class TestSummarizeSkills:
    """Validate summarization skill set is consistent."""

    def test_valid_skills(self):
        from pipeline.orchestrator import SUMMARIZE_SKILLS

        assert "studie" in SUMMARIZE_SKILLS
        assert "leitlinie" in SUMMARIZE_SKILLS
        assert "screenshot" in SUMMARIZE_SKILLS
        assert "standard" in SUMMARIZE_SKILLS

    def test_skills_match_router(self):
        from api.routers.summarize import VALID_SKILLS
        from pipeline.orchestrator import SUMMARIZE_SKILLS

        assert VALID_SKILLS == SUMMARIZE_SKILLS


class TestOcrBackends:
    """OCR seam: ordered-try over configured backends, no batch."""

    def test_empty_config_raises_no_backend(self, tmp_path, monkeypatch):
        from pipeline.ocr_backend import NoOcrBackendError, extract_text_from_file

        monkeypatch.setattr("pipeline.ocr_backend.settings.ocr_backends", [])
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake")
        with pytest.raises(NoOcrBackendError) as ei:
            extract_text_from_file(img)
        assert ei.value.reasons == []

    def test_first_backend_wins(self, tmp_path, monkeypatch):
        from pipeline.ocr_backend import _BACKENDS, extract_text_from_file

        monkeypatch.setattr("pipeline.ocr_backend.settings.ocr_backends", ["a", "b"])
        calls = []

        def fake_a(path):
            calls.append("a")
            return "alpha"

        def fake_b(path):
            calls.append("b")
            return "beta"

        monkeypatch.setitem(_BACKENDS, "a", fake_a)
        monkeypatch.setitem(_BACKENDS, "b", fake_b)
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake")

        assert extract_text_from_file(img) == "alpha"
        assert calls == ["a"]  # b never tried

    def test_unavailable_skips_to_next(self, tmp_path, monkeypatch):
        from pipeline.ocr_backend import _BACKENDS, extract_text_from_file

        monkeypatch.setattr("pipeline.ocr_backend.settings.ocr_backends", ["a", "b"])

        def fake_a(path):
            raise Exception("unavailable")  # noqa: BLE001  -> recorded as failure

        def fake_b(path):
            return "beta"

        monkeypatch.setitem(_BACKENDS, "a", fake_a)
        monkeypatch.setitem(_BACKENDS, "b", fake_b)
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake")

        assert extract_text_from_file(img) == "beta"

    def test_all_failed_collects_reasons(self, tmp_path, monkeypatch):
        from pipeline.ocr_backend import NoOcrBackendError, _BACKENDS, extract_text_from_file

        monkeypatch.setattr("pipeline.ocr_backend.settings.ocr_backends", ["a", "b"])
        monkeypatch.setitem(_BACKENDS, "a", lambda p: (_ for _ in ()).throw(ValueError("boom")))
        monkeypatch.setitem(_BACKENDS, "b", lambda p: "")
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake")

        with pytest.raises(NoOcrBackendError) as ei:
            extract_text_from_file(img)
        names = [n for n, _ in ei.value.reasons]
        assert "a" in names and "b" in names
        assert any("boom" in r for n, r in ei.value.reasons if n == "a")

    def test_unknown_backend_warned_and_skipped(self, tmp_path, monkeypatch):
        from pipeline.ocr_backend import _BACKENDS, extract_text_from_file

        monkeypatch.setattr("pipeline.ocr_backend.settings.ocr_backends", ["nope", "a"])
        monkeypatch.setitem(_BACKENDS, "a", lambda p: "text")
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake")
        assert extract_text_from_file(img) == "text"

    def test_backend_override_runs_only_that_one(self, tmp_path, monkeypatch):
        """A forced backend runs alone, bypassing OCR_BACKENDS order."""
        from pipeline.ocr_backend import _BACKENDS, extract_text_from_file

        monkeypatch.setattr("pipeline.ocr_backend.settings.ocr_backends", ["a", "b"])
        calls = []

        def fake_a(path):
            calls.append("a")
            return "alpha"

        monkeypatch.setitem(_BACKENDS, "a", fake_a)
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake")

        # Force 'a' — works even though only 'a' is registered.
        assert extract_text_from_file(img, backend="a") == "alpha"
        assert calls == ["a"]

    def test_backend_override_unknown_raises(self, tmp_path, monkeypatch):
        from pipeline.ocr_backend import NoOcrBackendError, _BACKENDS, extract_text_from_file

        monkeypatch.setattr("pipeline.ocr_backend.settings.ocr_backends", ["a"])
        monkeypatch.setitem(_BACKENDS, "a", lambda p: "alpha")
        img = tmp_path / "scan.png"
        img.write_bytes(b"fake")

        with pytest.raises(NoOcrBackendError) as ei:
            extract_text_from_file(img, backend="nope")
        assert any(n == "nope" for n, _ in ei.value.reasons)


class TestOcrBackendHttpMapping:
    def test_unconfigured_maps_409(self):
        from pipeline.ocr_backend import NoOcrBackendError, http_error_for_ocr

        code, _ = http_error_for_ocr(NoOcrBackendError("none", reasons=[]))
        assert code == 409

    def test_configured_failed_maps_502(self):
        from pipeline.ocr_backend import NoOcrBackendError, http_error_for_ocr

        code, detail = http_error_for_ocr(
            NoOcrBackendError("x", reasons=[("openrouter-vision", "failed: boom")])
        )
        assert code == 502
        assert "boom" in detail


class TestOcrBackendsConfig:
    """OCR_BACKENDS env parsing: comma string and JSON array forms."""

    def test_comma_string_split(self):
        from api.config import Settings

        s = Settings(ocr_backends="tesseract , openrouter-vision")
        assert s.ocr_backends == ["tesseract", "openrouter-vision"]

    def test_json_array_accepted(self):
        from api.config import Settings

        s = Settings(ocr_backends=["openrouter-vision", "tesseract"])
        assert s.ocr_backends == ["openrouter-vision", "tesseract"]

    def test_empty_string_yields_empty_list(self):
        from api.config import Settings

        s = Settings(ocr_backends="")
        assert s.ocr_backends == []

    def test_remote_defaults(self):
        from api.config import Settings

        s = Settings()
        assert s.openrouter_vision_model == "z-ai/glm-4.6v"
        assert s.ocr_remote_timeout_seconds == 300
        assert s.ocr_max_pages == 30
