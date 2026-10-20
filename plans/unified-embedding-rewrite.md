# Unified Embedding Rewrite — medwiss-db

**Goal:** transform medwiss-db from a document-level store into a chunk-level, vector-first
knowledge base over **one unified embedding model** (Qwen3-Embedding-8B Q6_K, 2048-dim MRL),
covering both the existing library (`knowledge_entries`) and the AWMF guideline corpus, with
retrieval, a citation-answer chat, and the same search UI. The current document-granularity
design is not more useful than a plain folder structure; chunks become the primary unit.

**Locked decisions (user-specified, 2026-08-24):**
- Re-embed **everything** with Qwen3-8B — one unified model, no 1536-dim leftovers.
- OK to rewrite the library approach of medwiss-db (not just extend it).
- Chat is new (verified: no chat exists today).
- AWMF pipeline core (extract → chunk → embed) is shared with
  `~/Projekte/embeddings/Leitlinien/docs/plans/awmf-embedding-kb-plan.md` (P0–P3); its P6
  fold-in ships the AWMF half into pgvector first.

---

## Environment (verified 2026-08-24)

- **Stack:** FastAPI + SQLAlchemy, PostgreSQL 15 + pgvector, SvelteKit UI (bun), JWT auth,
  alembic (2 revisions: `001_add_import_tracking`, `002_add_file_hash_if_not_exists`).
- **`knowledge_entries`:** document rows with `titel`, `zusammenfassung`, `inhalt`, `quelle`,
  `schwierigkeit`, `unterkategorie`, `dokumenttyp`, `source_hierarchy` JSONB, `source_path`,
  `file_hash`, `import_batch_id`, `search_vector` (trigger from titel A / zusammenfassung B /
  inhalt C), `embedding vector(1536)` with **IVFFLAT `lists=100`**.
- **Classification layer:** `fachgebiete` / `diagnosen` / `symptome` + M2M junction tables;
  `audit_log` trigger on knowledge_entries; view `v_entry_search`.
- **Embeddings today:** `pipeline/embeddings.py` — `EMBEDDING_DIMENSION = 1536`, disk + LRU
  cache, calls the shared llamaserver `/v1/embeddings` (`model: "embedding"`, 8000-char input
  cap). `search/hybrid.py` — FTS `ts_rank` + cosine (`1 - (embedding <=> :v)`) alpha-weighted;
  **graceful FTS-only fallback** when embedding fails.
- **Config:** `llamaserver_url = http://localhost:8080` (shared llama-server, same one the AWMF
  plan uses), `llamaserver_model = qwen35-9b-i` (the daily 9B driver), `LOCAL_API_KEY`.
- **VRAM:** RTX 3070 8 GB; the shared llama-server serves one model at a time. Embedder
  Q6_K = 6.21 GB, 9B fills the rest. Same topology as the AWMF plan: overnight batch pass
  swaps the server to the embedder; query time = CPU sidecar (`--n-gpu-layers 0`, port 8081)
  + 9B in VRAM for chat.
- **AWMF artifacts (from the Leitlinien plan):** `chunks.jsonl` (~340k chunks, metadata incl.
  awmf/society/title/page), `vectors.f32` + `vector_ids.jsonl` (2048-dim, slice→normalize).
  Reusable as-is — no re-embedding for AWMF.

---

## Architecture

```
library files + AWMF PDFs ──extract──▶ text ──chunk──▶ chunks.jsonl
                                                            │
      llama-server (Qwen3-Embedding-8B Q6_K, CUDA) ◀── embed (batch, checkpointed)
                                                            │
                                                            ▼
          PostgreSQL 15 + pgvector: chunks (vector(2048), HNSW) + awmf_documents
                                                            │
       /search (vector primary, FTS boost)   /chat (retrieve → 9B answer, citations)
```

Asymmetric instruction (Qwen3-Embedding, per the AWMF plan P0 gates):
- Documents: **no** prefix — embed raw chunk text.
- Queries: prefix `Instruct: Given a German medical guideline query, retrieve relevant
  guideline passages that answer the query\nQuery: <q>`.
- MRL order everywhere: **slice to 2048, then L2-normalize** (identical on both sides).

---

## Target schema (alembic `003_*`)

`knowledge_entries` **stays as the library document registry** — audit trigger, M2M
classifications, `created_by` and versioning are load-bearing compliance features, not the
"folder" problem. Its `embedding` column is dropped only after the re-embed is verified (R4
gate). AWMF documents get their own registry table; chunks are universal and polymorphic.

```sql
-- AWMF document registry (one row per PDF)
CREATE TABLE awmf_documents (
    id          SERIAL PRIMARY KEY,
    awmf        VARCHAR(20) NOT NULL,          -- e.g. '174-004'
    title       TEXT NOT NULL,
    society     TEXT NOT NULL,                 -- source folder
    path        TEXT NOT NULL UNIQUE,
    file_hash   VARCHAR(64),                   -- SHA-256
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Universal chunk store (library + AWMF)
CREATE TABLE chunks (
    id           BIGSERIAL PRIMARY KEY,
    source_type  VARCHAR(20) NOT NULL CHECK (source_type IN ('library','awmf')),
    source_id    INTEGER NOT NULL,             -- knowledge_entries.id | awmf_documents.id
    source_path  TEXT NOT NULL,                -- original file path
    title        TEXT NOT NULL,                -- denormalized for UI
    awmf         VARCHAR(20),                  -- awmf chunks only
    society      TEXT,                         -- awmf chunks only
    page         INTEGER,                      -- awmf chunks only (PDF page)
    seq          INTEGER NOT NULL,             -- chunk order within doc
    text         TEXT NOT NULL,
    embedding    vector(2048) NOT NULL,        -- Qwen3-8B Q6_K, slice→normalize
    search_vector TSVECTOR,                    -- German FTS, secondary
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,  -- fachgebiete/diagnosen/symptome
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_source   ON chunks (source_type, source_id);
CREATE INDEX idx_chunks_fts      ON chunks USING GIN (search_vector);

-- FTS trigger on chunks.text (pattern: existing update_search_vector)
```

- HNSW, **not** the project's IVFFLAT `lists=100` (degrades at ~340k rows).
- Polymorphic `(source_type, source_id)` has no FK constraint — app-enforced; a trigger can
  verify on insert if needed.
- **Relation to AWMF plan P6:** P6 creates `awmf_chunks` (awmf-only, same shape as `chunks`).
  R1 here absorbs it: `ALTER TABLE awmf_chunks RENAME TO chunks` + add `source_type`,
  `source_id`, `metadata`; existing rows become `source_type='awmf'`. No data movement.

---

## Phases

### R0 — Embedding runtime (~15 min + model download; shared with AWMF plan P0)

1. `Qwen3-Embedding-8B-Q6_K.gguf` (6.21 GB) → `/mnt/data/bin/gguf/embedders/`.
2. `/srv/docker/llamaserver/models/qwen3emb8b.yml` — `--embedding --pooling last
   --ctx-size 8192 --batch-size 4096 --ubatch-size 4096 -ngl 99`, alias `qwen3emb8b`.
3. P0 sanity gate (pooling LAST, dim 4096, similar-pair cosine, MRL order gate) — identical
   to the AWMF plan; the vectors this system stores depend on it.

### R1 — Schema + config (~1–2 h)

1. alembic `003`: `awmf_documents`, `chunks`, HNSW, FTS trigger. Absorb `awmf_chunks` if P6
   already shipped (rename + columns).
2. `api/config.py`: `embedding_url` (default `http://localhost:8081` — the CPU sidecar at
   query time, overridable to 8080 during passes) + `embedding_dimension = 2048`.
3. `pipeline/embeddings.py`: dimension 1536→2048, instruct prefix on **queries** only,
   target `embedding_url`.

### R2 — Library re-embed (pipeline work ~0.5 day; run = library size, hours not overnight)

1. Extract text from `knowledge_entries.inhalt` (+ `zusammenfassung` where inhalt is short).
2. Chunk with the shared heading-aware chunker (~800 chars, ~80 overlap) — add a markdown
   mode for library content; never split drug-dose/symptom lists. Flag <100-char output.
3. Embed (docs raw) → slice 2048 → normalize → INSERT into `chunks`
   (`source_type='library'`, `source_id=ke.id`, metadata from the M2M classifications).
4. Keep `knowledge_entries.embedding` (1536) until the R4 gate.

### R3 — AWMF fold-in (~0.5 day; no re-embed)

1. Load `chunks.jsonl` + `vectors.f32` + `vector_ids.jsonl` (AWMF P2/P3 artifacts) → INSERT
   into `chunks` (`source_type='awmf'`), register PDFs in `awmf_documents`. Bit-identical
   vectors — same model/quant/flags as the P0 gate.
2. Cross-check: chunk count matches `vector_ids.jsonl`; spot-check dims/norms.

### R4 — Search rewrite (~0.5–1 day)

1. `search/chunks.py` (new): embed query (instruct prefix) → HNSW cosine top-k → optional FTS
   alpha boost → return `{source_type, title, awmf, society, page, text, score}`.
2. `/api/v1/search?type=chunks&q=` (new mode in `api/routers/search.py`); keep `fts` /
   `faceted` / `hybrid` untouched (hybrid stays entry-level; chunks mode is the new primary).
3. SvelteKit search page: "Leitlinien & Bibliothek" results mode showing chunk hits with
   source pointers; group-by-document view.
4. **Gate:** HNSW recall vs exact scan on ~100 sampled queries (≥0.95 target); then drop
   `knowledge_entries.embedding` + IVFFLAT index (single source of truth).

### R5 — Chat (new; ~0.5–1 day)

1. `POST /api/v1/chat` `{question}` → SSE stream:
   embed question → HNSW top-k (k=6) → system prompt *"Answer in German, based ONLY on the
   provided context; cite [Quelle, Seite] inline; state it when the context is insufficient"*
   → llamaserver `/v1/chat/completions` (`qwen35-9b-i`, streamed) → answer with citations.
2. SvelteKit `/chat` route: textarea, streaming render, source list (title, awmf, page,
   path). Reuse existing `api.ts`/auth patterns.

### R6 — Verify + eval (~0.5 day + labeling)

1. Labeled eval set (~25 queries → expected AWMF number or entry title), hit@5 / MRR;
   thresholds agreed after the first baseline run (no invented targets).
2. P5 smoke queries from the AWMF plan re-run through `/search?type=chunks`.
3. Query latency (target <1 s retrieval, chat ~10–20 s end-to-end).
4. Docs: update `AGENTS.md`, `README.md`, `CHANGELOG.md`, schema doc.

---

## Migration & rollback

- **Ordered, reversible:** R2 keeps the 1536 column; R4 gate (recall + smoke) must pass
  before dropping it. Rollback = restore column from alembic downgrade.
- **No data loss:** library text stays in `knowledge_entries`; AWMF stays in PDFs +
  `chunks.jsonl`. `chunks` is derived state, rebuildable from the two sources + the embedder.
- **Downtime:** the re-embed pass occupies the shared llamaserver (9B offline) — schedule
  off-hours; checkpoint/resume per AWMF plan P3.

---

## Success criteria

1. Zero 1536-dim vectors remain; every stored vector is Qwen3-8B 2048 (SQL check).
2. `/search?type=chunks` returns hits with source path/page in <1 s (HNSW).
3. `/chat` answers with inline citations, each resolvable to a source document.
4. AWMF + library corpora both queryable through the same endpoints.
5. Eval: hit@5/MRR reported on the labeled set; smoke queries surface the right documents.

## Non-goals

- OCR of scanned PDFs (deferred; flagged in the AWMF plan's `unusable.txt`).
- Audio/image chunking; multi-user chat memory; chat history persistence.
- Rerankers, cross-encoders (possible later knob).
- Cloud GPU on the query path (public documents allow cloud for the batch pass only).

## Risks

| Sev | Risk | Impact | Fix |
|---|---|---|---|
| 🔴 | Re-embed pass takes the shared server — 9B offline | no daily LLM during the pass | schedule off-hours; `./llm` swap back anytime; checkpoint/resume |
| 🟠 | Model change breaks 1536-dim consumers | search returns garbage or errors | dimension + URL change in the same commit; existing FTS fallback stays |
| 🟠 | HNSW recall below exact scan | silent ranking loss | R4 recall gate on sampled queries before dropping IVFFLAT |
| 🟠 | Library chunking quality (markdown/heterogeneous) | weak retrieval on library content | markdown chunker mode; <100-char flag; eval covers library queries |
| 🟡 | Chat answers drift from context | hallucination | retrieve-only context + cite-or-say-insufficient prompt; eval spot-checks |
| 🟡 | alembic migration against live data | broken prod DB | migration on copy first; 1536 column kept until gate |
| 🔵 | Chat latency (9B + sidecar embed) | sluggish UX | stream tokens; measure first token in R6 |

## Relation to the AWMF plan

- Shared: P0 (runtime/gates), P1 (extract), P2 (chunk), P3 (embed pass) — built once in
  `~/Projekte/embeddings/Leitlinien/`, outputs consumed here.
- AWMF plan P6 ships `awmf_chunks` + chunk-search endpoint first; this plan absorbs it in R1
  and generalizes to `chunks` in R2.
- FAISS (AWMF plan P4) remains the standalone validation artifact; pgvector is the product
  surface.

## What's already known to work

- AWMF plan P0–P3 verified: text layers extract, Q6_K runs in the Docker llama-server with
  `--embedding --pooling last`, `/v1/embeddings` endpoint, measured throughput.
- medwiss-db: llamaserver calls (embed/classify/summarize) work against the shared server;
  FTS + vector search + UI exist; graceful fallback pattern proven.
