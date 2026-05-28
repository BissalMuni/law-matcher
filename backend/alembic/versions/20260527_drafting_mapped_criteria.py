"""add mapped_criteria to drafting_sections (조문별 적용기준 캐시)

Revision ID: 20260527_mapcrit
Revises: 20260527_drafting
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260527_mapcrit"
down_revision = "20260527_drafting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "drafting_sections",
        sa.Column("mapped_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("drafting_sections", "mapped_criteria")
