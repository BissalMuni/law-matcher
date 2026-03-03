"""create law_revision_reasons table

Revision ID: 20260303_000001
Revises: 20260221_needs_revision
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260303_000001"
down_revision = "20260221_needs_revision"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "law_revision_reasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("law_mst", sa.String(length=30), nullable=False),
        sa.Column("revision_reason", sa.Text(), nullable=True),
        sa.Column("amendment_content", sa.Text(), nullable=True),
        sa.Column("extracted_articles", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["law_id"], ["laws.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("law_id", name="uq_law_revision_reasons_law_id"),
    )
    op.create_index(
        "idx_law_revision_reasons_fetched_at",
        "law_revision_reasons",
        ["fetched_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("idx_law_revision_reasons_fetched_at", table_name="law_revision_reasons")
    op.drop_table("law_revision_reasons")
