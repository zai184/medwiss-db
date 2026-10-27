# PIPELINE MODULE

**Parent:** [../AGENTS.md](../AGENTS.md) | **App:** [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW
On-demand file content extraction for medical entries. Extraction (OCR for
image/PDF, direct read for text) runs **only when a user invokes it** — the
summarize ("Zusammenfassen") flow and the HTTP `/pipeline/process-file`
endpoint. **Never batch.** Files are indexed metadata-only at ingest; content
is extracted on demand. Audio transcription (whisper) was removed 2026-09-07:
audio files are link-only playable entries with no text extraction.

## STRUCTURE

```
pipeline/
├── orchestrator.py      # extract_text dispatch + summarize_file (on-demand)
├── ocr.py              # Tesseract OCR for images (one backend)
├── ocr_backend.py      # ordered-try seam over OCR backends (OCR_BACKENDS)
├── remote_ocr.py       # OpenRouter vision client (glm-4.6v)
├── batch_processor.py  # single-file process_file + calculate_file_hash only
└── prompts/
    └── summarize/      # Summarization skill prompts (studie, leitlinie, screenshot, standard)
```

## Responsibilities

| Task | Module | Notes |
|------|--------|-------|
| Image/PDF → Text | `ocr.py` (+ remote backends) | Tesseract local; OpenRouter glm-4.6v remote |
| Text file → Text | `orchestrator.extract_text` | direct read |
| File hashing | `batch_processor.calculate_file_hash` | SHA-256, used by sync/entry-service |

## CONVENTIONS

- **No batch processing.** There is no directory-scan / batch-OCR path.
  `BatchProcessor.process_file` is single-file only. Do not reintroduce
  `scan_directory`/`process_directory` or wire OCR into the watcher/timer.
- Extraction is on-demand: summarize flow and `/pipeline/process-file`.
  Ingest (`file_sync.ingest_file`) indexes extraction-dependent files
  metadata-only (empty `inhalt`).
- Backend order comes from `OCR_BACKENDS` (`tesseract`, `openrouter-vision`);
  empty list = OCR unavailable.
- No audio transcription (whisper removed). Audio files are link-only.
- File type detection by extension (.png, .jpg, .pdf, .txt)

## ANTI-PATTERNS

- **NEVER** add batch/loop processing over a directory of files
- **NEVER** trigger OCR from the watcher, startup reconcile, or a timer
- **NEVER** reintroduce whisper/audio transcription (removed 2026-09-07)
- **NEVER** modify source files - copy then process
