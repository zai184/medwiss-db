-- 006: Drop the batch-import job stack.
--
-- The filesystem is the source of truth and the SourceWatcher +
-- FileSyncService ingest files directly; ImportJob tracking is gone.
--
-- Order matters: drop the FK on knowledge_entries.import_batch_id first,
-- then the column, then the table and its indexes.

-- 1. FK + column on knowledge_entries
ALTER TABLE knowledge_entries
    DROP CONSTRAINT IF EXISTS knowledge_entries_import_batch_id_fkey;
ALTER TABLE knowledge_entries
    DROP COLUMN IF EXISTS import_batch_id;

-- 2. Indexes on import_jobs
DROP INDEX IF EXISTS idx_import_jobs_status;
DROP INDEX IF EXISTS idx_import_jobs_started_at;

-- 3. Table
DROP TABLE IF EXISTS import_jobs;
