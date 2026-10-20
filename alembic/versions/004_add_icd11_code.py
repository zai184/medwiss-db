"""add icd11_code to diagnosen

Revision ID: 004_add_icd11_code
Revises: 003_awmf_chunks
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa

revision = "004_add_icd11_code"
down_revision = "003_awmf_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "diagnosen",
        sa.Column("icd11_code", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("diagnosen", "icd11_code")
