**Goal:** load the AWMF guideline corpus (594,079 chunks) from the Leitlinien embedding KB into
medwiss-db pgvector, expose a chunk-search endpoint, and surface it as a **dedicated `/leitlinien`
search page** — kept structurally separate from the entry search (`/search`) so the two mechanisms
(entry/FTS vs chunk/vector) don't tangle in one UI.
This is the first executable slice of `plans/unified-embedding-rewrite.md` (its R1 schema + R3
fold-in + R4-subset) — scoped to **AWMF only**; library re-embed (R2) and chat (R5) stay deferred.

---

## Context (verified 2026-08-25)

- **Leitlinien artifacts ready** (deduped, committed `88a4c0d`):
  - `chunks.jsonl` — 594,079 chunks, fields `{id, awmf, title, society, path, page, text, n_chars}`
  - `vectors.f32` — 594,079 × 2048 fp32, L2-normalized (MRL slice→normalize, Qwen3-Embedding-8B Q6_K)
  - `vector_ids.jsonl` — 594,079 ids, positionally aligned to vectors (verified 0 mismatches)
  - `meta.sqlite` — `pdfs` (1,886 rows) + `chunks` tables
  - Location: `~/Projekte/embeddings/Leitlinien/data/`
- **medwiss-db state:**
  - alembic at `002` — no `chunks`/`awmf_documents` table yet
  - `knowledge_entries.embedding vector(1536)` IVFFLAT `lists=100` (unchanged — out of scope)
  - pgvector extension already in use (`database/models.py` imports `pgvector.sqlalchemy.Vector`)
  - search convention: **separate routes** (`/search/faceted`), not `type=` params → chunks follows suit
  - config: `settings.llamaserver_url = :8080` (9B), no embedding-specific URL/dimension
- **Query embedder live:** CPU sidecar on `:8081` (`qwen3emb8b`, `--pooling last`, returns 4096-dim;
  slice→normalize to 2048 at call site). Same model/quant/flags as the indexed vectors → query vectors
  are bit-consistent with the corpus.
- **Instruct prefix (query side only)** — MUST match the corpus' query convention exactly:
  `Instruct: Given a German medical guideline query, retrieve relevant guideline passages that answer the query\nQuery: <q>`

---

## Scope

**In:**
- alembic `003`: `awmf_documents` + universal `chunks` tables, German FTS trigger (HNSW dropped —
  pgvector caps HNSW at 2000 dims; vectors are 2048 → exact `<=>` scan)
- `api/config.py`: `embedding_url` (default `:8081`), `embedding_dimension = 2048`
- Loader `scripts/import_awmf_chunks.py`: 594,079 chunks + 1,886 documents from Leitlinien artifacts
- `search/chunks.py` + `GET /api/v1/search/chunks` + `ChunkResultItem`/`ChunkSearchResponse`
- UI: **dedicated `/leitlinien` search page** (own route, shared `ChunkResults` component + client
  module; the entry search store is NOT touched), dashboard entry point
- Verification (HNSW recall gate, smoke, latency) + tests + docs (CHANGELOG/AGENTS/README)

**Out (deferred to `unified-embedding-rewrite.md`):** library re-embed into `chunks` (R2), dropping
`knowledge_entries.embedding` (R4 gate), chat (R5), FTS boost on chunks, rerankers.

---

## Architecture

```
Leitlinien data/ (chunks.jsonl + vectors.f32 + vector_ids.jsonl)
      │  scripts/import_awmf_chunks.py  (one-off load, medwiss-db venv)
      ▼
PostgreSQL 15 + pgvector:  awmf_documents  +  chunks (vector(2048), exact <=>, source_type='awmf')
      ▲
      │  /api/v1/search/chunks?q=   (query → sidecar :8081 embed → exact cosine top-k)
      │
  SvelteKit /leitlinien — dedicated AWMF search page   +   dashboard quick-entry
```

Schema follows `unified-embedding-rewrite.md` (universal `chunks`, polymorphic source) so the
library re-embed (R2) slots in with no schema change. One amendment to the plan: `chunks` gains
`updated_at` (satisfies `database-rules.md` "every table needs id, created_at, updated_at").

---

## Phases

### F0 — Prereqs (user actions, ~2 min)
1. Start PostgreSQL+pgvector: `cd medwiss-db && docker compose up -d` (user runs docker manually).
2. Sidecar already running on `:8081` (verified). If not: `docker compose -f
   /srv/docker/llamaserver/docker-compose.sidecar.yml up -d`.

### F1 — Schema + config (~1–2 h)
1. **alembic `003_awmf_chunks`** (follow `001`/`002` style, idempotent `DO $$` blocks):
   - `awmf_documents(id, awmf, title, society, path UNIQUE, file_hash, created_at, updated_at)`
   - `chunks(id BIGSERIAL, source_type VARCHAR(20) CHECK IN ('library','awmf'), source_id INT,
     source_path TEXT, title TEXT, awmf VARCHAR(20), society TEXT, page INT, seq INT,
     text TEXT NOT NULL, embedding vector(2048) NOT NULL, search_vector TSVECTOR,
     metadata JSONB DEFAULT '{}', created_at, updated_at)`
   - `idx_chunks_source (source_type, source_id)`; FTS trigger on `text` (German config, pattern of
     existing `update_search_vector`). **No HNSW index**: pgvector HNSW is capped at 2000 dims and
     vectors are 2048 → exact `<=>` scan (594k × 2048, ~sub-second; faster to build & simpler).
   - Polymorphic `(source_type, source_id)` FK-less per unified plan — integrity app-enforced;
     documented decision (database-rules FK preference noted as a tradeoff).
2. **`database/models.py`**: `AWMADocument` + `Chunk` SQLAlchemy models (`pgvector.sqlalchemy.Vector`,
   `Vector(2048)`), mirroring `KnowledgeEntry` conventions.
3. **`api/config.py`**: `embedding_url: str = "http://localhost:8081"`, `embedding_dimension: int = 2048`.

### F2 — Loader: `scripts/import_awmf_chunks.py` (new, medwiss-db venv; ~0.5 day + load run)
Placed in medwiss-db (not `src/load_pgvector.py`) because it needs sqlalchemy+pgvector and the DB
lives here; reads Leitlinien artifacts by path (arg or `LEITLINIEN_DATA` env).
1. Register 1,886 docs from `meta.sqlite` `pdfs` → `awmf_documents`.
2. Stream `chunks.jsonl` + `vectors.f32` (memmap, aligned by `vector_ids.jsonl`) → bulk INSERT
   `chunks` (`source_type='awmf'`, `source_id=awmf_documents.id`, `embedding` from vectors.f32 rows,
   `seq` from id suffix). Batches of ~2,000. **Bit-identical vectors — no re-embedding.**
3. After load: no vector index needed — exact `<=>` scan via `vector_cosine_ops` (pgvector HNSW
   caps at 2000 dims; 2048-dim vectors). 
4. Idempotent: skip if `chunks` already populated (or `--truncate` to reload).

### F3 — Search backend (~0.5 day)
1. **`search/chunks.py`** (new): `embed_query(q)` — instruct prefix + sidecar `:8081` + slice→normalize;
   `search_chunks(q, limit, offset, db)` — SQLAlchemy `Chunk.embedding.cosine_distance(:v)` ordered
   top-k on `source_type='awmf'`; graceful 503 when the sidecar is down (pattern of `search/hybrid.py`).
2. **`api/routers/search.py`**: `GET /search/chunks` (mirrors `/search/faceted` precedent) →
   `ChunkSearchResponse`.
3. **`api/models.py`**: `ChunkResultItem{id, source_type, title, awmf, society, page, text, score,
   source_path, document_id}` + `ChunkSearchResponse{items, total, limit, offset, query}`.
   (Deliberate shape — a chunk is not a `knowledge_entry`; reusing `SearchResponse` would force
   entry-shaped fields and pollute the contract. Justified by `architecture-rules.md` "avoid
   inconsistent response shapes".)

### F4 — UI: dedicated `/leitlinien` page (~0.5 day)

A standalone route, structurally isolated from the entry search — the shared search store is NOT
touched. Shared pieces are factored so nothing is duplicated:
1. **`ui/src/lib/api.ts`**: `ChunkResultItem`/`ChunkSearchResponse` interfaces + `searchChunksApi`
   (reusable client module).
2. **`ui/src/lib/components/ChunkResults.svelte`** (new, shared): render `awmf` badge, `title`,
   `society`, `Seite N`, snippet, score; group-by-document optional; link to source PDF path.
3. **`ui/src/lib/chunkSearch.ts`** (new, shared): page-local chunk search state + query embedding
   calls — NOT wired into `stores/search.ts` (keeps entry-search state clean).
4. **`ui/src/routes/leitlinien/+page.svelte`**: thin page — query box + `ChunkResults`; its own
   history key (`medwiss_leitlinien_history`), no entry filters.
5. **Dashboard `ui/src/routes/+page.svelte`**: quick-action "Leitlinien durchsuchen" → `/leitlinien`
   (and a chunk-count stat if cheap).

The two mechanisms stay visually and structurally separate: `/search` = entries (FTS/faceted/hybrid),
`/leitlinien` = AWMF passages (vector).

### F5 — Verify + docs (~0.5 day)
1. **Data integrity:** `SELECT count(*) FROM chunks` = 594,079; all `source_type='awmf'`; spot-check
   `|embedding| ≈ 1`; every row's `awmf` resolves in `awmf_documents`.
2. **Exact-scan sanity** (HNSW unavailable at 2048 dims): spot-check ranking on ~20 queries against
   the known-good FAISS index results (Leitlinien) — expect agreement since both are exact cosine.
3. **Smoke:** the 5 `eval_queries.jsonl` queries via `/search/chunks`; expected guidelines surface.
4. **Latency:** exact scan ~5 s retrieval + ~1 s sidecar embed ≈ 6 s/query — CANNOT use pgvector
   ANN (HNSW/IVFFLAT cap at 2000 dims; vectors 2048). User accepted ~5 s exact scan (2026-08-25);
   ANN-via-quantization is a future knob without changing stored vectors.
5. **Test:** `tests/test_chunk_search.py` — query embedding contract (dim 2048, normalized, prefix),
   endpoint 503-on-sidecar-down (mock), response shape.
6. **Docs:** medwiss-db `CHANGELOG.md` (v1.13.0, timestamp, LOC added/total), `AGENTS.md` (endpoints +
   schema), `README.md`; fix the stale `src/load_pgvector.py` reference in Leitlinien
   `docs/architecture.md`; update Leitlinien `docs/todo.md` (P6 done).

---

## Migration & rollback

- `chunks`/`awmf_documents` are additive; `knowledge_entries` untouched → rollback = alembic downgrade
  (drop the two tables). No data loss; re-loadable from Leitlinien artifacts.
- Loader is idempotent (`--truncate` to rebuild).
- Migration runs on a copy first per `database-rules.md` (live data).

## Success criteria
1. 594,079 AWMF chunks in pgvector, source_type='awmf', norms ≈ 1, all rows source-resolvable.
2. `GET /api/v1/search/chunks?q="Antikoagulation bei Vorhofflimmern"` → ranked hits with awmf/title/
   society/page in < 1 s (retrieval).
3. Exact-scan ranking agrees with the FAISS baseline on sampled queries (both exact cosine).
4. Dedicated `/leitlinien` page + dashboard entry render results; the entry search store and
   `/search` response shapes are untouched.
5. Tests pass; CHANGELOG/AGENTS updated with timestamp + LOC.

## Optional follow-up (out of scope here)
- **Entry "Hybrid"/"Semantic" tab cleanup** — today it embeds via `settings.llamaserver_url`
  (`:8080`, the 9B) which has no `--embedding` → the tab 503s at query time, and its convention
  (1536-dim, no prefix) differs from the chunk path. Decide: point it at the sidecar (migrate to
  2048 + instruct prefix) or remove it. Kept separate so the chunk feature doesn't depend on it.

## Non-goals
- Library re-embed / 1536-drop / chat / FTS-boost on chunks / rerankers (all in `unified-embedding-rewrite.md`).

## Risks

| Sev | Risk | Impact | Mitigation |
|---|---|---|---|
| 🔴 | DB not up at load time | loader blocks | F0 prereq; user starts docker |
| 🟢 | pgvector HNSW unavailable (2000-dim cap, vectors 2048) | no ANN index | exact `<=>` scan, sub-second at 594k; verified in F5 |
| 🟠 | Instruct-prefix mismatch on query | wrong retrieval | reuse the exact Leitlinien query prefix; unit-test the contract |
| 🟠 | Sidecar down at query time | `/search/chunks` 503 | graceful 503 (hybrid pattern); FTS fallback later |
| 🟡 | Migration on live DB | broken prod | test on copy; additive-only; rollback available |
| 🟡 | `/home` disk during load | loader OOM/ENOSPC | artifacts on /home already (12 GB free); vectors streamed via memmap, not loaded whole |

## Relation to other plans
- `plans/unified-embedding-rewrite.md` — parent vision; this delivers R1+R3+R4-subset (AWMF half).
  R2 (library) and R5 (chat) remain.
- `~/Projekte/embeddings/Leitlinien/docs/plans/awmf-embedding-kb-plan.md` P6 — the fold-in this plan
  implements (corrected loader location + current 594,079 count).
