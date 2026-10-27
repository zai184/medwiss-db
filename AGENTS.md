# AGENTS.md - Documentation

> Medical Knowledge Database - Architecture and Implementation Documentation

	**Last Updated:** 2026-10-27 (Ctrl+C/stop.sh cleanup: start.sh `cleanup` now runs once — SIGINT+EXIT trap double-fired, so `dc down`/sudo prompt ran twice — and its stderr swallow dropped like stop.sh Phase 7's; stop.sh leftover report excludes the codegraph MCP (argv carries the repo path, multi-line argv leaked past grep -v). Earlier: start.sh sidecar handling: compose `up -d` errors no longer swallowed by `2>/dev/null`, health timeout 60 s → 300 s (8B Q6 CPU load), closing banner reports sidecar NOT READY instead of claiming it is up, and `sidecar_up()` retries `down`+`up -d` once when a stale container is bound to a deleted network (`network … not found`); README + config/AGENTS corrected — `load_sources()` is discovery ∪ yaml, the live API lists 12 sources / 14 watch paths incl. auto-discovered `10_Bücher`. Earlier today: removed `1_AGENTS.md` (stray personal file) and `knowledge_entries.embedding` end-to-end: column + IVFFLAT index out of `schema.sql`, model field out of `database/models.py`, ingest writer out of `file_sync.py`, `scripts/generate_embeddings.py` + `pipeline/embeddings.py` deleted, `medwiss-embeddings` entry point and `tqdm` dependency dropped, migration `007_drop_entry_embeddings.sql` for existing databases (`chunks.embedding` for Leitlinien search untouched); `api/AGENTS.md` router tree now lists all 12 routers. Earlier today: repo-wide staleness sweep against code: README Batch-Import/JWT/roles/folder-table, QUICKSTART init_db.py + hybrid + bun.lockb + references-404, root AGENTS diagram/env-table/known-issues/recent-fixes, all module AGENTS re-checked; pyproject drops entry points for deleted modules and declares `tqdm` (undeclared import in generate_embeddings.py), TODO publish marked done 2026-10-20. Earlier today: stale auth docs purged from README (### Authentication endpoints) and api/AGENTS.md (auth.py router, dependencies.py JWT deps, Auth-requirements row, Bearer convention), all removed with auth 2026-08-29; QUICKSTART Default Credentials table + login/Bearer curls dropped earlier today; stop.sh kill fixes: multi-PID kills were no-ops — zsh does not word-split, so `kill -9 "1\n2"` failed silently; BRE patterns in pgrep's ERE engine never matched (tesseract/multiprocessing/vite phases); PROJECT_ROOT was the caller's cwd so scoping matched nothing outside the repo dir; compose unified via `dc()`, `cd || exit 1` before `down`, verification `ps|grep` → `pgrep`. Also start.sh streamlined 284→199 lines: prereq checks → one loop, dead `.env.example`/credentials/mac+Windows branches dropped, compose unified via `dc()`; fixes: zsh `${BASH_SOURCE[0]}` was empty → `${0:A:h}` script dir, fixed `sleep 3`/`sleep 4` → `wait_for_health` polling, `bun install` unconditional, sidecar health timeout no longer aborts startup, cleanup propagates real exit codes. Earlier: 2026-10-15 deploy host/port moved to gitignored `.private/deploy.env`; home paths and WireGuard address live in `.private/infra.md`. Earlier: svelte-check warnings 32→1: entry detail/edit staleness bugs fixed — same-route navigation kept old entry's form data, detail uses `$derived` + `inhaltOverride`, edit re-snapshots via `formSnapshot` effect; a11y label/aria-controls/role fixes; dead CSS deleted; KIPreview+bibliothek icon CSS made `:global` (was never applying — {@html}/lucide passthrough); StatCard runes cleanup. Security audit 2026-09-24 fully cleared: stored XSS High fixed via shared `ui/src/lib/highlight.ts` escape-then-`<mark>`, bun test regression (`cd ui && bun test`, bun-types added); uv.lock upgrades pillow 12.3.0 / starlette 1.8.0 / python-multipart 0.0.32 / anyio / idna / pydantic-settings / mako / click; requirements.txt deleted — uv.lock is the only dep source, QUICKSTART updated; start.sh dev API binds 127.0.0.1; files.py allowlist via Path.is_relative_to (sibling-prefix rejected); PubMed via defusedxml; README warning block replaces stale admin credentials.)
	**Total LOC:** ~97,706
# Documentation
!! Important: after working on the codebase, write all changes to CHANGELOG.md including timestamp (yyyy-mm-dd hh-mm), LOC added and LOC total. update AGENTS.md !!

**Security audit 2026-09-24** (Tier 2) was removed from the tree. Its findings were fixed 2026-10-15: stored XSS (High) via shared
`ui/src/lib/highlight.ts` (escape-then-`<mark>`, regression test `highlight.test.ts`,
run with `cd ui && bun test`), `uv.lock` dep upgrades (pillow 12.3, starlette 1.8, …),
`requirements.txt` deleted (uv.lock is the only dep source), `start.sh` binds
127.0.0.1, file allowlist via `Path.is_relative_to`, PubMed parsing via `defusedxml`.

**Run after an API shape change** (Pydantic / `response_model` / request body — same commit):

```bash
./scripts/gen-api.sh
```

Writes `contracts/api/openapi.json` + `ui/src/lib/api-types.d.ts`. Do not edit those files by hand.

**Releases**: semver, single source = `pyproject.toml` `version`. Cut a release with
`./scripts/release.sh X.Y.Z` (bumps version, versions the CHANGELOG, annotated tag
`vX.Y.Z`, push `--follow-tags`; refuses a dirty tree). The running version is exposed
at `GET /api/v1/version` (reads pyproject at startup).


**Git topology (since 2026-10-20 GitHub publish)**: public `main` is a fresh
single-commit squash → `origin` = `github.com/zai184/medwiss-db`. The former
96-commit history lives in branch `archive` → `backup` (NAS) — it contains
old host details and the 2026-09-24 audit report; never push `archive` or the
old tags to GitHub. `scripts/release.sh` tags on the new history from now on.
Guard: `core.hooksPath` points at `.private/githooks` — its `pre-push` refuses
every non-`main` ref to GitHub and greps outgoing commits for the `.private/`
host tokens. Re-arm after a fresh clone: `git config core.hooksPath .private/githooks`.

## Overview

The **Medizinische Wissensdatenbank** (Medical Knowledge Database) shows the files in the configured source folders. Those files are the library. PostgreSQL 15 + pgvector is required as the index: `knowledge_entries` is one row per file (path, hash, tags, full-text search), and `chunks` holds AWMF guideline passages for Leitlinien search. A directory listing cannot replace that. Rechner and Notfall are frontend lists and do not use the database. OCR and summarization run on demand.

Application code is GNU AGPL-3.0 (`LICENSE`), the same license as Odysseus. There is no contributor license agreement. The medical corpus is not in this repository and is not under that license.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (SvelteKit)                     │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐ │
│   │Dashboard│   │ Search  │   │ Entry   │   │  KI Upload      │ │
│   │   /    │   │/search  │   │/eingabe │   │  Processing     │ │
│   └─────────┘   └─────────┘   └─────────┘   └─────────────────┘ │
│                                                                   │
│   ┌─────────────────────┐   ┌─────────────────────────────────┐ │
│   │ Entry Detail        │   │  Entry Edit                     │ │
│   │ /entry/[id]         │   │  /entry/[id]/edit              │ │
│   └─────────────────────┘   └─────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────────────┐
│                    Backend (FastAPI)                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│   │   CRUD  │  │  Search  │  │    Stats     │  │
│   │ /entries │  │ /search  │  │  /files  │  │   /stats     │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │                  KI Pipeline                              │ │
│   │  ┌───────┐  ┌──────────────┐  ┌─────────────┐         │ │
│   │  │  OCR  │  │  Summarize   │  │  Remote OCR │         │ │
│   │  │Tesseract│  │   LLM      │  │ glm-4.6v    │         │ │
│   │  └───────┘  └──────────────┘  └─────────────┘         │ │
│   └──────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SQL
┌──────────────────────────▼──────────────────────────────────────┐
│                   PostgreSQL 15 + pgvector                      │
│   ┌─────────────┐  ┌────────────┐  ┌─────────────────────────┐   │
│   │  Tables    │  │    FTS     │  │      pgvector          │   │
│   │  (14)     │  │  (tsvector)│  │    (embeddings)        │   │
│   └─────────────┘  └────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Purpose |
|----------|------------|---------|
| **Database** | PostgreSQL 15 + pgvector | Index of source files, tags, and guideline chunks |
| **Backend** | FastAPI + SQLAlchemy | REST API |
| **OCR** | Tesseract (pytesseract) + OpenRouter glm-4.6v | On-demand image/PDF text extraction |
| **AI** | Llamaserver (local LLM) + OpenRouter | Summarization, RAG |
| **Frontend** | SvelteKit + TypeScript | Web UI |
| **UI types from API** | `./scripts/gen-api.sh` | FastAPI OpenAPI → `contracts/api/openapi.json` + `ui/src/lib/api-types.d.ts` |
| **Package Manager** | bun | Fast JS/TS package manager & runtime |
| **Charts** | Chart.js | Dashboard visualizations |

## Directory Structure

```
medwiss-db/
├── api/                          # FastAPI application
│   ├── main.py                   # App entry point, CORS, routes
│   ├── config.py                 # Settings via pydantic-settings
│   ├── database.py               # SQLAlchemy engine
│   ├── models.py                 # Pydantic models
│   └── routers/
│       ├── entries.py            # /entries CRUD
│       ├── search.py             # /search (keyword), /search/chunks, /search/chunks/rag
│       ├── stats.py              # /stats/overview, /stats/by-fach
│       ├── pipeline.py           # /pipeline/process-file (single file)
│       ├── summarize.py          # /entries/{id}/summarize
│       ├── admin.py              # /admin/classify-from-filename (regex classification)
│       ├── icd11.py              # /icd11/token (WHO OAuth2 proxy for ECT browser)
│       ├── references.py         # /references (live parse of medlinks.txt)
│       └── pubmed.py             # /pubmed/search
│
├── api/services/                 # Business logic services
│   ├── file_sync.py             # File synchronization with database (single reconcile core)
│   ├── source_watcher.py        # Watchdog source folder monitoring (live upserts)
│   ├── sync_state.py            # In-memory last-change state for /admin/sync-status
│   ├── regex_classifier.py      # Deterministic regex classification (no LLM)
│   └── icd11.py                 # WHO ICD-11 API client (OAuth2, enrichment)
│
├── database/                     # Database schema & migrations
│   ├── schema.sql               # All tables, triggers, indexes
│   ├── alembic.ini              # Alembic config
│   ├── migrations/             # SQL migrations (001-006)
│   └── seeds.sql               # Test data
│
├── pipeline/                    # KI Pipeline modules
│   ├── ocr.py                  # Tesseract OCR (local backend)
│   ├── ocr_backend.py          # Ordered-try OCR seam (tesseract / openrouter-vision)
│   ├── remote_ocr.py           # OpenRouter vision OCR (glm-4.6v)
│   ├── orchestrator.py          # On-demand extract_text + summarize_file
│   ├── batch_processor.py       # Single-file process_file + calculate_file_hash
│   ├── classification_resolver.py # LLM output resolution
│   ├── duplicate_detector.py     # SHA-256 duplicate detection
│   └── prompts/
│       └── summarize/           # Summarization skill prompts
│           ├── studie.txt       # Study summary skill
│           ├── leitlinie.txt    # Guideline summary skill
│           ├── screenshot.txt   # Image analysis skill
│           └── standard.txt     # General summary skill
│
├── search/                      # Search implementations
│   ├── keyword.py              # Simple ILIKE keyword search over entries
│   └── chunks.py               # AWMF chunk vector search (exact cosine)
│
├── contracts/api/               # Generated OpenAPI (do not edit by hand)
│   └── openapi.json
│
├── scripts/                     # Utility scripts
│   ├── gen-api.sh              # FastAPI OpenAPI → ui/src/lib/api-types.d.ts
│   ├── export_openapi.py
│   ├── import_files_as_links.py  # Link-only import
│   └── stop.sh                 # Stop all services
│
├── config/                      # Configuration system
│   ├── __init__.py            # Config loader + Pydantic models
│   └── sources.yaml           # YAML overrides over auto-discovered folders
│
├── ui/                         # SvelteKit frontend
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte           # Dashboard
│   │   │   ├── +layout.svelte          # Root layout with sidebar
│   │   │   ├── search/+page.svelte     # Search interface (reference design)
│   │   │   ├── eingabe/+page.svelte    # Entry form with KI upload
│   │   │   ├── rechner/+page.svelte   # Klinische Rechner (MDCalc-Favoriten + Suchlinks)
│   │   │   ├── admin/                  # Admin section
│   │   │   │   └── +page.svelte        # Dark Mode, Klassifizierung, Labels
│   │   │   ├── entry/[id]/             # Entry detail view
│   │   │   │   ├── +page.svelte        # Detail page (view mode)
│   │   │   │   ├── +page.ts            # Detail load function
│   │   │   │   └── edit/               # Entry edit route
│   │   │   │       ├── +page.svelte    # Edit form
│   │   │   │       └── +page.ts        # Edit load function
│   │   ├── lib/
│   │   │   ├── api.ts                  # API client (axios)
│   │   │   ├── calculators.ts          # Curated MDCalc calculator links (Rechner page)
│   │   │   ├── api-types.d.ts          # Generated OpenAPI types (do not edit)
│   │   │   ├── stores/                 # Svelte stores
│   │   │   │   ├── search.ts           # Search state
│   │   │   │   └── entryForm.ts         # Form state
│   │   │   └── components/
│   │   │       ├── SearchResults.svelte
│   │   │       ├── FacetFilters.svelte
│   │   │       ├── FileUpload.svelte
│   │   │       ├── KIPreview.svelte
│   │   │       ├── TranscribeModal.svelte     # OCR text extraction modal
│   │   │       ├── MultiSelect.svelte
│   │   │       ├── StatCard.svelte
│   │   │       ├── ActivityList.svelte
│   │   │       └── charts/
│   │   │           ├── FachDistribution.svelte
│   │   │           └── DiagnoseBarChart.svelte
│   │   └── app.css              # Global styles
│   ├── package.json
│   ├── svelte.config.js        # Static adapter
│   └── vite.config.ts          # API proxy
│
├── docker-compose.yml           # PostgreSQL + pgvector
├── start.sh                    # One-command startup
├── stop.sh                     # Stop all services
├── pyproject.toml             # Project metadata
├── flake.nix                  # Nix dev shell configuration
└── .envrc                     # Direnv auto-activation
```

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `knowledge_entries` | Index of one source file: path, hash, title, tags, search text |
| `fachgebiete` | Medical specialties lookup |
| `diagnosen` | Diagnoses lookup |
| `symptome` | Symptoms lookup |
| `entry_fach` | M2M: entry → specialty |
| `entry_diagnose` | M2M: entry → diagnosis |
| `entry_symptom` | M2M: entry → symptom |
| `dokumenttypen` | Document types lookup (Leitlinie, SOP, Studie, …) |
| `ordner_labels` | Folder hierarchy labels lookup |
| `entry_ordner_label` | M2M: entry → folder label |
| `awmf_documents` | AWMF PDF registry (one row per guideline) |
| `chunks` | Universal chunk store (AWMF now; library later) — `vector(2048)`, polymorphic `(source_type, source_id)` |

### Indexes

- `idx_knowledge_entries_fts` - GIN index on `search_vector` (FTS)
- `idx_knowledge_entries_title_trgm` - GIN index on `titel` (fuzzy)

## API Endpoints

### Knowledge Entries

> **No authentication** — auth (JWT, users, login) was removed 2026-08-29. All
> endpoints are public; the `users` table survives only as an attribution target
> for `created_by`/`updated_by` columns.
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/entries` | List entries (paginated) |
| GET | `/api/v1/entries/{id}` | Get single entry |
| POST | `/api/v1/entries` | Create entry |
| PUT | `/api/v1/entries/{id}` | Update entry |
| DELETE | `/api/v1/entries/{id}` | Delete entry |
| GET | `/api/v1/entries/{id}/tag-suggestions` | Folder-path tag suggestions |
| POST | `/api/v1/entries/{id}/tag-suggestions/apply` | Apply folder hierarchy metadata |
| POST | `/api/v1/resolve-labels` | Resolve string labels to lookup IDs (`fachgebiete`, `diagnosen`, `symptome`, `dokumenttyp`, `ordner_labels`; auto-creates missing rows) |
| GET | `/api/v1/pending-review` | Admin review queue for auto-created tags (5 kinds incl. dokumenttyp + ordner_label) |

### Classifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/fachgebiete` | List specialties |
| POST | `/api/v1/fachgebiete` | Create specialty |
| GET | `/api/v1/fachgebiete/{id}/entries` | Entries by specialty |
| GET/POST | `/api/v1/dokumenttypen` | List / create document types |
| PUT/DELETE | `/api/v1/dokumenttypen/{id}` | Rename / delete (FK SET NULL — entries keep legacy string) |
| GET/POST | `/api/v1/ordner-labels` | List / create folder labels |
| PUT/DELETE | `/api/v1/ordner-labels/{id}` | Rename / delete (junction cascades) |

### Unified Tagging System (2026-08-29)

The five tag dimensions (Fachgebiete, Diagnosen, Symptome, Dokumenttypen, Ordner-Labels)
are unified: every tag is a row in a lookup table linked by ID.

- **Source of truth**: lookup tables. `knowledge_entries.dokumenttyp_id` FK +
  `entry_ordner_label` junction (column is `label_id` — matches migration 005).
- **Dual-write**: legacy columns stay current on every write — `dokumenttyp` string and
  `source_hierarchy` JSONB are mirrored from IDs (`entry_service.create_entry/update_entry`,
  `tagging_service.apply_proposals`). Stats/faceted/FTS read both safely.
- **Frontend** sends `dokumenttyp_id` + `ordner_label_ids`; Dokumenttyp is a table-backed
  `<select>`, Ordner-Labels an editable MultiSelect. Inline-create POSTs the real endpoint;
  409 → resolve to existing ID. No fake `Date.now()` IDs anywhere.
- **Auto-create**: `pipeline/classification_resolver.resolve_dokumenttyp/resolve_ordner_label`
  — exact case-insensitive match, else create. LLM-sourced rows get `needs_review=True`
  (pending-review queue); folder-sourced rows are trusted (`needs_review=False`).
- **Search**: `v_entry_search` aggregates tags from the lookup tables with legacy-column
  fallback (regular view, always current, no refresh).
- **Entry responses** populate `dokumenttyp_id`, `dokumenttyp_ref`, `ordner_labels`;
  detail chips fall back to legacy `dokumenttyp`/`source_hierarchy` for pre-migration rows.

| Component | Path | Purpose |
|---|---|---|
|**CRUD endpoints**|`api/routers/classifications.py`|dokumenttypen + ordner-labels CRUD, resolve-labels, pending-review (5 kinds)|
|**ID switch + dual-write**|`api/services/entry_service.py`|create/update handle both ID fields, mirror legacy columns|
|**apply_proposals dual-write**|`api/services/tagging_service.py`|folder/LLM proposals write ID + legacy, link OrdnerLabel rows|
|**Resolvers**|`pipeline/classification_resolver.py`|`resolve_dokumenttyp`, `resolve_ordner_label`|
|**Tag editors**|`ui/src/routes/eingabe/+page.svelte`, `ui/src/routes/entry/[id]/edit/+page.svelte`|Dokumenttyp select + Ordner-Labels MultiSelect, real inline create|
|**Tag chips**|`ui/src/routes/entry/[id]/+page.svelte`|one "Tags" group, 5 accent colors, legacy fallback|
|**Admin tabs**|`ui/src/routes/admin/+page.svelte`|"Labels verwalten" with 5 tabs incl. Dokumenttypen, Ordner-Labels|
|**Search view**|`database/schema.sql` (`v_entry_search`)|tag aggregation from lookup tables + legacy fallback|

### Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/search?q=&limit=&offset=&fachgebiet=&dokumenttyp=&folder=` | Keyword ILIKE search with tier ranking; optional filters (fachgebiet id/name, dokumenttyp id/name w/ legacy string fallback, first source_hierarchy segment) ANDed on top; `q` optional when filters set; response includes `filters` options block |
| GET | `/api/v1/search/chunks?q=&limit=&offset=` | AWMF chunk vector search (exact cosine, ~5 s) — instruct-prefix embed via sidecar :8081 |
| GET | `/api/v1/search/chunks/rag?q=&top_k=` | RAG over AWMF chunks: retrieve top-k → prompt 9B (:8080, qwen35-9b-i) → German answer + source pointers (~30 s) |

### Statistics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/stats/overview` | Total counts |
| GET | `/api/v1/stats/by-category` | By category |
| GET | `/api/v1/stats/by-fach` | By specialty |

### File Sync
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/files/admin/sync-status` | Cheap sync status (in-memory state, no re-hash; UI polls every 10 s) |
| POST | `/api/v1/files/admin/sync` | Manual full reconcile (ingest/modify/delete/rename) |
| POST | `/api/v1/files/sync` | Lightweight link-only import (no OCR/classification) |

### Files
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/files/entries/{id}/view` | Serve entry source file inline (scoped to `ALLOWED_ROOTS`) |
| GET | `/api/v1/files/entries/{id}/download` | Force-download entry source file |
| GET | `/api/v1/files/entries/{id}/info` | Entry file metadata |
| GET | `/api/v1/files/chunks/{chunk_id}/view` | Serve AWMF chunk's source PDF inline (scoped to `AWMF_ROOT` = content root `/3_Leitlinien`, distinct from `ALLOWED_ROOTS`) |

### Admin (Classification)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/classify-from-filename` | Deterministic regex classification: Fachgebiet from folder, Diagnose/Symptom from filename, then ICD-11 enrichment via WHO API. Body: `{force, dry_run, limit}`. Instant (~1 s regex, +~17 s ICD-11). |

### ICD-11
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/icd11/token` | OAuth2 token for WHO ICD-11 ECT browser |

### References
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/references` | Parse `~/Dokumente/Medizin/md/medlinks.txt` live into nested sections |

### Summarization
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/entries/{id}/summarize` | Extract and summarize entry file |

## KI Pipeline

### Processing Flow

```
Input File (image/audio/text)
         │
         ▼
┌─────────────────┐
│ File Type Detection │
└─────────────────┘
         │
    ┌────┴────┐
    │          │
 Image      Audio       Text
    │        (link-only,
    │         no extract)
    ▼
┌─────────────────┐
│  OCR (on-demand)│  tesseract local / glm-4.6v remote
│Tesseract/glm-4.6v│  (summarize / /pipeline/process-file only)
└─────────────────┘
         │
         ▼
    Plain Text → summarize
```

LLM classification was removed 2026-09-07. Fachgebiet/Diagnose/Symptom tags come
from folder hierarchy, the admin regex classifier, or manual edits — not from an LLM.

### Folder-Derived Fachgebiet (5_Fächer)

For the `5_Fächer` source (specialty folders), entries derive their **Fachgebiet directly from the top-level subfolder name** — no AI classification required. `FolderHierarchyStrategy.propose` (`api/services/tagging_service.py`) emits a `FACHGEBIET` proposal for the first path segment only (e.g. `5_Fächer/Kardiologie/…` → Fachgebiet "Kardiologie"). Deeper topic/author subfolders remain hierarchy labels and are **not** turned into Fachgebiete. Loose files directly in the source root get no Fachgebiet. This path never
calls an LLM, so it works with Llamaserver down.

### Supported File Types

Extraction is **on demand only** (summarize / `/pipeline/process-file`); ingest
indexes these metadata-only (empty content). Backends are tried in `OCR_BACKENDS`
order.

| Type | Extension | Extraction (on-demand) |
|------|----------|----------|
| Image | PNG, JPG, PDF | `tesseract` (local) / `openrouter-vision` (glm-4.6v) |
| Audio | MP3, WAV, M4A | none — link-only playable entries (whisper removed) |
| Text | TXT, MD | Direct |

## Regex Classification (deterministic, no LLM)

The **"Automatische Klassifizierung"** feature on the Admin page classifies entries
deterministically by regex-matching the folder path and filename against an editable
keyword library — no LLM, instant (~1 s for all 2865 entries), reproducible and idempotent.

### How it works

1. **Fachgebiet** — matched against the folder path (e.g. `5_Fächer/Kardiologie/…` →
   Kardiologie; `SOPs Notaufnahme/…` → Notfallmedizin). For Leitlinien, matched against the
   AWMF topic subfolder name.
2. **Diagnose** — matched against the filename (e.g. `akute-pankreatitis` → Pankreatitis K85).
3. **Symptom** — matched against the filename.
4. **ICD-11 enrichment** — after regex assignment, each diagnosis without an ICD-11 code is
   looked up via the WHO ICD-11 API (OAuth2 client in `api/services/icd11.py`).

### Library file (`data/classification_library.txt`)

One rule per line (`#` = comment), three kinds:

```
F|<keyword>|<display_name>              # Fachgebiet (match against folder path)
D|<keyword>|<display_name>|<ICD-10?>     # Diagnose (match against filename)
S|<keyword>|<display_name>              # Symptom (match against filename)
```

Keywords match case-insensitively as substrings. ~33 Fachgebiete, ~83 Diagnosen, ~17 Symptome
rules currently. Edit the file and re-run Klassifizieren — no restart needed (library reloads
per request).

### API

| Method | Endpoint | Body |
|--------|----------|------|
| POST | `/api/v1/admin/classify-from-filename` | `{force, dry_run, limit}` |

`force=true` reclassifies all entries (clearing stale LLM tags); `force=false` (default) only
touches unclassified entries. `dry_run=true` previews counts without writing.

### Component Locations

| Component | Path | Purpose |
|-----------|------|---------|
| **RegexClassifier** | `api/services/regex_classifier.py` | Core engine, loads library, `classify_all` |
| **Classification library** | `data/classification_library.txt` | Editable keyword rules |
| **ICD-11 client** | `api/services/icd11.py` | WHO API OAuth2 + search |
| **Admin router** | `api/routers/admin.py` | `POST /admin/classify-from-filename` |
| **Admin UI** | `ui/src/routes/admin/+page.svelte` | "Automatische Klassifizierung" box |

## Files stay in the file manager

The UI displays indexed files. Rename and delete happen in the file manager under
`~/Dokumente/Medizin`. The watcher drops the database row when the file is gone
and re-ingests it if the file comes back, so a database-only delete does not stick.

`DELETE /api/v1/entries/{id}` remains for the reconcile path
(`FileSyncService.delete_entry`). The entry page has no Löschen button.

## Rechner Page (Klinische Rechner)

The **"Rechner"** page (`/rechner`, nav: "Referenz" section) links clinical calculators.
Frontend-only, no schema/backend involvement.

- **Tier 2 (curated)**: `ui/src/lib/calculators.ts` — 37 MDCalc deep links
  (stable `/calc/<id>/<slug>` URLs from the favorites export), organized by
  discipline boxes with subgroups (Kardiologie: EKG/Gefäße/Gerinnung;
  Pulmologie: Asthma/COPD/Pneumonie; Allgemein, Notfall, Neurologie, Intensiv,
  Infektiologie, Gastro & Hepatologie, Nephrologie, Labor). New favorites =
  new rows; keywords match German/English terms.
- **Tier 1 (search links)**: any query also renders MDCalc/QxMD search links
  plus matching DB Diagnosen (`GET /diagnosen`) as search-link chips.
- **nieren.app (ÖGN)**: the Nephrologie box also carries two external links
  (`/calculator`, `/guidelines`) — external only, the site forbids iframing
  (`X-Frame-Options: SAMEORIGIN`).

## Notfall Page (Algorithmen)

`/notfall` route (nav "Referenz", lucide `Siren`) — **library-sourced** views
over the corpus, no hard-coded content (`notfall.ts` is gone; only grouping
keywords remain in `ui/src/lib/notfallGroups.ts`). Tabs:

- **Algorithmen** — the md quick-reference docs (BLS, 4H/4T, ABCDE, AMPLE,
  GCS, FAST, Anaphylaxie) in `2_Notfall/00_Notfall_SOPs/md/`, flat list.
  **Curate by editing the md files in that folder** — the watcher ingests
  them, the tab lists them.
- **SOPs** — non-md files (PDF/images) in `2_Notfall/00_Notfall_SOPs`
  (keyword-grouped via `notfallGroups.ts`).
- **SOPs Notaufnahme** — `1_SOPs/SOPs Notaufnahme`.

Files hitting no group rule fall into "Weitere". The red banner on the page is
the medical disclaimer (see 2026-10-21) — keep it.

## Markdown Rendering & Inline Edit

Both the **FileViewer** (linked source file) and the **"Inhalt"** section render markdown.

- **FileViewer** (`ui/src/lib/components/FileViewer.svelte`) — `.md` source files are detected via
  `text/markdown` / `text/x-markdown` mime type, fetched as text, and rendered as formatted markdown
  (`marked` + `isomorphic-dompurify`, sanitized `@html` — same XSS-safe pattern as the Leitlinien RAG
  answer) instead of a raw-text iframe. The file label shows "Markdown".
- **PDF** (FileViewer) — rendered with lazy-loaded **pdf.js** (`pdfjs-dist`,
  worker chunk only fetched when a PDF opens), not an iframe: mobile browsers
  refuse to render PDFs inside iframes. Pages are drawn to canvases in a
  scrollable column, width-fit to the container; re-rendered on container
  resize (fullscreen toggle, rotation); torn down per entry switch and on
  unmount via the loading task (pdf.js v6 API). Errors (password-protected,
  load failure) show a message plus an "Im Tab öffnen" fallback.
- **Mermaid** (`ui/src/lib/mermaid.ts`) — ```mermaid fences in rendered
  markdown (both surfaces) are swapped for inline SVGs after sanitization
  (`mermaid` npm package, `securityLevel: strict`, dark-theme aware); blocks
  that fail to parse keep showing their source.
- **Audio** (FileViewer) — custom player, full-width seek bar (1 s steps),
  ±20 s (`<<` / `>>`), speed 1× / 1,25× / 1,5× / 2×. Native `<audio controls>` was a
  500px-wide strip and unusable on long files. The element stays hidden;
  the browser still range-requests `/files/entries/{id}/view`.
- **Image zoom** (FileViewer) — wheel zooms (1–8×), drag pans when zoomed,
  double-click resets, click toggles the native fullscreen viewer.
- **Inhalt inline edit** (`ui/src/routes/entry/[id]/+page.svelte`) — the **"Bearbeiten"** button
  toggles the rendered markdown to a raw-source textarea with **Speichern** / **Abbrechen** buttons
  (saves `inhalt` via `PUT /entries/{id}`; `inhalt` is reactive `$state` so the edit reflects
  immediately). `renderedInhalt = DOMPurify.sanitize(marked.parse(inhalt))`.

## Transkribieren (OCR text extraction)

The **Transkribieren** button extracts the raw text of a file-backed entry's
linked file via the on-demand OCR seam (tesseract local / openrouter-vision
remote for image & PDF; direct read for text) — **no LLM summarization**. It
is shown in `FileViewer`'s action bar (next to "Herunterladen"), reachable both
on the entry detail page and inside the gallery overlay. It opens
`TranscribeModal`, which runs the extraction and shows the raw text for
viewing/copying.

### User Workflow

1. Open a file-backed entry (detail page or gallery overlay)
2. Click **"Transkribieren"** in the FileViewer action bar
3. Optionally pick an **OCR-Motor** in the modal dropdown
   (Automatisch = OCR_BACKENDS order / Tesseract lokal / glm-4.6v OpenRouter)
4. Click **Transkribieren** to run extraction; the raw text is shown for copying
5. Copy the text (or close) — nothing is written to the entry

### API Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/entries/{id}/transcribe` | Extract entry's linked file text only (no LLM) |

**Request body:** `{ "backend": "tesseract" | "openrouter-vision" | null }` —
null (default) runs the configured `OCR_BACKENDS` seam in order (Auto).

**Response:**
```json
{ "success": true, "extracted_text": "...", "file_type": "image" }
```

Errors: 404 entry/file not found, 400 no linked file, 409/502 no OCR backend
available / backends failed (image/PDF).

### Component Locations

| Component | Path | Purpose |
|-----------|------|---------|
| **TranscribeModal** | `ui/src/lib/components/TranscribeModal.svelte` | OCR-only modal (Motor dropdown, view + copy) |
| **FileViewer** | `ui/src/lib/components/FileViewer.svelte` | "Transkribieren" button |
| **API Router** | `api/routers/summarize.py` | `POST /{entry_id}/transcribe` + `_transcribe_file` helper |
| **Orchestrator** | `pipeline/orchestrator.py` | `detect_file_type()` + `extract_text()` |

### Supported File Types

| Type | Extensions | Extraction Method |
|------|------------|-------------------|
| PDF | `.pdf` | OCR seam (`tesseract`/`openrouter-vision`) — on-demand |
| Images | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff` | OCR seam — on-demand |
| Audio | `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac` | none — link-only playable (whisper removed) |
| Text | `.txt`, `.md` | Direct read |

## Legacy: `/summarize` endpoint (API-only, no UI)

The LLM summarize **UI** was removed 2026-09-07 (replaced by Transkribieren).
The backend `POST /entries/{id}/summarize` endpoint and its skill prompts
(`pipeline/prompts/summarize/*.txt` — studie, leitlinie, screenshot, standard)
remain API-callable for any client that wants extract + LLM summary. The former
`SummaryModal`/`ModelSelector`/`SkillSelector`/`pendingSummary` components were
deleted. Llamaserver-unreachable fallback to OpenRouter DeepSeek applies inside
`summarize_file`.

## Search Implementations

### Keyword Search (default)
- `search/keyword.py`: one boring SQL query — `ILIKE` substring matching over
  `titel`, `zusammenfassung`, `inhalt`, `source_path`/filename, folder segments
  (`source_hierarchy`). Does **not** scan `chunks` (that query pegged CPU on
  ~594k AWMF rows). PDF/passage search is `/search/chunks` (Leitlinien).
- Fixed tier ranking: title (3) > filename (2) = fuzzy title — pg_trgm `%`
  typo tolerance (2) > folder (1.5) > content (1).
- FacetFilters sidebar: collapsible accordion (checkboxes per dimension,
  Apply). Six dimensions. Active-filter chips were added then reverted.
- Endpoint: `GET /api/v1/search?q=&limit=&offset=`.

### Chunk Search / RAG (separate features — do not fold into keyword search)
- `GET /api/v1/search/chunks` — AWMF chunk search, mode via `CHUNK_SEARCH_MODE`:
  `embed` (default, local) = Qwen3 vector search via CPU sidecar;
  `keyword` (VPS) = tsvector full-text over `chunks.search_vector`, no sidecar
  (2 GB box) — needs the chunks text import + GIN index (host deploy notes,
  slice 4b). Item shape is identical in both modes.
- `GET /api/v1/search/chunks/rag` — answer + sources over AWMF chunks. Chat:
  Llamaserver primary, OpenRouter DeepSeek V4 Flash fallback when
  `OPENROUTER_API_KEY` is set.

The former faceted (`v_entry_search` view) and hybrid (alpha-weighted vector)
search were removed 2026-09-01 as dead weight. Drop the view on existing
installations: `DROP VIEW IF EXISTS v_entry_search CASCADE;`.


## User Roles

Removed 2026-08-29 together with auth. Legacy `role` column still exists on the
unused `users` table.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql://... | PostgreSQL connection |
| `LLAMASERVER_API_KEY` | (empty) | Auth key sent as `Authorization: Bearer` to Llamaserver (embeddings, summarize) |
| `LLAMASERVER_URL` | http://localhost:8080 | Llamaserver endpoint |
| `OPENROUTER_DEFAULT_MODEL` | deepseek/deepseek-v4-flash | Default cloud chat model for summarize when none is passed. |
| `OPENROUTER_FALLBACK_MODEL` | deepseek/deepseek-v4-flash | Fallback chat model for chunk RAG + summarize when Llamaserver is unreachable (provider: OpenRouter). |
| `FILE_WRITEBACK_ENABLED` | false | When true, editing a text entry writes the source file (atomic, optimistic hash lock, hash re-stamped — no re-ingest). Off = DB-only edits. |
| `CHUNK_SEARCH_MODE` | embed | `embed` = sidecar vectors (local). `keyword` = tsvector over `chunks.search_vector` (VPS). |
| `API_VERSION` | v1 | API prefix segment — routes mount at `/api/{API_VERSION}` |
| `VITE_DISABLE_LEITLINIEN` | (unset) | Legacy. The Leitlinien page is now enabled on the VPS build (keyword chunk search); do not set this flag anymore. |
| `OCR_BACKENDS` | `[]` | Ordered, comma-separated OCR backends (on-demand image/PDF extraction): `tesseract` (local), `openrouter-vision` (glm-4.6v via `OPENROUTER_API_KEY`). Empty = OCR unavailable. tux and VPS both `tesseract,openrouter-vision` (VPS unit PATH: tesseract5 deu+eng + poppler-utils; venv needs pymupdf ≥1.24.14 for cp313 — keep it in pyproject/uv.lock). |
| `OPENROUTER_VISION_MODEL` | `z-ai/glm-4.6v` | Vision model for the `openrouter-vision` backend. |
| `OCR_REMOTE_TIMEOUT_SECONDS` | 300 | Read timeout for remote OCR (covers multi-page PDFs). |
| `OCR_MAX_PAGES` | 30 | Page cap per remote call; >30-page PDFs are chunked. |

## Development Environment

### Nix Dev Shell (Recommended)

The project includes a Nix flake for reproducible development:

```bash
# Enter dev shell (auto-activates with direnv)
cd medwiss-db

# Or manually
nix develop

# Tools available:
# - Node.js 22 + npm
# - Python 3.12 with all dependencies
# - Docker Compose
# - ruff (Python linter)
```

### One-Command Startup (Recommended)

```bash
# Start all services (PostgreSQL, Llamaserver, FastAPI, SvelteKit)
./start.sh

# Services will be available at:
# - Frontend: http://localhost:5175 (opens automatically in your default browser)
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Llamaserver: http://localhost:8080

# Press Ctrl+C to stop all services
```

### Backend Development

```bash
# Start PostgreSQL
docker-compose up -d

# Run API server
cd medwiss-db
uvicorn api.main:app --reload

# API docs: http://localhost:8000/docs
```

### Frontend Development

```bash
cd medwiss-db/ui
bun install
bun run dev

# Frontend: http://localhost:5175
# Proxies /api to http://localhost:8000
```

### Static Build (Production)

```bash
cd ui
bun run build
# Output in ui/build/
```

Serve with any static file server.

## Design System

### CSS Custom Properties
All frontend pages use consistent design tokens defined in `app.css`:

| Token Category | Examples | Usage |
|----------------|----------|-------|
| Colors | `--color-primary`, `--color-background-primary` | Consistent color palette |
| Spacing | `--space-4`, `--space-6` | Uniform spacing scale |
| Typography | `--font-size-lg`, `--font-weight-semibold` | Text hierarchy |
| Radius | `--radius-lg`, `--radius-xl` | Border consistency |
| Shadows | `--shadow-md`, `--shadow-focus` | Elevation states |

### Page Structure Standard
All pages follow the Search page pattern:
```svelte
<div class="page-container">
  <header class="page-header">
    <h1>Page Title</h1>
    <p class="subtitle">Description</p>
  </header>
  
  <section class="content-section">
    <!-- Content -->
  </section>
</div>
```

### Responsive Breakpoints
- Desktop: > 768px - Full layouts with side-by-side content
- Mobile: ≤ 768px - Stacked layouts, hidden sidebar (bottom nav)

### Collapsible Sidebar
The app sidebar (`ui/src/routes/+layout.svelte`) is collapsible via a toggle button in the header:
- **Expanded**: full 260px nav with labels
- **Collapsed**: icon-only 74px rail (labels & logo text hidden)
- Toggle state is persisted in `localStorage` (`sidebar-collapsed`)
- On mobile (≤ 768px) the collapsed state is ignored; the sidebar is always the full-width bottom nav

## Known Issues

### Infrastructure Requirements
- **Llamaserver** (optional — summarize and chunk RAG): start with
  `./start.sh --qwen` (compose files under `/srv/docker/llamaserver`, together with
  the CPU embedding sidecar on `:8081`). Auth key: `LLAMASERVER_API_KEY`.
- **Embedding sidecar** (`:8081`): needed only for Leitlinien chunk search in
  `embed` mode; the VPS runs `CHUNK_SEARCH_MODE=keyword` instead (no sidecar).
- **PostgreSQL + pgvector**: Required. Library search, tags, and Leitlinien passage search read this index. The source files are not queried live.

### Frontend
- **Svelte Warnings**: Non-blocking warnings present (a11y labels, state_referenced_locally)

### File Sync Notes (files are the library, PostgreSQL is the index)
- `~/Dokumente/Medizin` is the single source of truth (`MEDWISS_CONTENT_ROOT` override; VPS: `/srv/medwiss/Dokumente/Medizin` → symlink to `/srv/medwiss/corpus`). **Read-only to the app** — no code path writes there.
- Local→VPS transport: one-way rsync push, daily `medwiss-sync.timer` + manual `systemctl start medwiss-sync` (corpus sync script on the host; target in `.private/`). Never reverse; no Syncthing.
- The watcher ingests directly (no import jobs); renames (delete+create with same hash) preserve entry ID + manual tags; `on_moved` handles rsync's temp-file rename.
- Update branch refreshes only content/hash/hierarchy labels — manual tag edits are never overwritten (tags assigned on CREATE only).
- Startup reconcile runs in a background thread 2 s after boot and heals drift.

### Implementation Phases
- **Phase 1**: ✅ Complete (Entry Detail View)
- **Phase 2**: ✅ Complete (Batch Import System)
- **Phase 3**: ✅ Complete (CLI Tool)
- **Phase 4**: Pending (Enhanced Entry Management)

See `docs/plans/` for implementation plans.

## Module Documentation

| Module | Documentation | Purpose |
|--------|---------------|---------|
| `api/` | [api/AGENTS.md](api/AGENTS.md) | FastAPI backend conventions |
| `pipeline/` | [pipeline/AGENTS.md](pipeline/AGENTS.md) | AI processing pipeline |
| `ui/src/` | [ui/src/AGENTS.md](ui/src/AGENTS.md) | SvelteKit frontend |
| `search/` | [search/AGENTS.md](search/AGENTS.md) | Search implementations |
| `database/` | [database/AGENTS.md](database/AGENTS.md) | Schema & migrations |
| `scripts/` | [scripts/AGENTS.md](scripts/AGENTS.md) | CLI tools |
| `config/` | [config/AGENTS.md](config/AGENTS.md) | Configuration system |

## Development Commands

### One-Command Startup
```bash
./start.sh  # Starts PostgreSQL, Llamaserver, FastAPI, SvelteKit
```

### Individual Services
```bash
# Database only
docker-compose up -d

# Backend only
uv run uvicorn api.main:app --reload

# Frontend only
cd ui && bun run dev

# Production build
cd ui && bun run build
```

### Lint & Test
```bash
# Python
uv run --extra test pytest

# TypeScript
cd ui && bun run check
```

## Build & Deployment

### Infrastructure
- **PostgreSQL 15 + pgvector** via Docker Compose
- **Llamaserver** (optional, for AI features) at `/app/llama-server`
- **No app containerization** - runs natively with uv/bun

### Nix Dev Shell (Recommended)
```bash
# Auto-activates with direnv, or:
nix develop
```

### Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection | postgresql://... |
| `LLAMASERVER_URL` | LLM endpoint | http://localhost:8080 |
| `LLAMASERVER_API_KEY` | Llamaserver auth | (empty) |
| `VITE_API_URL` | Frontend API URL | http://localhost:8000 |
| `VITE_DISABLE_LEITLINIEN` | Legacy, unused — Leitlinien enabled on VPS via `CHUNK_SEARCH_MODE=keyword`. | (unset) |
| `OCR_BACKENDS` | On-demand OCR backends (image/PDF; empty = unavailable) | `[]` |

## Recent Fixes

Fix history lives in `CHANGELOG.md` — do not add release-era fix notes here.
