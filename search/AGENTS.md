# search/ - Search Implementations

> Simple keyword search, AWMF chunk vector search, and chunk RAG.

## OVERVIEW

- `keyword.py`: boring ILIKE substring search over `knowledge_entries` (title, summary, body, source path/filename, folder hierarchy segments). No `chunks` table — a correlated ILIKE EXISTS over ~594k AWMF rows never returns. PDF/chunk search is `/search/chunks` only. Fixed tier ranking: title (3) > filename (2) > folder (1.5) > content (1).
- `chunks.py`: vector search over the `chunks` table (AWMF corpus).
- `rag.py`: question answering over AWMF chunks.

## WHERE TO LOOK

| File | What | Key Patterns |
|------|------|-------------|
| `keyword.py` | Keyword search | Raw SQL via `text()`; `ILIKE` with escaped pattern (`like_pattern()`); entries table only |
| `chunks.py` | Chunk vector search | Instruct-prefix embedding, slice→normalize, HNSW cosine top-k |

## CONVENTIONS

- **Raw SQL via `text()`**: Search modules use SQLAlchemy `text()`, not the ORM.
- **Escape LIKE patterns**: Always route user input through `like_pattern()` (escapes `%`, `_`, `\`) and use `ESCAPE '\'`.
- **No tsvector / no vectors in keyword search**: Keep it a single boring SQL query.

## ANTI-PATTERNS

- **Don't reintroduce faceted/hybrid/FTS machinery**: The tsquery builder, pg_trgm fuzzy union, `v_entry_search` view, and alpha-weighted hybrid search were removed as dead weight (2026-09-01). `/search/chunks` and `/search/chunks/rag` are separate RAG features — leave them alone.
- **Don't assume llamaserver is up**: Only the chunk endpoints need the embedding sidecar; keyword search is pure SQL.
