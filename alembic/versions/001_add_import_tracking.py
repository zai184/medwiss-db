"""Add import tracking tables and columns

Revision ID: 001_add_import_tracking
Revises:
Create Date: 2026-04-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_add_import_tracking"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add import tracking columns and table."""
    op.create_table(
        "import_jobs",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("total_files", sa.Integer(), server_default="0"),
        sa.Column("processed_files", sa.Integer(), server_default="0"),
        sa.Column("failed_files", sa.Integer(), server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_import_jobs_status", "import_jobs", ["status"])
    op.create_index(
        "idx_import_jobs_started_at", "import_jobs", [sa.literal_column("started_at DESC")]
    )

    op.add_column("knowledge_entries", sa.Column("source_path", sa.Text(), nullable=True))
    op.add_column("knowledge_entries", sa.Column("file_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "knowledge_entries", sa.Column("import_batch_id", postgresql.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_knowledge_entries_import_batch_id",
        "knowledge_entries",
        "import_jobs",
        ["import_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove import tracking columns and table."""
    op.drop_constraint(
        "fk_knowledge_entries_import_batch_id", "knowledge_entries", type_="foreignkey"
    )
    op.drop_column("knowledge_entries", "import_batch_id")
    op.drop_column("knowledge_entries", "file_hash")
    op.drop_column("knowledge_entries", "source_path")
    op.drop_index("idx_import_jobs_started_at", table_name="import_jobs")
    op.drop_index("idx_import_jobs_status", table_name="import_jobs")
    op.drop_table("import_jobs")
