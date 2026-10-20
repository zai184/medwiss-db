# Unified Tagging System — Implementation Plan

**Date:** 2026-08-26 (revised 2026-08-29 after `unified-tagging-system-critique.md`)
**Status:** Ready to implement — re-scoped as **wire-up**: DB layer is already merged
**Goal:** Every entry has a single, consistent set of user-editable tags. No read-only dimensions, no hardcoded lists, no broken inline create.

---

## Decisions Made

| Question | Answer |
|----------|--------|
| Ordner-Labels → real lookup table? | **Yes** — done (migration 005 applied) |
| Dokumenttyp single or multi-select? | **Single-select**, plain `<select>` fed by the API (no MultiSelect changes) |
| Who can create labels? | **Anyone** — auth was removed (WG-only deployment, commit `8323206`); no role gating exists or returns |
| Write strategy for old columns? | **Dual-write** (`dokumenttyp` string + `source_hierarchy` JSONB stay updated) until Phase 7 redefines the search MV — prevents stale reads in stats/faceted/FTS |
| `unterkategorie` | **Keep, dual-written** — actively read by `mv_entry_search` (`schema.sql:304`); writer stays in `tagging_service` |

---

## Current State (verified 2026-08-29)

### Already implemented — do NOT redo

| Layer | State | Evidence |
|-------|-------|----------|
| Migration | ✅ Applied | `database/migrations/005_unified_tagging.sql` — dokumenttypen + 12 seeds, ordner_labels, entry_ordner_label, `dokumenttyp_id` FK, data backfill |
| schema.sql | ✅ Updated | tables at lines 56/67/196, FK + indexes at 110/139, junction index at 202 |
| SQLAlchemy models | ✅ Exist | `database/models.py`: `Dokumenttyp` (~181), `OrdnerLabel` (~162), `dokumenttyp_ref` + `ordner_labels` relationships on `KnowledgeEntry` |
| Pydantic models | ✅ Exist | `api/models.py`: `dokumenttyp_id` (:99), `ordner_label_ids` (:113,130), `dokumenttyp_ref` (:147), `ordner_labels` (:148) |
| API contract | ✅ Advertises fields | `contracts/api/openapi.json` + `ui/src/lib/api-types.d.ts` contain the new response fields — but they are always `null`/`[]` (service never populates them) |
| Value lists | ✅ Consistent | 005 seeds = `DOKUMENTTYP_OPTIONS` (edit page) = 12 identical names |

### Missing — the actual work

| Gap | Evidence |
|-----|----------|
| No CRUD endpoints for dokumenttypen / ordner-labels | `api/routers/classifications.py` — only fach/diagnose/symptom + resolve-labels |
| `dokumenttyp_id` written **nowhere** | `entry_service.create_entry` uses string (:255); `tagging_service.apply_proposals` uses string (:285) |
| `ordner_label_ids` accepted and **silently dropped** | `update_entry` pops only fach/diagnose/symptom id lists (:300–302), then `setattr`s the rest onto the ORM object — plain attribute, vanishes on commit; `create_entry` ignores it entirely |
| Responses never populate `dokumenttyp_ref` / `ordner_labels` | `entry_service.to_response` (:55–105) sets neither; `_base_query` (:39–45) doesn't load them |
| Edit page: hardcoded select + read-only hierarchy | `DOKUMENTTYP_OPTIONS` (:11), `<select bind:value={dokumenttyp}>` (:252), `sourceHierarchy` plain state (:25), submit sends strings (:123–124) |
| Eingabe page: inline create uses fake `Date.now()` IDs | :215–228; never persisted |
| Admin page: only 3 tabs | `LabelTab = 'fach' \| 'diagnose' \| 'symptom'` |
| Detail page: 5 chip groups, Dokumenttyp styled as `tag-fach` | entry/[id]/+page.svelte:152–199 |
| Search MV/FTS built from legacy columns | `mv_entry_search` reads `ke.dokumenttyp` (:366) and weights `source_hierarchy` at C (:352); `search/faceted.py` filters `mv.dokumenttyp` (:129); stats group by string (`stats.py:96–98`) |

---

## Phase 1: CRUD Endpoints

**File:** `api/routers/classifications.py` — mirror the existing fachgebiete pattern exactly (duplicate-name check → 409, inline db ops, `FachgebietCreate`-style request models in `api/models.py`):

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dokumenttypen` | List all |
| POST | `/dokumenttypen` | Create |
| PUT | `/dokumenttypen/{id}` | Rename |
| DELETE | `/dokumenttypen/{id}` | Delete (FK is `ON DELETE SET NULL` — entries keep running) |
| GET | `/ordner-labels` | List all |
| POST | `/ordner-labels` | Create |
| PUT | `/ordner-labels/{id}` | Rename |
| DELETE | `/ordner-labels/{id}` | Delete (junction `ON DELETE CASCADE`) |

Pydantic: `DokumenttypCreate` (name), `OrdnerLabelCreate` (name). Responses exist already (`DokumenttypResponse`, `OrdnerLabelResponse`). Skip `GET /{id}` and `/{id}/entries` — nothing consumes them; add on demand.

**SoT rule:** after Phase 2, the DB tables are the only source of Dokumenttyp values; `DOKUMENTTYP_OPTIONS` dies in Phase 4.

## Phase 2: Service Layer — writes, reads, silent-drop fix

**File:** `api/services/entry_service.py`

- `_base_query`: add `joinedload(KnowledgeEntry.dokumenttyp_ref)`, `joinedload(KnowledgeEntry.ordner_labels)`
- `to_response`: populate `dokumenttyp_ref` (id/name) and `ordner_labels` from the relationships
- `create_entry`: accept `dokumenttyp_id`; resolve to row and set **both** `dokumenttyp_id` and the legacy `dokumenttyp` string (dual-write); accept `ordner_label_ids` → set `db_entry.ordner_labels` (same pattern as fachgebiete) and mirror into `source_hierarchy` (sorted names)
- `update_entry`: pop `dokumenttyp_id` and `ordner_label_ids` explicitly (kill the silent drop — `dokumenttyp_id` currently "works" only by accident of `setattr` hitting a real column); on rename-sync, if `dokumenttyp` string is updated instead, resolve to ID. Same dual-write mirroring as create
- `get_dokumenttypen`: return names from the `Dokumenttyp` table (keeps `/entries/dokumenttypen` response shape stable) — callers: `api/routers/entries.py:37`

**File:** `api/services/tagging_service.py`

- `apply_proposals` (:273–326): when setting `entry.dokumenttyp`, look up/insert the `Dokumenttyp` row and set `dokumenttyp_id` too; keep `source_hierarchy`/`unterkategorie` writes (dual-write)
- `resolve_labels_to_ids` (:368+): extend for optional `dokumenttyp: str` (name → id, auto-create with `needs_review=True`) — used by Phase 3 fallback and `apply_proposals`

## Phase 3: Inline Create Fix (frontend only — no backend role change)

**Files:** `ui/src/routes/eingabe/+page.svelte`, `ui/src/routes/entry/[id]/edit/+page.svelte`

Replace the `Date.now()` handlers (:215–228 in eingabe). Keep the existing `oncreate` detail shape (`detail: { value: string }`):

```ts
async function handleCreateFachgebiet(detail: { value: string }) {
  const name = detail.value.trim();
  if (!name) return;
  try {
    const created = await classificationsApi.createFachgebiet({ name });
    fachgebiete = [...fachgebiete, created];
    selectedFachgebiete = [...selectedFachgebiete, created.id];
  } catch {
    // 409 = already exists → resolve to its ID; other errors → resolve-labels auto-creates with needs_review
    const resolved = await classificationsApi.resolveLabels({ fachgebiete: [name], diagnosen: [], symptome: [] });
    if (resolved.fachgebiet_ids.length > 0) {
      fachgebiete = await classificationsApi.getFachgebiete();
      selectedFachgebiete = [...selectedFachgebiete, resolved.fachgebiet_ids[0]];
    }
  }
}
```

Same pattern for Diagnosen, Symptome, and (new, Phase 4/5) Ordner-Labels/Dokumenttypen via their new endpoints. `MultiSelect.allowCreate` already exists — no component change needed.

## Phase 4: Edit Page — Unified Tags Section

**File:** `ui/src/routes/entry/[id]/edit/+page.svelte`

- Delete `DOKUMENTTYP_OPTIONS`; load dokumenttypen once on mount, render plain `<select>` bound to `dokumenttyp_id`; on submit send `dokumenttyp_id` (drop the string field)
- Ordner-Labels: replace read-only `sourceHierarchy` chips with `<MultiSelect allowCreate>` loaded from `/ordner-labels`, bound to `ordner_label_ids`; "Ordner-Labels übernehmen" banner stays as pre-fill (maps suggestion names → IDs via the loaded list, creating missing ones first)
- Group Dokumenttyp + Ordner-Labels + Fachgebiete + Diagnosen + Symptome under one "Tags" header; "KI vorschlagen" stays at the bottom
- Submit payload: `dokumenttyp_id`, `ordner_label_ids` instead of `dokumenttyp`, `source_hierarchy`

## Phase 5: Eingabe Page — same tag editors

**File:** `ui/src/routes/eingabe/+page.svelte`

- Same Dokumenttyp `<select>` + Ordner-Labels MultiSelect as Phase 4
- Fixed inline-create handlers from Phase 3 wired to all five dimensions

## Phase 6: Detail Page — Unified Tag Chips

**File:** `ui/src/routes/entry/[id]/+page.svelte`

One "Tags" section; read `entry.dokumenttyp_ref?.name` (fallback `entry.dokumenttyp` for pre-migration rows) and `entry.ordner_labels` (fallback `entry.source_hierarchy`):

```svelte
<div class="entry-tags">
  <h2 class="section-label">Tags</h2>
  <div class="tags">
    {#if entry.dokumenttyp_ref || entry.dokumenttyp}
      <span class="tag tag-dokumenttyp">{entry.dokumenttyp_ref?.name ?? entry.dokumenttyp}</span>
    {/if}
    {#each entry.ordner_labels as label}
      <span class="tag tag-hierarchy">{label.name}</span>
    {/each}
    {#each entry.fachgebiete as fach}<span class="tag tag-fach">{fach.name}</span>{/each}
    {#each entry.diagnosen as d}<span class="tag tag-diagnose">{d.code ? `${d.code}: ` : ''}{d.name}</span>{/each}
    {#each entry.symptome as s}<span class="tag tag-symptom">{s.name}</span>{/each}
  </div>
</div>
```

Accent colors: dokumenttyp purple, hierarchy gray, fach blue, diagnose green, symptom orange (latter three exist); same chip shape for all.

## Phase 7: Admin Tabs + Search MV + Stats

**`ui/src/routes/admin/+page.svelte`** — extend `LabelTab` with `'dokumenttyp' | 'ordner'`; two new tabs in "Labels verwalten" using the existing CRUD wiring (`code` input only for Diagnosen).

**`database/schema.sql`** — redefine `mv_entry_search` so tags come from the new sources:
- `dokumenttyp` from `dokumenttypen` via `dokumenttyp_id` (left join, coalesce legacy column during transition)
- hierarchy labels aggregated from `entry_ordner_label` ⨝ `ordner_labels` (coalesce legacy `source_hierarchy`)
- keep the `setweight(... 'C')` FTS contribution fed by the new aggregation

**Read migrations (dual-write makes these safe to do anytime):**
- `search/faceted.py` — no change needed while MV exposes the same column names; verify after MV swap
- `api/routers/stats.py` by-category (:96–98): group via join to `dokumenttypen` (falls back to string while rows carry both)

## Phase 8: Contract Regen + Rollout

1. `./scripts/gen-api.sh` (new endpoints + populated response fields)
2. Deploy API + UI together (SPA + API, same commit)
3. `psql` — verify MV definition replaced; `POST /api/v1/search/refresh-index`
4. Spot-checks (acceptance criteria below)

### Acceptance criteria

- [ ] Create entry via eingabe with 1 Dokumenttyp + 2 Ordner-Labels (one created inline) → reload: all persist with correct IDs (no `Date.now()` values in DB)
- [ ] Inline-created label appears in admin tab; rename there propagates to detail chips after reload
- [ ] Detail page shows one Tags group, five accent colors
- [ ] FTS: `GET /search/chunks`-independent check — `q=<ordner label name>` hits the entry; faceted filter by Dokumenttyp returns it
- [ ] `GET /api/v1/entries?dokumenttyp=<name>` still filters correctly
- [ ] Stats by-category counts match dokumenttypen table

### Migration safety & rollback

- No schema changes in this plan (005 already applied). All changes are code.
- Old columns stay dual-written → reverting any frontend/service commit is safe; data never diverges
- Rollback = `git revert` + `refresh-index`; the MV redefinition is the only piece needing the revert to include its previous definition (kept in `schema.sql` git history)

---

## Files Changed

| Phase | File | Change |
|-------|------|--------|
| 1 | `api/routers/classifications.py` | dokumenttypen + ordner-labels CRUD (8 endpoints) |
| 1 | `api/models.py` | `DokumenttypCreate`, `OrdnerLabelCreate` |
| 2 | `api/services/entry_service.py` | populate refs, handle both id fields (fix silent drop), dual-write, get_dokumenttypen from table |
| 2 | `api/services/tagging_service.py` | resolve names→IDs, dual-write in apply_proposals |
| 3–5 | `ui/src/lib/api.ts` | `dokumenttypenApi`, `ordnerLabelsApi`, types; EntryCreate/Update gain `dokumenttyp_id`, `ordner_label_ids` |
| 3 | `ui/src/routes/eingabe/+page.svelte` | real inline create, new tag editors |
| 4 | `ui/src/routes/entry/[id]/edit/+page.svelte` | unified Tags section, ID-bound editors |
| 6 | `ui/src/routes/entry/[id]/+page.svelte` | unified tag chips |
| 7 | `ui/src/routes/admin/+page.svelte` | 2 new label tabs |
| 7 | `database/schema.sql` | MV redefinition |
| 7 | `api/routers/stats.py` | by-category via lookup join |
| 8 | `contracts/api/openapi.json`, `ui/src/lib/api-types.d.ts` | regenerated (do not hand-edit) |

**Total:** 12 files. Backend ~half day, frontend ~1 day, MV + verification ~half day.
