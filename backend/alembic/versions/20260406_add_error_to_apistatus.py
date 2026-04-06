"""add error value to apistatus enum

Revision ID: 20260406_001
Revises: None
Create Date: 2026-04-06
"""
from alembic import op


revision = "20260406_001"
down_revision = "20260310_reviewed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE apistatus ADD VALUE IF NOT EXISTS 'error'")
    op.execute("ALTER TYPE apistatus ADD VALUE IF NOT EXISTS 'no_change'")


def downgrade() -> None:
    pass
