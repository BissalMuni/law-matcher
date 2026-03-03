"""add revision metadata columns to articles

Revision ID: 20260303_000003
Revises: 20260303_000002
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa


revision = "20260303_000003"
down_revision = "20260303_000002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("articles", sa.Column("revision_type_detail", sa.String(length=50), nullable=True))
    op.add_column("articles", sa.Column("change_flag", sa.String(length=5), nullable=True))


def downgrade():
    op.drop_column("articles", "change_flag")
    op.drop_column("articles", "revision_type_detail")
