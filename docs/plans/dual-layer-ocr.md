# On-Demand OCR: Local Tesseract + OpenRouter Vision (glm-4.6v)

> **Status:** Revised after boss correction + provider decision | **Date:** 2026-09-07
> Supersedes earlier drafts that referenced GLM-OCR MaaS (Z.ai).

## Goal

Extract text from image/PDF files **only on demand** — inside the existing
**Zusammenfassen** (summarize) flow. **No batch OCR at ingest, no backfill, no
background extraction.** A file stays textless until a user opens it and hits
"Zusammenfassen"; then OCR runs once and the text feeds the summary.

Deploys:
- **tux**: local Tesseract **and** remote (OpenRouter glm-4.6v).
- **VPS (2 GB)**: remote only (OpenRouter glm-4.6v). No tesseract/poppler/whisper.

**Remote OCR uses the existing `OPENROUTER_API_KEY`** — no second provider, no
new secret. (GLM-OCR's dedicated `glm-ocr` layout_parsing endpoint is Z.ai-only
and was rejected: it needs a separate `ZAI_API_KEY` + resource package. glm-4.6v
on OpenRouter is the remote vision/OCR path.)

## Boss constraints (locked)

1. **OCR only inside Zusammenfassen.** No separate "extract text" action. No
   `inhalt` storage from OCR. No new write path.
2. **Never batch-process OCR.** Ingest/reconcile/watcher never OCRs
   extraction-dependent files — indexed metadata-only.
3. **No full backfill.**
4. Remote OCR is pay-per-call; on-demand keeps cost proportional to use.

## Problem

1. **Ingest auto-OCRs today** (`api/services/file_sync.py` `ingest_file` calls
   `process_file` on every new/modified file, from startup reconcile `api/main.py`,
   watcher upserts, and `POST /files/admin/sync`). Writes `extracted_text` into
   `inhalt` + embeds it when OCR was enabled. Boss wants the opposite.
2. **Only local engine existed**: `pipeline/ocr.py` (Tesseract). The UI's
   "Vision/OCR" model never received image bytes — summarize was text-in/text-out.
3. **VPS can't OCR**: no tesseract/poppler/whisper (2 GB, `h.strict`); files were
   link-only and unreadable on the box serving production.

## Architecture

```
User opens file-backed entry → clicks "Zusammenfassen"
   │
   ▼
POST /entries/{id}/summarize
   │
   ▼
orchestrator.summarize_file
   │  detect_file_type
   │  ├─ text   → direct read
   │  ├─ audio  → transcribe_audio (on-demand)
   │  └─ image/PDF → extract_text_from_file(path)   ◄── seam
   │        try each configured OCR_BACKENDS in order:
   │           tesseract (local)          — tux only
   │           openrouter-vision (glm-4.6v)— remote (OPENROUTER_API_KEY)
   ▼
LLM summarizes extracted text → returns {extracted_text, summary} to modal
```

The seam is reached **only** from the summarize path (and the single-file
`/pipeline/process-file`). Ingest never touches it.

## What changes

### 1. Stop auto-OCR at ingest (done)
`api/services/file_sync.py::ingest_file`: extraction-dependent suffixes
(PDF/image/audio/office) → `_link_only_index` (metadata-only, empty content);
text files (.md/.txt) keep direct read. Batch OCR machinery purged
(`run_pipeline.py` deleted; orchestrator `process_file`/`process_directory` and
batch_processor directory methods removed).

### 2. Remote-capable extraction seam (done)
`pipeline/orchestrator.py::extract_text` image branch → seam
`pipeline/ocr_backend.py::extract_text_from_file(path)`. Audio/text unchanged.

### 3. Config (done)
`api/config.py`: `ocr_backends` (ordered list, `NoDecode` + comma/JSON validator)
replaces `ocr_enabled`. New `openrouter_vision_model` (glm-4.6v),
`ocr_remote_timeout_seconds`, `ocr_max_pages`. Uses existing `openrouter_api_key`.

### 4. Remote client (done)
`pipeline/remote_ocr.py`: `openrouter_vision_extract` — glm-4.6v chat-completions
via OpenRouter; pymupdf page-raster **generator** (never materializes the list);
page cap `ocr_max_pages`; explicit httpx timeouts; retry only 429/5xx/connect;
401/403/413 immediate `_BackendUnavailable`.

### 5. Seam taxonomy (done)
`_BackendUnavailable` (skip→next) / runtime failure (record+continue) /
`NoOcrBackendError` at exhaustion with reasons. `http_error_for_ocr`: nothing
configured → 409; configured-but-failed → 502.

### 6. UI
No new route/action. `SummaryModal` (Zusammenfassen) is the on-demand surface.
Phase-1: model dropdown static; server selects OCR backend by `OCR_BACKENDS` order.

## Backends

| Backend | tux | VPS | Needs |
|---|---|---|---|
| `tesseract` (local) | **enabled** | absent | tesseract+poppler binaries |
| `openrouter-vision` (remote) | enabled | **enabled** | `OPENROUTER_API_KEY` + `OPENROUTER_VISION_MODEL` |
| `glmocr-selfhost` | phase-2 | — | GPU + vLLM serving GLM-OCR |
| `paddleocr` | phase-2 | — | paddle runtime |

- tux: `OCR_BACKENDS=tesseract,openrouter-vision`
- VPS: `OCR_BACKENDS=openrouter-vision`

## Env / deploy

- tux `.env`: `OCR_BACKENDS=tesseract,openrouter-vision`, `OPENROUTER_VISION_MODEL`.
  `OPENROUTER_API_KEY` from shell env.
- `modules/medwiss.nix`: `OCR_BACKENDS=openrouter-vision` (replaces `OCR_ENABLED=false`).
  sops env: `OPENROUTER_API_KEY` already present.

Because ingest never OCRs, no ingest-time key dependency — VPS boots and syncs the
whole corpus with or without the key; the key is needed only when a user summarizes.

## Tests (done)

- `tests/test_pipeline.py`: seam ordered-try (skip-on-unavailable,
  record-and-continue, exhaustion-with-reasons), unknown-backend warning,
  HTTP-mapping (409 unconfigured / 502 configured-failed), config validator
  (comma string, JSON array).
- `tests/test_ingest_ondemand.py`: extraction-dependent → metadata-only
  (`process_file` never runs); text files keep direct read; ingest succeeds with
  no OCR backend configured.

## Verification

- **tux ingest**: PDF added → entry with empty `inhalt`, no OCR, no remote call.
- **tux summarize on-demand**: image → text via tesseract; with
  `OCR_BACKENDS=openrouter-vision` first, via glm-4.6v.
- **Remote failure non-fatal**: no `OPENROUTER_API_KEY` → ingest still indexes
  metadata-only; only an explicit summarize errors cleanly.
- **VPS**: `systemctl restart medwiss-api`; sync → all metadata-only, zero remote
  calls; summarize one PDF → text + summary (was link-only + 409).
- **Regression**: full `pytest` + `bun run check`.

## Estimated LOC

~575 net across: seam (~90), remote client (~200), config validator + settings
(~25), orchestrator/file_sync rewire (~65), tests (~180), envs + docs (~35).
Plus the batch purge (−691 in code).

## Risks / Notes

- **Empty `inhalt` for extraction-dependent files**: search won't index text
  inside image/PDFs unless a user has summarized them (summary → `zusammenfassung`
  only if adopted). Accepted — on-demand tradeoff.
- **glm-4.6v vs dedicated OCR**: glm-4.6v is a general vision model, not a
  layout/table parser like GLM-OCR. Acceptable for text-heavy medical screenshots
  and pages; tables/formulas are weaker. If that later matters, phase-2
  `glmocr-selfhost` (tux GPU) or PaddleOCR are the upgrade paths — both local.
- **`OCR_ENABLED` removed**; batch machinery purged; docs reflect the no-batch,
  on-demand-only model.
