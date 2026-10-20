"""Add awmf_documents + universal chunks tables (AWMF fold-in)

Revision ID: 003_awmf_chunks
Revises: 002_add_file_hash_if_not_exists
Create Date: 2026-08-25

Polymorphic (source_type, source_id) is app-enforced / FK-less by design —
see plans/awmf-foldin-dashboard.md (architecture-rules: follow the unified
embedding rewrite schema; database-rules FK preference noted as tradeoff).
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003_awmf_chunks"
down_revision: Union[str, Sequence[str], None] = "002_add_file_hash_if_not_exists"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create awmf_documents + chunks (HNSW index built post-load in the loader)."""
    # awmf_documents — registry, one row per AWMF PDF
    op.execute(
        """
        DO $awmf$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'awmf_documents') THEN
                CREATE TABLE awmf_documents (
                    id          SERIAL PRIMARY KEY,
                    awmf        TEXT NOT NULL,
                    title       TEXT NOT NULL,
                    society     TEXT NOT NULL,
                    path        TEXT NOT NULL UNIQUE,
                    file_hash   VARCHAR(64),
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            END IF;
        END
        $awmf$;
        """
    )

    # chunks — universal chunk store (source_type='awmf' for now; 'library' when re-embed lands)
    op.execute(
        """
        DO $chunk$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'chunks') THEN
                CREATE TABLE chunks (
                    id          BIGSERIAL PRIMARY KEY,
                    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('library', 'awmf')),
                    source_id   INTEGER NOT NULL,               -- awmf_documents.id | knowledge_entries.id
                    source_path TEXT NOT NULL,                  -- original file path
                    title       TEXT NOT NULL,                  -- denormalized for UI
                    awmf        TEXT,                           -- awmf chunks only
                    society     TEXT,                           -- awmf chunks only
                    page        INTEGER,                        -- awmf chunks only (PDF page)
                    seq         INTEGER NOT NULL,               -- chunk order within doc
                    text        TEXT NOT NULL,
                    embedding   vector(2048) NOT NULL,          -- Qwen3-8B Q6_K, slice→normalize
                    search_vector TSVECTOR,                     -- German FTS, secondary (unused today)
                    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX idx_chunks_source ON chunks (source_type, source_id);
            END IF;
        END
        $chunk$;
        """
    )

    # German FTS search_vector on chunks.text (idempotent — guard on the trigger name)
    op.execute(
        """
        DO $trg$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'chunks_search_vector_update'
            ) THEN
                CREATE FUNCTION chunks_search_vector_update() RETURNS trigger AS $func$
                BEGIN
                    NEW.search_vector := to_tsvector('german', COALESCE(NEW.text, ''));
                    RETURN NEW;
                END
                $func$ LANGUAGE plpgsql;

                CREATE TRIGGER chunks_search_vector_update
                BEFORE INSERT OR UPDATE OF text ON chunks
                FOR EACH ROW EXECUTE FUNCTION chunks_search_vector_update();
            END IF;
        END
        $trg$;
        """
    )


def downgrade() -> None:
    """Drop chunks + awmf_documents (reverse of upgrade)."""
    op.execute("DROP TRIGGER IF EXISTS chunks_search_vector_update ON chunks")
    op.execute("DROP FUNCTION IF EXISTS chunks_search_vector_update()")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS awmf_documents")
