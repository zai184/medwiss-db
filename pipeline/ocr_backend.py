"""Ordered-try OCR backend seam (image/PDF → text), used on demand.

Extraction (summarize / /pipeline/process-file) resolves OCR_BACKENDS in
order and returns the first backend's non-empty text. Backends that are not
usable on this host (missing key/binary, file over a deterministic limit)
raise ``_BackendUnavailable`` and are skipped; runtime failures are recorded
and the next backend is tried. If no backend yields text, ``NoOcrBackendError``
is raised carrying per-backend reasons so callers can tell "not configured"
from "provider failed".

No batch/loop OCR lives here or anywhere: this seam is reachable only from
on-demand extraction paths.
"""

from __future__ import annotations

import logging
from pathlib import Path

from api.config import settings

logger = logging.getLogger(__name__)


class _BackendUnavailable(Exception):
    """Backend not usable on this host (missing key/dep) or the file exceeds
    a deterministic backend limit. Skip to the next configured backend."""


class NoOcrBackendError(RuntimeError):
    """No OCR backend produced text.

    ``reasons`` is a list of ``(backend, message)`` tuples covering both
    skipped (unavailable) and failed backends. Callers distinguish:
    - reasons empty and nothing configured  → 409-style "OCR not configured"
    - reasons present (backends configured but all failed) → 502/503.
    """

    def __init__(self, message: str, reasons: list[tuple[str, str]] | None = None):
        super().__init__(message)
        self.reasons = reasons or []


# Backend callables: `(Path) -> str`. Imported lazily inside each function so
# importing this module never pulls tesseract/httpx and there are no import
# cycles with pipeline.ocr / pipeline.remote_ocr.


def _tesseract_extract(path: Path) -> str:
    from pipeline.ocr import OCRDisabledError, extract_text_from_image

    try:
        return extract_text_from_image(path)
    except OCRDisabledError as e:
        # pytesseract/tesseract missing on this host -> try the next backend.
        raise _BackendUnavailable(str(e)) from e


def _openrouter_vision_extract(path: Path) -> str:
    from pipeline.remote_ocr import openrouter_vision_extract

    return openrouter_vision_extract(path)


_BACKENDS = {
    "tesseract": _tesseract_extract,
    "openrouter-vision": _openrouter_vision_extract,
}


def _run_one(path: Path, name: str, reasons: list[tuple[str, str]]) -> str | None:
    """Run a single OCR backend. Returns text, or None (recorded in reasons)."""
    fn = _BACKENDS.get(name)
    if fn is None:
        reasons.append((name, "unknown backend name"))
        return None
    try:
        text = fn(path)
        if text and text.strip():
            return text
        reasons.append((name, "returned empty text"))
    except _BackendUnavailable as e:
        reasons.append((name, f"unavailable: {e}"))
        logger.info(f"OCR backend {name} unavailable for {path}: {e}")
    except Exception as e:
        reasons.append((name, f"failed: {e}"))
        logger.warning(f"OCR backend {name} failed for {path}: {e}")
    return None


def extract_text_from_file(path: str | Path, backend: str | None = None) -> str:
    """OCR-extract text. With ``backend`` set, try only that one; otherwise
    walk ``OCR_BACKENDS`` in order and return the first non-empty result.

    Raises:
        NoOcrBackendError: if no backend is configured, the requested backend
            is unknown, or every backend failed/unavailable. ``.reasons``
            carries per-backend detail.
    """
    path = Path(path)
    configured = settings.ocr_backends
    names = [backend] if backend else configured
    if not names:
        raise NoOcrBackendError(
            "No OCR backend configured (OCR_BACKENDS empty) — OCR unavailable "
            "for image/PDF extraction.",
            reasons=[],
        )

    reasons: list[tuple[str, str]] = []
    for name in names:
        text = _run_one(path, name, reasons)
        if text:
            return text

    detail = "; ".join(f"{n}: {r}" for n, r in reasons)
    raise NoOcrBackendError(
        f"No OCR backend produced text for {path} ({detail})", reasons=reasons
    )


def http_error_for_ocr(e: NoOcrBackendError) -> tuple[int, str]:
    """Map an exhausted OCR seam to (HTTP status, detail).

    409 — nothing configured (OCR not set up on this host).
    502 — backends configured but all failed/unavailable (provider problem).
    """
    if not e.reasons:
        return (
            409,
            "OCR ist nicht konfiguriert (OCR_BACKENDS leer) - keine "
            "Textextraktion für Bilder/PDFs. / OCR not configured "
            "(OCR_BACKENDS empty) - image/PDF extraction unavailable.",
        )
    detail = ", ".join(r for _, r in e.reasons)
    return (
        502,
        "OCR-Backend(s) fehlgeschlagen. / OCR backend(s) failed: " + detail,
    )
