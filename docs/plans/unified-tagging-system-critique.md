# Critique: Unified Tagging System — Implementation Plan

**Reviewed:** `docs/plans/unified-tagging-system.md` (plan date 2026-08-26, "Ready to implement")
**Reviewer date:** 2026-08-29
**Sources cross-checked:** `database/migrations/005_unified_tagging.sql`, `database/schema.sql`, `database/seeds.sql`, `database/models.py`, `api/models.py`, `api/routers/classifications.py`, `api/services/entry_service.py`, `api/services/tagging_service.py`, `ui/src/lib/api.ts`, `ui/src/lib/components/MultiSelect.svelte`, `ui/src/routes/entry/[id]/edit/+page.svelte`, `ui/src/routes/entry/[id]/+page.svelte`, `ui/src/routes/eingabe/+page.svelte`, `ui/src/routes/admin/+page.svelte`, git log

---

## Summary verdict

The plan's architecture (lookup tables + M2M junctions, FK for single-select Dokumenttyp, non-destructive rollback) is sound and matches the existing Fachgebiet/Diagnose/Symptom pattern. But the plan is **stale**: its Phase 1–2 database work (migration, schema, SQLAlchemy models, Pydantic models) is **already implemented and merged** — `database/migrations/005_unified_tagging.sql` exists, `schema.sql` has all new tables/columns, `database/models.py` has `Dokumenttyp`/`OrdnerLabel`, and `api/models.py` has `dokumenttyp_id`/`ordner_label_ids`/`dokumenttyp_ref`/`ordner_labels`. Running the plan as written re-executes an already-applied, non-idempotent migration and hard-fails.

Two further problems: the plan's auth premise is gone (authentication was removed entirely — WireGuard-only deployment, commit `8323206`), so all `Editor+`/`Admin`/`require_editor_or_admin` content is fiction; and the plan ignores that full-text search (`search_vector` weight C) and `mv_entry_search` are built from the **old** `dokumenttyp` VARCHAR and `source_hierarchy` JSONB columns — moving writes without redefining the materialized view silently drops tags from search.

| Severity | Count | Summary |
|----------|-------|---------|
| 🔴 Blocker | 2 | Migration already applied; auth premise removed |
| 🟠 Bug | 3 | MV/FTS staleness; no dual-write behind "fallback"; silent drop of `ordner_label_ids` |
| 🟡 Inconsistency | 5 | Stale current-state; duplicate seed SoT; unterkategorie owner; handler signature; fresh-install seeds |
| 🔵 Missing | 5 | Single-select MultiSelect support; stats/faceted migration; acceptance criteria; apply procedure; resolve-labels extension |

---

## 1. Blockers

### B1 — Migration 005 already exists and is applied

**Problem:** Phase 1.1/2.1 propose creating `database/migrations/005_unified_tagging.sql` — that file already exists with the same DDL (`CREATE TABLE dokumenttypen …` at line 13, `ordner_labels`, `entry_ordner_label`, `dokumenttyp_id`, data backfill). The plan's "Migration Safety" claim *"Migration is idempotent (ON CONFLICT DO NOTHING)"* is false: only the backfill INSERTs use `ON CONFLICT`; the `CREATE TABLE` / `ALTER TABLE` / `CREATE INDEX` statements have no `IF NOT EXISTS` and will hard-fail on any database where 005 was applied.

**Impact:** Day-one failure for anyone following the plan; or worse, a hand-edited variant that diverges from the applied schema.

**Fix:** Delete Phase 1.1/2.1 and 1.2/2.2 (schema.sql is already updated: tables at lines 56–75, junction at 196, `dokumenttyp_id` at 110). Mark them "done, do not re-run." If an idempotency guard is wanted for other environments, add `IF NOT EXISTS` in a follow-up, not by re-running.

### B2 — Auth/role model no longer exists

**Problem:** Phase 1.5/2.5 endpoint tables specify `Auth: None / Editor+ / Admin`, and Phase 3 says *"Change `require_admin` to `require_editor_or_admin` on POST endpoints in `classifications.py`."* Authentication was removed from this project entirely (no `dependencies.py`, no `Depends` auth guards in any router; commit `8323206` "api: remove authentication entirely (WG-only deployment)"). There is no `require_admin`, no roles, no login.

**Impact:** The "Editors can create labels" decision is moot (everyone can); implementers would search for functions that don't exist; endpoint tables misdocument the API.

**Fix:** Strip all Auth columns and Phase 3's backend role change. The inline-create fix needs **no** backend permission work — POST endpoints are already callable. If per-user authorization ever returns, that's a separate plan.

---

## 2. Bugs

### U1 — FTS and `mv_entry_search` are built from the old columns

**Problem:** `schema.sql` defines `mv_entry_search` from `ke.dokumenttyp` (line 366), `ke.unterkategorie` (304), and builds `search_vector` with `setweight(... source_hierarchy ...)` at weight C (line 352). Faceted search reads the same strings. The plan moves writes to `dokumenttyp_id` + `entry_ordner_label` but never mentions the materialized view, the FTS vector, or `/api/v1/search/refresh-index`.

**Impact:** After cutover, every new or edited entry loses its tags from full-text and faceted search (old columns stop being updated). Silent wrong results — the worst kind.

**Fix:** Add a phase (or explicit step in 1.6/2.6): redefine `mv_entry_search` to aggregate from `dokumenttypen` (via FK) and `entry_ordner_label` (via junction), then call `POST /search/refresh-index` after migration and document it as a post-deploy step.

### U2 — "Backward compat fallback" without dual-write = stale reads

**Problem:** The plan keeps `dokumenttyp` VARCHAR and `source_hierarchy` as read fallbacks "during rollout," but nothing writes both. Today the write path is string-only: `entry_service.create_entry` sets `dokumenttyp=entry_data.dokumenttyp` (line 255), `tagging_service.apply_proposals` sets `entry.dokumenttyp = proposal.label` (line 285) and `entry.source_hierarchy` (line 323). `dokumenttyp_id` is written by **nothing** in `api/` (verified by grep: only `api/models.py` mentions it). After the plan's frontend cutover, old columns go stale for all new/edited rows while `get_dokumenttypen` (distinct over the stale column, entry_service:340–344), stats by-category, and the detail page's `{:else if entry.dokumenttyp}` fallback keep reading them.

**Impact:** Mixed old/new rows display inconsistent tags; stats and search filters silently diverge.

**Fix:** Pick one, explicitly: (a) **hard cutover** — switch all reads to the new columns in the same change, keep old columns only for pre-migration rows that were backfilled (then U1's MV fix makes old columns irrelevant); or (b) **dual-write window** — every write sets both string and ID until reads are migrated. Option (a) is simpler and the backfill already ran in 005.

### U3 — `ordner_label_ids` is accepted today and silently dropped

**Problem:** `EntryCreate`/`EntryUpdate` already carry `ordner_label_ids` (api/models.py:113, 130), but `update_entry` pops only `fachgebiet_ids`/`diagnose_ids`/`symptom_ids` (entry_service:300–302) and then `setattr`s every remaining field onto the ORM object — `ordner_label_ids` is not a column, so it's set as a plain Python attribute and vanishes on commit. `create_entry` ignores it entirely (explicit kwargs, line 255).

**Impact:** The API contract already promises a field that does nothing. Any client sending it gets 200 OK and no effect — the same class of bug as the plan's Phase 3 "fake IDs" problem, but server-side and live today.

**Fix:** In 2.6, note this as an existing bug to fix, not just new behavior: pop `ordner_label_ids` and replace junction rows (same pattern as `entry.fachgebiete = …` above), and handle it in `create_entry` too.

---

## 3. Inconsistencies

### I1 — "Current State" describes pre-migration reality

**Problem:** The plan's Current State diagram and Problems table (#1, #2) say Dokumenttyp and Ordner-Labels have "no table". Phase 1.1–1.4 and 2.1–2.4 (DB, schema, SQLAlchemy, Pydantic) are all already merged: `database/models.py` has `OrdnerLabel` (line ~162) and `Dokumenttyp` (line ~181) with the exact `needs_review`/`source`/`created_at` shape the plan specifies; `api/models.py` has `DokumenttypResponse`, `OrdnerLabelResponse`, `dokumenttyp_ref`, `ordner_labels` (lines 97–148).

**Fix:** Rewrite the plan as a **wire-up** plan. Remaining work: CRUD endpoints (1.5/2.5), entry_service (1.6/2.6), tagging_service (1.7/2.7), and the entire frontend (1.8–1.10, 2.8–2.10, Phases 3–5). Adjust the 12-file table and re-estimate.

### I2 — Three competing sources of truth for Dokumenttyp values

**Problem:** The plan seeds 12 values (including `Fachgebiet`, `Red Flags`, `Nachschlagen`); the applied migration 005 has its own INSERT list; the edit page hardcodes `DOKUMENTTYP_OPTIONS` (edit/+page.svelte:11). Nothing verifies 1.9's replacement matches 005's actual rows.

**Fix:** Before 1.8, diff `DOKUMENTTYP_OPTIONS` against `SELECT name FROM dokumenttypen` and reconcile; treat the DB table as the only SoT afterwards.

### I3 — `unterkategorie` fate undefined while it is actively written

**Problem:** The target-state diagram marks `unterkategorie` "kept for backward compat," but `tagging_service` line 325 actively writes it (`entry.unterkategorie = stored_hierarchy[-1]`) and `mv_entry_search`/faceted search read it. The plan never says who owns it after Ordner-Labels move to M2M.

**Fix:** Decide: keep `unterkategorie` as a derived convenience column (then 2.7 must keep writing it from the last label) or drop it from the write path and redefine the MV accordingly.

### I4 — Phase 3 handler signature doesn't match the real one

**Problem:** The snippet declares `async function handleCreateFachgebiet(name: string)`, but the existing handlers receive an event detail: `handleCreateFachgebiet(detail: { value: string })` with `const newId = Date.now()` (eingabe/+page.svelte:215–228). `MultiSelect` supports `allowCreate` (MultiSelect.svelte:13,24) — the plan's premise is right, the code is wrong.

**Fix:** Align the snippet with `oncreate` detail shape, or change MultiSelect's `oncreate` contract — one or the other, stated explicitly.

### I5 — Fresh installs get empty lookup tables

**Problem:** `INSERT INTO dokumenttypen` / `INSERT INTO ordner_labels` exist only in migration 005 — not in `schema.sql` or `seeds.sql` (verified by grep). Environments built from `schema.sql` + `seeds.sql` (the documented init path) produce empty lookups, which 1.8's dropdown and 1.9's admin tab would then display.

**Fix:** Add the seed rows to `seeds.sql` (or schema.sql), same as the other lookup tables.

---

## 4. Missing / omissions

### M1 — Single-select mode for Dokumenttyp isn't a feature yet

**Problem:** 1.8 says "Single-select mode (only one selection allowed)" via `<MultiSelect>`. The component has `allowCreate` but no single-select/max-1 prop (verified). The eingabe page also uses `<MultiSelect>` today for three multi dimensions only.

**Fix:** Add "extend MultiSelect with a `singleSelect` prop" to the file list, or use a plain `<select>` fed by `/dokumenttypen` — simpler, matches the old UX.

### M2 — Stats and faceted search not in scope

**Problem:** `/stats/by-category` groups by the `dokumenttyp` string; faceted search (`search/faceted.py`, `mv_entry_search`) filters on it too. Plan section 1.6 covers `list_entries` and `get_dokumenttypen` only.

**Fix:** Add explicit read-migration steps for stats and faceted (or document that they stay on the old column and therefore U2's dual-write is mandatory).

### M3 — No acceptance criteria

**Problem:** "Success" is never defined; the plan can be "done" while tags are invisible in search.

**Fix:** Add a checklist, e.g.: create entry with 1 Dokumenttyp + 2 Ordner-Labels via edit UI → visible on detail page (unified Tags section), in FTS (`q=<label>` hits), in faceted filters, in admin tabs; inline-created label persists after reload; `refresh-index` run.

### M4 — No apply/rollout procedure

**Problem:** Migrations are raw SQL files; the plan doesn't state how 005 was/will be applied per environment (local + VPS), nor that a deploy must trigger `refresh-index`.

**Fix:** One short "Rollout" section: psql apply order, restart, `POST /search/refresh-index`, spot-check queries.

### M5 — `resolve-labels` not extended

**Problem:** Phase 3's fallback uses `resolveLabels({fachgebiete…})` (exists: classifications.py:574–586, api.ts:248), but the new dimensions' inline create would also want name→ID resolution with `needs_review=true` — `resolve_labels_to_ids` covers only fach/diagnose/symptom.

**Fix:** Either extend `ResolveLabelsRequest/Response` for `dokumenttyp`/`ordner_labels`, or state that inline create for the new dimensions goes exclusively through the new POST endpoints (then the fallback branch is unnecessary).

---

## 5. What the plan gets right

| Decision | Assessment |
|----------|------------|
| Lookup table + M2M pattern mirroring Fachgebiet/Diagnose/Symptom | ✅ Consistent with codebase; the applied 005 matches it exactly |
| Keep old columns, no destructive drop | ✅ Right instinct — but needs U2's write-strategy fix |
| `ON CONFLICT DO NOTHING` backfills | ✅ Applied migration is safe to re-run *for those steps* |
| Phase 3 problem diagnosis (fake `Date.now()` IDs) | ✅ Verified real: eingabe/+page.svelte:215–228 |
| Phase 4/5 unification direction | ✅ Matches actual UI state (5 chip groups at detail:152–199; hardcoded select at edit:252–254) |
| Rollback plan (drop new tables/columns, old data intact) | ✅ Valid, simple |

---

## 6. Codebase facts verified

| Claim in plan | Verified against | Result |
|---|---|---|
| Dokumenttyp "no table" | `database/migrations/005_unified_tagging.sql`, `schema.sql:56` | ❌ Table exists |
| Ordner-Labels "read-only JSONB, no table" | `schema.sql:67,196`, `database/models.py` (OrdnerLabel) | ❌ Table + M2M exist |
| Migration file `005_unified_tagging.sql` (new) | `database/migrations/` listing | ❌ Already exists |
| `dokumenttyp_id` FK column to add | `schema.sql:110`, `api/models.py:99` | ❌ Already exists |
| `ordner_label_ids` in Create/Update | `api/models.py:113,130` | ❌ Already exists |
| `/dokumenttypen`, `/ordner-labels` CRUD endpoints | `api/routers/classifications.py` grep | ✅ Not implemented (real remaining work) |
| Entry service uses ID/junction | `api/services/entry_service.py:255,300–330` | ✅ Still string-only; `dokumenttyp_id` written nowhere |
| Hardcoded `DOKUMENTTYP_OPTIONS` | edit/+page.svelte:11,252–254 | ✅ Real |
| Read-only Ordner-Labels on edit | edit/+page.svelte:25 (`sourceHierarchy` plain state) | ✅ Real |
| Inline create fake IDs | eingabe/+page.svelte:215–228 | ✅ Real |
| 5 chip groups on detail page | entry/[id]/+page.svelte:152–199 | ✅ Real (Dokumenttyp reuses `tag-fach` style, line 155) |
| `require_admin` → `require_editor_or_admin` | `api/routers/*` grep; commit `8323206` | ❌ No auth exists at all |
| Admin tabs for new dimensions | admin/+page.svelte `LabelTab` type | ✅ Not implemented (`'fach' \| 'diagnose' \| 'symptom'` only) |
| `MultiSelect` `allowCreate` | MultiSelect.svelte:13,24 | ✅ Exists; single-select prop does not |

---

## 7. Recommended plan revisions (priority order)

1. **Re-scope:** delete/mark-done Phase 1.1–1.4 and 2.1–2.4; rewrite as a wire-up plan (CRUD endpoints, entry/tagging service switch, frontend, admin tabs). Update the Files-Changed table and estimate.
2. **Add search-index strategy (U1):** redefine `mv_entry_search` over the new tables, schedule `POST /search/refresh-index` post-deploy, add FTS verification to acceptance criteria.
3. **Pick a write strategy (U2):** hard cutover (recommended — backfill already ran) or explicit dual-write window; then align `get_dokumenttypen`, stats, faceted, and detail-page fallback reads.
4. **Remove all auth/role content (B2):** drop Auth columns and the Phase 3 backend change; note WG-only, no roles.
5. **Fix `ordner_label_ids` silent drop (U3)** in create and update paths as part of 2.6.
6. **Fresh-install seeds (I5):** add dokumenttypen/ordner_labels rows to `seeds.sql`; reconcile the three value lists (I2).
7. **Decide `unterkategorie` ownership (I3)** and reflect it in 2.7 + the MV.
8. **Correct Phase 3 snippets (I4)** to the real `oncreate` detail shape; decide M5 (extend resolve-labels vs POST-only).
9. **Add acceptance criteria (M3)** and a rollout section (M4); specify single-select approach for Dokumenttyp (M1).

---

## 8. Conclusion

**Revise before implement.** The architecture is right and half of it already ships in the codebase — the danger is that the plan sends an implementer backward (re-running a migration, resurrecting auth) while omitting the one change that protects search correctness (the materialized view). A half-day re-write of the plan turns this into a clean 2–3 hour frontend-plus-endpoints job.
