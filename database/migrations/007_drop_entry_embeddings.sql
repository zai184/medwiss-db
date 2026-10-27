-- 007: Drop knowledge_entries.embedding (entry-level vector search).
--
-- Hybrid search over entry embeddings was removed 2026-09-01; the column was
-- still written at ingest and by scripts/generate_embeddings.py, but nothing
-- reads it. chunks.embedding (AWMF Leitlinien search, sidecar 2048) is
-- untouched — pgvector stays installed.
--
-- Run on existing databases: psql -U medwiss -d medwiss < database/migrations/007_drop_entry_embeddings.sql
-- Fresh installs get the reduced schema from database/schema.sql.

DROP INDEX IF EXISTS idx_knowledge_entries_embedding;
ALTER TABLE knowledge_entries DROP COLUMN IF EXISTS embedding;
