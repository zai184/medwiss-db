# Critique: Classify-From-Filename + ICD-11 Validation

**Reviewed:** `docs/plans/classify-from-filename.md` (2026-08-26)
**Reviewer date:** 2026-08-26
**Sources cross-checked:** `api/main.py`, `api/config.py`, `api/classifier.py`, `api/dependencies.py`, `api/routers/files.py`, `pipeline/classification_resolver.py`, `database/models.py`, `alembic.ini`, `.env`

---

## Summary verdict

Architecture is sound — the two-phase approach (LLM builds keyword dict, then local regex matching) is pragmatic and fast. However, the plan has several correctness issues that would cause failures at runtime: batch sizes that overflow the classifier's prompt truncation limit, missing reuse of existing label-resolution infrastructure, and an inconsistent async/sync contract. The ICD-11 integration is well-conceived but the plan omits critical operational details (error handling, rate limiting, token caching implementation).

| Severity | Count | Summary |
|----------|-------|---------|
| 🔴 Blocker | 2 | Batch size overflows classifier limit; Diagnose.code UNIQUE constraint risk |
| 🟠 Bug | 2 | Async/sync mismatch; no ICD-11 error handling |
| 🟡 Inconsistency | 3 | Plan rewrites existing infrastructure; missing needs_review/source tracking; wrong alembic path |
| 🔵 Missing | 4 | Symptom classification absent from implementation; no dedup strategy; no logging/progress; no LLM response validation fallback |

---

## 1. Blockers

### B1 — Batch size overflows classifier prompt truncation

**Problem:** The plan proposes ~200 filenames per batch. The existing `BaseClassifier._format_prompt()` truncates input text to 4000 chars (`api/classifier.py:211`). 200 filenames at ~40 chars each = ~8,000 chars → 50% of content is silently dropped. Even if the plan builds its own prompt (not using the existing template), the LLM (Qwen 9B with 8K context) must fit: prompt + 200 filenames (~8K chars) + JSON response (~2K chars). This is tight and risks truncation or garbled output.

**Impact:** LLM receives incomplete data; keyword dict is partial; classification coverage silently drops.

**Fix:** Reduce batch size to ~80-100 filenames per batch. This keeps input well under context limits (~4K chars) with room for the JSON response. At ~30 batches for 2865 entries, total LLM time is still ~90s — acceptable.

### B2 — Diagnose.code UNIQUE constraint collision risk

**Problem:** `Diagnose.code` has a `unique=True` constraint (`database/models.py:131`). The plan's `_link_diagnoses` calls "Create/lookup Diagnosis rows" but doesn't specify how code collisions are handled. If the LLM maps two different keyword names to the same ICD-10 code (e.g. "VHF" and "Vorhofflimmern" both → I48), the second INSERT fails with a unique violation.

**Impact:** ImportError / IntegrityError at runtime; entries with duplicate code diagnoses silently fail to link.

**Fix:** Before inserting, look up by code first (`resolve_diagnose(db, code=code)` already handles this). The existing `resolve_classifications()` in `pipeline/classification_resolver.py` does exactly this — code match first, then name fuzzy match. **Reuse it.** Don't write new `_link_diagnoses`.

---

## 2. Bugs

### U1 — Async/sync mismatch in plan API

**Problem:** The plan shows `classify_all` as `async`, `_parse_llm_response` as `async`, and `_validate_with_icd11` as `async`. But the plan says "Batch filenames to Llamaserver" — the existing `LlamaserverClassifier.classify_async()` exists and uses `httpx.AsyncClient`. Good. However, the plan's custom prompt bypasses the existing classifier entirely and proposes building its own prompt + calling Llamaserver directly. This duplicates the LLM-calling infrastructure (URL construction, headers, payload format, response parsing) without reusing `BaseClassifier._get_url()`, `_get_headers()`, `_build_payload()`, or `_extract_content()`.

**Impact:** Maintenance burden — two parallel LLM-calling codepaths that must stay in sync if the Llamaserver config changes.

**Fix:** Either (a) reuse the existing classifier infrastructure by extending `BaseClassifier` with a `classify_filenames(text)` method, or (b) if the custom prompt truly needs different behavior, at minimum extract the HTTP call logic from the existing `_build_payload`/`_get_url`/`_get_headers` pattern. Don't reinvent the HTTP layer.

### U2 — No ICD-11 error handling or rate limiting

**Problem:** The plan's `_validate_with_icd11` loops over all diagnoses and calls the WHO API per diagnosis. No try/except, no rate limiting, no token refresh logic beyond "cache 55 min". If the WHO API returns 429 (rate limit), 401 (expired token), or network error, the entire batch fails. The plan says "degrades gracefully without it" but the enrichment step doesn't implement graceful degradation.

**Impact:** One network hiccup kills classification of the entire batch. 89 unique diagnoses × individual API calls = high chance of hitting rate limits.

**Fix:** (a) Wrap each ICD-11 lookup in try/except — on failure, skip ICD-11 enrichment for that diagnosis, proceed with ICD-10 only. (b) Add a semaphore (max 5 concurrent requests) to avoid rate limiting. (c) Implement token refresh on 401. (d) Consider a single bulk search endpoint if available, or batch the lookups.

---

## 3. Inconsistencies

### I1 — Plan rewrites existing resolve_classifications infrastructure

**Problem:** The plan's `FilenameClassifier._link_diagnoses` description says "Create/lookup Diagnosis rows + M2M link". This is exactly what `pipeline.classification_resolver.resolve_classifications()` + `TaggingService.resolve_labels_to_ids()` already do — with fuzzy matching, caching, `needs_review` tracking, and proper conflict resolution. The plan creates parallel infrastructure.

**Fix:** The `_link_diagnoses` method should call `resolve_classifications(db, diagnosen=[...])` and then link the returned IDs. The existing `batch_import_worker._resolve_classifications_for_result()` at lines 127-210 of `api/services/batch_import_worker.py` is the exact reference implementation — copy its pattern, don't reinvent.

### I2 — Missing needs_review and source tracking for auto-created diagnoses

**Problem:** The existing `Diagnose` model has `needs_review: bool` and `source: str` fields (`database/models.py:135-136`). When `resolve_classifications` creates a new row, it sets `needs_review=True` and `source="llm"`. The plan doesn't mention these fields — auto-created diagnoses would get `needs_review=False` and `source="seed"` (the model defaults), making them indistinguishable from curated seed data.

**Fix:** When creating diagnoses via the filename classifier, ensure `needs_review=True` and `source="filename_classifier"` (or reuse the existing `TagSource.LLM` enum from `tagging_service.py`). The existing `resolve_classifications` already sets `needs_review=True` for new rows — so reuse it (see I1).

### I3 — Wrong alembic migration path

**Problem:** The plan says "DB migration — Create" and lists "~10 lines". The actual alembic setup is at project root: `alembic.ini` + `alembic/` (not `database/alembic/versions/` as might be assumed from the directory structure). The plan doesn't specify where the migration file goes.

**Fix:** Create the migration at `alembic/versions/004_add_icd11_code.py` using `alembic revision --autogenerate`. The existing pattern uses numeric prefixes (001, 002, 003). Add `icd11_code VARCHAR(20)` nullable column to `diagnosen` table.

---

## 4. Missing / omissions

### M1 — Goal mentions symptoms but implementation only covers diagnoses

**Problem:** The plan goal states "Classify entries' diagnoses AND symptoms" but every step — the LLM prompt, the matching logic, the API response — only handles diagnoses. Symptoms are mentioned in the goal (line 7) and the architecture (line 29: "diagnoses and symptoms"), but the implementation has zero symptom handling.

**Fix:** Either (a) add symptom extraction to the LLM prompt and matching logic (the existing `resolve_classifications` already supports symptoms), or (b) explicitly state symptoms are out of scope for v1 and remove them from the goal.

### M2 — No deduplication strategy for keyword dict across batches

**Problem:** The plan says "Deduplicate across batches" (step 4) but doesn't specify the merge strategy. If batch 1 produces keyword "Kardiologie" → {"name": "Koronare Herzkrankheit", "code": "I25"}, and batch 2 produces keyword "Kardiologie" → {"name": "Herzinsuffizienz", "code": "I50"}, which wins?

**Fix:** Specify: (a) keyword key must be unique — if a keyword appears in multiple batches with different meanings, the first occurrence wins (or flag for manual review), (b) if two keywords map to the same ICD-10 code, merge into one entry.

### M3 — No progress logging or job tracking

**Problem:** The API returns a single JSON response after full completion. For 2865 entries across ~30 LLM batches, this could take 1-2 minutes. No progress indicator, no server-side logging, no way to check status if the request times out.

**Fix:** Either (a) use the existing `ImportJob` model + `ImportJobService` for progress tracking (the batch import already does this), or (b) at minimum, add structured logging (`logger.info(f"Batch {i}/{total}: classified {n} entries")`) and document that the endpoint may take 1-2 minutes.

### M4 — No LLM response validation fallback

**Problem:** The plan says the LLM returns JSON. But if the LLM returns malformed JSON, partial JSON, or a different structure than expected, there's no fallback. The existing `_parse_json_response()` in `api/classifier.py` handles markdown code blocks and nested JSON — the plan should reuse this. No mention of what happens when 200 filenames produce an unparseable response.

**Fix:** Reuse `_parse_json_response()` from `api/classifier.py`. If parsing fails for a batch, log the error and skip that batch (don't fail the entire operation). The `dry_run` mode should report parse failures separately.

---

## 5. What the plan gets right

| Decision | Assessment |
|----------|------------|
| Two-phase approach (LLM → regex) | ✅ Correct — avoids per-entry LLM cost; regex is instant |
| Keyword dict from LLM, not ICD codes from LLM | ✅ Good separation — LLM extracts names, regex matches, ICD-11 validates |
| ICD-11 as enrichment layer, not primary | ✅ Correct — ICD-10 is the working code system, ICD-11 is supplementary |
| Dry-run default on | ✅ Safe — prevents accidental bulk writes |
| `force` flag for re-classification | ✅ Correct — allows re-running without data loss |
| Endpoint as POST with body params | ✅ Correct pattern for mutation with options |
| Reusing existing admin page for the trigger button | ✅ Consistent with project UI patterns |
| ICD-11 client as optional (degrades gracefully) | ✅ Good — feature works without WHO API credentials |

---

## 6. Codebase facts verified

| Claim in plan | Verified against | Result |
|---------------|------------------|--------|
| 2865 entries with empty diagnosen | `curl /api/v1/stats/overview` + `curl /api/v1/diagnosen` | ✅ Confirmed |
| Diagnose model has code/name/descripcion | `database/models.py:126-138` | ✅ Correct; also has needs_review, source |
| resolve_classifications exists | `pipeline/classification_resolver.py` | ✅ Full fuzzy-match resolution with cache |
| Llamaserver at localhost:8080 | `api/config.py:llamaserver_url` | ✅ Correct |
| classify_async exists | `api/classifier.py:268-313` | ✅ Uses httpx.AsyncClient |
| Admin auth uses require_admin | `api/routers/files.py:308` | ✅ Pattern: `Depends(require_admin)` |
| Routers registered in main.py | `api/main.py:64-73` | ✅ All routers imported and included |
| Alembic at project root | `alembic.ini` + `alembic/env.py` | ✅ At root, not under database/ |
| Diagnose.code is UNIQUE | `database/models.py:131` | ✅ `unique=True` constraint confirmed |
| BaseClassifier truncates to 4000 chars | `api/classifier.py:211` | ✅ `text[:4000]` |

---

## 7. Recommended plan revisions (priority order)

1. **Reduce batch size to ~80-100** — 200 overflows the classifier's 4000-char prompt limit. Update architecture diagram step 2 and prompt section.

2. **Reuse `resolve_classifications()` for diagnosis linking** — Replace `_link_diagnoses` with calls to `pipeline.classification_resolver.resolve_classifications()`. Copy pattern from `batch_import_worker._resolve_classifications_for_result()` (lines 127-210).

3. **Add ICD-11 error handling** — Wrap enrichment in try/except with per-diagnosis fallback. Add semaphore for rate limiting. Implement token refresh on 401.

4. **Clarify symptoms scope** — Either add symptom extraction to the LLM prompt and matching logic, or explicitly remove symptoms from the goal.

5. **Add progress logging** — Structured logging per batch, or integration with ImportJob for progress tracking.

6. **Fix alembic migration path** — Specify `alembic/versions/004_add_icd11_code.py`.

7. **Document dedup merge strategy** — First-wins or flag-for-review when keywords collide across batches.

8. **Reuse `_parse_json_response()`** from `api/classifier.py` for LLM response parsing instead of writing new parsing logic.

---

## 8. Conclusion

The plan's architecture is solid and the approach is well-reasoned. The main risks are implementation-level: batch size overflow, missing infrastructure reuse, and incomplete error handling. **Revise before implementing** — address the 2 blockers (batch size, UNIQUE constraint) and 2 bugs (async/sync, ICD-11 error handling) to avoid runtime failures. The 3 inconsistencies and 4 omissions can be addressed during implementation but should be tracked.
