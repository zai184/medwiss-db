## [Unreleased] - 2026-10-21 11-45
### Added
- **Medical disclaimers** (review request 2026-10-21): README gains a proper
  "Medical Disclaimer" section (educational-only, verify vs current guidelines,
  112/144 emergency notice, AGPL §15 no-warranty, MDR 2017/745 Art. 2
  not-a-device note); global footer line in `+layout.svelte`; red
  `role="alert"` warning banner on the Notfall page (learning-reference,
  not emergency management, 112/144). svelte-check: 0 errors.

LOC added: ~60 | LOC removed: 1 | LOC total: ~98,480

## [Unreleased] - 2026-10-21 11-15
### Fixed
- **Favicon copyright**: the old `favicon.png` was derived from the copyrighted
  `oip.jpg` (removed 2026-10-21). Replaced with a clean hand-drawn
  `ui/static/favicon.svg` (rod + serpent, no third-party source); 64×64 PNG
  fallback regenerated from the SVG via magick; `app.html` links SVG first,
  PNG fallback via `alternate icon`.

LOC added: 12 | LOC removed: 2 | LOC total: ~98,420

## [Unreleased] - 2026-10-20 12-10
### Added
- **Pre-push guard** (`.private/githooks/pre-push`, wired via
  `core.hooksPath`): GitHub only ever receives `refs/heads/main`, and only
  commits whose diff is free of the VPS tokens extracted from
  `.private/deploy.env`/`infra.md`. Verified: archive push blocked, leak-test
  commit blocked, clean main push passes. Hook is local-only and never pushed.

LOC added: ~45 | LOC removed: 0 | LOC total: ~98,405

## [Unreleased] - 2026-10-20 11-40
### Changed
- **Published to GitHub** (`github.com/zai184/medwiss-db`, AGPL-3.0, public).
  Public `main` is a fresh single-commit squash of the former 96-commit
  history: that history contained VPS username/WireGuard IP/SSH port and the
  2026-09-24 audit report (all scrubbed from the tree on 2026-10-15, but
  alive in old commits). Topology since then: local `main` = public history →
  `origin` (GitHub); branch `archive` = full old history → `backup` (NAS).
  Old semver tags exist only on `archive`/NAS — never push them to GitHub.
  `.codegraph/` untracked + gitignored.

LOC added: 10 | LOC removed: 0 | LOC total: ~98,360

## [Unreleased] - 2026-10-15 23-28
### Fixed
- **`scripts/deploy-vps.sh` copies `uv.lock` and runs `uv sync --frozen`**
  before restart. The 23:21 deploy restarted the API onto code that imports
  `defusedxml` without installing it, so `medwiss-api` crash-looped until
  the lock was synced by hand.

LOC added: ~6 | LOC removed: 0 | LOC total: ~98,350

## [Unreleased] - 2026-10-15 23-50
### Removed
- **`docs/audits/`** — the 2026-09-24 security audit. The fixes stay in the
  code. The directory is gitignored.

LOC added: 0 | LOC removed: ~the audit | LOC total: ~98,350

## [Unreleased] - 2026-10-15 23-40
### Removed
- **`.sisyphus/`** — agent plans, notepads, and screenshots. The directory
  is gitignored. `AGENTS.md` now points at `docs/plans/`.

LOC added: ~5 | LOC removed: ~the .sisyphus tree | LOC total: ~98,350

## [Unreleased] - 2026-10-15 23-15
### Changed
- **Deploy target left the tracked tree.** `scripts/deploy-vps.sh` reads
  `MEDWISS_DEPLOY_HOST` and `MEDWISS_DEPLOY_PORT` from gitignored
  `.private/deploy.env`. Host, SSH user, WireGuard address, and home paths
  moved to `.private/infra.md`. Tracked docs name the variables.

LOC added: ~45 | LOC removed: ~20 | LOC total: ~98,350

## [Unreleased] - 2026-10-15 17-05
### Fixed
- **svelte-check warnings 32 → 1** —
  - Real staleness bugs: entry detail + edit pages kept the old entry's form
    data on same-route navigation (`/entry/3` → `/entry/7`) because
    `const entry = data.entry` / `$state(data.…)` snapshot once. Detail page now
    `$derived(data.entry)` with an optimistic `inhaltOverride` (reset via
    `$effect` on entry change); edit page re-snapshots all 16 form fields via
    `formSnapshot(data)` in an entry-id-keyed `$effect`.
  - A11y: FileUpload label associated with its file input (module counter id);
    MultiSelect combobox gets `aria-controls` → listbox id; SearchResults
    result card `article role="button"` → `div role="button"`.
  - Dead CSS deleted: `.subtitle` (eingabe), `.classification-group`/
    `.group-label` (entry detail), `.suggestion-chip.unresolved`, `.fach-search`,
    `.hierarchy-chips/-chip`, `.tag-grid`/`.tag-button*` (edit page — 9 rules).
  - False-positive "unused" selectors fixed instead: KIPreview status icons are
    injected via `{@html}` and bibliothek row icons are lucide class
    passthroughs — scoped CSS never reached them; now `:global()` so spin
    animation + colors actually apply.
  - StatCard: `$derived(colorClasses[color])`, deprecated `<svelte:component>`
    replaced by capitalized dynamic component.
  - Remaining 1 warning is a deliberate initial form snapshot (see above).

LOC added: 95 | LOC removed: 122 | LOC total: ~98,328

## [Unreleased] - 2026-10-15 16-05
### Fixed
- **Security audit findings cleared (docs/audits/security-audit-2026-09-24.md)** —
  all remaining findings fixed ahead of open-sourcing:
  - Stored XSS (High): see 14-57 entry below; highlight logic now shared in
    `ui/src/lib/highlight.ts` (`highlightTerms`) used by SearchResults +
    ChunkResults, with `ui/src/lib/highlight.test.ts` as the regression test
    (audit asked for a test runner: `bun test`, script added to `ui/package.json`,
    `bun-types` for tsconfig).
  - Pillow 12.2.0 → 12.3.0, starlette 1.0.0 → 1.8.0, python-multipart 0.0.32,
    anyio 4.14.2, idna 3.20, pydantic-settings 2.16.0, mako 1.4.3, click 8.5.0
    (all audit-flagged advisories).
  - `requirements.txt` deleted (pinned Pillow 10.4.0, 17 advisories, contradicted
    uv.lock) — `uv.lock`/`pyproject.toml` are the only dependency source;
    QUICKSTART.md + AGENTS.md updated.
  - `start.sh` dev API binds `127.0.0.1` instead of `0.0.0.0` (auth-less app,
    loopback only).
  - File-serving allowlist (`api/routers/files.py` `_is_path_allowed`,
    `_is_awmf_path_allowed`) uses `Path.is_relative_to` containment instead of
    `startswith` — sibling dirs sharing the prefix are rejected; accepts str
    input deny-safe.
  - PubMed XML parsed with `defusedxml` instead of stdlib `ElementTree`.
  - README warning block (no auth / trusted network only, corpus not included,
  requirements) replaces the stale admin/admin123 credentials section.

LOC added: 118 | LOC removed: 61 | LOC total: ~98,355

## [Unreleased] - 2026-10-15 14-57

## [Unreleased] - 2026-10-15 14-45
### Fixed
- **PDF viewer works on tablets (pdf.js)** — the FileViewer rendered PDFs in a
  plain `<iframe>`, which mobile browsers refuse (Android Chrome/Firefox render
  no PDFs in iframes; iPad Safari only the first page). Replaced with
  `pdfjs-dist` (lazy-loaded, ~1.3 MB worker chunk only on first PDF) drawing
  pages to canvases in a scrollable column: width-fit, DPR capped at 2 with a
  16M-pixel iOS guard, progressive page rendering, ResizeObserver re-render on
  fullscreen/rotation, task teardown on entry switch/unmount, password/failure
  error state with "Im Tab öffnen" fallback. `app.d.ts` gained the `vite/client`
  reference for `?url` worker imports.
- **FileViewer action bar moved to top** — the file-type info + Herunterladen +
  Transkribieren bar sat below the preview; it now renders above it (margin-bottom
  spacing), so the buttons are visible without scrolling past tall previews.

LOC added: 281 | LOC removed: 54 | LOC total: ~98,280

## [Unreleased] - 2026-10-09 16-46
### Fixed
- **Mobile: Leitlinien link + pagination overflow** — the Leitlinien nav item
  carried `mobile-hidden`, a leftover from when chunk search was broken on the
  VPS; removed, so it now shows in the mobile nav (page works via
  `CHUNK_SEARCH_MODE=keyword`). The numbered page-link rows in
  `SearchResults.svelte` and `ChunkResults.svelte` were nowrap flex rows
  (~350 px of fixed-width buttons) and overflowed narrow screens; both now
  `flex-wrap: wrap`.

LOC added: 3 | LOC removed: 1 | LOC total: ~98,050

## [Unreleased] - 2026-10-08 10-00
### Removed
- **`CLA.md`** — licensing matches Odysseus: AGPL-3.0 only, no contributor
  agreement. `CONTRIBUTING.md` no longer asks for a signature.

LOC added: 0 | LOC removed: ~45 | LOC total: ~98,050

## [Unreleased] - 2026-10-08 09-40
### Added
- **`CLA.md` and `CONTRIBUTING.md`** — outside patches need a contributor
  license agreement before merge. The grant lets the copyright holder
  sublicense those patches, including under proprietary terms. The public
  tree stays AGPL-3.0. Governing law and the Holder's legal name are still
  placeholders.

LOC added: ~55 | LOC removed: 0 | LOC total: ~98,100

## [Unreleased] - 2026-10-08 09-45
### Changed
- **Project description** — docs now say the source folders are the library and
  PostgreSQL is the index (`knowledge_entries`, tags, Leitlinien `chunks`).
  Rechner and Notfall stay frontend-only. Updated README, AGENTS.md,
  `database/AGENTS.md`, and `pyproject.toml`.

LOC added: 0 | LOC removed: 0 | LOC total: ~98,050

## [Unreleased] - 2026-10-08 09-31
### Added
- **AGPL-3.0** — `LICENSE` plus a README license section. The application may be
  reused and shared; a closed product built from it is not allowed. The medical
  corpus stays out of the repository.

LOC added: ~650 | LOC removed: ~1 | LOC total: ~98,050

## [Unreleased] - 2026-09-25 11-45
### Removed
- **Entry detail Löschen** — the button deleted only the database row, and the
  next file scan put the entry back. Rename and delete stay in the file manager.

LOC added: 0 | LOC removed: ~55 | LOC total: ~97,350

## [Unreleased] - 2026-09-25 12-00
### Changed
- **FileViewer audio** — replaced the native 500px `<audio controls>` strip
  with a full-width seek bar, current/total time, ±20 s (`<<` / `>>`), and 1×–2× speed.
  Long recordings can be scrubbed by dragging the bar.

LOC added: ~207 | LOC removed: ~10 | LOC total: ~97,400

## [Unreleased] - 2026-09-24 21-57
### Added
- **`docs/audits/security-audit-2026-09-24.md`** — Tier 2 security audit (upgraded
  `sec-codebase-security-audit` skill, post-verdict-discipline change): 1 Confirmed High
  (stored XSS in `SearchResults.svelte` / `ChunkResults.svelte` — DB text unescaped into
  `{@html}` via `highlightText` / `highlight` / `snippet`), 2 Needs-validation (Pillow
  12.2.0 decode-path reachability; `start.sh` binds `0.0.0.0` for the auth-less API),
  4 Informational, 10 Rejected. No code changed — report only. AGENTS.md points at the
  audit directory.

LOC added: ~95 | LOC removed: 0 | LOC total: ~97,199

## [Unreleased] - 2026-09-18 14-55
### Fixed
- **Duplicate `entry_ordner_label` INSERT on file update** (VPS reconcile
  error): the HIERARCHY proposal guards in `TaggingService.apply_proposals`
  compared stored hierarchy/label names case-sensitively while
  `resolve_ordner_label` resolves case-insensitively — a humanized
  case-variant (stored `notfall`, proposed `Notfall`) passed both guards and
  re-INSERTed an existing junction row (PK violation, file left stale).
  Guards are now case-insensitive. Regression test added; also fixed a
  pre-existing broken monkeypatch path in
  `test_extract_tag_suggestions_delegates_to_tagging_service`.

LOC added: ~55 | LOC removed: ~4 | LOC total: ~97,104

## [Unreleased] - 2026-09-18 13-15
### Added
- **Source folder "Fortbildungen"** (Bibliothek): added `Fortbildungen/`
  (Amboss, Cases+Clues, FOMF, GiDi, Medbee, Podcasts) as source #11 in
  `config/sources.yaml` — category `fortbildung`, default Fachgebiet
  Allgemeinmedizin, file types incl. audio (link-only playable). The
  discovery whitelist (`config/discover_sources.py`) only knew singular
  `Fortbildung`, so the YAML entry is the seam; `load_sources()` re-reads
  it per call — no restart needed, startup reconcile / manual sync ingest.

LOC added: ~19 | LOC removed: 0 | LOC total: ~97,049

## [Unreleased] - 2026-09-10 20-40
### Changed
- **Favicon**: replaced the old favicon.svg with the Rod-of-Asclepius image
  (oip.jpg) — converted to a 64×64 PNG centered on a round white disc with
  transparent corners (`ui/static/favicon.png`); `app.html` icon link now
  points at it.

LOC added: ~5 | LOC removed: ~2 | LOC total: ~97,030
## [Unreleased] - 2026-09-08 23-05
### Fixed
- **pymupdf missing from pyproject/uv.lock** (VPS deploy bug): remote PDF OCR
  crashed with `No module named 'fitz'` on the VPS — the deploy installs via
  `uv sync --frozen` (uv.lock), but pymupdf had only been added to
  requirements.txt. Bumped to 1.28.2 in all three manifests (1.24.10 has no
  cp313 wheel; VPS runs Python 3.13).

LOC added: ~45 | LOC removed: ~1 | LOC total: ~97,025
## [Unreleased] - 2026-09-07 21-40
### Changed
- **Transkribieren: OCR-Motor-Auswahl**: `POST /entries/{id}/transcribe` accepts
  an optional `backend` body field (`tesseract` | `openrouter-vision` | null).
  null = run the configured `OCR_BACKENDS` seam in order (Auto). The seam's
  `extract_text_from_file(path, backend=...)` runs a forced backend alone;
  `TranscribeModal` now shows a Motor dropdown (Automatisch / Tesseract lokal /
  glm-4.6v OpenRouter) and starts on a Transkribieren button press (no longer
  auto-runs on open, so the choice applies). New `TranscribeRequest` model.
  Tests: forced-backend + unknown-backend seam cases added.

LOC added: ~226 | LOC removed: ~44 | LOC total: ~96,981
## [Unreleased] - 2026-09-07 18-10
### Changed
- **FileViewer "Zusammenfassen" → "Transkribieren" (OCR only)**: the button
  (entry detail + gallery overlay) now opens `TranscribeModal`, which runs a
  new `POST /entries/{id}/transcribe` endpoint — pure on-demand OCR text
  extraction (image/PDF via the OCR_BACKENDS seam, direct read for text), no
  LLM. Raw text shown for viewing/copying; nothing written to the entry.
### Removed
- **LLM summarize UI** (backend kept API-only): deleted `SummaryModal.svelte`,
  `ModelSelector.svelte`, `SkillSelector.svelte`, `pendingSummary.ts` store +
  its edit-page adoption flow, and `summarizeApi` from `api.ts`. The
  `/entries/{id}/summarize` endpoint and skill prompts remain API-callable.

LOC added: ~120 | LOC removed: ~680 | LOC total: ~96,799
## [Unreleased] - 2026-09-07 17-40
### Removed
- **Audio transcription (whisper) purged** — not needed. Deleted
  `pipeline/transcription.py` + `pipeline/test_transcription.py`; removed the
  `transcribe_audio` import and audio branch from `pipeline/orchestrator.py`
  (audio type now raises a clean "not supported" ValueError). Audio files
  remain in the library as **link-only playable entries** (native `<audio>`
  player) — no text extraction. `.env` `WHISPER_MODEL_PATH`, AGENTS
  transcription rows/flow diagram, and router docstrings updated.

LOC added: ~49 | LOC removed: ~950 | LOC total: ~97,240

## [Unreleased] - 2026-09-07 17-00
### Added
- **On-demand OCR backend seam (OpenRouter-only remote):** a prototype `glmocr-maas`
  (Z.ai layout_parsing) backend was built then **removed** — glm-ocr is not on
  OpenRouter and would need a separate `ZAI_API_KEY` + resource package.
  Remote OCR uses `openrouter-vision` (glm-4.6v) with the existing
  `OPENROUTER_API_KEY`; no second provider/key. Config fields
  `zai_api_key`/`glm_ocr_api_url` dropped.
- **On-demand OCR backend seam** (`pipeline/ocr_backend.py`): ordered-try over
  `OCR_BACKENDS` (comma list). Three-signal taxonomy — `_BackendUnavailable`
  (skip → next) / runtime failure (record + continue) / `NoOcrBackendError` at
  exhaustion carrying per-backend reasons. `http_error_for_ocr` maps: nothing
  configured → 409; configured-but-failed → 502.
- **Remote OCR client** (`pipeline/remote_ocr.py`): `openrouter-vision`
  (glm-4.6v via the existing `OPENROUTER_API_KEY`; pymupdf page-raster
  generator, no list materialization, page cap). Explicit httpx timeouts;
  retry only 429/5xx/connect with backoff; 401/403/413 immediate unavailable.
  (A `glmocr-maas`/Z.ai layout_parsing backend was prototyped then removed —
  glm-ocr is not on OpenRouter and would need a separate `ZAI_API_KEY`.)
- **Config** (`api/config.py`): `ocr_backends` replaces `ocr_enabled`
  (`NoDecode` + validator accepts comma string / JSON array); new
  `openrouter_vision_model`, `ocr_remote_timeout_seconds`, `ocr_max_pages`.
- **Ingest is metadata-only for extraction-dependent files** (`file_sync.py`):
  PDF/image/audio/office files are link-only indexed (empty content) at
  reconcile/watcher/sync — OCR/whisper runs only on demand. Text files
  (.md/.txt) keep direct read.
- `pymupdf` dependency (pure wheel, no poppler) for remote PDF raster/count.
- Tests: seam ordered-try + HTTP mapping, config validator forms, ingest
  routing regression (`tests/test_pipeline.py`, `tests/test_ingest_ondemand.py`).

LOC added: ~360 | LOC removed: ~1,100 | LOC total: ~98,137

## [Unreleased] - 2026-09-07 16-20
### Removed
- **Batch OCR / directory processing purged (OCR is on-demand only):**
  deleted `scripts/run_pipeline.py` (CLI, no importers, unwired); removed
  `pipeline/orchestrator.py` `process_file`/`_save_result`/`process_directory`;
  stripped `pipeline/batch_processor.py` to single-file `process_file` +
  `calculate_file_hash` only (removed `FileScanResult`, `BatchProcessingResult`,
  `scan_directory`, `process_directory`, async/parallel variants). Enforces the
  no-batch decision: no directory-scan/loop OCR path exists; ingest stays
  metadata-only. `pipeline/AGENTS.md` updated with the no-batch rule.
  Plan: `docs/plans/dual-layer-ocr.md`.

LOC added: ~40 | LOC removed: ~691 | LOC total: ~97,239

## [Unreleased] - 2026-09-07 16-00
### Fixed
- **Gallery ‹/› buttons now show inside fullscreen** (image + PDF): they were
  rendered in the viewer overlay, outside the fullscreen element — invisible in
  native fullscreen where only the element's subtree displays. Navigation moved
  into FileViewer, rendered inside `.image-scroll`/`.pdf-container`, visible in
  preview and fullscreen, edge-gated, stopPropagation so a nav click/Enter does
  not toggle fullscreen. Overlay's own buttons removed.

LOC added: ~70 | LOC removed: ~30 | LOC total: ~97,890

## [Unreleased] - 2026-09-07 15-20
### Fixed
- **Gallery swipe now works inside image fullscreen** (was preview-only):
  mobile browsers fire `pointercancel` instead of `pointerup` when they claim
  the touch as a scroll/gesture inside the fullscreen scroll container — the
  viewer overlay now treats `pointercancel` (with its final coordinates) as a
  swipe end too.
  **Fullscreen no longer exits on swipe**: the gallery remounted FileViewer
  per step (`{#key active.entry.id}`), destroying the fullscreen element;
  FileViewer now reloads reactively on `entryId` (keeps current content
  visible while the next image loads, resets zoom). EntryViewerOverlay dropped
  the `{#key}`.
  A drag/swipe no longer synthesizes a click that toggled fullscreen
  (movement > 10 px suppresses the fullscreen-toggle click); also fixes
  drag-pan while zoomed (delta was computed against an already-updated
  `lastX` — always 0).

LOC added: ~54 | LOC removed: ~8 | LOC total: ~97,850

## [Unreleased] - 2026-09-07 13-40
### Changed
- **ModelSelector: GLM 4.6V added** (`openrouter/z-ai/glm-4.6v`, vision/OCR, $0.30/$0.90
  per Mtok). GLM-OCR and PaddleOCR-VL-1.5 are NOT on OpenRouter (checked live
  `/api/v1/models`) — glm-4.6v is the closest selectable vision/OCR model there.

LOC added: ~10 | LOC removed: ~4 | LOC total: ~97,800

## [Unreleased] - 2026-09-07 13-05
### Removed
- **LLM classification pipeline removed** (deterministic regex classification and
  folder-derived tags stay): deleted `api/classifier.py` (BaseClassifier,
  LlamaserverClassifier, OpenRouterClassifier, `OPENROUTER_MODELS`),
  `pipeline/classifier.py`, `pipeline/prompts/classification.txt`;
  `POST /entries/{id}/classify` endpoint + `EntryService.classify_entry` +
  `ClassifyEntryRequest/Response`/`ClassificationResult`/`DiagnoseExtraction` models;
  classification step in `pipeline/orchestrator.process_file`,
  `batch_processor` and `process_directory` (`run_classification` flags);
  `/pipeline/process-file` is extraction-only (no `provider`/`model` form fields,
  `PipelineResult` lost `classification`/`model_used`);
  `file_sync` ingest titles from filename, tags from `source.default_fachgebiete` only;
  `TaggingService.LLMClassificationStrategy` + `apply_llm_classification` removed.
### Changed
- **Summarize decoupled from the classifier**: `pipeline/orchestrator._call_llm`
  calls Llamaserver/OpenRouter directly (OpenAI-compatible), Llamaserver→DeepSeek
  fallback kept. `openrouter_default_model` default now `deepseek/deepseek-v4-flash`.
- **ModelSelector**: Qwen 3.5 9B (lokal), DeepSeek V4 Flash, GLM 5.3 Flash
  (`z-ai/glm-5.3-flash`) via OpenRouter — Kimi/Grok entries dropped, list now matches
  backend defaults.
- **KI-Upload (Eingabe)**: no model selector, no LLM tag autofill — extraction
  preview + "Übernehmen" fills content only. Edit page: "KI vorschlagen" button removed.
- OpenAPI contract + `ui/src/lib/api-types.d.ts` regenerated (`./scripts/gen-api.sh`).

LOC added: ~230 | LOC removed: ~1,870 | LOC total: ~97,800

## [Unreleased] - 2026-09-06 21-38
### Added
- **Links (Referenz) mobile overflow fixed**: long link labels no longer force the row wider than the card (`flex-shrink: 0` removed; label now ellipsizes, domain fixed-shrink) — the page fits the screen width on mobile.
- **Gallery navigation works inside image fullscreen**: the ‹/› arrows now float above the CSS-fullscreen image (z-index above the fullscreen layer) and swipe still works; in native fullscreen, ←/→ keys and swipe navigate. EntryViewerOverlay dialog got `tabindex="-1"` (a11y warning cleared).
- **Deprecated `<svelte:component>` removed in FileViewer** — type icon is now a `$derived` component (`TypeIcon`).
- **SummaryModal unused-CSS warnings fixed**: status/button icons wrapped in spans carrying the classes, so the scoped `.title-icon`/`.btn-icon` styles actually apply.
- **Gallery view in the browse viewer**: clicking a file-backed entry in Suche, Bibliothek (incl. search matches) or Dashboard activity now opens the fullscreen EntryViewerOverlay as a swipeable gallery of that list's file-backed entries — touch swipe (skipped while zoomed via `data-zoomed` guard on FileViewer's image container), ‹/› overlay arrows, ←/→ keys, "n / total" counter in the header; PDFs swipe too. Single-result lists keep the plain viewer.

LOC added: ~100 | LOC removed: ~16 | LOC total: ~99,150

## [Unreleased] - 2026-09-04 15-54
### Changed
- **FileViewer mobile image scroll**: while unzoomed the image uses `touch-action: pan-y` and skips pointer capture, so tall images scroll natively by touch (inline preview + fullscreen); pinch-zoom still works; zoomed drag-pan and desktop wheel unchanged.
- **FileViewer fullscreen close is now a plain black X** (white pill background/border removed; lucide X only).
- **Browse preview popup header keeps only title + ×** — the "Detail" link was removed (EntryViewerOverlay).
- **Mobile file actions**: Herunterladen + Zusammenfassen now sit side-by-side on one line, each narrower, labels centered and not wrapping (file-info above on its own row).
- **Suche mobile filter overlay got a close (×) button** (top-right above the facet card).
- **Referenz page subtitle removed** — "Nützliche Links und Ressourcen — live geladen aus medlinks.txt" (header keeps title + reload button). [This was the text the boss called out; it lived on the Referenz page, not Suche.]
- **Bibliothek root tiles are squares with centered content** (`aspect-ratio: 1/1`, square corners); recolor: Notfall red, Red Flags orange, Fächer blue, Fragebögen yellow; folder-name matching normalized (numeric prefix/underscores/diacritics/ae-oe-ue).
- **Notfall "SOPs" and "SOPs Notaufnahme" tabs group rows under themed headings** (Reanimation & Kreislaufstillstand, Rhythmusstörungen & Elektrolyte, Kinder & Neugeborene, Kardiologie & Kreislauf, Lunge & Atemwege, Niere & Elektrolyte …) via new `ui/src/lib/notfallGroups.ts` (keyword rules, fallback "Weitere", nothing dropped, no group duplication). Algorithmen tab stays flat.

LOC added: ~456 | LOC removed: ~47 | LOC total: ~99,050


## [Unreleased] - 2026-09-03 21-55
### Fixed
- **Suche filter checkboxes show a checkmark** when selected (drawn tick in
  a 16px box; native input + preventDefault never painted the tick).

LOC added: ~25 | LOC removed: ~12 | LOC total: ~98,640


## [Unreleased] - 2026-09-03 21-25
### Fixed
- **Suche hung / CPU pegged, no results**: keyword search ran a correlated
  `EXISTS (chunks.text ILIKE …)` per entry against ~594k AWMF chunks — and
  with an empty query (filters only) the pattern was `%%`, so every chunk
  matched. Removed chunks from keyword search. Folders / filenames / entry
  text still match. PDF passages stay on Leitlinien (`/search/chunks`).
- Filter box sits **under the search bar**, left of the results.

LOC added: ~30 | LOC removed: ~45 | LOC total: ~98,625


## [Unreleased] - 2026-09-03 21-10
### Fixed
- **Suche filters apply on checkbox click** (not only "Filter anwenden");
  send lookup id when present; ignore stale in-flight listing so the
  unfiltered onMount fetch cannot overwrite a filtered result.
- **Filter box is a left sidebar** of the Suche page (280px sticky column,
  search + results on the right, page width 1400px). Mobile: Filter overlay.

LOC added: ~40 | LOC removed: ~20 | LOC total: ~98,640


## [Unreleased] - 2026-09-03 21-00
### Changed
- **Suche filters are a collapsible accordion again**: Fachgebiete / Diagnosen
  / Symptome / Dokumenttyp / Ordner-Labels / Ordner start collapsed (chevron
  tree), checkboxes inside a 220px scroll box, badge + Zurücksetzen +
  "Filter anwenden". The open 100s-long button list is gone.

LOC added: ~120 | LOC removed: ~80 | LOC total: ~98,620


## [Unreleased] - 2026-09-03 20-45
### Fixed
- **Suche restored to pre-simplification layout** (keyword + filters only):
  sticky 280px filter sidebar, mobile Filter toggle overlay, facet options
  loaded on mount. No FTS/hybrid/AI tabs.
- **Fachgebiet + Dokumenttyp filters actually applied**: the `/search` router
  accepted the query params but never passed them into `search_keyword`.
- **Keyword search PDF/chunk matching** was added here, then **removed**
  2026-09-03 21-25 (594k-row ILIKE EXISTS pegged CPU). Do not reintroduce.

LOC added: ~90 | LOC removed: ~25 | LOC total: ~98,580


## [Unreleased] - 2026-09-03 20-21
### Fixed
- **Suche search bar CSS restored**: adding the facet sidebar (2026-09-01)
  replaced `.search-input-wrapper` / `.search-input-container` with the
  layout grid and left the bar unstyled (no flex row, no border, history
  dropdown not positioned). Restored the original input styles; placeholder
  back. Filter chips stay removed (intentional revert 2026-09-03 14-22).

LOC added: ~15 | LOC removed: 0 | LOC total: ~98,515


## [Unreleased] - 2026-09-03 18-30
### Changed
- **FileViewer PDF fullscreen toggle**: the Maximize button no longer overlays the PDF
  (where it fought the page background). It now sits right-aligned in a slim `.pdf-toolbar`
  above the preview, shown only when not fullscreen; the × close remains the white overlay
  inside the fullscreen `.pdf-container`. Icon-only (title tooltip "Vollbild").
- **FileViewer fullscreen image centered on both axes**: `margin: 0 auto` → `margin: auto`
  (flex auto-margins) — vertical + horizontal centering; tall images still scroll from the
  top rather than clipping.
- Closed the previously-implicit `</audio>` (real DOM hazard, compiler warning).

LOC added: ~41 | LOC removed: ~29 | LOC total: ~98,500


## [Unreleased] - 2026-09-03 18-19
### Changed
- **In-app fullscreen viewer for file-backed entries** (Bibliothek, Suche, Dashboard
  Aktivität): clicking a PDF — or any entry with a source file — opens a fullscreen
  overlay (dark scrim, centered panel, title + × close), rendered once in the root
  layout, instead of routing to the item page. New `EntryViewerOverlay.svelte` +
  `stores/entryViewer.ts` (open/close + `openBrowseEntry` helper: file-backed →
  overlay, file-less → `/entry/{id}`). Markdown renders sanitized; PDFs embed
  same-origin with a native-fullscreen Maximize button; images/audio/text handled.
  Esc / × / backdrop close; header "Detail" link reaches the item page; auto-closes on
  navigation. Wired into `SearchResults.svelte` (Suche), `bibliothek/+page.svelte`,
  and `ActivityList.svelte` (Dashboard "Aktuelle Aktivität" — its row link pointed at a
  non-existent `/entries/{id}`; now opens the viewer or the correct `/entry/{id}`).
- **Notfall page uses the same fullscreen overlay model**: clicking a row opens the doc
  fullscreen in-app (markdown rendered, PDF embed fullscreen) instead of the prior
  new-tab direct-file link.
- **FileViewer PDF native fullscreen**: PDF iframe wrapped in a `.pdf-container` with a
  Maximize button (native `requestFullscreen`, CSS-overlay fallback), mirroring the
  existing image fullscreen; `fullscreen-close` button in fullscreen mode.

LOC added: ~400 | LOC removed: ~26 | LOC total: ~98,500


## [Unreleased] - 2026-09-03 17-20
### Changed
- Notfall: rows are now a single link that opens the source file directly
  fullscreen in a new tab (`/api/v1/files/entries/{id}/view`, `target=_blank`)
  — inline accordion previewer (expandedId, markdown render / PDF iframe /
  inline image) and its now-dead script + CSS removed.

LOC added: ~6 | LOC removed: ~129 | LOC total: ~98,100


## [Unreleased] - 2026-09-03 16-18
### Changed
- Notfall: tab "Notfall-SOPs" renamed to "SOPs"; subtitle replaced with
  external guideline links (ERC / GRC / ARC).
- TODO.md: added the open tux<->VPS bidirectional-sync decision (Syncthing A
  vs Unison C; proposal in docs/plans/bidirectional-corpus-sync.md).

LOC added: ~20 | LOC removed: ~2 | LOC total: ~98,200

## [Unreleased] - 2026-09-03 14-37
### Changed
- PubMed abstracts: German section labels added (Hintergrund, Patienten und
  Methodik, Ergebnisse, Schlussfolgerungen, …) plus "Purpose of review" /
  "Key messages"; "Patients" removed as a split label (false positives).
- Notfall: tab order is now Algorithmen · Notfall-SOPs · SOPs Notaufnahme;
  expanding a row previews the file inline (PDF in an embedded viewer,
  images inline) instead of only markdown.

LOC added: ~30 | LOC removed: ~5 | LOC total: ~98,200


## [Unreleased] - 2026-09-03 14-22
### Added
**Notfall page rework** — Algorithmen content now lives as md docs in the corpus
(`2_Notfall/00_Notfall_SOPs/`, 8 files, watcher-ingested); `/notfall` lists
DB entries in three tabs (Algorithmen / SOPs Notaufnahme / Notfall-SOPs) with
inline rendered-markdown accordion (no navigation), filter box, and direct
file-open links. Hardcoded `notfall.ts` removed.
**`GET /api/v1/entries?source_path=`** — escaped substring filter for
path-scoped listing (backend + api client).
**MD write-through** (opt-in): `FILE_WRITEBACK_ENABLED=true` makes entry
edits write `.md`/`.txt`/`.rst` back to the source file — atomic write,
optimistic lock (file changed on disk → error), new hash stamped on the
entry so reconcile never re-ingests. Off by default. Tests in
`tests/test_write_through.py`.
**Chunk search fallback** — embed mode degrades to keyword search
(tsvector) when the sidecar is down instead of 503; docstring documents the
one-time `search_vector` population SQL.

### Fixed
- Suche page reverted to the original working version (filter chips
  removed); backend trigram typo tolerance kept.
- Mobile menubar pinned to the exact viewport width (`left/right: 0`,
  `box-sizing: border-box`); items share the full width.
- Entry preview full-bleed on mobile (breaks out of side paddings).
- Entry page widened 1000 → 1400px (all previews get more room).
- Mobile image viewing: tap opens fullscreen (CSS fallback for iOS),
  pinch-zoom 1–8×, drag pans, double-tap resets, close button.
- PubMed: 20 results per page, capped at the top 100; abstracts render as
  labeled sections like PubMed's original display.

LOC added: ~350 | LOC removed: ~90 | LOC total: ~98,100


## [Unreleased] - 2026-09-03 12-17
### Added
**DeepSeek V4 Flash fallback LLM via OpenRouter (summarize + chunk RAG)**:
- `api/config.py`: `OPENROUTER_FALLBACK_MODEL` (default
  `deepseek/deepseek-v4-flash`); key handling stays `OPENROUTER_API_KEY`
  (values live only in host env/sops — never in repo files).
- `api/classifier.py`: `OPENROUTER_MODELS` gains the `deepseek-v4-flash`
  short name; no dedicated DeepSeek provider class — OpenRouter already
  covers it.
- `pipeline/orchestrator.py`: `summarize_file` keeps Llamaserver primary; on
  connect/timeout failure it retries once via OpenRouter DeepSeek when a key
  is set (no re-extraction — only the LLM call retries).
- `search/rag.py`: `_chat` provider chain — llamaserver first, OpenRouter
  fallback; `model` in the response reports who answered. RAG answers on the
  VPS now work with just the sidecar question embedding + OpenRouter key.
- UI: `ModelSelector.svelte` gains "DeepSeek V4 Flash (OpenRouter)".

**Leitlinien search on the VPS (keyword-only chunks)**:
- The VPS (2 GB / 1 vCPU) cannot host the Qwen3-Embedding sidecar, so chunk
  search runs without vectors: `api/config.py` `CHUNK_SEARCH_MODE`
  (`embed` default local / `keyword` VPS), `search/chunks.py`
  `_keyword_search_chunks` (websearch tsquery + `ts_rank` over
  `chunks.search_vector`, identical item shape; true total for pagination).
- host config: `medwiss-api` unit gets `CHUNK_SEARCH_MODE=keyword`; deploy
  playbook gains slice 4b (chunks text-only export/import with pre-computed
  `search_vector` + GIN index; embeddings never leave tux), slice 3 drops
  `VITE_DISABLE_LEITLINIEN=1`, smoke now expects chunks 200. Stale "FTS-only"
  comments in `hosts/vps/config.nix` fixed.

**Notfall page** (`/notfall`, nav "Referenz"):
- Curated emergency algorithm cards (Überlebenskette, BLS, 4H/4T, ABCDE, GCS,
  AMPLE, FAST, Anaphylaxe) in `ui/src/lib/notfall.ts` — to be curated by boss;
  local search box, three groups. No backend.

**Rechner: nieren.app (ÖGN)** — two external links (`/calculator`,
`/guidelines`) in the Nephrologie box (site forbids iframing → no tab).

**Suche: filter chips + typo tolerance**:
- Active-filter chips above the results (click = remove) in
  `ui/src/routes/search/+page.svelte`.
- pg_trgm fuzzy title matching in `search/keyword.py`: `ke.titel % :raw`
  extends WHERE + adds fuzzy tier (2); GIN trigram index on `titel` already
  exists. Contract test updated.

**Image zoom (FileViewer)** — wheel zoom (1–8×), drag pan when zoomed,
double-click reset; click keeps toggling the native fullscreen viewer.

**Mermaid in markdown** — `ui/src/lib/mermaid.ts` swaps ```mermaid fences in
the entry "Inhalt" and FileViewer markdown for inline SVGs (`mermaid` npm
package, `securityLevel: strict`, dark-theme aware; parse errors keep source).

**PubMed abstract labels** — structured abstract labels (Background/Methods/
Results/…) render bold: text is escaped first, then known labels are wrapped
(external-content safe).

**Mobile UI** — global `img/video/iframe { max-width: 100% }` guard
(`app.css`); mobile top-nav items now shrink with label ellipsis instead of
overflowing ("menu bar auto adjust width").

**Docs** — `docs/plans/bidirectional-corpus-sync.md`: proposal for
bidirectional tux↔VPS corpus sync (Syncthing recommended, Unison alternative;
conflicts become files, DBs never sync). AGENTS.md updated (new env vars,
provider table, Notfall/Rechner/search sections).

### Fixed
- Repo-wide ruff sweep: 22 errors → 0. `api/main.py` imports moved above
  `logging.basicConfig` (E402); unused imports dropped (alembic migration,
  scripts, tests); bare `except:` → `except Exception:` ×4
  (`scripts/test_bibliothek.py`); ambiguous `l` renamed
  (`scripts/import_awmf_chunks.py`); dead locals removed (`folder_name`,
  `skipped`, `entries_already_correct`); stale f-strings de-fanged (F541).

LOC added: ~700 | LOC removed: ~120 | LOC total: ~97,800


## [1.8.1] - 2026-09-02 09-05
### Added
**"Rechner" page (Tier 1 + Tier 2 calculator linking, frontend-only)**:
- New route `ui/src/routes/rechner/+page.svelte` + sidebar nav item
  "Rechner" under "Referenz" (`+layout.svelte`, lucide `Calculator` icon).
- Tier 1: search box builds provider search links (MDCalc, QxMD Calculate)
  for any term; matching Diagnosen from `GET /diagnosen` render as
  per-provider search-link chips (cap 60, ≥2 chars). No schema change.
- Tier 2: `ui/src/lib/calculators.ts` — 37 curated calculators from the
  MDCalc favorites export (stable `/calc/<id>/<slug>` URLs), organized by
  discipline boxes with subgroups (Kardiologie: EKG/Gefäße/Gerinnung;
  Pulmologie: Asthma/COPD/Pneumonie; plus Allgemein, Notfall (Wells
  Lungenembolie), Neurologie, Intensiv, Infektiologie, Gastro & Hepatologie,
  Nephrologie, Labor), each
  box with a discipline-colored heading. Search matches render as prominent
  discipline-colored buttons; help texts and input placeholder removed.
  Frontend-only — new favorites = new rows in `calculators.ts`.
  New: Asthma Predictive Index (API), Pediatric Asthma Score (PAS), PASS.

### Fixed
- Unused-CSS-selector warnings swept: lucide icon classes moved onto wrapper
  elements (`rechner`, `pubmed`, `leitlinien`, `ChunkResults`, `RagResults`);
  dead `.dashboard-header*`/`.subtitle` rules removed (dashboard,
  leitlinien). `bun run check`: 0 errors, warnings 51 → 40, rechner/pubmed/
  leitlinien/dashboard/ChunkResults/RagResults clean.

Verified: `bun run check` — 0 errors.

LOC: ~560 added / ~36,410 total.


## [1.8.0] - 2026-09-01 20-55
### Changed
**OCR pipeline deactivated by default via `OCR_ENABLED` config gate** (code kept, inert):
- `api/config.py`: `ocr_enabled: bool = False` (env override `OCR_ENABLED=true` re-enables Tesseract/Whisper extraction).
- `pipeline/orchestrator.py` `extract_text()`: image/PDF dispatch raises `OCRDisabledError` (new, in `pipeline/ocr.py`) when the flag is off; `pipeline.ocr` import is now lazy. `pipeline/ocr.py` guards the `pytesseract` import (try/except) so the app no longer requires tesseract at import time; `extract_text_from_image` raises `OCRDisabledError` when pytesseract is missing.
- `pipeline/batch_processor.py`: catches `OCRDisabledError`, logs a single INFO ("OCR disabled, skipping text extraction for X") and returns a skip result — `file_sync.ingest_file` then link-only indexes the file with hash stamp (existing `EXTRACTION_DEPENDENT_SUFFIXES` path), so ingestion (link, hash, folder tags) continues.
- `api/routers/summarize.py` + `api/routers/pipeline.py`: `OCRDisabledError` → HTTP 409 with detail "OCR ist deaktiviert (OCR_ENABLED=false) - Textextraktion für Bilder/PDFs ist nicht verfügbar. / OCR is disabled…". `summarize_file` re-raises instead of swallowing it into a 500.
- `tests/test_pipeline.py`: 3 new tests (flag default off; image extraction raises `OCRDisabledError` with flag off; extraction calls through with flag on via monkeypatch).
- Docs: AGENTS.md env-var tables (both) + file-type tables note the gate.

Verified: `ruff` clean on all touched files; `pytest -q` 67 passed + 2 pre-existing failures (`test_hierarchy_labels` import error, `test_search` `R.cnt`). Live smoke: flag off → INFO skip + `result.error="OCR disabled (skipped)"`; `summarize_file` propagates `OCRDisabledError`; `OCR_ENABLED=true` restores the old path. Nothing committed.

LOC: ~110 added / ~35,850 total.

## [1.8.0] - 2026-09-01 20-10
### Added
**Search filters on top of the keyword search (plain WHERE clauses, no facet machinery)**:
- `GET /api/v1/search` gained optional filter params: `fachgebiet`
  (id or case-insensitive name → `entry_fach`/`fachgebiete` EXISTS),
  `dokumenttyp` (id or name → `dokumenttyp_id` match with legacy
  `dokumenttyp` string OR-fallback, mirroring the dual-write convention),
  and `folder` (exact match on the first `source_hierarchy` segment).
  Filters are ANDed on top of the keyword OR-group (`_build_where`);
  `q` is now optional, so filters alone list matching entries.
  Unresolvable fachgebiet/dokumenttyp values → 422.
- Response extended with a `filters` options block: `fachgebiete` (id+name),
  `dokumenttypen` (id+name), top-level `folders` (name + entry count) —
  one cheap grouped query each, no caching. Contracts regenerated
  (`./scripts/gen-api.sh`).
- UI: compact filter row (Fachgebiet / Dokumenttyp / Ordner dropdowns +
  "Filter löschen" button) above the results; changing a filter re-runs the
  search and resets to page 1. Filtered requests go through `/search` even
  with an empty query (plain `/entries` listing only when nothing is set).
  `/search/chunks` + `/search/chunks/rag` untouched.
- Tests: `tests/test_search.py` extended to 20 cases (WHERE construction,
  filter resolution/422, combination params, filter options shape).
  Verified: `ruff` clean on touched files, `pytest tests/test_search.py`
  20 passed, full suite 65 passed + the known `test_hierarchy_labels`
  failure, `bun run check` 0 errors. Live API smoke skipped: local
  PostgreSQL is down and docker requires sudo.

LOC: ~640 added / ~35,740 total.

## [1.8.0] - 2026-09-01 19-15
### Fixed
**VPS deployment fixes (4 issues)**:
- **PDF preview 500**: `GET /files/entries/{id}/view` (and `/download`, `/chunks/{id}/view`)
  crashed with `UnicodeEncodeError` (latin-1) on filenames containing non-ASCII characters
  (e.g. "Reanimationsleitlinien 2021 – die BIG-FIVE.pdf"). New
  `_content_disposition()` in `api/routers/files.py` emits RFC 5987
  `filename*=UTF-8''…` plus an ASCII fallback.
- **Admin-Klassifizierung 500**: `data/classification_library.txt` is git-tracked but the
  deploy playbook's app rsync never shipped `data/` to the VPS → `FileNotFoundError`.
  Endpoint now returns HTTP 503 with a clear message when the library is missing
  (`api/routers/admin.py`); playbook rsync extended (`data/`, `main.py`).
- **Leitlinien page**: env-driven gate `VITE_DISABLE_LEITLINIEN=1` hides the sidebar
  link (`+layout.svelte`) and redirects `/leitlinien` → `/`
  (`leitlinien/+page.svelte`). Documented in AGENTS.md; VPS builds set it
  (`VITE_DISABLE_LEITLINIEN=1 bun run build`).
- **ICD-11 coverage audit (read-only, VPS)**: 3,846 entries; 588 (15.3 %) have ≥1
  Diagnose, 583 have a Diagnose with ICD-11 code. 74/78 Diagnosen have ICD-11;
  4 missing: Analkarzinom (C21), Pankreaserkrankung (K86), Bienengiftallergie (T63),
  Neuroborreliose (A69).

LOC: ~25 added / 30,090 total.

## [1.8.0] - 2026-09-01 19-10
### Changed
**Search rework — simple keyword search (replaces FTS/faceted/hybrid)**:
- `GET /api/v1/search` is now a single ILIKE keyword query over `titel`,
  `zusammenfassung`, `inhalt`, `source_path`/filename, `source_hierarchy`
  folder segments, and extracted AWMF chunk text of the entry's source file.
  Fixed tier ranking: title (3) > filename (2) > folder (1.5) > content (1).
  Pagination via `limit`/`offset`. No tsvector, no vectors, no sidecars.
- Removed as dead weight: `search/fts.py`, `search/faceted.py`,
  `search/hybrid.py`, `search/common_filters.py`, the `/search/faceted`,
  `/search/filters`, `/search/refresh-index` endpoints, the `SearchType` /
  `alpha` / `fuzzy` parameters, and the `v_entry_search` view
  (drop on existing installs: `DROP VIEW IF EXISTS v_entry_search CASCADE;`).
  `/search/chunks` and `/search/chunks/rag` (RAG features) are untouched.
- UI: search page reduced to one keyword input + history + paginated results;
  mode tabs, facet filter sidebar, and hybrid alpha slider removed
  (`FacetFilters.svelte` deleted). OpenAPI types regenerated.
- New module `search/keyword.py` with pattern escaping (`like_pattern`);
  `tests/test_search.py` rewritten for it.

## [1.8.0] - 2026-08-31 18-04
### Changed
**Files are the database — unilateral rsync + live sync (plan: `docs/plans/file-sync-simplification.md`)**:
- **Canonical content root**: new `MEDWISS_CONTENT_ROOT` (`config.get_content_root`,
  default `~/Dokumente/Medizin`; VPS resolves via symlink to `/srv/medwiss/corpus`).
  `discover_sources`, `load_sources`, `references.py` and `files.py` (`AWMF_ROOT`,
  `ALLOWED_ROOTS`) all derive from it. `sources.yaml` rewritten to the real folder
  names (previous yaml rows pointed at long-gone `2_Leitlinien`/`3_Studien`/…).
  Read-only invariant: the app never writes to the content tree.
- **OCR deactivatable per host**: `OCR_ENABLED=false` (VPS `medwiss.nix`) —
  PDF/image/audio/pptx/docx files are **link-only indexed** (hash stamped, no
  re-attempt loop; folder tags best-effort in a savepoint). First pass backfilled
  923 link-only entries + stamped 2,665 hashes; reconcile errors 3,652 → 1.
- **FileSyncService is now the single-file pipeline** (`ingest_file`): direct
  extract → classify → save, no more per-call `uuid4()` throwaway ImportJobs.
  Update branch touches only content/hash/hierarchy labels — manual tags survive.
- **Renames**: `run_sync` pairs delete+create by file hash and moves the existing
  entry (ID + manual tags preserved); watcher gained `on_moved` (required: rsync
  lands updates as hidden temp file + rename) and a 2 s delete grace period.
- **Startup reconcile** runs in a background thread 2 s after boot (non-blocking).
- **`GET /files/admin/sync-status` is cheap**: served from new in-memory
  `api/services/sync_state.py` (watcher-fed last-change timestamp + counts);
  no more full-tree hashing per poll. Dashboard polls it every 10 s and refetches
  on change.
- **Batch-import stack deleted**: `batch_import_worker.py`, `import_jobs.py`,
  `routers/batch_import.py`, `scripts/batch_import_cli.py`, `pipeline/monitor.py`,
  ImportJob model/FK/column (`migration 006_drop_import_jobs.sql`), Pydantic job
  models, generated `/batch-import` types. `run_pipeline.py` lost `--monitor`.
- **Transport**: daily `medwiss-sync.timer` + manual trigger
  (`systemctl start medwiss-sync` / `medwiss-sync` command) wrapping the existing
  one-way `sync-medwiss-corpus.sh` (mint-hps: `modules/medwiss-sync.nix`).
  No Syncthing; VPS cannot pull.
- **schema.sql drift repair**: added `knowledge_entries.unterkategorie` and
  `diagnosen.icd11_code` (existed in models/live DB, missing from schema).

  LOC total: ~35,100

## [1.8.0] - 2026-08-31 14-55
### Fixed
- **Referenz page infinite "Laden..."**: a duplicate URL in `medlinks.txt`
  (`symptomsuche.at` twice under Allgemein) crashed Svelte 5's keyed each block
  (`each_key_duplicate`) mid-render, leaving the component stuck on the spinner.
  Link loop now keyed by `url + '#' + index` (`ui/src/routes/referenz/+page.svelte`)
  so duplicate URLs in the data can never crash the page; duplicate line removed
  from `medlinks.txt` and re-deployed to the VPS (`/srv/medwiss/Dokumente/Medizin/md/`).
  Fresh UI build deployed to `/srv/medwiss/build`.
  LOC added: 2 | LOC removed: 1 | LOC total: ~32,455

### Added
- **Plan**: `docs/plans/file-sync-simplification.md` — "files are the database"
  architecture: Syncthing local→VPS file sync, slimmed SourceWatcher with direct
  pipeline calls (no temp import jobs), startup reconcile, batch-import stack
  removal, 10 s UI polling. Awaiting approval.
  LOC added: ~120 | LOC total: ~32,575

## [1.8.0] - 2026-08-29 13-45
### Added
- **Favicon**: `ui/static/favicon.svg` (medical cross, `--color-primary` blue) +
  `app.html` icon link switched to `type="image/svg+xml"` (previous `favicon.png`
  link pointed at a missing file — `ui/static/` was empty).
  LOC added: 8 | LOC total: ~32,450

## [1.8.0] - 2026-08-29 11-50
### Changed
- **Fleet release convention**: `scripts/release.sh` generalized (root pyproject / package.json /
  manifest.json / apps+web pair / apps/web / manifest-less — CHANGELOG+tag only). Same script
  deployed to all 8 project repos; initial `v0.1.0` tags cut everywhere (medwiss-db stays `v1.7.6`).
  VPS `/healthz` now reports the deployed app version from pyproject.toml (host config repo).
  LOC added: ~120 | LOC total: ~32,440

## [1.7.6] - 2026-08-29 11-35
### Added
- **Release versioning**: single-source version in `pyproject.toml` (now `1.7.6`),
  annotated git tags `vX.Y.Z`, `scripts/release.sh` (bump → version CHANGELOG →
  tag → push `--follow-tags`, refuses dirty tree), and `GET /api/v1/version`
  returning the pyproject version (visible through the VPS same-origin proxy).
  All previous `[Unreleased]` CHANGELOG sections versioned as `1.7.6` (first
  real tag; earlier `v1.7.x` mentions were informal, never tagged).

## [1.7.6] - 2026-08-29 11-15
### Added
**Unified Tagging System implemented** (plan `docs/plans/unified-tagging-system.md`, all 8 phases):
- **CRUD endpoints** for `dokumenttypen` + `ordner-labels` (GET/POST/PUT/DELETE each,
  409 on duplicate, `?reviewed_only=`), pending-review queue now covers both kinds
  (`api/routers/classifications.py`, `api/models.py`).
- **Service ID-switch + silent-drop fix**: `create_entry`/`update_entry` handle
  `dokumenttyp_id` + `ordner_label_ids` explicitly (update previously dropped
  `ordner_label_ids` silently); `dokumenttyp_id: null` clears ID + legacy string;
  legacy `dokumenttyp` string writes resolve back to an ID (rename-sync);
  `to_response` populates `dokumenttyp_id`, `dokumenttyp_ref`, `ordner_labels`;
  `/entries/dokumenttypen` now reads the lookup table (SoT). Dual-write keeps
  `dokumenttyp` string + `source_hierarchy` JSONB current (stats/faceted/FTS never stale).
- **Resolver**: `resolve_dokumenttyp`/`resolve_ordner_label` (exact case-insensitive
  match, auto-create; LLM-source rows flagged `needs_review`, folder-source trusted).
  `apply_proposals` links OrdnerLabel rows for hierarchy proposals and sets
  `dokumenttyp_id` alongside the string; `resolve_labels` accepts
  `dokumenttyp` + `ordner_labels`.
- **Frontend unified tag editors** (`ui/src/lib/api.ts`, eingabe, edit, detail, admin):
  fake `Date.now()` inline-create replaced by real POST + 409→resolve fallback;
  Dokumenttyp is a table-backed `<select>` bound to `dokumenttyp_id`; Ordner-Labels
  editable MultiSelect (replaces read-only hierarchy chips); detail page shows one
  "Tags" group with distinct accent colors (dokumenttyp purple, hierarchy gray,
  fach blue, diagnose green, symptom orange); admin "Labels verwalten" gains
  Dokumenttypen + Ordner-Labels tabs.
- **Search view** `v_entry_search` redefined (schema.sql + applied live): dokumenttyp
  from `dokumenttypen` via `dokumenttyp_id` (coalesce legacy), hierarchy labels from
  `entry_ordner_label ⨝ ordner_labels` (coalesce legacy `source_hierarchy`); FTS
  setweight 'C' fed by the new aggregation. `stats/by-category` groups via lookup join.
- **Fixed latent ORM/DB mismatch**: `entry_ordner_label` junction column is
  `label_id` (migration 005), `database/models.py` declared `ordner_label_id` —
  the `ordner_labels` relationship could never load. Aligned to `label_id`.
- Contract regenerated (`scripts/gen-api.sh`).
  Verified: API smoke (create/clear/rename-sync/dual-write/FTS/faceted/stats/pending-review),
  browser E2E (inline create → real ID, eingabe submit with Dokumenttyp + 2 labels,
  detail chips, edit round-trip, admin rename), `bun run check` 0 errors, `ruff` clean
  on touched files, pytest 56 passed / 8 pre-existing failures unchanged.
  LOC added: ~940 (+ generated contract) | LOC total: ~32,320

## [1.7.6] - 2026-08-29 10-05
### Changed
- **Unified tagging plan re-scoped** (`docs/plans/unified-tagging-system.md`) — exploration showed
  Phase 1–2 DB work already merged (migration 005, schema, SQLAlchemy + Pydantic models, contract
  fields). Plan rewritten as wire-up: CRUD endpoints, service ID-switch + silent-drop fix
  (`ordner_label_ids`), dual-write strategy, frontend phases, admin tabs, `mv_entry_search`
  redefinition + refresh-index, acceptance criteria. Critique added earlier stays as
  `unified-tagging-system-critique.md`.
  LOC added: ~300 (docs) | LOC total: ~31,410

## [1.7.6] - 2026-08-29 09-48
### Changed
- **Dark Mode without own box** (`ui/src/routes/admin/+page.svelte`) — the "Erscheinungsbild"
  section header/icon/description removed; the page now opens with a bare Dark Mode toggle card.
  Redundant "Dark Mode aus" reset button + `handleReset` dropped; unused `Moon`/`RotateCcw`
  imports and dead styles (.subtitle, .field-label, .field-select, .save-*) removed.
  Verified in browser: toggle dark/light works, layout renders. `bun run check` 0 errors.
  LOC added: 22 | LOC removed: 197 | LOC total: ~31,112

## [1.7.6] - 2026-08-29 09-35
### Removed
- **Dead Admin controls** (`ui/src/routes/admin/+page.svelte`) — stripped Sprache, Kompaktansicht,
  Automatisches Speichern, Export-Format + "Daten exportieren" (no onclick), and the fake
  "Speichern" button (800 ms sleep + success banner). Admin page now shows only working
  features: Dark Mode, Automatische Klassifizierung, Labels verwalten; "Dark Mode aus" replaces
  Speichern/Zurücksetzen. Also removed `DEEPSEEK_API_KEY` from `.env` (compose line already
  gone); TODO item 5 added: VPS wire-in of DeepSeek.
  Verified in browser: three sections render, no selects/exports left, `bun run check` 0 errors.
  LOC added: 11 | LOC removed: 104 | LOC total: ~31,287

## [1.7.6] - 2026-08-29 09-24
### Removed
- **Authentication** — the backend had no auth left (no `auth.py`, no `dependencies.py`, no
  `Depends` guards); this change purges the dead remainder. Removed: user/token/login Pydantic
  models (`api/models.py`), JWT settings (`api/config.py`), `python-jose`/`passlib`/`bcrypt`
  deps (`requirements.txt`, `pyproject.toml`, `uv.lock`), seeded test users admin/test123
  (`database/seeds.sql`), `created_by` from seed inserts, token interceptor + Authorization
  headers (`ui/src/lib/api.ts`, `ui/src/routes/icd11/+page.svelte`). `scripts/import_files_as_links.py`
  now imports without attribution user. `users` table kept (FK target of
  `created_by`/`updated_by`). Contract regenerated: `openapi.json` + `api-types.d.ts` contain
  zero auth paths. AGENTS.md auth sections updated.
  Verified: app imports, `ruff` clean on touched files, `bun run check` 0 errors, live API
  answers `200` without any token, `/api/v1/auth/login` → 404, UI dashboard loads login-free.
  LOC added: 157 | LOC removed: 1644 | LOC total: ~31,380

## [1.7.6] - 2026-08-29 09-04
### Fixed
- **Dark Mode toggle** (`ui/src/routes/admin/+page.svelte`) — the "Erscheinungsbild" switch was
  purely decorative. Now a `$effect` sets `document.documentElement.dataset.theme` and persists
  to `localStorage('theme')`; an inline script in `ui/src/app.html` applies it before first paint
  (no flash). Dark palette added as `[data-theme="dark"]` token overrides in `ui/src/app.css`;
  hardcoded `background: #fff` replaced with `var(--color-background-primary)` (ChunkResults,
  RagResults, ICD-11, Leitlinien, Admin) and Tailwind `bg-white`/`text-gray-*` utilities
  dark-overridden. Verified in browser: toggle on/off, persistence across pages.
  LOC added: 59 | LOC total: ~31,223

## [1.7.6] - 2026-08-28 00:45
### Added
- **Mobile top-nav auto-hide** — bar slides away when scrolling down, returns on
  scroll up (translateY + margin-top reclaim). **Leitlinien** (RAG search needs
  llamaserver, absent on VPS) and **Neuer Eintrag** (needs workover) hidden from
  the mobile nav. TODO item 4 added for the eingabe workover.
  Verified at 390px viewport. Deployed to VPS.
  LOC added: 14 | LOC total: ~31,164

## [1.7.6] - 2026-08-28 00:20
### Added
- **Mobile layout** (`ui/src/routes/+layout.svelte`) — on <=768px the nav moves from a
  bottom bar to a sticky **top bar**; width-fit guards (`max-width:100vw`,
  `overflow-x:hidden`) make content fit the viewport; the top nav scrolls
  horizontally internally instead of wrapping. Verified at 390px viewport.
  Deployed to VPS.
  LOC added: 16 | LOC total: ~31,150

## [1.7.6] - 2026-08-27 23:36
### Fixed
- **Referenz page subsection spacing** — subsections within section cards now
  have visible separation (margin + border-top) via `.ref-subsection + .ref-subsection`
  adjacent sibling selector, replacing broken `.subsection-title:first-of-type` that
  matched the first h3 in every card. Wrapped each subsection in `div.ref-subsection`.
  Deployed to VPS.
  LOC added: 8 | LOC total: ~31,134

## [1.7.6] - 2026-08-27 12:03
### Fixed
- **Referenz page 404** — `GET /api/v1/references` and `GET /api/v1/icd11/token` were
  imported in `api/main.py` but never `include_router`'d, so `/referenz` showed
  axios "Request failed with status code 404". File `~/Dokumente/Medizin/md/medlinks.txt`
  was never the problem.
  LOC added: 2 | LOC total: ~31,126

### Added
- **OpenAPI → TS types** — `./scripts/gen-api.sh` dumps FastAPI `app.openapi()` to
  `contracts/api/openapi.json` and generates `ui/src/lib/api-types.d.ts`. `$lib/api.ts`
  re-exports `ApiComponents` / `ApiPaths`; handwritten interfaces kept until
  call sites switch. Axios client unchanged.
  LOC: generated `openapi.json` + `api-types.d.ts` (~11k lines); harness scripts small.

## [1.21.0] - 2026-08-27 08:30
### Added
- **Referenz page** (`/referenz`, `ui/src/routes/referenz/+page.svelte`) — links to medical
  resources, parsed **live** from `~/Dokumente/Medizin/md/medlinks.txt` on every request (edits
  show on refresh). Backend `api/routers/references.py` `GET /api/v1/references` parses the
  text file into nested sections (`#`/`##`/`###` headers, `* Label` + URL pairs, bare URLs and
  domains; bare domains get `https://`). UI renders a card grid per section with the full URL
  shown under each link label; refresh button re-fetches.
- **PubMed search page** (`/pubmed`, `ui/src/routes/pubmed/+page.svelte`) — live literature
  search via NCBI E-utilities. Backend `api/routers/pubmed.py` `GET /api/v1/pubmed/search`
  proxies three calls: ESearch (relevance-sorted IDs + total) → ESummary (title/authors/
  journal/date/DOI) → EFetch (abstracts, `BACKGROUND:`-labels preserved). UI: search bar,
  result cards with PMID/DOI/journal/authors line, per-card abstract expand/collapse, external
  PubMed links, `?q=` deep-link param. `tool=medwiss-db` + `email` sent per NCBI policy.
- **PubMed field filters** — Filters panel (toggle button): Titel `[Title]`, Autor `[Author]`,
  Artikeltyp `[Publication Type]` (case_reports/clinical_study/clinical_trial/dataset/review),
  Zeitschrift `[Journal]`, Erscheinungsdatum (1/5/10 Jahre presets + custom range → `[dp]`).
  Query built server-side (`_build_term`) and shown above results.
- **PubMed sort dropdown** — Relevanz (default) / Neueste zuerst (`pub_date`) / Autor (A-Z) /
  Zeitschrift (A-Z), validated server-side.
- **Sidebar** (`+layout.svelte`) — "Links" and "PubMed" nav items under the Referenz section
  (Link / Newspaper icons).
- **LOC added**: ~1,295 | **LOC total**: ~31,124

## [1.20.6] - 2026-08-26 23:15
### Changed
- **Image preview in FileViewer** (`ui/src/lib/components/FileViewer.svelte`) — tall images are
  now displayed at full container width inside a scrollable box (max-height 800px, `overflow-y:
  auto`) instead of being squeezed to fit 800px height (which made tall images tiny/narrow).
  Clicking the image (or Enter/Space when focused) toggles the browser Fullscreen API on the
  image container; in fullscreen the image is centered and scrollable at natural size. Added a
  `Maximize` hint badge. Mobile: scroll box capped at 400px.
- **LOC added**: ~35 | **LOC total**: ~29,922

## [1.20.5] - 2026-08-26 23:00
### Changed
- **Leitlinien-Suche**: removed the empty-state hint "Geben Sie eine Suchanfrage ein."
  (`ui/src/lib/components/ChunkResults.svelte`) — no text is shown before a query; only
  "Keine Treffer gefunden." appears when a query yields nothing.
- **ICD-11 Browser**: restored the subtitle "Klassifikation der Weltgesundheitsorganisation"
  below the page title (`ui/src/routes/icd11/+page.svelte`).
- **LOC added**: ~1 | **LOC total**: ~29,887

## [1.20.4] - 2026-08-26 22:55
### Changed
- **Removed all placeholder ("phantom") texts and page subtitle/help texts** across the UI.
  Removed `placeholder`/`searchPlaceholder` from all inputs and MultiSelects (Suche, Leitlinien,
  Bibliothek, Eintrag anlegen/bearbeiten, Admin) and the page-header subtitle paragraphs on
  Dashboard, Suche, Admin, Neuer Eintrag, ICD-11 and Leitlinien. Removed the
  `Plaintext/Markdown unterstützt` field hint (+ its now-unused `.field-hint` CSS).
  Bibliothek's live `{totalDocs} Dokumente` count kept (data, not help text).
- **Removed Dashboard title** — `<h1>Dashboard</h1>` and its subtitle removed from the
  dashboard page header.
- **ICD-11 Browser width** — page container set to `max-width: 1200px`.
- **LOC added**: ~0 | **LOC total**: ~29,886

## [1.20.3] - 2026-08-26 22:40
### Changed
- **Unified page width to 1000px** — all page containers now `max-width: 1000px` (was
  mixed: dashboard/search/entry-detail 1200px, icd11 1600px, bibliothek 1300px, admin/
  eingabe/edit 900px, leitlinien unconstrained). Files: `ui/src/routes/{+page,admin,
  bibliothek,eingabe,icd11,leitlinien,search}.svelte`,
  `ui/src/routes/entry/[id]/{+page,edit/+page}.svelte`.
- **LOC added**: ~2 | **LOC total**: ~29,886

## [1.20.2] - 2026-08-26 22:15
### Fixed
- **Dashboard / Bibliothek / Suche 500 errors** — `GET /entries`, `/stats/overview`,
  `/stats/by-category` returned `500 Internal Server Error`. Root cause: schema drift — the
  SQLAlchemy model references `knowledge_entries.dokumenttyp_id` (unified-tagging migration
  `005`), but the running DB was at alembic `004` and the `005_unified_tagging.sql` migration
  had never been applied (`column knowledge_entries.dokumenttyp_id does not exist`).
  Applied migration `005`: created `dokumenttypen` (12 seed rows), `ordner_labels` (1036),
  `entry_ordner_label` junction (6886 rows), added `dokumenttyp_id` FK + index, backfilled
  existing `dokumenttyp` strings (2603 entries linked) and `source_hierarchy` folder labels.
  Also fixed a latent bug in the migration's step 7 (`source_hierarchy::text[]` is an invalid
  cast on a `jsonb` column) — replaced with `jsonb_array_elements_text(source_hierarchy)`.
- **LOC added**: ~40 | **LOC total**: ~29,850

### Changed
- **ICD-11 Browser page** (`ui/src/routes/icd11/+page.svelte`) — widened container from
  `max-width: 1100px` to `1600px`; added a "WHO ICD-11 öffnen" header link (top-right) to the
  original WHO site (`https://icd.who.int/browse/2026-01/mms/de`), opening in a new tab.
- **LOC added**: ~34 | **LOC total**: ~29,884

## [1.20.1] - 2026-08-26 19:52
### Fixed
- **ICD-11 Browser still not loading** (`ui/src/routes/icd11/+page.svelte`) — the WHO CDN
  loads ECT **1.8**, whose API is `ECT.Handler.configure(settings, callbacks)` (callbacks as
  the **second** argument) with a `div.ctw-eb-window[data-ctw-ino]` mount point. The page
  still used the old 1.6 API (`ect.configure({...})` + `ect.EmbeddedBrowser(id, ...)`), which
  does not exist in 1.8 (`window.ECT` only exposes `Handler`/`Settings`), so `configure`
  threw and the fallback "konnte nicht geladen werden" always showed.
  Now: loads CSS/JS from WHO CDN, calls `ECT.Handler.configure(settings, callbacks)` with
  `apiServerUrl: https://id.who.int`, and binds manually via `ECT.Handler.bind('mb-main')`
  with `autoBind:false` (autoBind hooks the window `load` event, which has already fired in
  an SPA). Container changed from `#icd11-browser` to `class="ctw-eb-window" data-ctw-ino="mb-main"`.
- **LOC added**: ~10 | **LOC total**: ~29,810

## [1.20.0] - 2026-08-26 17:50
### Fixed
- **ICD-11 Browser not loading** (`ui/src/routes/icd11/+page.svelte`) — the page loaded
  `/static/ect.js` which was a core-js polyfill, not the WHO ECT library. Now loads both
  CSS and JS from the WHO CDN (`icdcdn.who.int/embeddedct/icd11ect-1.8.*`). Added
  `apiSecured: true` with `getNewTokenFunction` that fetches an OAuth2 token from the
  new backend proxy endpoint.

### Added
- **ICD-11 token proxy** (`api/routers/icd11.py`) — `GET /api/v1/icd11/token` returns
  a cached WHO ICD-11 OAuth2 token for the embedded ECT browser. Reuses the existing
  `ICD11Client` token management.
- **Unified tagging system plan** (`docs/plans/unified-tagging-system.md`) — design doc
  for replacing the 5 fragmented tag dimensions with proper lookup tables + M2M junctions.
  Decisions: Ordner-Labels → real lookup table, editors can create labels, Dokumenttyp
  stays single-select. 5 phases, 12 files, ~3-4 hours implementation.
- **DB migration** (`database/migrations/005_unified_tagging.sql`) — creates `dokumenttypen`
  and `ordner_labels` lookup tables, `entry_ordner_label` M2M junction, adds
  `dokumenttyp_id` FK to `knowledge_entries`, migrates existing data.
- **SQLAlchemy models** (`database/models.py`) — `Dokumenttyp`, `OrdnerLabel` models,
  `entry_ordner_label_table` association, `KnowledgeEntry.dokumenttyp_id` +
  `dokumenttyp_ref` + `ordner_labels` relationships.
- **Pydantic models** (`api/models.py`) — `DokumenttypResponse`, `OrdnerLabelResponse`,
  `dokumenttyp_id` on `EntryBase`, `ordner_label_ids` on `EntryCreate`/`EntryUpdate`,
  `dokumenttyp_ref` + `ordner_labels` on `EntryResponse`.

### Removed
- **Local ECT assets** (`ui/static/ect.js`, `ui/static/ect.css`) — replaced by WHO CDN.

- **LOC added**: ~620 | **LOC total**: ~29,800

## [1.19.0] - 2026-08-26 16:50
### Added
- **ICD-11 Browser page** (`ui/src/routes/icd11/+page.svelte`) — embeds the official WHO
  Embedded Classification Tools (ECT) browser in German (`@whoicd/icd11ect@1.8.0` from
  `ui/static/ect.js`). Full ICD-11 chapter tree + search, with code-selection bar and
  clipboard copy. Falls back to WHO external link if ECT fails to load.
- **Label manager on Admin page** (`admin/+page.svelte`) — "Labels verwalten" section
  with three tabs (Fachgebiete/Diagnosen/Symptome). Full CRUD: add, rename (inline edit),
  delete (with confirm). Wired to existing classification CRUD API. Diagnose tab shows
  ICD-10 + ICD-11 codes.
- **Classification CRUD in frontend** (`ui/src/lib/api.ts`) — `create/update/delete`
  methods for Fachgebiete, Diagnosen, Symptome in `classificationsApi`. Added `icd11_code`
  to `DiagnoseResponse`.

### Changed
- **Search Fachgebiete filter collapsed by default** (`FacetFilters.svelte`) — was open,
  now starts collapsed like the other filter sections.
- **Fach filter matches source_hierarchy** (`entry_service.py`) — the `/entries?fach=`
  endpoint now matches both real junction links AND `source_hierarchy` folder segments,
  consistent with the `v_entry_search` view's `fachgebiete_names` semantics. Fixes
  "100 Medikamente (100)" showing 0 results when facet count showed 100.
- **ICD-11 nav item** (`+layout.svelte`) — new "Referenz" section in sidebar with
  ICD-11 link (BookOpen icon).
- **Admin section description** — updated to "Automatische Klassifizierung" with regex
  description.

### Fixed
- **Fach filter 0-results bug** — facet counts (from `v_entry_search` view) include
  `source_hierarchy` folder segments, but the entries endpoint only matched junction links.
  Now both match the same union, so clicking "100 Medikamente (100)" correctly shows 100.

## [1.18.0] - 2026-08-26 15:55
### Added
- **Deterministic regex classification** (`api/services/regex_classifier.py`) — replaces the
  brittle LLM-based classification. Matches folder path → Fachgebiet, filename → Diagnose +
  Symptom against `data/classification_library.txt` (format `F|D|S|<keyword>|<name>|<ICD-10>`).
  Instant (~1s for 2865 entries), reproducible, idempotent. Reuses `resolve_classifications`
  for DB linking.
- **ICD-11 enrichment** (`api/services/icd11.py`) — OAuth2 client for the WHO ICD-11 API,
  post-processes diagnoses to attach ICD-11 codes (versioned path `2026-01/mms/search`,
  `theCode` field, HTML-stripped titles). 74 diagnoses enriched.
- **Classification library** (`data/classification_library.txt`) — editable keyword rules
  (33 Fachgebiete, 83 Diagnosen, 17 Symptome).
- **Filename export tool** (`scripts/export_filenames.py`, `data/filenames.txt`) — dumps all
  2865 entry paths for building/curating the library.
- **ICD-11 DB column** (`alembic/versions/004_add_icd11_code.py`) — `diagnosen.icd11_code`
  VARCHAR(20), also added to SQLAlchemy `Diagnose` model.

### Changed
- **Admin "Automatische Klassifizierung"** (`admin/+page.svelte`) — regex-based (no LLM);
  result grid shows Fachgebiete/Diagnosen/Symptome/Einträge/ICD-11 counts; updated api.ts types.
- **`start.sh --qwen`** — starts Llamaserver + embedding sidecar together (fixed hang from
  `--wait`; added `wait_for_health` polling + port pre-flight checks; removed uvicorn `--reload`).
- **`stop.sh`** — added port-based kill phase (`kill_port` via `lsof`) to reliably free
  ports 8000/5175/8080/8081 from orphaned processes.

### Removed
- **`api/services/filename_classifier.py`** — LLM-based classifier (unreliable, slow);
  replaced by regex classifier.

### Fixed
- **WHO ICD-11 search 404s** — search requires versioned release path (`2026-01`), code field
  is `theCode` (not `code`), titles strip HTML markup.

- **LOC added**: ~1,200 | **LOC total**: ~28,600

## [1.17.0] - 2026-08-26 10:35
### Changed
- **Bibliothek: removed ORDNER sidebar** (`bibliothek/+page.svelte`) — the left folder tree
  was redundant with the breadcrumb navigation and root folder tiles; content now takes full width.
- **Bibliothek: search works from root** (`bibliothek/+page.svelte`) — search now searches all
  entries across all folders regardless of current path; results show file name + folder path +
  date.
- **Admin page created** (`admin/+page.svelte`) — new `/admin` route with Erscheinungsbild
  (Sprache, Dark Mode, Kompaktansicht) and Daten (Export-Format, Auto-Save, Daten exportieren)
  sections, moved from the former Settings page.
- **Settings page deleted** (`settings/+page.svelte`) — Erscheinungsbild and Daten moved to
  Admin; Profil and Benachrichtigungen removed (unused dummy data).
- **Layout nav updated** (`+layout.svelte`) — Settings link removed; Admin link now points to
  `/admin` (was `/admin/sync`).

### Removed
- **SyncStatusDashboard** (`SyncStatusDashboard.svelte`, `admin/sync/`) — replaced by the
  simpler `syncAndRefresh` on the Dashboard page; `batchImportApi` + `ImportJobResponse` removed
  from `api.ts`.

### Fixed
- **11 pre-existing type errors** across 6 files:
  - Svelte 4→5 event handler migration (`SummaryModal.svelte`, `eingabe/+page.svelte`,
    `ModelSelector.svelte`, `SkillSelector.svelte`)
  - Chart.js v4 type strictness: `fontWeight` string→number, `drawBorder`→`border.display`
    (`DiagnoseBarChart.svelte`, `FachDistribution.svelte`)
  - `marked.parse()` return cast for `DOMPurify.sanitize()` (`RagResults.svelte`,
    `entry/[id]/+page.svelte`)

- **LOC added**: ~480 | **LOC removed**: ~1,460 | **LOC total**: ~27,410

## [1.16.0] - 2026-08-26
### Fixed
- **Mobile access over WireGuard** — `ui/src/lib/api.ts` API base URL is now relative (`/api/v1`,
  proxied by Vite) instead of hardcoded `http://localhost:8000`; the SPA now works from phone/other
  mesh peers (previously the phone's own `localhost` was hit, breaking Bibliothek/API calls).
- **Bibliothek horizontal scroll on mobile** — `.main-content` `min-width: 0`, `.fm`
  `align-items: stretch`, `.fm-tree`/`.fm-content`/rows `min-width: 0` + `overflow-x: hidden`
  (`+layout.svelte`, `bibliothek/+page.svelte`); the deep folder tree no longer forces the
  document wider than the viewport.
- **Leitlinien results overflow** — `ChunkResults.svelte`: title/source/snippet now wrap
  (`overflow-wrap: anywhere`, `word-break: break-word`) instead of overflowing the display.

### Added
- **Admin button hidden on mobile** (`+layout.svelte`) — `admin-only` class + `display:none` in
  the ≤768px media query; Settings stays visible.
- **Unnumbered source folders** (`bibliothek/+page.svelte`) — root detection also matches the
  `Fortbildung <year>` convention, so files with `\d+_`-prefixed names under it no longer become
  bogus top-level grid tiles.
- **Folder grid 2-up on mobile** (`bibliothek/+page.svelte`) — `repeat(2, minmax(0,1fr))` on
  narrow screens (was 1 column below 272px).
- **Back-nav restores folder** (`bibliothek/+page.svelte`) — `currentPath` persisted to
  `sessionStorage` (not the URL/history API, which SvelteKit owns); browser back from an entry
  returns to the originating folder instead of the root grid.

### Security
- **PostgreSQL bound to localhost** (`docker-compose.yml`) — `127.0.0.1:${POSTGRES_PORT}:5432`
  so the DB (password still default `changeme`) is not reachable from the WG mesh.

- **LOC added**: ~38 | **LOC total**: ~28,388

## [1.15.0] - 2026-08-25
### Added
- **Markdown rendering for `.md` source files + inline edit toggle** — The entry detail page
  (`/entry/{id}`) FileViewer now renders `.md` files as formatted markdown (via `marked` +
  `isomorphic-dompurify`, same XSS-safe pattern as the Leitlinien RAG answer) instead of showing
  the raw source in a text iframe. Detection via `text/markdown` / `text/x-markdown` mime type;
  the file label shows "Markdown". The "Inhalt" section gained an inline **Bearbeiten** toggle:
  clicking it swaps the rendered markdown for a raw-source textarea with **Speichern** /
  **Abbrechen** buttons (saves via `PUT /entries/{id}` with just `inhalt`; `inhalt` is now
  reactive `$state` so the edit reflects immediately).
- **Files**: `ui/src/lib/components/FileViewer.svelte`, `ui/src/routes/entry/[id]/+page.svelte`
- **LOC added**: ~215 | **LOC total**: ~28,350

## [1.14.0] - 2026-08-25
### Added
- **RAG layer over AWMF chunks** — `GET /api/v1/search/chunks/rag?q=&top_k=` retrieves top-k
  chunks (reusing the exact-cosine `search_chunks`), builds a German prompt, and calls the 9B
  (Qwen3.5-9B-Instruct on GPU `:8080`) for an answer with source pointers. New `search/rag.py`
  (retrieval stays in `search_chunks`), `RagResponse`/`RagSourceItem` models, `ragApi` client,
  `RagResults.svelte`. `/leitlinien` page gained a **Passagen / Antwort mode toggle** (Sparkles);
  answer renders with clickable sources that open the original PDF at the matched page.
  ~30 s per answer; VRAM headroom verified (no OOM at 1024 max_tokens).
- **Markdown rendering** — RAG answers and entry `inhalt` (both markdown) now render via `marked` +
  `isomorphic-dompurify` (sanitized `@html`) instead of raw text / `<pre>`. LLM/imported content is
  untrusted, so output is DOMPurify-sanitized (XSS-safe). Swapped browser-only `dompurify` →
  `isomorphic-dompurify`: `sanitize` is undefined in Node SSR (no `window`), which 500'd the entry
  page on server render. Deps: `marked@18`, `isomorphic-dompurify@3.23`.

### Fixed
- **Suche/Bibliothek file display** — the chunk-endpoint refactor had renamed `_is_path_allowed`
  → `_is_awmf_path_allowed`, leaving the entry view/info/download endpoints calling a missing name
  (`NameError` broke in-page file display). Restored `_is_path_allowed` (entry `ALLOWED_ROOTS`)
  alongside the new AWMF variant.
- **config** — added `llamaserver_url`/`llamaserver_api_key` fields (were `.env`-only, so
  `settings.llamaserver_url` failed at runtime).

### Notes
- `api/config.py`, `api/models.py`, `api/routers/search.py`, `api/routers/files.py`,
  `search/{rag.py,chunks.py}`, `ui/src/lib/{api.ts,chunkSearch.ts,components/{ChunkResults,RagResults}.svelte}`,
  `ui/src/routes/{leitlinien/+page.svelte,entry/[id]/+page.svelte}`, `AGENTS.md`
- **LOC added**: ~610 | **LOC total**: ~27,270

### Fixed
- **Suche/Bibliothek file display** — the chunk-endpoint refactor had renamed `_is_path_allowed`
  → `_is_awmf_path_allowed`, leaving the entry view/info/download endpoints calling a missing name
  (`NameError` broke in-page file display). Restored `_is_path_allowed` (entry `ALLOWED_ROOTS`)
  alongside the new AWMF variant.
- **config** — added `llamaserver_url`/`llamaserver_api_key` fields (were `.env`-only, so
  `settings.llamaserver_url` failed at runtime).

### Notes
- `api/config.py`, `api/models.py`, `api/routers/search.py`, `api/routers/files.py`,
  `search/{rag.py,chunks.py}`, `ui/src/lib/{api.ts,chunkSearch.ts,components/{ChunkResults,RagResults}.svelte}`,
  `ui/src/routes/leitlinien/+page.svelte`, `AGENTS.md`
- **LOC added**: ~480 | **LOC total**: ~27,080

## [1.13.0] - 2026-08-25
### Added
- **AWMF chunks fold-in + dedicated `/leitlinien` search page** — Loaded the AWMF guideline corpus
  (594,079 chunks, 1,757 documents) from the Leitlinien embedding KB into pgvector and surfaced it
  as a standalone page. `chunks` (universal, `source_type='awmf'`) + `awmf_documents` tables (alembic
  `003`), German FTS trigger, `Vector(2048)` embeddings with slice→normalize matching the corpus.
  `POST`-free `GET /api/v1/search/chunks` endpoint (instruct-prefix query via the CPU sidecar
  `:8081` → exact cosine `<=>` top-k). New `scripts/import_awmf_chunks.py` loads the artifacts
  bit-identically (no re-embed). `ui/src/routes/leitlinien/` page with `ChunkResults` component +
  history; dashboard + sidebar "Leitlinien" entry.
- **Files**: `alembic/versions/003_awmf_chunks.py`, `database/models.py`, `api/config.py`,
  `api/models.py`, `api/routers/search.py`, `search/chunks.py`, `scripts/import_awmf_chunks.py`,
  `ui/src/lib/{api.ts,chunkSearch.ts,components/ChunkResults.svelte}`,
  `ui/src/routes/{leitlinien/+page.svelte,+layout.svelte,+page.svelte}`, `tests/test_chunk_search.py`,
  `plans/awmf-foldin-dashboard.md`
- **LOC added**: ~200 | **LOC total**: ~17,500

### Notes
- **pgvector ANN unavailable at 2048 dims** — HNSW and IVFFLAT hard-cap at 2000 dims; the corpus
  vectors are 2048. Serving uses exact `<=>` scan (~5 s on 594k×2048, accepted tradeoff). FAISS
  remains the standalone index; pgvector exact ranking verified identical to it.
- **Pre-existing** broken entry Hybrid tab (embeds via `:8080`, no `--embedding`) and 8 `test_search.py`
  failures are untouched by this change.

## [1.12.2] - 2026-08-04
## [1.12.3] - 2026-08-24 14-03
### Added
- **Unified embedding rewrite plan** — New `plans/unified-embedding-rewrite.md` (235 LOC): chunk-level, vector-first rewrite over one unified embedding model (Qwen3-Embedding-8B Q6_K, 2048-dim MRL), re-embedding the whole library, adding `awmf_documents` + universal `chunks` table (HNSW), a chunk-search endpoint, and a citation-answer chat. Absorbs the AWMF fold-in (Leitlinien plan P6). Total LOC ~28,370.

## [1.12.2] - 2026-08-04
### Changed
- **Bibliothek → file-manager browse (original folder structure)** — Rebuilt the library page as a two-pane file manager that mirrors the real on-disk layout: left folder tree + right pane showing the current folder's subfolders and files, with breadcrumb and up-button navigation. The tree is built from each entry's raw `source_path` (relative to the source root), so **original folder names and nesting are preserved** (`3_Leitlinien/AWMF_Leitlinien/DEGAM_Allgemeinmedizin/053-001_Brennen-beim-Wasserlassen/…`). Numeric folder prefixes are stripped for display (`1_SOPs` → `SOPs`); **folders are listed before files** (files attach to their real parent folder — a fix for filenames being misclassified as folders), files sorted by title. All tree nodes are shown as folder icons (leaf folders that contain only files no longer render with a file icon). Search filters files/folders live. `ui/src/routes/bibliothek/+page.svelte` (1060 → 405 lines).

## [1.12.1] - 2026-08-04
### Changed
- **Bibliothek redesign (flat folder overview)** — Replaced the 4-level nested expandable tree (Kategorie → Unterkategorie → Topic → Fachgebiet) with a streamlined 2-level browse: category fold-out rows with clickable **folder chips** (specialty folders, each with entry count), clicking a chip shows that folder's entries as a plain list. Entries grouped by the 2nd path segment of `source_hierarchy`. Reduced page from 1060 → 823 lines (`ui/src/routes/bibliothek/+page.svelte`).

## [1.12.0] - 2026-08-04
### Removed
- **Entry `status` attribute entirely** — The publish-status field (entwurf/review/freigegeben/archiviert) is removed across the whole stack:
  - **DB**: dropped `knowledge_entries.status` column (+ its index) and removed it from the `v_entry_search` view; recreated the view. The column is gone from the live database.
  - **Backend**: removed `EntryStatus` enum, `status` from `EntryCreate`/`EntryUpdate`/`EntryResponse`/`SearchResultItem`/`StatsOverview.entries_by_status`, all `status` filters in `entries`/`search`/`faceted`/`fts`/`hybrid`, the stats status aggregation, and the `status="entwurf"` defaults in import/files scripts.
  - **Frontend**: removed the status badge on entry detail, the Status form field on entry create/edit, the Status search facet + filter, the dashboard "Freigegeben"/"In Review" stat rows, and `entries_by_status` from the API client.

## [1.11.7] - 2026-08-04
### Removed
- **Dashboard "Status" distribution card** — Removed the status distribution panel and its `statusStats`/`statusColors` derived state from the dashboard (`ui/src/routes/+page.svelte`). The entry-status stat cards (Freigegeben / In Review) remain.

## [1.11.6] - 2026-08-04
### Added
- **Fachgebiet from folder names** — For the `5_Fächer` source, entries now derive their Fachgebiet from the top-level specialty subfolder (no AI/Llamaserver needed). `FolderHierarchyStrategy.propose` emits a `FACHGEBIET` proposal for the first path segment (e.g. `Kardiologie/` → Fachgebiet "Kardiologie"); deeper topic/author subfolders stay as hierarchy labels only. Backfilled 164 existing `5_Fächer` entries so the dashboard "Nach Fachgebiet" chart is populated.
- **Files**: `api/services/tagging_service.py`

## [1.11.5] - 2026-08-04
### Changed
- **Dashboard Übersicht as list** — Replaced the per-value stat boxes with a single plain list (one bordered container, rows with label left / value right); removed now-unused `StatCard` component import and `BookOpen`/`Sparkles`/`FolderOpen` icons (`ui/src/routes/+page.svelte`)

## [1.11.4] - 2026-08-04
### Changed
- **Collapsible sidebar** — Sidebar toggle button in the app header collapses the nav to icon-only (74px) and expands it back; state persisted in `localStorage`; mobile bottom-nav ignores the collapsed state (`ui/src/routes/+layout.svelte`)
- **Smaller dashboard buttons** — Quick-action cards compacted: reduced padding, smaller icons (20px), smaller icon tiles (38px) and labels; grid min column 240→200px (`ui/src/routes/+page.svelte`)

## [1.11.3] - 2026-08-04
### Added
- **Delete entry button** — Entry detail page (`/entry/{id}`) now has a "Löschen" button next to "Bearbeiten"; confirms before deleting, then navigates to the dashboard. Backed by `DELETE /entries/{id}` (204). Uses `entriesApi.delete()`.
- **Files**: `ui/src/lib/api.ts`, `ui/src/routes/entry/[id]/+page.svelte`

## [1.11.2] - 2026-08-04
### Added
- **Auto-open browser** — `start.sh` now opens `http://localhost:5175` in the default browser after the frontend starts (`xdg-open`, with `open`/`powershell` fallbacks)
- **Files**: `start.sh`

## [1.11.1] - 2026-08-03
### Changed
- **Dev port** — Frontend serving port changed from 5173 → 5175 (`vite.config.ts`, `api/config.py` CORS, `start.sh`, docs)
- **Docker security** — `start.sh` and `stop.sh` use `sudo docker-compose` instead of bare `docker-compose` (no docker group membership required)
- **Files access 403 fix** — `ALLOWED_ROOTS` was hardcoded to an old absolute content path; now computed dynamically from workspace parent (`api/routers/files.py`)

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.11.0] - 2026-06-05 15-30
### Removed
- **`falltyp` column** — Dropped from `knowledge_entries`; all data migrated to `dokumenttyp` (human labels via `CATEGORY_LABELS`)
- **`EntryFalltyp` enum** — Removed from API models
- **Search/entry filters** — `kategorie`/`falltyp` params replaced by `dokumenttyp`
### Added
- **Migration** — `scripts/migrate_falltyp_to_dokumenttyp.py` (backfill, drop column, recreate `v_entry_search`)
- **Helper** — `dokumenttyp_from_category()` in `hierarchy_labels.py`
### Changed
- **API** — `/entries/categories` → `/entries/dokumenttypen`; stats/recent use `dokumenttyp`
- **Import/sync** — Batch import and file sync set `dokumenttyp` from source category slug
- **Frontend** — Search filters renamed Kategorien → Dokumenttyp; eingabe/bibliothek/ActivityList use `dokumenttyp`
- **Files**: `database/schema.sql`, `database/models.py`, `api/models.py`, `api/services/entry_service.py`, `search/*`, `ui/src/lib/stores/search.ts`, `ui/src/lib/components/FacetFilters.svelte`, `ui/src/routes/eingabe/+page.svelte`, `ui/src/routes/bibliothek/+page.svelte`
- **LOC added**: ~120 | **LOC total**: ~28,770

## [1.10.2] - 2026-06-05 14-00
### Changed
- **Edit page** — Removed "Curated Tags" heading; removed Status and Falltyp fields (values unchanged on save)

## [1.10.1] - 2026-06-05 13-45
### Fixed
- **API crash on restart** — Circular import between `hierarchy_labels` and `tagging_service` (lazy import)
- **Edit page** — MultiSelect migrated to Svelte 5 `$bindable`; curated fachgebiete load (`reviewed_only=true` + entry tags merged)
- **Eingabe** — MultiSelect `oncreate` callback after component migration

## [1.10.0] - 2026-06-05 14-30
### Added
- **TaggingService** — Unified tagging with FolderHierarchy, LLM, and Manual strategies (`api/services/tagging_service.py`)
- **Derived labels** — `source_hierarchy` JSONB + `dokumenttyp` on entries; folder labels stored as metadata, not M2M pollution
- **Lookup metadata** — `needs_review` + `source` columns on `fachgebiete`, `diagnosen`, `symptome`
- **API** — `POST /entries/{id}/classify`, `POST /entries/{id}/tag-suggestions/apply`, `POST /resolve-labels`, `GET /pending-review`
- **Migration** — `scripts/migrate_tagging_architecture.py`
### Changed
- **Edit page** — MultiSelect for curated tags, KI classify button, folder-label banner (only when actionable)
- **Eingabe KI apply** — Uses `/resolve-labels` to create missing lookup rows
- **Search** — `v_entry_search` unions `source_hierarchy` with curated fachgebiete; `dokumenttyp` facet
- **Files**: `api/services/*`, `database/models.py`, `database/schema.sql`, `ui/src/routes/entry/[id]/edit/*`, `ui/src/routes/eingabe/+page.svelte`, `tests/test_tagging_service.py`
- **LOC added**: ~650 | **LOC total**: ~28,650

## [1.9.5] - 2026-06-05 13-15
### Added
- **Edit-page tag auto-suggest** — Folder-path Fachgebiet suggestions on `/entry/{id}/edit`; auto-selects existing matches; banner with resolve for missing lookup rows
- **API** — `GET /entries/{id}/tag-suggestions`, `POST /entries/{id}/tag-suggestions/resolve`
- **Files**: `api/services/hierarchy_labels.py`, `api/services/entry_service.py`, `api/routers/entries.py`, `ui/src/routes/entry/[id]/edit/*`, `tests/test_hierarchy_labels.py`
### Changed
- **Classification list limits** — `/fachgebiete`, `/diagnosen`, `/symptome` default limit raised to 10000 for edit/create forms
- **LOC added**: ~180 | **LOC total**: ~28,000

## [1.9.4] - 2026-06-05 12-32
### Fixed
- **Search filter options** — Load from `/api/v1/search/filters` (tags actually on entries with counts) instead of full `/fachgebiete` table with orphaned prefixed names
- **Fachgebiet alias consolidation** — Merge prefixed records (`AWMF_Leitlinien` → `Leitlinien`, etc.) via `consolidate_fachgebiet_aliases()`
- **Files**: `ui/src/lib/stores/search.ts`, `ui/src/lib/components/FacetFilters.svelte`, `api/services/hierarchy_labels.py`

## [1.9.3] - 2026-06-05 12-20
### Changed
- **Human-readable hierarchy tags** — Strip org prefixes (`DRG_Radiologie` → `Radiologie`, `DEGAM_Leitlinien` → `Leitlinien`); exact-match resolution avoids fuzzy re-linking to old names
- **Backfill** — `--replace-stale-tags` removes raw folder tags before applying humanized labels
- **Files**: `api/services/hierarchy_labels.py`, `pipeline/classification_resolver.py`, `scripts/backfill_hierarchy_labels.py`, `tests/test_hierarchy_labels.py`

## [1.9.2] - 2026-06-05 12-10
### Added
- **Folder-hierarchy labeling** — Subfolders under source roots (up to 4 levels) become `Fachgebiet` tags; deepest folder → `unterkategorie`
- **`api/services/hierarchy_labels.py`** — Shared extraction/apply logic for batch import, sync, and backfill
- **`scripts/backfill_hierarchy_labels.py`** — Backfill existing entries from `source_path` (ran: 2639 updated, 6629 tags added)
- **Files**: `api/services/batch_import_worker.py`, `api/routers/files.py`, `tests/test_hierarchy_labels.py`
- **LOC added**: ~200 | **LOC total**: ~27,820

## [1.9.1] - 2026-06-05 12-00
### Fixed
- **Suche page filtering** — Facettiert tab now calls `/api/v1/search/faceted`; filter clear re-runs search; tab switch re-executes query
- **Search filter params aligned** — `/api/v1/search` accepts `fach`, `diagnose`, `symptom`, `kategorie`, `status` (same as `/entries`); FTS and hybrid backends apply multi-value classification filters
- **Faceted status/kategorie** — `/api/v1/search/faceted` supports `status` and `kategorie` filters
- **Files**: `ui/src/lib/stores/search.ts`, `ui/src/lib/components/FacetFilters.svelte`, `ui/src/routes/search/+page.svelte`, `api/routers/search.py`, `search/fts.py`, `search/hybrid.py`, `search/faceted.py`, `search/common_filters.py`, `tests/test_search.py`
- **LOC added**: ~120 | **LOC total**: ~27,620

## [1.9.0] - 2026-05-29 14-00
### Changed

- **P0: Materialized view → regular view** — Eliminated stale search results
  - Replaced `mv_entry_search` materialized view with `v_entry_search` regular view in `database/schema.sql`
  - Removed `refresh_entry_search_view()` function and all MV-specific indexes
  - Updated `search/faceted.py` to query `v_entry_search` instead of `mv_entry_search`
  - Made `refresh_search_index()` a no-op (kept for backward compatibility)
  - Removed refresh from `/api/v1/search/refresh-index` endpoint
  - **Files**: `database/schema.sql`, `search/faceted.py`, `api/routers/search.py`, `scripts/migrate_add_unterkategorie.py`

- **P1: Non-blocking pipeline** — Summarization no longer blocks ASGI workers
  - Wrapped `orchestrator.summarize_file()` in `asyncio.to_thread()` in `api/routers/summarize.py`
  - **Files**: `api/routers/summarize.py`

- **P1: Regression tests** — First automated test suite
  - Created `tests/` directory with pytest infrastructure
  - `tests/test_search.py`: FTSQueryBuilder tokenizer tests, FacetedSearchQuery SQL generation, refresh_search_index no-op contract
  - `tests/test_pipeline.py`: File type detection parametrized tests, extension set consistency, ProcessingResult contract, summarize skill validation
  - **New files**: `tests/__init__.py`, `tests/conftest.py`, `tests/test_search.py`, `tests/test_pipeline.py`

- **P2: EntryService extraction** — Thin routers, testable business logic
  - Created `api/services/entry_service.py` with `EntryService` class containing all CRUD logic
  - Refactored `api/routers/entries.py` from 317 to 105 lines (68% reduction)
  - Router now handles only HTTP concerns: validation, auth, error mapping
  - **Files**: `api/services/entry_service.py` (new), `api/routers/entries.py`

- **P2: Fixed `zusammefassung` typo** — Column renamed from `zusammefassung` → `zusammenfassung`
  - Updated `database/schema.sql` (column, trigger, view, comments)
  - Updated `database/models.py` (SQLAlchemy column)
  - Updated `api/models.py` (Pydantic fields in EntryBase, EntryUpdate, SearchResultItem)
  - Updated all routers: `classifications.py`, `files.py`, `search.py`, `stats.py`, `summarize.py`
  - Updated search modules: `fts.py`, `faceted.py`, `hybrid.py`
  - Updated services: `entry_service.py`, `batch_import_worker.py`
  - Updated scripts: `generate_embeddings.py`, `import_files_as_links.py`
  - Updated `database/seeds.sql` (all INSERT column lists)
  - Updated `database/AGENTS.md` anti-pattern note
  - **Note**: Requires database migration (`ALTER TABLE knowledge_entries RENAME COLUMN zusammefassung TO zusammenfassung`) to apply

- **P3: Package entry points** — Proper CLI commands
  - Added `[project.scripts]` to `pyproject.toml`: `medwiss-import`, `medwiss-pipeline`, `medwiss-embeddings`
  - Added `scripts*` to `[tool.setuptools.packages.find]`
  - **Files**: `pyproject.toml`

- **P3: Merged config systems** — Single import point
  - `config/__init__.py` now re-exports `api.config.settings` and `api.config.Settings`
  - Consumers can do `from config import settings, load_sources` from one place
  - **Files**: `config/__init__.py`

- **P2: Frontend `zusammefassung` typo fix** — TypeScript interfaces and property accesses updated
  - Fixed `zusammefassung` → `zusammenfassung` in 7 frontend files (17 locations)
  - `ui/src/lib/api.ts`: `EntryResponse`, `EntryCreate`, `SearchResultItem` interfaces
  - `ui/src/lib/components/ActivityList.svelte`: property accesses
  - `ui/src/lib/stores/search.ts`: property accesses in `executeSearch()`
  - `ui/src/routes/bibliothek/+page.svelte`: search filter
  - `ui/src/routes/entry/[id]/+page.svelte`: display conditional
  - `ui/src/routes/entry/[id]/edit/+page.svelte`: local variable, pendingSummary callback, API payload key, textarea binding
  - `ui/src/routes/eingabe/+page.svelte`: API payload key
  - Also added `source_path` and `file_hash` to TS `EntryResponse` interface (were returned by API but missing from frontend types)
  - **Files**: 8 files updated

- **P2: Bibliothek 4-level hierarchy** — Topic-level grouping from `source_path`
  - Added `TopicGroup` level between Subcategory and Fachgebiet in the Bibliothek tree
  - `extractTopic()`: parses `source_path` to find directory one level deeper than `unterkategorie`
  - `formatTopicName()`: transforms raw directory names to human-readable labels
    - Strips organization prefixes (e.g., `DGKJP_Kinderpsychiatrie` → `Kinderpsychiatrie`)
    - Replaces underscores with spaces
    - Supports explicit mapping via `topicDisplayNameMap` for custom transformations
  - New `expandedTopic` state with toggle controls (Set-based, multi-expand)
  - Updated `getFilteredGroups()` to walk the full 4-level tree during search
  - New `Layers` icon and topic section styles
  - **Files**: `ui/src/routes/bibliothek/+page.svelte`, `ui/src/lib/api.ts`
### Added

#### Dynamic source folder discovery (no more hardcoded YAML)
- **Created `config/discover_sources.py`** - scans filesystem to auto-detect source folders
  - `discover_sources()`: discovers all numbered folders (`1_SOPs`, `2_Leitlinien`, etc.) and `Fortbildung`
  - Derives category from folder name (strips number prefix, normalizes umlauts)
  - Returns structured config with `name`, `path`, `category`, `description`, `file_types`
  - **New file**: `config/discover_sources.py` (~78 lines)

- **Created `/api/v1/sources` endpoint** (`api/routers/sources.py`)
  - Returns all source configs with `display_name` (strips `1_`, `2_` prefixes)
  - Exposes `category`, `file_types`, `default_fachgebiete`, `subcategories`
  - **New file**: `api/routers/sources.py` (~43 lines)

- **`config/__init__.py` updated** to merge discovered + YAML sources
  - `load_sources()` now calls `discover_sources()` first, then applies YAML overrides
  - Fallback behavior: if discovery fails, falls back to YAML only
  - **Files changed**: `config/__init__.py` (~20 lines changed)

#### Subcategory (unterkategorie) support for knowledge entries
- **Database schema**: Added `unterkategorie VARCHAR(100)` nullable column to `knowledge_entries` table
  - Stores subfolder names (e.g., "SOPs Notaufnahme", "Kardio", "AWMF_Leitlinien")
  - Added index `idx_knowledge_entries_unterkategorie`
  - Updated materialized view `mv_entry_search` to include `unterkategorie`
  - Added index `idx_mv_entry_search_unterkategorie` on materialized view
  - **Files changed**: `database/schema.sql` (~5 lines added)

- **SQLAlchemy model**: Added `unterkategorie: Mapped[Optional[str]]` field to `KnowledgeEntry`
  - **Files changed**: `database/models.py` (1 line added)

- **Pydantic models**: Added `unterkategorie` field to `EntryBase`, `EntryUpdate`, `EntryResponse`, and `SearchResultItem`
  - Field: `Optional[str] = Field(None, max_length=100, description="Subfolder name")`
  - **Files changed**: `api/models.py` (~4 lines added)

- **Dynamic subfolder discovery**: `config/discover_sources.py` extended
  - Added `discover_subcategories(source_path)`: scans immediate subdirectories of each source folder
  - Returns sorted list of subfolder names (hidden folders excluded)
  - Wired into `discover_sources()` output as `subcategories` field
  - **Files changed**: `config/discover_sources.py` (~20 lines added)

- **Sources API exposes subcategories**: `api/routers/sources.py`
  - `SourceInfo` model now includes `subcategories: List[str]`
  - Passes through from `load_sources()` to API response
  - **Files changed**: `api/routers/sources.py` (2 lines added)

- **Batch import auto-detects subcategory**: `api/services/batch_import_worker.py`
  - `_create_entry_from_result()` extracts subfolder from file path using `Path.relative_to()`
  - Example: `../1_SOPs/SOPs Notaufnahme/file.pdf` -> `unterkategorie="SOPs Notaufnahme"`
  - Files directly in source folder (no subfolder) get `unterkategorie=None`
  - **Files changed**: `api/services/batch_import_worker.py` (~12 lines added)

- **API response fix**: `api/routers/entries.py`
  - `_entry_to_response()` now includes `unterkategorie=entry.unterkategorie`
  - Was missing, causing all entries to show `unterkategorie=null` in frontend
  - **Files changed**: `api/routers/entries.py` (1 line added)

#### Migration scripts
- **Created `scripts/migrate_add_unterkategorie.py`**
  - Adds `unterkategorie` column, creates index, refreshes materialized view
  - Supports `--dry-run` mode, idempotent
  - **New file**: `scripts/migrate_add_unterkategorie.py` (~60 lines)

- **Created `scripts/migrate_falltyp_from_quelle.py`** (4-phase migration)
  - Phase 1: Parses `quelle` field to derive correct `falltyp` from source folder path
  - Phase 2: Cleans up legacy falltyp values (`richtlinien` -> `leitlinien`, `studie` -> `studien`, etc.)
  - Phase 3: Deletes demo categories (`forschung`, `lehrfall`, `fall`, `nachschlagen`) - 185 entries removed
  - Phase 4: Maps singular forms to plural (`infoblatt` -> `infoblaetter`, `fragebogen` -> `frageboegen`, etc.)
  - Result: 2,560 entries correctly categorized across 9 clean categories
  - **New file**: `scripts/migrate_falltyp_from_quelle.py` (~280 lines)

### Changed

#### Bibliothek frontend - dynamic categories + subcategory display
- **Dynamic category loading**: `ui/src/routes/bibliothek/+page.svelte`
  - Fetches `/api/v1/sources` on mount to get real category names and colors
  - Falls back to hardcoded maps if API fails
  - Uses `display_name` from API instead of raw folder names (shows "SOPs" not "1_SOPs")
  - **Files changed**: `ui/src/routes/bibliothek/+page.svelte` (~40 lines changed)

- **Subcategory grouping**: `ui/src/routes/bibliothek/+page.svelte`
  - Entries grouped by `unterkategorie` within each category
  - New `SubcategoryGroup` interface: `{ subcategoryName, fachGroups, totalCount }`
  - Entries without subcategory placed in "Allgemein" group (sorted first)
  - Subcategories sorted alphabetically
  - Each subcategory is collapsible with `expandedSubcategory` state (Set)
  - Subcategory headers styled with `Tag` icon and entry count badge
  - **Files changed**: `ui/src/routes/bibliothek/+page.svelte` (~120 lines added/changed)

- **Dashboard category display**: `ui/src/routes/+page.svelte`
  - Uses API `display_name` for category labels instead of hardcoded map
  - **Files changed**: `ui/src/routes/+page.svelte` (~5 lines changed)

#### API models - relaxed enum validation (from v1.8.1)
- `EntryBase.falltyp`: `Optional[EntryFalltyp]` -> `Optional[str]`
- `EntryBase.schwierigkeit`: `Optional[EntrySchwierigkeit]` -> `Optional[str]`
- `EntryBase.status`: `EntryStatus` -> `str`
- Prevents 500 errors when database contains category values not in enum
- **Files changed**: `api/models.py` (~6 lines changed)

#### Source configuration
- `config/sources.yaml`: Updated folder numbering to match actual filesystem
  - `7_Frageboegen`, `8_Infoblaetter` instead of incorrect numbers
  - **Files changed**: `config/sources.yaml` (~2 lines changed)

### Fixed

#### Bibliothek showing wrong/duplicate categories
- **Root cause**: Categories were hardcoded in frontend with outdated values; `CATEGORY_MAP` in migration script mapped plurals to singulars; batch import used `falltyp="unbekannt"` instead of `source.category`
- **Fixes applied**:
  - `api/services/batch_import_worker.py:268`: `falltyp=source.category` (was hardcoded `falltyp="unbekannt"`)
  - `scripts/migrate_falltyp_from_quelle.py`: `CATEGORY_MAP` keeps plural forms (`infoblaetter`, `frageboegen`, `faecher`)
  - Removed demo categories: `forschung` (49 entries -> `studie`), `lehrfall` (deleted), `fall` (deleted), `nachschlagen` (185 entries deleted)
  - Fixed duplicate `Frageboegen` / `Fragebogen` by standardizing on plural form
- **Result**: 9 clean categories matching actual source folders

#### Frontend TypeScript interfaces
- `ui/src/lib/api.ts`: Added `unterkategorie: string | null` to `EntryResponse`
- `ui/src/lib/api.ts`: Added `subcategories: string[]` to `SourceInfo`
- **Files changed**: `ui/src/lib/api.ts` (~3 lines added)

### Statistics
- **Total LOC**: ~27,150 (was ~26,950)
- **Lines Added**: ~620
- **Lines Removed**: ~420
- **Net Change**: +200 lines
- **Files Added**: 4 (`discover_sources.py`, `sources.py`, `migrate_add_unterkategorie.py`, `migrate_falltyp_from_quelle.py`)
- **Files Modified**: 12

### QA Testing
- `bun run check` passes with zero new errors in modified files
- `bun run build` completes successfully (12.35s)
- API `/sources` returns 10 sources with correct subcategories
- API `/entries` returns entries with correct `unterkategorie` values
- Database: 2,560 entries across 9 categories with 57 distinct subcategories
- All remaining diagnostics are pre-existing in unrelated files
## [1.8.1] - 2026-05-20 10-00

### Changed

#### Sync Behavior - Delete orphaned entries instead of archiving
- **File sync now hard-deletes database entries when source files are removed**
  - `api/services/file_sync.py`: Replaced `archive_entry()` with `delete_entry()` - permanently removes DB rows via `db.delete()` + `db.commit()`
  - Junction table rows (`entry_fach`, `entry_diagnose`, `entry_symptom`) are automatically cleaned up by database ON DELETE CASCADE
  - `SyncResult` dataclass: renamed field `archived` → `deleted`
  - `run_sync()`: now calls `delete_entry()` and tracks `result.deleted`
  - **Files changed**: `api/services/file_sync.py` (~10 lines changed)

- **Source watcher real-time deletion handling updated**
  - `api/services/source_watcher.py`: `on_deleted()` now calls `sync_service.delete_entry()` instead of `archive_entry()`
  - **Files changed**: `api/services/source_watcher.py` (~3 lines changed)

- **Admin sync endpoint (`/files/admin/sync`) updated**
  - `api/routers/files.py`: Response `changes_detected` now returns `deleted` instead of `archived`
  - **Files changed**: `api/routers/files.py` (~5 lines changed)

- **Lightweight sync endpoint (`/files/sync`) updated**
  - `api/routers/files.py`: Dead-path detection now uses `db.delete(entry)` instead of setting `status = "archiviert"`
  - Response message changed from "archiviert" to "gelöscht"
  - **Files changed**: `api/routers/files.py` (~10 lines changed)

- **Dashboard UI updated to show deletions**
  - `ui/src/lib/components/SyncStatusDashboard.svelte`: "Archiviert" label changed to "Einträge entfernt" with `deleted` count
  - `ui/src/routes/+page.svelte`: Dashboard sync result summary shows "gelöscht" instead of "archiviert"
  - **Files changed**: `ui/src/lib/components/SyncStatusDashboard.svelte`, `ui/src/routes/+page.svelte` (~4 lines changed)

- **Test script updated**
  - `scripts/test_file_sync.py`: Output now shows "Deleted" instead of "Archived"
  - **Files changed**: `scripts/test_file_sync.py` (~1 line changed)

### Fixed

#### Bibliothek 500 Error
- **Root cause**: Pydantic enum validation rejected database `falltyp` values that didn't match `EntryFalltyp` enum
  - Source config categories (e.g., `red_flags`, `frageboegen`, `infoblaetter`, `faecher`, `faelle`) didn't match enum values (`redflag`, `fragebogen`, `infoblatt`, `fach`, `fall`)
  - When `/entries` returned entries with these "invalid" falltyp values, `EntryResponse` validation failed with HTTP 500

- **Backend fix**: Relaxed Pydantic validation to accept any string
  - `api/models.py`: Changed `EntryBase.falltyp` from `Optional[EntryFalltyp]` → `Optional[str]`
  - `api/models.py`: Changed `EntryBase.schwierigkeit` from `Optional[EntrySchwierigkeit]` → `Optional[str]`
  - `api/models.py`: Changed `EntryBase.status` from `EntryStatus` → `str`
  - `api/models.py`: Changed `EntryUpdate` fields similarly
  - `SearchResultItem` already used `str` types, so search continued working
  - **Files changed**: `api/models.py` (~6 lines changed)

- **Frontend fix**: Updated Bibliothek category mappings to match actual source config categories
  - `ui/src/routes/bibliothek/+page.svelte`: Updated `categoryLabels`, `categoryColors`, and `preferredOrder` to use actual DB values: `red_flags`, `frageboegen`, `infoblaetter`, `faecher`, `faelle`
  - **Files changed**: `ui/src/routes/bibliothek/+page.svelte` (~15 lines changed)

- **Dashboard fix**: Updated category color map and stat lookups to use raw falltyp values
  - `ui/src/routes/+page.svelte`: `categoryColors` keys now use raw values (`sop`, `leitlinien`, `red_flags`, etc.)
  - `ui/src/routes/+page.svelte`: `categoryData` lookups use `['sop']`, `['leitlinien']`, etc.
  - **Files changed**: `ui/src/routes/+page.svelte` (~8 lines changed)

## [1.8.0] - 2026-05-19 10-30

### Changed

#### UI/UX - Dashboard & Navigation Cleanup
- **Removed redundant `/stats` page**
  - Deleted `ui/src/routes/stats/+page.svelte` (626 lines removed)
  - Removed duplicate "Statistiken" navigation items from sidebar (`ui/src/routes/+layout.svelte`)
  - Removed stats quick-action card from dashboard
  - **Rationale**: Statistics were already displayed in the dashboard, making the separate page redundant

- **Moved distribution widgets to Dashboard**
  - Added "Kategorien" and "Status" bar-chart widgets to `ui/src/routes/+page.svelte`
  - Uses real API data (`entries_by_category`, `entries_by_status`) with color mapping
  - Added `calculatePercentage()` helper and responsive CSS for distribution section
  - Added color maps for all 11 categories and 3 statuses
  - **LOC changed**: +158/-0 in dashboard

#### UI/UX - Bibliothek Reorganization
- **Complete rewrite of Bibliothek page** (`ui/src/routes/bibliothek/+page.svelte`)
  - Categories now display as expandable folder cards (2 per row on desktop)
  - Folder icons (`Folder`/`FolderOpen`) with category-specific colors
  - Accordion behavior: only one category expanded at a time
  - Entries grouped by primary `Fachgebiet` inside expanded categories
  - Fachgebiet groups sorted alphabetically; entries sorted by title
  - Categories follow specified priority: SOPs → Red Flags → Fragebögen → Studien → Leitlinien → Infoblätter → Fälle → Fächer
  - Compact single-line entry cards showing icon, title, file badge, date, arrow
  - Responsive: collapses to 1 column on mobile
  - Uses typed API client (`entriesApi.getAll()`) instead of raw `fetch`
  - Search filters across titles, summaries, sources, and Fachgebiet names
  - **LOC changed**: +159/-485 (net: -326)

#### UI/UX - Entry Detail Navigation
- **Smart back button** (`ui/src/routes/entry/[id]/+page.svelte`)
  - Changed from hardcoded `<a href="/search">` to `<button onclick={() => history.back()}>`
  - Label changed from "Zurück zur Suche" → "Zurück"
  - Now returns user to wherever they came from (Bibliothek, Search, Dashboard, etc.)
  - **LOC changed**: ~0

#### Bug Fixes
- **Fixed "Top Diagnosen" chart showing no data**
  - Root cause: `diagnoseData` was initialized to `[]` and never populated
  - Dashboard only fetched `overview` and `byFach` stats, not diagnosis stats
  - Added `DiagnoseStats` interface and `statsApi.getByDiagnose()` to `ui/src/lib/api.ts`
  - Dashboard now fetches diagnosis stats in parallel and transforms response for chart
  - **Files changed**: `ui/src/lib/api.ts` (+15 lines), `ui/src/routes/+page.svelte`

### Files Modified
| File | Lines | Purpose |
|------|-------|---------|
| `ui/src/routes/stats/+page.svelte` | -626 | Removed redundant stats page |
| `ui/src/routes/+page.svelte` | +158 | Added distribution widgets, removed stats card |
| `ui/src/routes/+layout.svelte` | -8 | Removed duplicate Statistiken nav items |
| `ui/src/routes/bibliothek/+page.svelte` | +159/-485 | Complete folder-style rewrite |
| `ui/src/routes/entry/[id]/+page.svelte` | ~0 | Smart back button |
| `ui/src/lib/api.ts` | +15 | DiagnoseStats + getByDiagnose endpoint |

### Statistics
- **Total LOC**: ~26,951 (was ~23,400)
- **Lines Added**: +332
- **Lines Removed**: -1,119
- **Net Change**: -787 lines
- **Files Removed**: 1
- **Files Modified**: 5

### QA Testing
- `bun run check` passes with zero new errors/warnings in modified files
- All remaining diagnostics are pre-existing in unrelated files

## [1.7.6] - 2026-04-18 16-45

### Fixed

#### UI (medwiss-db/ui/)
- **Fixed edit page not receiving summary from navigation state**
  - Root cause: Edit page tried to read `data.summaryFromState` but load function doesn't return this property
  - Summary is passed via SvelteKit navigation state (`goto` with `state` option), not load data
  - Changed to use `$page.state.summary` from `$app/state` (Svelte 5 pattern)
  - Added reactive `$effect` to check for summary and append to `zusammenfassung` field
  - Summary is appended with separator (`\n\n---\n\n`) if existing content present
  - Visual indication (summary banner + AI badge) shows when summary was applied
  - **LOC changed:** ~30 lines in `ui/src/routes/entry/[id]/edit/+page.svelte`

## [1.7.5] - 2026-04-18 15-30

### Added

#### Infrastructure (medwiss-db/)
- **Added Llamaserver startup to start.sh**
  - `start.sh`: Now automatically starts Llamaserver with `--embeddings` flag if available at `/app/llama-server`
  - Includes verification step to check if embeddings support is enabled
  - Properly passes `LOCAL_API_KEY` environment variable for authentication
  - Added cleanup to stop Llamaserver on script exit
  - Displays Llamaserver URL in startup summary

## [1.7.4] - 2026-04-18 15-15

### Fixed

#### Configuration (medwiss-db/api/)
- **Fixed Llamaserver API key not reading from environment**
  - Root cause: `llamaserver_api_key` field had literal `"$LOCAL_API_KEY"` default instead of env var
  - Changed to `Field(default="", alias="LOCAL_API_KEY")` to properly read from environment
  - Environment variable `LOCAL_API_KEY` is now correctly sourced
  - **Note**: Llamaserver needs `--embeddings` flag to support vector generation
    - Currently running without embeddings support (returns 501 error)
    - Hybrid search falls back to FTS-only mode gracefully

## [1.7.3] - 2026-04-18 15-00

### Fixed

#### Search (medwiss-db/search/)
- **Fixed all three search types**
  - **Full-Text Search (FTS)**: Fixed SQL syntax error in `search/fts.py`
    - Root cause: `:query::text` parameter binding conflict with PostgreSQL cast operator
    - Changed to `CAST(:query AS text)` on lines 248, 251
  - **Faceted Search**: Fixed empty results
    - Root cause: Materialized view `mv_entry_search` not populated after bulk import
    - Refreshed index via `/api/v1/search/refresh-index` endpoint
  - **Hybrid Search**: Working with FTS fallback
    - Uses AI embeddings when llamaserver available, falls back to FTS-only when not
    - Alpha parameter controls FTS vs vector weight (0.0-1.0)
- All search types now return results: FTS ✓, Faceted ✓, Hybrid ✓

## [1.7.2] - 2026-04-18 14-45

### Fixed

#### API Backend (medwiss-db/api/)
- **Fixed PDF opening in new tab instead of inline preview**
  - Root cause: `/files/entries/{id}/view` endpoint missing `Content-Disposition: inline` header
  - `api/routers/files.py`: Added `Content-Disposition: inline` header to view endpoint (line 112)
  - PDFs now display correctly in iframe on entry detail page instead of opening in new tab
  - Download button still forces download via `Content-Disposition: attachment`

## [1.7.1] - 2026-04-18 14-25

### Fixed

#### API Backend (medwiss-db/api/)
- **Fixed bibliothek "Failed to load entries" error**
  - Root cause: Pydantic enum validation rejected database values
  - `api/models.py`: Expanded `EntryFalltyp` enum to include all 13 values used in database
    - Added: `sop`, `studie`, `redflag`, `fragebogen`, `nachschlagen`, `infoblatt`, `fach`, `fall`, `pharma`, `fortbildung`
  - `api/models.py`: Expanded `EntrySchwierigkeit` enum to include `grundlegend`
  - `api/routers/entries.py`: Increased `limit` parameter max from 100 to 10,000
  - **Total LOC**: ~22,150 (unchanged - schema changes only)

## [1.7.0] - 2026-04-17 22-00

### Added

#### Scripts
- `scripts/import_files_as_links.py` - Fast link-only import without OCR
  - Imports 1,377 files in ~22 seconds
  - Creates database entries with absolute paths
  - No text extraction - files are viewed directly
  - Usage: `python scripts/import_files_as_links.py`

#### Data
- **1,377 files imported** from all source folders:
  - 1_SOPs, 2_Leitlinien, 3_Studien, 4_Red Flags
  - 5_Fragebögen, 6_Nachschlagen, 7_Infoblätter
  - 8_Fächer, 9_Fälle, 10_Pharma
  - Fortbildung 2024, 2025, 2026

### Changed
- Database now contains 1,397 total entries (20 seed + 1,377 imported)
- All entries use absolute paths for reliable file serving
- File-first architecture complete - database syncs with filesystem

## [1.0.0] - 2026-04-07 21-00

### Added

#### Database (medwiss-db/database/)
- `schema.sql` - PostgreSQL schema with 9 tables, GIN indexes, triggers
- `seeds.sql` - Test data with 8 fachgebiete, 10 diagnosen, 15 symptome, 20 entries
- `migrations/001_initial_migration.py` - Alembic initial migration
- `alembic.ini` - Alembic configuration

#### API Backend (medwiss-db/api/)
- `main.py` - FastAPI application with CORS, health endpoint
- `config.py` - pydantic-settings configuration management
- `database.py` - SQLAlchemy engine with connection pooling
- `dependencies.py` - JWT auth dependencies (verify_token, require_admin, etc.)
- `models.py` - Pydantic models for API request/response
- `routers/auth.py` - Authentication endpoints (login, register, me)
- `routers/entries.py` - CRUD endpoints for knowledge entries
- `routers/classifications.py` - Classification management endpoints
- `routers/search.py` - Search endpoints (fts, faceted, hybrid)
- `routers/stats.py` - Dashboard statistics endpoints

#### KI Pipeline (medwiss-db/pipeline/)
- `ocr.py` - Tesseract OCR with German language support
- `transcription.py` - Whisper.cpp integration for audio transcription
- `classifier.py` - Llamaserver-based medical content classification
- `embeddings.py` - Vector embedding generation via Llamaserver
- `orchestrator.py` - Pipeline coordination and file routing
- `monitor.py` - Watchdog-based file monitoring
- `prompts/classification.txt` - Classification prompt template

#### Search (medwiss-db/search/)
- `fts.py` - PostgreSQL full-text search (tsvector + pg_trgm)
- `faceted.py` - Faceted navigation with materialized views
- `hybrid.py` - Hybrid search combining FTS + vector similarity

#### Scripts (medwiss-db/scripts/)
- `init_db.py` - Database initialization script
- `run_pipeline.py` - CLI for manual pipeline execution
- `generate_embeddings.py` - Batch embedding generation script

#### Frontend UI (medwiss-db/ui/src/)
- `routes/+page.svelte` - Dashboard with statistics
- `routes/+layout.svelte` - Root layout with navigation
- `routes/search/+page.svelte` - Search interface with 3 modes
- `routes/eingabe/+page.svelte` - Entry form with KI upload
- `lib/api.ts` - API client with axios
- `lib/stores/search.ts` - Search state management
- `lib/stores/entryForm.ts` - Entry form state management
- `lib/components/SearchResults.svelte` - Search results display
- `lib/components/FacetFilters.svelte` - Faceted search filters
- `lib/components/FileUpload.svelte` - Drag & drop file upload
- `lib/components/KIPreview.svelte` - KI processing preview
- `lib/components/MultiSelect.svelte` - Multi-select dropdown
- `lib/components/StatCard.svelte` - Statistics card
- `lib/components/ActivityList.svelte` - Recent activity list
- `lib/components/charts/FachDistribution.svelte` - Pie chart
- `lib/components/charts/DiagnoseBarChart.svelte` - Bar chart

#### Infrastructure
- `docker-compose.yml` - PostgreSQL + pgvector
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project metadata
- `.env.example` - Environment template
- `QUICKSTART.md` - Quick start guide
- `AGENTS.md` - Architecture documentation

### Security
- JWT authentication on all write endpoints
- Role-based access control (Admin/Editor/Viewer)
- Protected POST/PUT/DELETE on entries (Editor+)
- Protected POST/PUT/DELETE on classifications (Admin only)

## [1.0.1] - 2026-04-07 23-25

### Fixed

#### Bug Fixes - Frontend Stability
- **Optional Chaining Fix** (`ui/src/routes/+page.svelte`)
  - Fixed 4 instances of broken optional chaining with bracket notation
  - Changed `stats?.entries_by_category['SOPs']` to `stats?.entries_by_category?.['SOPs']`
  - Prevents runtime crashes when nested properties are undefined
  - Lines changed: +4/-4

- **API Endpoint Correction** (`ui/src/lib/api.ts`)
  - Fixed classifications API endpoints from `/classifications/fachgebiete` to `/fachgebiete`
  - Same fix for `/diagnosen` and `/symptome` endpoints
  - Aligns frontend with backend router structure
  - Lines changed: +3/-3

- **Vite Proxy Configuration** (`ui/vite.config.ts`)
  - Removed erroneous path rewrite rule that stripped `/api` prefix
  - Frontend now correctly proxies to `/api/v1` endpoints
  - Lines changed: +1/-1

#### Dependencies
- **Nix Dev Shell** (`flake.nix`, `.envrc`)
  - Added Nix flake for reproducible development environment
  - Includes Node.js 22, Python 3.12, Docker Compose
  - Direnv integration for automatic shell activation
  - Lines added: ~75

- **Package Compatibility** (`ui/package.json`)
  - Downgraded vite from `^6.0.0` to `^5.4.0`
  - Resolves peer dependency conflict with `@sveltejs/vite-plugin-svelte@4.0.4`
  - Lines changed: +1/-1

### QA Testing Results
- **Lint**: All 25 issues resolved (ruff)
- **API**: 13/15 endpoints functional (2 known issues with FTS search and email validation)
- **Frontend**: npm install succeeds, dev server starts on port 5175
- **Integration**: Dashboard loads, search interface renders, entry form accessible

### Statistics
- **Total Files**: 58 source files
- **Lines of Code**: ~14,976 LOC
- **Languages**: Python, TypeScript, Svelte, SQL

### Dependencies

#### Python (Backend)
- fastapi, uvicorn, pydantic, pydantic-settings
- sqlalchemy, psycopg2-binary, alembic
- python-jose[cryptography], passlib[bcrypt]
- pytesseract, Pillow, pdf2image
- watchdog, httpx, pytest

#### JavaScript (Frontend)
- svelte, @sveltejs/kit, @sveltejs/adapter-static
- axios, chart.js, lucide-svelte
- bun (package manager & runtime)

## [1.2.1] - 2026-04-15

### Fixed

#### Search Status Filter (Critical Bug Fix)
- **Changed search default status** (`api/routers/search.py`, `search/fts.py`)
  - Changed from `status="freigegeben"` to `status=None`
  - Search now shows ALL entries by default (entwurf, review, freigegeben, archiviert)
  - Added status query parameter support to filter by specific status
  - Lines changed: +2/-2

- **Updated materialized view** (`database/schema.sql`)
  - Removed `WHERE ke.status = 'freigegeben'` from `mv_entry_search`
  - Faceted search now includes entries with all statuses
  - Added `trigger_refresh_entry_search()` function for auto-refresh
  - Added `trg_refresh_entry_search` trigger on knowledge_entries table
  - Materialized view refreshes automatically after INSERT/UPDATE/DELETE
  - Lines changed: +12/-2

- **Frontend status filter** (`ui/src/lib/stores/search.ts`, `ui/src/lib/components/FacetFilters.svelte`)
  - Added `status` field to SearchFilters interface
  - Added `setStatusFilter()` action to search store
  - Added status dropdown in FacetFilters component
  - Status options: Alle Status, Entwurf, Review, Freigegeben, Archiviert
  - Updated executeSearch to include status parameter in API calls
  - Lines added: +25

#### Database Engine Consolidation
- **Removed duplicate engine** (`database/models.py`)
  - Removed duplicate `engine`, `SessionLocal`, `Base`, `get_db` from models.py
  - Now imports `Base` from `api.database`
  - Eliminates confusion from two separate SQLAlchemy engines
  - Lines changed: +2/-10

#### Entry Creation Audit Fields
- **Added created_by/updated_by** (`api/routers/entries.py`)
  - `create_entry` now sets `created_by=current_user.id` and `updated_by=current_user.id`
  - `update_entry` now sets `updated_by=current_user.id`
  - Entries now properly track who created/modified them
  - Lines changed: +4/-0

### Files Modified
- `api/routers/search.py` - Default status parameter
- `search/fts.py` - Default status filter
- `database/schema.sql` - Materialized view includes all statuses, added refresh trigger
- `database/models.py` - Import Base from api.database, removed duplicates
- `api/routers/entries.py` - Set created_by/updated_by fields
- `ui/src/lib/stores/search.ts` - Added status filter support
- `ui/src/lib/components/FacetFilters.svelte` - Added status dropdown UI

### Statistics
- **Lines Added**: +43
- **Lines Removed**: -14
- **Net Change**: +29 lines

## [1.2.0] - 2026-04-15

### Added

#### Entry Detail View (Phase 1)
- **Entry Detail Route** (`ui/src/routes/entry/[id]/`)
  - Created `/entry/[id]/+page.svelte` - Full entry display with title, content, metadata
  - Created `/entry/[id]/+page.ts` - Load function fetching entry by ID
  - Markdown rendering for content display
  - Shows classifications (Fachgebiete, Diagnosen, Symptome) as tags
  - Displays entry metadata (status, difficulty, source, dates)
  - Edit button for authorized users
  - Back navigation to search
  - Lines added: +200

- **Entry Edit Route** (`ui/src/routes/entry/[id]/edit/`)
  - Created `/entry/[id]/edit/+page.svelte` - Edit form with all entry fields
  - Created `/entry/[id]/edit/+page.ts` - Load function with entry + classifications
  - Pre-populated form with existing data
  - Multi-select for Fachgebiete, Diagnosen, Symptome
  - Save/Cancel actions with error handling
  - Lines added: +420

- **API Client Enhancement** (`ui/src/lib/api.ts`)
  - Added `entriesApi.getById(id)` - GET `/api/v1/entries/{id}`
  - Added `entriesApi.update(id, data)` - PUT `/api/v1/entries/{id}`
  - Lines added: +10

- **Search Click Handlers** (`ui/src/lib/components/SearchResults.svelte`)
  - Added click handler to navigate to entry detail on card click
  - Added `goto(/entry/${id})` on result card selection
  - Lines changed: +5

### Fixed

#### Backend Bug Fixes
- **Email Validation** (`api/models.py`)
  - Changed from Pydantic `EmailStr` to `str` with custom validator
  - Fixed rejection of `.local` domain emails like `admin@medwiss.local`
  - Lines changed: +8/-3

#### Frontend Bug Fixes
- **API Endpoint Prefix** (`ui/src/lib/stores/search.ts`)
  - Changed `/api/fachgebiete` to `/api/v1/fachgebiete`
  - Same fix for all classification endpoints
  - Lines changed: +3/-3

- **Mock Data Removal** (`ui/src/routes/+page.svelte`)
  - Removed hardcoded mock data fallback (42 entries)
  - Dashboard now shows only real API data
  - Lines changed: +2/-45

- **Auto-load Entries** (`ui/src/routes/search/+page.svelte`)
  - Added `executeSearch()` call on page mount
  - Entries now load automatically when visiting search
  - Lines changed: +1

### Files Modified
- `api/models.py` - Email validation fix
- `ui/src/lib/stores/search.ts` - API prefix correction
- `ui/src/lib/api.ts` - Added getById/update methods
- `ui/src/routes/+page.svelte` - Mock data removed
- `ui/src/routes/search/+page.svelte` - Auto-load entries
- `ui/src/lib/components/SearchResults.svelte` - Click handlers added
- `ui/src/routes/entry/[id]/+page.svelte` - NEW (entry detail view)
- `ui/src/routes/entry/[id]/+page.ts` - NEW (detail load function)
- `ui/src/routes/entry/[id]/edit/+page.svelte` - NEW (edit form)
- `ui/src/routes/entry/[id]/edit/+page.ts` - NEW (edit load function)

### QA Testing
- Build succeeds: `bun run build` completes without errors
- Entry detail page loads with full content display
- Edit form pre-populates with existing data
- Save updates persist correctly
- Navigation between search → detail → edit works
- Svelte warnings present but non-blocking (a11y, state_referenced_locally)

### Statistics
- **Lines Added**: +640
- **Lines Removed**: -51
- **Net Change**: +589 lines

### Documentation
- Created `.sisyphus/plans/phase-2-4-implementation.md` - Comprehensive implementation plan for remaining phases

## [1.1.1] - 2026-04-14 22-50

### Fixed

#### Backend Dependencies (`pyproject.toml`)
- Consolidated all Python dependencies from requirements.txt into pyproject.toml
- Added JWT Auth: `python-jose[cryptography]>=3.3.0`, `passlib[bcrypt]>=1.7.4`, `bcrypt>=4.2.0,<5.0.0`
- Added Pipeline: `watchdog>=4.0.2`, `pytesseract>=0.3.13`, `Pillow>=10.4.0`, `pdf2image>=1.17.0`
- Added API: `python-multipart>=0.0.12`, `email-validator>=2.0.0`, `pgvector>=0.2.0`, `httpx>=0.27.0`
- Note: bcrypt pinned to <5.0.0 due to passlib 1.7.4 incompatibility with bcrypt 5.x
- Lines added: +18

#### Classification Router Prefix (`api/routers/classifications.py`)
- Changed `prefix="/classifications"` to `prefix=""`
- Routes now work at `/api/v1/fachgebiete` instead of `/api/v1/classifications/fachgebiete`
- Fixed frontend/backend routing mismatch
- Lines changed: +1/-1

#### Schema Validation (`api/routers/classifications.py`)
- Changed `created_at: Optional[str]` to `created_at: Optional[datetime]` in:
  - `FachgebietResponse`
  - `DiagnoseResponse`
  - `SymptomResponse`
  - `KnowledgeEntrySummary`
- Fixed `ResponseValidationError` when returning datetime from database
- Lines changed: +4/-4

#### Database Fixes
- Regenerated admin password hash for bcrypt 4.x compatibility
- Updated admin email from `admin@medwiss.local` to `admin@medwiss.de`
- Pydantic v2 strict email validation rejects `.local` TLD

#### Scripts
- `start.sh` - Updated to use `uv` for Python package management (uv sync, uv run uvicorn)
- `stop.sh` - Created to kill uvicorn, vite, and docker-compose processes
- Lines added: +65

### Files Modified
- `pyproject.toml` - Dependencies consolidation
- `api/routers/classifications.py` - Router prefix and schema types
- `start.sh` - uv migration
- `stop.sh` - New file

### QA Testing
- Classification endpoints return 200 OK with data
- Login returns valid JWT token
- Entry creation works with authenticated requests
- API docs accessible at /docs

## [1.1.0] - 2026-04-14 19-50

### Changed

#### UI/UX Redesign - Design System Alignment
Complete redesign of all frontend pages to match the Search page quality and establish a consistent design system across the application.

**Dashboard (`ui/src/routes/+page.svelte`)**
- Complete refactor from 244 to 509 lines
- Removed duplicate header (now uses layout sidebar only)
- Converted from Tailwind utilities to CSS custom properties
- Added consistent page header with title/subtitle pattern
- Redesigned quick action cards with hover effects and transitions
- Styled stat cards with trend indicators and color-coded icons
- Added section-based layout with proper visual hierarchy
- Implemented responsive grid layouts
- Lines changed: +265/-65 (net: +200)

**Entry Form (`ui/src/routes/eingabe/+page.svelte`)**
- Complete refactor from 491 to 704 lines
- Removed duplicate header
- Converted to CSS custom properties design system
- Added page header with gradient KI section
- Redesigned form inputs with focus states and transitions
- Styled form cards with consistent borders and shadows
- Improved button styling with primary/secondary variants
- Added responsive form grid layout
- Enhanced file upload section with visual polish
- Lines changed: +213/-78 (net: +135)

**Stats Page (`ui/src/routes/stats/+page.svelte`)**
- Complete rebuild from 42 to 626 lines
- Added comprehensive statistics dashboard
- Implemented 4 overview stat cards with trends
- Added Fach Distribution chart section
- Added Diagnose Bar Chart section
- Created category distribution bars with percentages
- Created status distribution bars with color coding
- Added monthly trend visualization
- Implemented loading states with spinner
- Added error handling with retry functionality
- Lines added: +584 (net: +584)

**Settings Page (`ui/src/routes/settings/+page.svelte`)**
- Created new settings page (618 lines)
- Added profile management section (name, email, role)
- Added notification preferences with toggle switches
- Added appearance settings (dark mode, compact view, language)
- Added data management section with export options
- Implemented save/reset functionality with success feedback
- Custom toggle switch components with smooth animations
- Responsive layout matching other pages
- Lines added: +618 (net: +618)

**Package Manager Migration - npm to bun**
- Migrated from npm to bun for faster package management
- Removed `package-lock.json`, using `bun.lockb` instead
- Updated all documentation (QUICKSTART.md, AGENTS.md, flake.nix)
- All `npm install` commands changed to `bun install`
- All `npm run` commands changed to `bun run`
- Created `start.sh` script for one-command project startup

**Start Script (`start.sh`)**
- Created comprehensive startup script (208 lines)
- Automatically starts PostgreSQL with Docker
- Waits for database to be ready
- Initializes database if needed
- Sets up Python virtual environment
- Installs Python dependencies
- Starts FastAPI backend
- Installs frontend dependencies with bun
- Starts SvelteKit frontend
- Provides colored output and service status
- Handles cleanup on Ctrl+C
- Lines added: +208

**Layout Updates (`ui/src/routes/+layout.svelte`)
- Added active state for settings navigation item
- Fixed duplicate "Statistiken" link in sidebar
- Lines changed: +1/-5 (net: -4)

**Design System Standardization**
- All pages now use CSS custom properties from `app.css`:
  - `--color-*` for consistent color palette
  - `--space-*` for uniform spacing
  - `--radius-*` for consistent border radius
  - `--shadow-*` for unified elevation
- Standardized page structure: header → sections → content
- Consistent max-width containers (1200px for dashboard/stats, 900px for forms)
- Unified responsive breakpoints (768px mobile)
- Matching transition and animation timings

### Files Modified
- `ui/src/routes/+page.svelte` - Dashboard redesign
- `ui/src/routes/eingabe/+page.svelte` - Entry form redesign
- `ui/src/routes/stats/+page.svelte` - Stats page complete rebuild
- `ui/src/routes/settings/+page.svelte` - Settings page created
- `ui/src/routes/+layout.svelte` - Added settings nav active state
- `ui/package.json` - Package manager metadata
- `QUICKSTART.md` - Updated commands (npm → bun)
- `AGENTS.md` - Updated tech stack and commands
- `flake.nix` - Updated dev shell hints
- `start.sh` - Created (new file)

### Statistics
- **Total Files**: 60 source files (was 58)
- **Lines of Code**: ~17,221 LOC (was ~14,976)
- **Lines Added**: +1,888
- **Lines Removed**: -143
- **Net Change**: +1,745 lines

### QA Testing
- All pages render without errors
- CSS custom properties correctly applied
- Responsive layouts functional on mobile/desktop
- Form inputs have proper focus states
- Charts load and display correctly
- Navigation between pages works smoothly
- Settings page loads and saves correctly
- bun install and bun run dev work correctly
- start.sh script successfully starts all services

## [1.4.0] - 2026-04-16 00-00

### Added

#### Configuration System (medwiss-db/config/)
- `sources.yaml` - Configuration file defining all 11 source folders
  - Path mapping relative to workspace root
  - Default category for each folder
  - Default fachgebiete for each folder
  - Auto-classify flag per folder
  - File type filters per folder
  - Support for additional_paths (Fortbildung aggregates 2024, 2025, 2026)
- `__init__.py` - Configuration loader with Pydantic models
  - `SourceConfig` - Pydantic model for single source validation
  - `SourcesConfig` - Root configuration model
  - `load_sources()` - Main loader function
  - `get_source_by_name()` - Lookup source by name
  - `get_sources_by_category()` - Filter by category
  - `get_all_categories()` - Get unique categories
  - Environment variable overrides: `WORKSPACE_ROOT`, `SOURCES_PATH`

### Dependencies
- Added `pyyaml>=6.0` to pyproject.toml

## [1.5.0] - 2026-04-16 22-00

### Added

#### Batch Import System (Phase 2-4 Content Integration)

**Database Extensions** (`database/`, `alembic/`)
- `alembic/versions/001_add_import_tracking.py` - Migration adding:
  - `import_jobs` table (UUID PK, status, counters, error_log)
  - `source_path`, `file_hash`, `import_batch_id` columns on `knowledge_entries`
  - Foreign key constraints and indexes
- `api/services/import_jobs.py` - ImportJobService with CRUD + status transitions
  - Status transitions: pending → running → completed/failed
  - Progress tracking: increment_processed(), increment_failed()
  - Error logging with JSONB

**Batch API Endpoints** (`api/routers/batch_import.py`)
- `POST /api/v1/batch-import` - Start import job
- `GET /api/v1/batch-import/{job_id}` - Get job status
- `GET /api/v1/batch-import/{job_id}/errors` - Get error log
- `POST /api/v1/batch-import/{job_id}/retry` - Retry failed files
- Background task integration for async processing

**Batch Processor Module** (`pipeline/batch_processor.py`)
- `BatchProcessor` class for orchestrating file processing
- `scan_directory()` - Scan folder for processable files
- `process_file()` - Process single file through OCR → classification
- `process_directory()` - Batch process all files in directory
- `ProgressCallback` - Progress reporting system
- `calculate_file_hash()` - SHA-256 utility for duplicate detection
- Async method signatures prepared for parallel processing (Task 6)

**Classification Resolver** (`pipeline/classification_resolver.py`)
- `resolve_fachgebiet()` - Match LLM output to existing DB specialty
- `resolve_diagnose()` - Match ICD-10 code/name to existing diagnosis
- `resolve_symptom()` - Match symptom name to existing symptom
- Fuzzy matching (case-insensitive, whitespace normalization, pg_trgm similarity)
- In-memory caching for repeated lookups
- Admin approval queue via `needs_review` flag in beschreibung

**Duplicate Detection System** (`pipeline/duplicate_detector.py`)
- `DuplicateDetector` class with SHA-256 hash-based detection
- `DuplicateStrategy` enum: SKIP, UPDATE, FAIL
- `is_duplicate()` - Check if hash exists in database
- `get_existing_entry()` - Retrieve existing entry by hash
- `mark_as_processed()` - Store hash after successful import
- `DuplicateFileError` exception for collision handling

**Integration Worker** (`api/services/batch_import_worker.py`)
- `BatchImportWorker` - Full pipeline orchestration
- Duplicate detection before processing
- Classification resolution with fuzzy matching
- Entry creation with metadata
- Embedding generation after entry creation
- Job progress tracking throughout

**CLI Tool** (`scripts/batch_import_cli.py`)
- Commands: `preview`, `import folder`, `import all`, `status`, `retry`
- Flags: `--dry-run`, `--yes`, `--wait`
- Rich output with colored tables and progress bars
- API-based job tracking

### Files Created
| File | Lines | Purpose |
|------|-------|---------|
| `alembic/versions/001_add_import_tracking.py` | 68 | Database migration |
| `api/routers/batch_import.py` | 182 | Batch import API router |
| `api/services/import_jobs.py` | 126 | Import job service |
| `api/services/batch_import_worker.py` | 531 | Integration worker |
| `api/services/__init__.py` | 8 | Service exports |
| `pipeline/batch_processor.py` | 524 | Batch processing engine |
| `pipeline/classification_resolver.py` | 449 | LLM output resolution |
| `pipeline/duplicate_detector.py` | 192 | SHA-256 duplicate detection |
| `config/__init__.py` | 197 | Config loader + models |
| `config/sources.yaml` | 150 | Source folder definitions |
| `scripts/batch_import_cli.py` | 618 | CLI interface |

### Statistics
- **Lines Added**: ~2,995
- **Lines Removed**: ~0
- **Net Change**: +2,995 lines
- **Files Created**: 10
- **Files Modified**: 3

### Testing Results
- **Test Import**: 23 files imported (4_Red Flags, 6_Nachschlagen)
- **Success Rate**: 100% (file processing)
- **CLI**: All commands functional
- **Config**: 11 sources loaded correctly
- **API**: Batch endpoints registered and responding

### Known Limitations
- **AI Classification**: Requires llamaserver running (401 if not available)
- **Embeddings**: Require llamaserver for vector generation
- **Parallel Processing**: Async scaffold exists but processes sequentially
- **Search**: Working (FTS), embeddings optional for hybrid search

### Dependencies
- Added `pyyaml>=6.0` to pyproject.toml

## [1.6.0] - 2026-04-17 20-00

### Added

#### Source Folder Watcher (Automatic File Sync)

**Source Watcher Service** (`api/services/source_watcher.py`)
- `SourceWatcher` class - Watchdog-based file monitoring for all source folders
  - Monitors 13 configured source paths (11 main + 2 Fortbildung additional)
  - Non-blocking operation using separate threads per folder
  - Loads paths dynamically from `config/sources.yaml`
  - `start()` - Creates and starts observers for all source folders
  - `stop()` - Gracefully stops all observers and cleans up resources
  - `is_running()` - Check if watcher is active
  - `get_watch_paths()` - Get list of monitored paths
  - ThreadPoolExecutor for async processing
  - Lines added: +376

- `SourceFolderEventHandler` class - FileSystemEventHandler implementation
  - `on_created()` - Detects new files, calls `sync_new_file()`
  - `on_modified()` - Detects modified files, calls `sync_modified_file()`
  - `on_deleted()` - Detects deleted files, calls `archive_entry()`
  - Duplicate detection to avoid processing same file multiple times
  - `_is_supported_file()` - Filter by supported extensions
  - `_get_entry_by_path()` - Database lookup for existing entries
  - Configurable delay (0.5s) to ensure files are fully written
  - Lines added: +376 (shared file)

**Integration**
- Supports all file extensions from FileSyncService: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.md`, `.txt`, `.docx`, `.pptx`, `.mp3`, `.wav`, `.m4a`
- Integrates with existing `FileSyncService` for actual sync operations
- Uses existing database session from calling context
- Compatible with FastAPI lifespan for startup/shutdown

**Test Scripts**
- `scripts/test_source_watcher.py` - Basic functionality test
- `scripts/test_watcher_integration.py` - Integration test with file operations

### Usage Example
```python
# In FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db_context() as db:
        watcher = SourceWatcher(db)
        watcher.start()
        yield
        watcher.stop()
```

### Statistics
- **Lines Added**: +376 (source_watcher.py)
- **Lines Added**: +75 (test scripts)
- **Net Change**: +451 lines
- **Files Created**: 1

### QA Testing Results
- **Path Loading**: ✓ 13 source folders loaded from config
- **Observer Start**: ✓ All 13 observers started successfully  
- **Observer Stop**: ✓ Clean shutdown with proper cleanup
- **File Detection**: ✓ File creation events detected and processed
- **Integration**: ✓ Works with FileSyncService for database sync

## [1.7.0] - 2026-04-17 22-00

### Added

#### Sync Status Dashboard (Task 10)

**Backend API Endpoints** (`api/routers/files.py`)
- `GET /api/v1/files/admin/sync-status` - Returns sync status information (admin only)
  - Total files monitored across all source folders
  - Files waiting to be processed (new/modified)
  - Last sync timestamp
  - Sync errors list
  - Source folder details with file counts
- `POST /api/v1/files/admin/sync` - Triggers manual file synchronization (admin only)
  - Runs full sync: imports new files, updates modified, archives deleted
  - Returns success status and change summary
- Admin-only access via `require_admin` dependency
- Uses `FileSyncService` for actual sync operations
- Lines added: +120

**Frontend Component** (`ui/src/lib/components/SyncStatusDashboard.svelte`)
- Real-time sync status display
- Statistics cards showing:
  - Total files monitored
  - Files waiting for processing
  - Last sync timestamp
  - Sync error count
- Source folder overview with:
  - Folder name and category
  - File count per folder
  - Existence status (missing folders highlighted)
- Manual resync button with loading state
- Sync result feedback with change summary
- Error display section for sync errors
- German UI text consistent with application
- Responsive design for mobile/desktop
- Lines added: +450

**Admin Route** (`ui/src/routes/admin/sync/+page.svelte`)
- New admin page at `/admin/sync`
- Integrates SyncStatusDashboard component
- Admin header with shield icon
- Consistent page styling with other pages
- Lines added: +85

**Navigation Update** (`ui/src/routes/+layout.svelte`)
- Added Admin link to System section in sidebar
- Shield icon for admin navigation
- Active state handling for `/admin` routes
- Lines changed: +5/-1

### Files Created/Modified
| File | Lines | Purpose |
|------|-------|---------|
| `api/routers/files.py` | +120 | Admin sync endpoints |
| `ui/src/lib/components/SyncStatusDashboard.svelte` | +450 | Sync dashboard component |
| `ui/src/routes/admin/sync/+page.svelte` | +85 | Admin sync page |
| `ui/src/routes/+layout.svelte` | +5/-1 | Admin nav link |

### Statistics
- **Lines Added**: +660
- **Lines Removed**: ~1
- **Net Change**: +659 lines
- **Files Created**: 2
- **Files Modified**: 2

### Security
- Admin-only access enforced on both endpoints
- Returns 403 Forbidden for non-admin users
- No file contents exposed, only metadata

### QA Testing
- API endpoints return correct JSON structure
- Frontend displays sync status correctly
- Manual resync triggers FileSyncService
- Admin authentication working correctly
