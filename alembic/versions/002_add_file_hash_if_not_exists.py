"""Add file_hash column if not exists

Revision ID: 002_add_file_hash_if_not_exists
Revises: 001_add_import_tracking
Create Date: 2026-04-17

"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_add_file_hash_if_not_exists"
down_revision: Union[str, Sequence[str], None] = "001_add_import_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add file_hash column to knowledge_entries if it doesn't exist."""
    # Use DO block to make this idempotent - only adds column if not exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'knowledge_entries'
                AND column_name = 'file_hash'
            ) THEN
                ALTER TABLE knowledge_entries
                ADD COLUMN file_hash VARCHAR(64);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Remove file_hash column (only if exists and no other dependency)."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'knowledge_entries'
                AND column_name = 'file_hash'
            ) THEN
                ALTER TABLE knowledge_entries DROP COLUMN file_hash;
            END IF;
        END $$;
        """
    )
