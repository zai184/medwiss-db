# Plan: Upgrade to WHO ICD-11 classification via the ICD-API

**Status:** Proposed — pending credentials & scope decisions
**Date:** 2026-08-04
**Repo:** medwiss-db

> Sources: WHO ICD-API official docs (`https://icd.who.int/icdapi`, `https://icd.who.int/docs/icd-api/APIDoc-Version2/`). API v2.6, ICD-11 2026 release available; MMS linearization is the correct one for code structure as shown in the ICD-11 browser.

---

## 1. Objective

Integrate the official WHO **ICD-11 API** (`https://id.who.int`) so diagnosis codes in the `diagnosen` lookup are real **ICD-11 MMS codes**, and (optionally) so entry content can be **auto-coded** to ICD-11 instead of relying on the local LLM (Llamaserver, currently unavailable).

This is an **augmentation of the existing `diagnosen` system, not a rewrite** — the DB shape and M2M links stay; ICD-11 is layered on top.

---

## 2. Current state (verified)

- `diagnosen` table: **10 seeded rows**, all ICD-10 codes, `source='seed'`, `needs_review=False`.
  - `code varchar(20)` — already wide enough for ICD-11 alphanumeric codes (e.g. `4A00`, `6A71.21`).
  - `name varchar(255)`, `beschreibung text`, `created_at`, `needs_review bool`, `source varchar(20)`.
- `entry_diagnose` M2M: `(entry_id, diagnose_id)` — no change needed.
- No entries currently have diagnoses linked (`entry_diagnose` = 0). The dashboard "Häufigste Diagnosen" chart is empty because of this.
- Web UI only lists diagnoses (`classificationsApi.getDiagnosen`); **no UI to add new ones**. Create path is API-only (`POST /diagnosen`, admin).
- AI classification (`resolve_diagnose`) auto-creates rows with `needs_review=True`, `source='llm'`, and `TEMP-*` codes — this mechanism will be re-used for ICD-11 sourcing.

---

## 3. ICD-API mechanics (verified from WHO docs)

| Aspect | Value |
|---|---|
| API base URL | `https://id.who.int` |
| Token endpoint | `https://icdaccessmanagement.who.int/connect/token` |
| Auth grant | OAuth 2 **client_credentials** (HTTP Basic with client id/secret) |
| Token scope | `icdapi_access` |
| Token lifetime | ~1 hour (must be cached + refreshed) |
| Required header | `API-Version: v2` |
| Language | `Accept-Language: de` (German titles available) |
| Accept | `application/json` (JSON-LD) |
| Coding endpoint | `POST https://id.who.int/icd11/coding` — free-text → ICD-11 code(s) |
| Search endpoint | `POST/GET https://id.who.int/icd/release/11/{release}/mms/search` (flexisearch) |
| Entity URI | `https://id.who.int/icd/entity/{id}` (canonical identity for de-dup / deep links) |
| Linearization | `mms` (Mortality & Morbidity Statistics) — the structured code list matching the ICD-11 browser |

**Token request:**
```
POST https://icdaccessmanagement.who.int/connect/token
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded
grant_type=client_credentials&scope=icdapi_access
```
→ `{ "access_token": "...", "expires_in": 3600, "token_type": "Bearer" }`

**Search request (POST):**
```json
POST https://id.who.int/icd/release/11/2024/mms/search
API-Version: v2
Authorization: Bearer <token>
Accept-Language: de
Content-Type: application/json

{
  "q": "koronare herzkrankheit",
  "useFlexisearch": false,
  "chapterFilter": [],
  "subtreesFilter": [],
  "propertiesToBeSearched": ["title", "synonym", "narrowerTerm"],
  "flatResults": true
}
```

---

## 4. Prerequisites (user action — blocks live calls)

1. **Register / log in** at `https://icd.who.int/icdapi`.
2. Obtain the **client id + client secret** ("View API access key" link).
3. Confirm **license** terms (ICD-11 license is now more open; key required for programmatic access).
4. Supply the credentials as **environment variables only** — never in the repo (same policy as `JWT_SECRET`, `OPENROUTER_API_KEY`).

---

## 5. Architecture

```
[entry content / user-typed diagnosis string]
                  │
                  ▼
api/services/icd_client.py        (NEW)  token cache + HTTP client
   ├─ get_token()                         OAuth client_credentials, cached until expiry
   └─ code_text(text, lang="de")          POST /icd11/coding → {code, title, uri}
                  │
                  ▼
api/services/icd_coding.py        (NEW)  service glue
   └─ diagnose_from_text(db, text, lang)  code → find-or-create `diagnosen` row
                  │
                  ▼
api/routers/classifications.py    (MODIFIED)
   ├─ GET   /diagnosen                    unchanged
   ├─ POST  /diagnosen                    unchanged (admin manual create)
   ├─ POST  /diagnosen/icd11/code    (NEW): code a text fragment, upsert into diagnosen
   └─ GET   /diagnosen/icd11/search  (NEW, optional): browse ICD-11
```

---

## 6. DB changes (minimal)

**`diagnosen`** — additive only:
- Add `icd11_uri TEXT NULL` — canonical `http://id.who.int/icd/entity/{id}` (deep link + dedup key).
- Add `icd_version VARCHAR(10) DEFAULT 'ICD-11'` — explicit lineage; keep old ICD-10 rows distinguishable.
- `code varchar(20)` already fits ICD-11. `name varchar(255)` fits German titles.

**No change** to `entry_diagnose` (M2M) or `knowledge_entries`.

Optional (Phase E): `scripts/migrate_to_icd11.py` maps the 10 seeded ICD-10 codes → ICD-11 and re-points links.

---

## 7. Config (`api/config.py` — pydantic-settings, matches existing pattern)

```python
# ICD-11 (WHO API)
icd11_client_id: str = ""
icd11_client_secret: str = ""      # secret — env only
icd11_base_url: str = "https://id.who.int"
icd11_token_url: str = "https://icdaccessmanagement.who.int/connect/token"
icd11_release: str = "2024"        # MMS release; vendor to avoid silent code drift
```

`.env` additions (gitignored):
```
ICD11_CLIENT_ID=...
ICD11_CLIENT_SECRET=...
```

---

## 8. Implementation phases

### Phase A — ICD client + token cache (foundation)
- `api/services/icd_client.py`
  - `get_token()` — fetch, cache `access_token` + `expires_in` (thread-safe, single-flight).
  - `request()` wrapper — attaches `API-Version: v2`, `Authorization: Bearer`, `Accept-Language`, `application/json`.
  - `code_text(text, lang="de")` → POST `/icd11/coding`, normalized result.
  - Error model: `ICDUnavailableError` (typed). On 401, refresh token once and retry.
  - **Graceful degradation**: if credentials missing or network fails, raise typed error that callers degrade on — the app keeps working via seeded/LLM diagnoses.
- Unit tests with a mocked HTTP layer (no real key in CI).

### Phase B — service glue + diagnosis upsert
- `api/services/icd_coding.py`
  - `diagnose_from_text(db, text, lang="de")`:
    1. Call ICD-API coding endpoint.
    2. Find-or-create a `diagnosen` row keyed on `icd11_uri` (else code/name fuzzy via existing `_find_fuzzy_diagnose`).
    3. Set `code`, `name`, `icd11_uri`, `source='icd11'`.
    4. Return the same `DiagnoseResponse` shape the UI already consumes.
  - Mirrors the existing `resolve_diagnose` path but sources from WHO instead of the LLM.

### Phase C — API endpoint for coding
- New `POST /api/v1/diagnosen/icd11/code` — body `{ "text": string, "lang": "de" }`, editor+.
  - Calls `diagnose_from_text`; on `ICDUnavailableError` return **503** with a clear message.
- Optional `GET /api/v1/diagnosen/icd11/search?q=` (admin) for browse/search.

### Phase D — frontend integration (where the value lands)
- Entry edit form (`ui/src/routes/entry/[id]/edit/+page.svelte`) and `eingabe/+page.svelte`:
  - Add an **"ICD-11 Diagnose suchen"** autocomplete that calls the new endpoint and adds the returned ICD-11 diagnosis to `selectedDiagnosen` — same `MultiSelect` pattern already used, minimal UI churn.
- Auto-created ICD-11 rows flow through the existing `needs_review` / pending-review admin workflow.

### Phase E — migration of existing 10 diagnoses (recommended)
- `scripts/migrate_to_icd11.py`: map the 10 seeded ICD-10 codes → ICD-11 equivalents (e.g. `I25.9` KHK → `BA40/BA41`, `J44.9` COPD → `CA22`, `F32.1` Depression → `6A71`), re-pointing `entry_diagnose`.
- Preserve old ICD-10 code in a legacy column if traceability matters; otherwise update in place.

---

## 9. Tradeoffs & decisions to confirm

1. **Integration depth**
   - **Recommended (opt-in):** browse-and-add via UI search only. Low risk; no mass re-coding.
   - **Heavier (follow-up):** batch auto-code all 2606 entries and/or auto-code on entry save. Rate-limited + requires network; do as a separate "fill missing `diagnosen`" job.
2. **Language:** German (`Accept-Language: de`) to match content — confirm.
3. **Release pinning:** vendor `icd11_release` in config so future WHO MMS releases don't silently re-map codes.
4. **Lookup vs per-entry code:** this keeps `diagnosen` a *curated lookup table* (pick from list), preserving M2M/search/chart. Storing the *exact* ICD-11 code per entry is a separate `knowledge_entries.icd11_code` concern if needed later.
5. **Credentials:** blocks live calls until supplied; scaffolding degrades gracefully without them.

---

## 10. Security notes

- Client **secret never in git / repo** — env-only (same as existing secrets).
- Token fetched **server-side only**, never exposed to the browser.
- **Rate-limit** the coding endpoint (WHO API has usage caps); add a small throttle/cooldown on the new route.

---

## 11. Files touched (summary)

| Path | Kind | Purpose |
|---|---|---|
| `api/services/icd_client.py` | NEW | OAuth token cache + HTTP client + coding call |
| `api/services/icd_coding.py` | NEW | `diagnose_from_text` service glue |
| `api/routers/classifications.py` | MOD | add `POST /diagnosen/icd11/code` (+ optional search) |
| `api/config.py` | MOD | ICD-11 settings |
| `api/models.py` | MOD | request/response Pydantic models for the new route |
| `database/schema.sql` + Alembic | MOD | `diagnosen.icd11_uri`, `icd_version` |
| `ui/src/lib/api.ts` | MOD | `classificationsApi.icd11Code()` / `icd11Search()` |
| `ui/src/routes/.../edit/+page.svelte`, `ui/src/routes/eingabe/+page.svelte` | MOD | ICD-11 search autocomplete in diagnosis picker |
| `scripts/migrate_to_icd11.py` | NEW | seed migration (phase E) |
| `tests/` | MOD | icd_client w/ mocked HTTP; diagnose_from_text |

---

## 12. Open questions

- [ ] Supply WHO ICD-API **client id + secret** (env).
- [ ] Confirm **integration depth**: UI browse-and-add only (recommended) vs. also batch auto-code.
- [ ] Confirm **language**: `de` (recommended).
- [ ] Confirm **ICD release** pin (default `2024`, or latest `2026`).
- [ ] Migrate the 10 existing ICD-10 seeds to ICD-11 now (phase E) or keep both in parallel?
