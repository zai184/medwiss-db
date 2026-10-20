# Critique: Dual-Layer OCR (Local Tesseract + Remote GLM-OCR / OpenRouter Vision)

**Reviewed:** `docs/plans/dual-layer-ocr.md` (plan date 2026-09-07)
**Reviewer date:** 2026-09-07
**Reviewer model:** `glm-5.3-flash` (Z.ai coding endpoint, boss-requested); every finding
cross-checked against on-disk code by the reviewing agent before acceptance.
**Sources cross-checked:** `api/config.py`, `pipeline/orchestrator.py`, `pipeline/ocr.py`,
`pipeline/batch_processor.py`, `api/services/file_sync.py`, `api/routers/summarize.py`,
`api/routers/pipeline.py`, `pipeline/test_ocr.py`, `pipeline/transcription.py`,
`requirements.txt`, `modules/medwiss.nix` (host config), Z.ai layout-parsing OpenAPI,
`~/Projekte/agents/tools/OCR/GLM-OCR` (SDK maas_client/config)

---

## Summary verdict

**Verdict:** The architecture is sound — a single ordered-try seam with fail-soft link-only fallback is the right shape for this codebase, and the choice of GLM-OCR MaaS as the VPS primary is well-evidenced. However, the plan has **three blockers**: two independent config-layer defects that mean the rollout either crashes at startup or silently no-ops on both deploys, and one regression that breaks audio link-only indexing on the VPS. The plan's own verification steps would pass despite these defects, which makes them especially dangerous.

| Severity | Count | Summary |
|----------|-------|---------|
| 🔴 Blocker | 3 | B1 env-var name maps to no field (silently ignored); B2 `list[str]` env parsing crashes startup; B3 audio link-only regression on VPS |
| 🟠 Bug | 3 | missing HTTP timeout; missing size/page/memory guards; conflated exception taxonomy → wrong 409 semantics |
| 🟡 Inconsistency | 4 | permanent stamping on transient failures; missing `gen-api.sh` step; hardcoded vision model; verification references tests the plan breaks |
| 🔵 Missing | 3 | backfill for already-stamped VPS corpus; no seam/validator/client tests; no retry/backoff policy |

---

## Findings

### 🔴 Blockers

**B1 — `MEDWISS_OCR_BACKENDS` doesn't match the settings schema and will be silently ignored**
· **Problem:** `api/config.py` defines `Settings` with `SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")` and **no `env_prefix`**. Every existing var is bare (`OCR_ENABLED`, `CHUNK_SEARCH_MODE`, `DATABASE_URL` — see `modules/medwiss.nix` Environment block). The plan's env var `MEDWISS_OCR_BACKENDS` maps to no field; with `extra="ignore"` it is dropped without warning, so `ocr_backends` defaults to `[]` **on both tux and the VPS**.
· **Impact:** The entire feature silently no-ops: tux loses remote OCR, VPS stays link-only. Worse, the plan's verification ("Remote-only simulation: `MEDWISS_OCR_BACKENDS=glmocr-maas` with no key → `NoOcrBackendError`") **still passes** under this bug, because an empty list also raises `NoOcrBackendError`. The rollout would be declared successful while nothing changed. The "verified on both deploys" step ("PNG and PDF yield markdown text") would catch it — but only after the config bug has already burned a debugging cycle.
· **Fix:** Name it `OCR_BACKENDS` in tux `.env`, `modules/medwiss.nix`, and docs (or add `validation_alias=AliasChoices("OCR_BACKENDS", "MEDWISS_OCR_BACKENDS")` in `api/config.py`). Additionally: (a) log the resolved backend list once at startup, and (b) add a verification step that `GET /api/v1/ocr/backends` (or the startup log) shows the *configured* list, not just that extraction fails. Also warn on unknown names in `_BACKENDS.get(name)` instead of `continue` — typos in the env list currently vanish silently.

**B2 — `list[str]` env parsing will crash `Settings()` under pydantic-settings 2.5.2**
· **Problem:** `requirements.txt` pins `pydantic-settings==2.5.2`. For `list[str]` fields, v2 expects a **JSON array** in the env var (`["tesseract","glmocr-maas"]`); the plan's documented form `OCR_BACKENDS=tesseract,glmocr-maas,openrouter-vision` fails validation, raising at `Settings()` instantiation — i.e., at import/startup. The plan specifies no `field_validator`.
· **Impact:** The app fails to boot on **both** deploys the moment step 1 (`api/config.py` swap) ships. This is the first thing implemented per the execution order, so it blocks everything.
· **Fix:** Add to `api/config.py`:
```python
@field_validator("ocr_backends", mode="before")
@classmethod
def _split_backends(cls, v):
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return v
```
Fold the legacy alias (`OCR_ENABLED=true` → `["tesseract"]` when `ocr_backends` unset) into the same validator or a `model_validator`, and unit-test all three forms (comma string, JSON array, legacy bool). Document the comma form in `docs/AGENTS.md` since it deviates from pydantic defaults.

**B3 — Rewiring the `file_sync` link-only condition breaks audio link-only indexing on the VPS**
· **Problem:** Today, `api/services/file_sync.py:269-332` link-only-indexes on `result.error AND not settings.ocr_enabled AND suffix in EXTRACTION_DEPENDENT_SUFFIXES` — and that suffix set (`file_sync.py:61`) **includes `.mp3/.wav/.m4a/.ogg/.flac`**. Audio never routes through the OCR seam: `pipeline/orchestrator.py`'s audio branch calls `transcribe_audio()` **unconditionally**. On the VPS, audio link-only indexing works *only because* `OCR_ENABLED=false` doubles as a proxy for "whisper missing". The plan keys the branch off "no OCR backend available" while leaving `EXTRACTION_DEPENDENT_SUFFIXES` unchanged — so on the VPS (where OCR backends *are* configured but whisper is absent), a failed transcription no longer matches the branch.
· **Impact:** Audio files on the VPS regress from link-only-indexed to hard-skipped/errored — directly contradicting the plan's own risk note ("audio stays link-only on VPS"). This is a production behavior regression in the ingest path.
· **Fix:** Split the condition by suffix class in `api/services/file_sync.py`: image/PDF suffixes → "no OCR backend available"; audio suffixes → a transcription availability signal (e.g., a `transcription_enabled: bool = False` setting mirroring today's semantics, or a registered transcription-backend check). Add a regression test: settings with `ocr_backends=["glmocr-maas"]`, no whisper → audio file with transcription error still lands in `_link_only_index`.

### 🟠 Bugs

**Bug 1 — No HTTP timeout specified; httpx's 5-second default will kill multi-page remote calls**
· **Problem:** `pipeline/remote_ocr.py` is specified as "thin HTTP, `httpx`" with no timeout. `httpx==0.27.2` defaults to a **5-second** total timeout. Evidence 4: layout_parsing is synchronous and evidence 7: throughput ≈1.86 PDF pages/s — a 30-page PDF cannot finish in 5s, nor can a 50 MB upload on a typical uplink. The existing `api_timeout_seconds: 120` is neither referenced by the plan nor obviously sufficient for 30-page jobs.
· **Impact:** Every multi-page PDF and large upload times out at the primary on the VPS, silently cascading to the lower-quality OpenRouter fallback or link-only. Intermittent, hard-to-diagnose behavior.
· **Fix:** Construct clients with explicit `httpx.Timeout(connect=10, read=300, write=120, pool=10)` (constants or new settings, e.g., `ocr_remote_timeout_seconds`). Reconcile with `api_timeout_seconds` and document why they differ.

**Bug 2 — No size/page/memory guards for the remote backends**
· **Problem:** Three unchecked limits. (a) App allows uploads to `max_file_size_mb: int = 50` (`api/config.py`), but Z.ai layout_parsing caps **images at 10 MB** (evidence 4) — a legal 40 MB PNG fails the primary with a 4xx and then gets base64-shoved at OpenRouter too. (b) The OpenRouter vision path has **no page cap**: a 300-page PDF triggers 300 serial paid vision calls (GLM-OCR's own 30-page limit doesn't apply to OpenRouter). (c) The plan mirrors `_pdf_to_images` and materializes **all** pages as a list — at 200 DPI that's ~350 MB of `Image.Image` for 30 pages, on a 2 GB box.
· **Impact:** Unbounded cost/latency, likely OOM on the VPS, and over-limit files degrade through confusing error paths instead of failing deterministically.
· **Fix:** In `pipeline/remote_ocr.py`: pre-check file size and raise `_BackendUnavailable("exceeds GLM-OCR image limit 10MB")`-style typed errors so the next backend/link-only path takes over cleanly. Chunk >30-page PDFs into multiple layout_parsing calls using `start_page_id`/`end_page_id` (evidence 4), with an env-configurable total page cap (default 30). For the OpenRouter path: yield pages **one at a time** from a generator (never build the list), fix DPI (150–200), downscale long edge, apply the same page cap.

**Bug 3 — Exception taxonomy conflates "not configured", "transiently failed", and "exhausted"; routers return misleading 409s; folding `OCRDisabledError` destroys the per-backend signal**
· **Problem:** The seam raises `NoOcrBackendError` both when the backend list is empty and when all configured backends *failed at runtime* (the `except Exception: logger.warning` branch also falls through). The plan then folds `pipeline.ocr.OCRDisabledError` into `NoOcrBackendError` — but `OCRDisabledError` is currently the *per-backend* "pytesseract missing" signal (`pipeline/ocr.py` raises it when `pytesseract is None`), which the seam must catch as `_BackendUnavailable`, not as global exhaustion. Routers (`api/routers/pipeline.py`, `summarize.py`) are told to emit the existing 409 "OCR ist deaktiviert…" for all of it.
· **Impact:** A Z.ai outage during an interactive summarize returns 409 "OCR is disabled" — wrong semantics (should be 502/503) and wrong message; operators can't distinguish "misconfigured box" from "provider down". Internally, if `ocr.py`'s missing-pytesseract case becomes `NoOcrBackendError`, it would be swallowed by the seam's generic `except Exception` and misreported.
· **Fix:** Three signals: `_BackendUnavailable` (skip to next backend; `pipeline/ocr.py`'s pytesseract-missing case maps here — keep `OCRDisabledError` as an alias during migration and update `pipeline/test_ocr.py` expectations), a runtime-failure classification (collect `(backend, reason)` for both skips and failures), and `NoOcrBackendError` raised only at exhaustion **carrying the collected reasons** (the components table promises "per-backend availability reasons"; the pseudocode doesn't deliver them). Routers: 409 only when nothing is *configured*; 502/503 with reasons when configured backends failed.

### 🟡 Inconsistencies

**Inc 1 — Permanent link-only stamping on transient remote failures**
· **Problem:** `file_sync` hash-stamps on error with "no re-attempt loop". Today the gate is a static human-set bool, so stamping is sound. With remote backends, a Z.ai blip or an expired key now produces the same permanent stamp.
· **Impact:** Files readable minutes later are permanently demoted to link-only; no recovery path short of manual DB surgery.
· **Fix:** Stamp only when no backend is *configured* (deterministic). On configured-but-failed exhaustion, record the error **without** the stamp (or with an attempt counter) so a later reconcile retries.

**Inc 2 — New router added without `./scripts/gen-api.sh`**
· **Problem:** `GET /api/v1/ocr/backends` changes the API shape; AGENTS.md requires regenerating `contracts/api/openapi.json` + `ui/src/lib/api-types.d.ts`. Not mentioned anywhere in the plan (components, execution order, verification).
· **Impact:** Contract drift; violates a documented repo rule; UI  cannot consume the new endpoint type-safely against a stale `ui/src/lib/api-types.d.ts`, and any check (or human) diffing `contracts/api/openapi.json` sees drift the moment the router merges. Since the endpoint's entire phase-1 purpose is "for future gating," shipping it against an unregenerated contract defeats its own point.
· **Fix:** Add an explicit execution-order step (with step 6): after creating `api/routers/ocr.py`, run `./scripts/gen-api.sh` and commit the regenerated `contracts/api/openapi.json` + `ui/src/lib/api-types.d.ts`. Add it to the components-table row and require `bun run check` to pass only after regeneration.

**Inc 3 — Vision model name hardcoded in the client contradicts the codebase's config-driven pattern**
· **Problem:** `_openrouter_vision_extract` hardcodes `z-ai/glm-4.6v` inside `pipeline/remote_ocr.py`. Every other model choice in this app flows through `api/config.py` (`openrouter_default_model`, `openrouter_fallback_model`, `llamaserver_model`). The plan adds `zai_api_key` and `glm_ocr_api_url` settings but no corresponding vision-model setting.
· **Impact:** A model rename or price change requires a code edit and redeploy instead of an env change; the UI's static model list and the client's actual call target can drift apart silently.
· **Fix:** Add `openrouter_vision_model: str = "z-ai/glm-4.6v"` to `api/config.py`; read it in `pipeline/remote_ocr.py`; include it in the `GET /api/v1/ocr/backends` payload.

**Inc 4 — Verification relies on a test suite the plan's own steps break**
· **Problem:** Verification says to "run existing `pipeline/test_ocr.py`", but execution-order step 3 deletes `OCRDisabledError` usages and step 2 changes the gating model — and `pipeline/test_ocr.py` covers error handling as well as preprocess/PNG/JPG/PDF paths (evidence 6). The suite as-is asserts on the exception and gate behavior the plan removes.
· **Impact:** The plan's regression gate fails as written — or, worse, someone quietly edits the tests to match changed behavior and calls it green.
· **Fix:** Add an explicit step: update `pipeline/test_ocr.py` (import of the renamed/aliased exception; gate via an `ocr_backends=["tesseract"]` fixture instead of `OCR_ENABLED=true`), and add the new coverage listed in M2 below.

### 🔵 Missing

**M1 — No migration/backfill path for the existing link-only-stamped VPS corpus**
· **Problem:** `file_sync` stamping is permanent ("hash stamped, no re-attempt loop"). Every PDF/image ingested on the VPS during the `OCR_ENABLED=false` era is stamped and will stay textless. The plan's VPS verification only ingests **one new** PDF.
· **Impact:** The plan's headline goal — "image/PDF text extraction works on both deploys" — is unmet for all existing production data; the very backlog that motivated the plan remains unread.
· **Fix:** Add an execution step: a one-off backfill that clears the extraction stamp for `EXTRACTION_DEPENDENT_SUFFIXES` rows with empty text and re-runs ingest (script or documented SQL). Before running, estimate duration/cost from evidence 7 (serial `BatchProcessor`; ~0.67 img/s, ~1.86 PDF pages/s, pay-per-call) and add a dry-run/limit flag.

**M2 — No automated tests for the new seam, validator, or remote clients**
· **Problem:** Verification is manual throwaway scripts plus the (broken) Tesseract suite. Nothing covers: the config validator's three input forms (comma string, JSON array, legacy bool — see B2), ordered-try semantics (skip-on-unavailable vs. record-failure vs. exhaustion message), `file_sync`'s split image/audio branch (B3), or the remote clients against mocked HTTP (`respx`/`httpx.MockTransport`), or the size/page guards (Bug 2).
· **Impact:** The highest-risk code in the plan — config parsing and fail-soft routing — ships untested. B1 already demonstrated that this plan's manual verification reports success while the feature no-ops.
· **Fix:** Add `pipeline/test_ocr_backend.py` plus config-validator tests; keep remote-client tests fully mocked (no network in CI); add the B3 audio regression test.

**M3 — No retry/backoff policy for transient remote errors**
· **Problem:** Each remote backend is a single-shot POST. The plan cites the vendored SDK's retry policy ("config.yaml has the retry policy") as reference material but specifies none. 429/5xx/network errors are indistinguishable from hard failures — and combined with Inc 1, they permanently stamp files.
· **Impact:** One Z.ai throttle window during bulk reconcile mass-downgrades files to the fallback (or link-only) and still pays for the partial calls.
· **Fix:** Inside each remote backend, retry only 429/5xx/connect errors (2–3 attempts, exponential backoff, honor `Retry-After`); raise `_BackendUnavailable` immediately on 401/403/413 (deterministic); raise a classified runtime failure on exhausted retries per the Bug 3 taxonomy.

---

## What the plan gets right

| # | Correct | Why (evidence) |
|---|---|---|
| 1 | **Diagnosis of the current state is accurate** — one bool gate, single local engine, decorative UI model, text-only summarize path | Matches `api/config.py` (`ocr_enabled: bool = False`), `pipeline/ocr.py`, and the summarize router evidence exactly, down to the cited line |
| 2 | **One seam, ordered-try, fail-soft to link-only** — right complexity level; no plugin framework for a 4-backend problem | Consistent with the existing `OCRDisabledError`-catch pattern in `batch_processor.py`/`file_sync.py` |
| 3 | **GLM-OCR MaaS as VPS primary**: file-direct (PDF included), markdown out, no poppler — and the quoted limits (image ≤10 MB, PDF ≤50 MB, ≤30 pages) are **exactly correct** | Evidence 4 (verified OpenAPI); `md_results`, Bearer auth, synchronous response all confirmed |
| 4 | **No new provider accounts or secrets** — reuses `ZAI_API_KEY` and the existing `OPENROUTER_API_KEY` (already in the VPS sops env) | `modules/medwiss.nix` `EnvironmentFile` |
| 5 | **pymupdf (pure wheel) over pdf2image/poppler** for the VPS raster path — correct constraint analysis for a 2 GB nixos box with `h.strict` | Evidence 3: pdf2image/pytesseract present locally only |
| 6 | **Thin `httpx` client instead of vendoring the glmocr SDK** — and httpx is already a dependency | Evidence 3 (`httpx==0.27.2`) |
| 7 | **Honest scoping**: audio/whisper explicitly out of scope; phase-2 (self-host vLLM, PaddleOCR) deferred rather than built speculatively; pay-per-call cost flagged | Matches the VPS design and the `_BACKENDS` dict's open shape |

## Codebase facts verified

| Plan claim | Verdict | Evidence |
|---|---|---|
| `settings.ocr_enabled` bool gates all extraction (`api/config.py:44`), `false` on VPS | ✅ | Config evidence; `OCR_ENABLED=false` in `modules/medwiss.nix` |
| Only `pipeline/ocr.py` implements image→text (pytesseract + pdf2image/poppler, `-l deu`) | ✅ | `ocr_module` evidence |
| `summarize_file` path is text-in/text-out; routers 409 on `OCRDisabledError` | ✅ | `summary_409` / `pipeline_409` evidence |
| `EXTRACTION_DEPENDENT_SUFFIXES` at `file_sync.py:61`, link-only on `not ocr_enabled` | ✅ — but the set **includes audio suffixes**, which the plan overlooked (→ B3) | `file_sync_ingest` evidence |
| Audio branch gated like images | ❌ mischaracterized: `transcribe_audio()` is **unconditional** today (→ B3) | `extract_text` evidence |
| httpx already a dep; pymupdf absent and must be added | ✅ | Evidence 3 |
| Z.ai layout_parsing: file-direct, `md_results`, Bearer, 10 MB/50 MB/30 pp limits | ✅ (plan missed `start_page_id`/`end_page_id`, which Bug 2's fix needs) | Evidence 4 |
| `MEDWISS_OCR_BACKENDS` maps to a Settings field | ❌ — no `env_prefix` exists; `extra="ignore"` swallows it | Config evidence (B1) |
| `list[str]` parses `"a,b,c"` from env | ❌ — needs JSON array or a validator | Evidence 1 (B2) |
| `NoOcrBackendError` carries "per-backend availability reasons" | ⚠️ promised in the components table, undesigned in the pseudocode | Bug 3 |
| Vendored SDK contents, boss's existing `ZAI_API_KEY`, key mgmt URLs | ❓ unverifiable from repo evidence — plausible assumptions, should be confirmed at step 4 | Outside evidence set |

## Recommended plan revisions (priority order)

1. **B2** — Add the `field_validator` for `ocr_backends` (+ legacy `OCR_ENABLED` alias in the same validator); unit-test comma string, JSON array, and legacy bool. Without this, step 1 of the execution order bricks startup on both deploys.
2. **B1** — Rename the env var to `OCR_BACKENDS` (or `AliasChoices`); log the resolved backend list at startup; warn on unknown names in `_BACKENDS.get()`; verification must assert the *configured* list is visible, not merely that extraction fails.
3. **B3** — Split the `file_sync` link-only condition by suffix class (image/PDF → OCR backends; audio → a `transcription_enabled` signal); add the VPS audio regression test.
4. **Bug 2** — Enforce image-size (10 MB) and total-page caps; chunk >30-page PDFs via `start_page_id`/`end_page_id`; stream pages one-at-a-time with fixed DPI for the OpenRouter path (memory on the 2 GB box).
5. **Bug 1** — Explicit `httpx.Timeout` on both remote clients; reconcile with `api_timeout_seconds`.
6. **Bug 3** — Three-signal exception taxonomy (`_BackendUnavailable` / runtime failure / exhaustion-with-reasons); 409 only when nothing is configured, 502/503 with reasons otherwise; map `ocr.py`'s pytesseract-missing to `_BackendUnavailable`.
7. **Inc 1** — Permanent hash-stamping only for deterministic unavailability; attempt-counter (retryable record) for configured-but-failed exhaustion.
8. **M3** — Retry 429/5xx/connect errors with backoff inside each remote backend.
9. **M1** — Backfill step for the existing stamped VPS corpus, with a cost/throughput estimate and dry-run flag.
10. **Inc 2** — `./scripts/gen-api.sh` step for the new router; commit regenerated contracts.
11. **Inc 3** — `openrouter_vision_model` setting instead of the hardcoded model string.
12. **Inc 4 / M2** — Update `pipeline/test_ocr.py`; add seam, validator, file_sync-branch, and mocked-client tests to the Verification section.

## Conclusion

**Approve with mandatory revisions.** The architectural direction — one ordered-try seam, remote-first on the VPS, link-only as the terminal fail-soft state, MaaS GLM-OCR as primary — is correct for this codebase, and every major design bet (GLM-OCR capabilities, limits, dependency footprint) checks out against the verified evidence. But as written, the plan fails at its first execution step (B2 crashes startup), silently no-ops even where it boots (B1), and regresses audio ingest on the VPS (B3) — all while its own verification section reports success. None of the required fixes change the architecture; they concentrate in `api/config.py` parsing, guards in `pipeline/remote_ocr.py`, the exception taxonomy in `pipeline/ocr_backend.py`, and the `file_sync` branch condition. With revisions 1–3 applied (non-negotiable) and 4–12 scheduled within the same PR or an immediate follow-up, this plan is ready to implement.